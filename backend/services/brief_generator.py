"""Site Intelligence Brief Generator: synthesizes per-site briefs from proactive scan findings."""

import json
import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.llm.failover import FailoverLLMClient
from backend.llm.utils import parse_llm_json
from backend.models.governance import AgentFinding, ProactiveScan, SiteIntelligenceBrief
from backend.prompts.manager import get_prompt_manager

logger = logging.getLogger(__name__)


class SiteIntelligenceBriefGenerator:
    """Generates per-site intelligence briefs from proactive scan findings."""

    async def generate_briefs(
        self,
        scan_id: str,
        findings: list[AgentFinding],
        db: Session,
    ) -> list[SiteIntelligenceBrief]:
        """Group findings by site, synthesize per-site briefs via LLM."""
        # Group findings by site_id
        by_site: dict[str, list[AgentFinding]] = defaultdict(list)
        for f in findings:
            site_key = f.site_id or "STUDY"
            by_site[site_key].append(f)

        if not by_site:
            return []

        settings = get_settings()
        llm = FailoverLLMClient(settings)
        prompts = get_prompt_manager()
        briefs = []
        failed_sites = []

        for site_id, site_findings in by_site.items():
            try:
                brief = await self._generate_one_brief(
                    scan_id, site_id, site_findings, llm, prompts, db
                )
                if brief:
                    briefs.append(brief)
            except Exception as e:
                logger.error("Brief generation failed for site %s: %s", site_id, e)
                failed_sites.append({"site_id": site_id, "error": str(e)})

        if failed_sites:
            logger.warning(
                "Brief generation failed for %d/%d sites in scan %s: %s",
                len(failed_sites), len(by_site), scan_id, failed_sites,
            )
        logger.info("Generated %d site intelligence briefs for scan %s", len(briefs), scan_id)
        return briefs

    async def _generate_one_brief(
        self,
        scan_id: str,
        site_id: str,
        findings: list[AgentFinding],
        llm,
        prompts,
        db: Session,
    ) -> SiteIntelligenceBrief | None:
        """Generate a single site intelligence brief."""
        # Format findings by agent for the prompt
        findings_by_agent: dict[str, list[dict]] = defaultdict(list)
        for f in findings:
            findings_by_agent[f.agent_id].append({
                "finding_type": f.finding_type,
                "severity": f.severity,
                "summary": f.summary,
                "confidence": f.confidence,
                "detail": f.detail,
            })

        findings_json = json.dumps(findings_by_agent, default=str)

        prompt = prompts.render(
            "proactive_site_brief",
            site_id=site_id,
            findings_by_agent=findings_json,
            findings_count=str(len(findings)),
        )

        response = await llm.generate_structured(
            prompt,
            system="You are a clinical operations intelligence analyst. Respond with valid JSON only.",
        )

        try:
            parsed = parse_llm_json(response.text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Brief LLM parse failed for site %s: %s", site_id, e)
            return None

        # Extract contributing agents from findings
        agent_map = {}
        for f in findings:
            if f.agent_id and f.agent_id not in agent_map:
                agent_map[f.agent_id] = {
                    "name": f.agent_id,
                    "role": self._get_agent_role(f.agent_id),
                }
        contributing_agents = list(agent_map.values()) if agent_map else None

        # Build investigation steps from findings reasoning traces
        investigation_steps = []
        seen_steps = set()  # Deduplicate steps
        for f in findings:
            if f.reasoning_trace and isinstance(f.reasoning_trace, dict):
                steps = f.reasoning_trace.get("steps", [])
                for step in steps:
                    # Create a unique key to deduplicate
                    step_key = (step.get("tool", ""), step.get("step", "")[:50])
                    if step_key not in seen_steps:
                        seen_steps.add(step_key)
                        investigation_steps.append({
                            "icon": step.get("icon", "search"),
                            "step": step.get("step", "Analyzed data"),
                            "tool": step.get("tool"),
                            "success": step.get("success", True),
                            "row_count": step.get("row_count"),
                        })
        # Limit to 10 most relevant steps for display
        if investigation_steps:
            investigation_steps = investigation_steps[:10]
        else:
            investigation_steps = None

        brief = SiteIntelligenceBrief(
            scan_id=scan_id,
            site_id=site_id,
            risk_summary=parsed.get("risk_summary"),
            vendor_accountability=parsed.get("vendor_accountability"),
            cross_domain_correlations=parsed.get("cross_domain_correlations"),
            recommended_actions=parsed.get("recommended_actions"),
            trend_indicator=parsed.get("trend_indicator", "stable"),
            agent="proactive_briefing_agent",
            contributing_agents=contributing_agents,
            investigation_steps=investigation_steps,
        )
        db.add(brief)
        db.commit()
        db.refresh(brief)
        logger.info("Created brief id=%d for site %s (scan %s)", brief.id, site_id, scan_id)
        return brief

    def _get_agent_role(self, agent_id: str) -> str:
        """Get human-readable role description for an agent."""
        roles = {
            "enrollment_agent": "Enrollment & Recruitment Analysis",
            "data_quality_agent": "Data Quality Monitoring",
            "financial_agent": "Financial & Budget Analysis",
            "data_integrity_agent": "Data Integrity & Fraud Detection",
            "vendor_agent": "Vendor Performance Tracking",
            "site_health_agent": "Site Health Assessment",
            "phantom_compliance": "Compliance & Fraud Detection",
        }
        return roles.get(agent_id, "Analysis & Investigation")

    async def generate_study_synthesis(
        self,
        scan_id: str,
        findings: list[AgentFinding],
        briefs: list[SiteIntelligenceBrief],
        db: Session,
    ) -> dict | None:
        """Generate study-wide cross-domain synthesis from all findings and briefs."""
        if not findings:
            return None

        settings = get_settings()
        llm = FailoverLLMClient(settings)
        prompts = get_prompt_manager()

        # Group findings by agent_id
        findings_by_agent: dict[str, list[dict]] = defaultdict(list)
        for f in findings:
            findings_by_agent[f.agent_id or "unknown"].append({
                "site_id": f.site_id,
                "severity": f.severity,
                "summary": f.summary,
                "confidence": f.confidence,
            })

        # Summarize briefs
        briefs_summary = []
        for b in briefs:
            risk = b.risk_summary or {}
            briefs_summary.append({
                "site_id": b.site_id,
                "risk_level": risk.get("overall_risk", "unknown"),
                "headline": risk.get("headline"),
                "cross_domain_correlations": b.cross_domain_correlations,
                "trend": b.trend_indicator,
            })

        prompt = prompts.render(
            "proactive_study_synthesis",
            findings_by_agent=json.dumps(findings_by_agent, default=str),
            site_briefs_summary=json.dumps(briefs_summary, default=str),
        )

        try:
            response = await llm.generate_structured(
                prompt,
                system="You are a clinical operations intelligence analyst. Respond with valid JSON only.",
            )
            parsed = parse_llm_json(response.text)
        except Exception as e:
            logger.error("Study synthesis LLM call failed for scan %s: %s", scan_id, e)
            return None

        # Store in ProactiveScan record
        scan = db.query(ProactiveScan).filter_by(scan_id=scan_id).first()
        if scan:
            scan.study_synthesis = parsed
            db.commit()
            logger.info("Stored study synthesis for scan %s", scan_id)

        return parsed
