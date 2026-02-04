"""Proactive Scan Orchestrator: autonomous agent scans triggered by API.

Directly instantiates agents and calls agent.run(directive_text) — no conductor
routing needed since directives already specify the target agent.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from backend.agents.base import AgentOutput, OnStepCallback
from backend.agents.registry import build_agent_registry
from backend.config import SessionLocal, get_settings
from backend.llm.failover import FailoverLLMClient
from backend.models.governance import AgentFinding, ProactiveScan, SiteIntelligenceBrief
from backend.prompts.manager import get_prompt_manager
from backend.services.alert_service import AlertService
from backend.services.brief_generator import SiteIntelligenceBriefGenerator
from backend.services.dedup_service import FindingDeduplicator
from backend.services.directive_catalog import DirectiveCatalog
from backend.tools.sql_tools import build_tool_registry
from backend.tools.vector_tools import index_finding

logger = logging.getLogger(__name__)


class ProactiveScanOrchestrator:
    """Runs autonomous proactive scans: loads directives, runs agents, deduplicates findings."""

    MAX_CONCURRENCY = 4

    async def run_scan(
        self,
        trigger_type: str = "api",
        agent_filter: list[str] | None = None,
        on_step: OnStepCallback | None = None,
        scan_id: str | None = None,
    ) -> dict:
        """Execute a full proactive scan across all enabled directives.

        1. Create or update ProactiveScan DB record
        2. Load enabled directives (optionally filtered by agent)
        3. Run each (agent, directive) pair with bounded concurrency
        4. Deduplicate findings, create alerts
        5. Generate site intelligence briefs
        6. Update scan record
        """
        scan_id = scan_id or str(uuid.uuid4())

        # ── Phase 1-2: Setup (short-lived DB session) ──
        try:
            directives = self._setup_scan(scan_id, trigger_type, agent_filter)
        except Exception as e:
            logger.error("Scan %s setup failed: %s", scan_id, e, exc_info=True)
            self._mark_scan_failed(scan_id, e)
            return self._failed_result(scan_id, e)

        # Capture date bucket for dedup consistency across the entire scan
        scan_date_bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # ── Phase 3: Run agents (no held DB connection) ──
        try:
            results = await self._run_agents(directives, scan_id, on_step)
        except (Exception, asyncio.CancelledError) as e:
            logger.error("Scan %s agent execution failed: %s", scan_id, e, exc_info=True)
            self._mark_scan_failed(scan_id, e)
            return self._failed_result(scan_id, e)

        # ── Phase 4: Process results (short-lived DB sessions per result) ──
        all_findings, agent_results, alerts_count = self._process_results(
            results, scan_id, scan_date_bucket
        )

        # ── Phase 5: Generate briefs (short-lived DB session) ──
        brief_ids = await self._generate_briefs(scan_id, all_findings)

        # ── Phase 5b: Study-wide synthesis ──
        if all_findings and brief_ids:
            synth_db = SessionLocal()
            try:
                briefs_objs = synth_db.query(SiteIntelligenceBrief).filter(
                    SiteIntelligenceBrief.id.in_(brief_ids)
                ).all()
                brief_gen = SiteIntelligenceBriefGenerator()
                await brief_gen.generate_study_synthesis(scan_id, all_findings, briefs_objs, synth_db)
            except Exception as e:
                logger.error("Study synthesis failed for scan %s: %s", scan_id, e)
            finally:
                synth_db.close()

        # ── Phase 6: Final status update (short-lived DB session) ──
        self._complete_scan(scan_id, agent_results, len(all_findings), alerts_count, brief_ids)

        result = {
            "scan_id": scan_id,
            "status": "completed",
            "findings_count": len(all_findings),
            "alerts_count": alerts_count,
            "briefs_count": len(brief_ids),
            "directives_executed": len(directives),
        }
        logger.info("Scan %s completed: %s", scan_id, result)
        return result

    def _setup_scan(self, scan_id: str, trigger_type: str, agent_filter: list[str] | None) -> list[dict]:
        """Create/update scan record, load directives. Returns directive list."""
        db = SessionLocal()
        try:
            scan = db.query(ProactiveScan).filter_by(scan_id=scan_id).first()
            if scan:
                scan.status = "running"
                scan.started_at = datetime.now(timezone.utc)
            else:
                scan = ProactiveScan(
                    scan_id=scan_id,
                    status="running",
                    trigger_type=trigger_type,
                    started_at=datetime.now(timezone.utc),
                )
                db.add(scan)
            db.commit()

            catalog = DirectiveCatalog()
            directives = catalog.get_enabled_directives()
            if agent_filter:
                directives = [d for d in directives if d["agent_id"] in agent_filter]

            logger.info("Scan %s: %d directives to execute", scan_id, len(directives))

            scan.directives_executed = [
                {"directive_id": d["directive_id"], "agent_id": d["agent_id"]}
                for d in directives
            ]
            db.commit()
            return directives
        finally:
            db.close()

    async def _run_agents(
        self, directives: list[dict], scan_id: str, on_step: OnStepCallback | None
    ) -> list:
        """Run all directive agents with bounded concurrency."""
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENCY)
        settings = get_settings()
        agent_registry = build_agent_registry()

        async def _run_one(directive: dict) -> dict:
            async with semaphore:
                return await self._execute_directive(
                    directive, scan_id, settings, agent_registry, on_step
                )

        return await asyncio.gather(
            *[_run_one(d) for d in directives],
            return_exceptions=True,
        )

    def _process_results(
        self, results: list, scan_id: str, scan_date_bucket: str
    ) -> tuple[list[AgentFinding], list[dict], int]:
        """Deduplicate findings, create alerts. Returns (findings, agent_results, alerts_count)."""
        all_findings: list[AgentFinding] = []
        agent_results = []
        alerts_count = 0
        alert_svc = AlertService()

        for r in results:
            if isinstance(r, Exception):
                logger.error("Directive execution failed: %s", r)
                agent_results.append({"error": str(r)})
                continue

            agent_results.append({
                "directive_id": r["directive_id"],
                "agent_id": r["agent_id"],
                "findings_count": len(r.get("findings", [])),
                "summary": r.get("summary", ""),
            })

            dedup_db = SessionLocal()
            try:
                deduplicator = FindingDeduplicator(dedup_db, date_bucket=scan_date_bucket)
                for f_idx, f_data in enumerate(r.get("findings", [])):
                    finding = deduplicator.persist_finding_if_new(
                        finding_data={
                            "agent_id": r["agent_id"],
                            "finding_type": f_data.get("finding_type", r.get("finding_type", "")),
                            "severity": f_data.get("severity", r.get("severity", "info")),
                            "site_id": f_data.get("site_id"),
                            "summary": f_data.get("finding", f_data.get("summary", "")),
                            "detail": f_data,
                            "confidence": f_data.get("confidence"),
                            "data_signals": r.get("data_signals"),
                            "reasoning_trace": r.get("reasoning_trace"),
                        },
                        scan_id=scan_id,
                        directive_id=r["directive_id"],
                        finding_index=f_idx,
                    )
                    if finding:
                        new_alerts = alert_svc.create_alerts_from_findings(finding.id, dedup_db)
                        alerts_count += len(new_alerts)
                        # Alert commit expires session objects. Refresh before
                        # detaching so brief generator can access attributes.
                        dedup_db.refresh(finding)
                        dedup_db.expunge(finding)
                        all_findings.append(finding)
                        # Index in vector store for context_search tool
                        index_finding(
                            finding_id=finding.id,
                            agent_id=finding.agent_id,
                            summary=finding.summary,
                            detail=f_data,
                            site_id=finding.site_id,
                            finding_type=finding.finding_type,
                            severity=finding.severity,
                        )
            finally:
                dedup_db.close()

        return all_findings, agent_results, alerts_count

    async def _generate_briefs(self, scan_id: str, all_findings: list[AgentFinding]) -> list[int]:
        """Generate site intelligence briefs. Returns list of brief IDs."""
        if not all_findings:
            return []
        brief_db = SessionLocal()
        try:
            brief_gen = SiteIntelligenceBriefGenerator()
            briefs = await brief_gen.generate_briefs(scan_id, all_findings, brief_db)
            return [b.id for b in briefs]
        finally:
            brief_db.close()

    def _complete_scan(
        self, scan_id: str, agent_results: list, findings_count: int,
        alerts_count: int, brief_ids: list[int],
    ) -> None:
        """Mark scan as completed with results."""
        db = SessionLocal()
        try:
            scan = db.query(ProactiveScan).filter_by(scan_id=scan_id).first()
            if scan:
                scan.status = "completed"
                scan.agent_results = agent_results
                scan.findings_count = findings_count
                scan.alerts_count = alerts_count
                scan.brief_ids = brief_ids
                scan.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()

    def _mark_scan_failed(self, scan_id: str, error: Exception) -> None:
        """Mark scan as failed with error detail."""
        db = SessionLocal()
        try:
            scan = db.query(ProactiveScan).filter_by(scan_id=scan_id).first()
            if scan:
                scan.status = "failed"
                scan.error_detail = str(error)[:2000]
                scan.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def _failed_result(scan_id: str, error: Exception) -> dict:
        return {
            "scan_id": scan_id,
            "status": "failed",
            "error": str(error),
            "findings_count": 0,
            "alerts_count": 0,
            "briefs_count": 0,
            "directives_executed": 0,
        }

    async def _execute_directive(
        self,
        directive: dict,
        scan_id: str,
        settings,
        agent_registry,
        on_step: OnStepCallback | None,
    ) -> dict:
        """Execute a single directive: instantiate agent, run PRPA loop."""
        agent_id = directive["agent_id"]
        directive_id = directive["directive_id"]

        agent_cls = agent_registry.get(agent_id)
        if not agent_cls:
            raise ValueError(f"Agent not found in registry: {agent_id}")

        catalog = DirectiveCatalog()
        directive_text = catalog.get_directive_text(directive_id)

        # Each agent gets an isolated DB session (same pattern as ConductorRouter)
        agent_db = SessionLocal()
        try:
            llm = FailoverLLMClient(settings)
            prompts = get_prompt_manager()
            tools = build_tool_registry()

            agent = agent_cls(
                llm_client=llm,
                tool_registry=tools,
                prompt_manager=prompts,
                db_session=agent_db,
            )

            logger.info("Scan %s: running %s with directive %s", scan_id, agent_id, directive_id)
            output: AgentOutput = await agent.run(
                directive_text, session_id=scan_id, on_step=on_step
            )

            return {
                "directive_id": directive_id,
                "agent_id": agent_id,
                "finding_type": output.finding_type,
                "severity": output.severity,
                "summary": output.summary,
                "confidence": output.confidence,
                "findings": output.findings,
                "investigation_complete": output.investigation_complete,
                "data_signals": output.data_signals,
                "reasoning_trace": output.reasoning_trace,
            }
        finally:
            agent_db.close()
