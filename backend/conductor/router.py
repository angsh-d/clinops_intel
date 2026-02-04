"""LLM-driven Conductor: semantic query routing and cross-domain synthesis.

Zero keyword matching. Every routing decision is made by the LLM.
"""

import asyncio
import json
import logging
import uuid

from sqlalchemy.orm import Session

from backend.llm.client import LLMClient
from backend.llm.utils import parse_llm_json
from backend.prompts.manager import PromptManager
from backend.agents.base import AgentOutput, OnStepCallback
from backend.agents.registry import AgentRegistry
from backend.tools.base import ToolRegistry
from backend.tools.vector_tools import index_finding

logger = logging.getLogger(__name__)


class ConductorRouter:
    """Fully LLM-driven conductor: routes queries, runs agents, synthesizes results."""

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_manager: PromptManager,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
    ):
        self.llm = llm_client
        self.prompts = prompt_manager
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry

    async def route_query(self, query: str, session_context: str = "") -> dict:
        """Use LLM to semantically understand and route the query."""
        prompt = self.prompts.render(
            "conductor_route",
            query=query,
            session_context=session_context or "No prior conversation.",
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical operations intelligence conductor. Respond with valid JSON only.",
        )
        try:
            return parse_llm_json(response.text)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Conductor route parse failed: %s — defaulting to data_quality", e)
            return {
                "selected_agents": ["data_quality"],
                "routing_rationale": f"Default routing due to parse error: {e}",
                "signal_summary": "",
                "requires_synthesis": False,
            }

    async def execute_query(
        self,
        query: str,
        session_context: str,
        db_session: Session,
        on_step: OnStepCallback | None = None,
    ) -> dict:
        """Full conductor pipeline: route -> run agents (parallel) -> synthesize."""
        from backend.config import SessionLocal

        query_id = str(uuid.uuid4())

        # 1. Route
        if on_step:
            await on_step("routing", "conductor", {"query": query})
        routing = await self.route_query(query, session_context)
        selected_agents = routing.get("selected_agents", [])
        requires_synthesis = routing.get("requires_synthesis", False)

        signal_detection = routing.get("signal_summary", routing.get("routing_rationale", ""))

        logger.info("Conductor routed to %s (synthesis=%s)", selected_agents, requires_synthesis)

        # 2. Run selected agents — each gets its own DB session for safety
        async def _run_one(agent_id: str) -> tuple[str, AgentOutput | None]:
            agent_cls = self.agent_registry.get(agent_id)
            if not agent_cls:
                logger.warning("Agent %s not found in registry", agent_id)
                return agent_id, None
            # Each agent gets an isolated session to prevent concurrent access issues
            agent_db = SessionLocal()
            try:
                agent = agent_cls(
                    llm_client=self.llm,
                    tool_registry=self.tool_registry,
                    prompt_manager=self.prompts,
                    db_session=agent_db,
                )
                output = await agent.run(query, session_id=query_id, on_step=on_step)
                return agent_id, output
            finally:
                agent_db.close()

        if len(selected_agents) > 1:
            results = await asyncio.gather(
                *[_run_one(aid) for aid in selected_agents],
                return_exceptions=True,
            )
            agent_outputs: dict[str, AgentOutput] = {}
            for r in results:
                if isinstance(r, Exception):
                    logger.error("Agent execution failed: %s", r)
                    continue
                aid, out = r
                if out is not None:
                    agent_outputs[aid] = out
        else:
            agent_outputs = {}
            for aid in selected_agents:
                _, out = await _run_one(aid)
                if out is not None:
                    agent_outputs[aid] = out

        # 2b. Index agent findings in vector store for future context_search
        for aid, out in agent_outputs.items():
            for f_idx, f in enumerate(out.findings or []):
                if isinstance(f, dict):
                    index_finding(
                        finding_id=f"reactive_{query_id}_{aid}_{f_idx}",
                        agent_id=aid,
                        summary=f.get("finding", f.get("summary", out.summary)),
                        detail=f,
                        site_id=f.get("site_id"),
                        finding_type=out.finding_type,
                        severity=f.get("severity", out.severity),
                    )

        # 2c. Adaptive re-routing based on cross_domain_followup
        additional_outputs, reroute_rationale = await self._adaptive_reroute(
            query, agent_outputs, set(selected_agents), on_step
        )
        if additional_outputs:
            agent_outputs.update(additional_outputs)
            # Index new findings
            for aid, out in additional_outputs.items():
                for f_idx, f in enumerate(out.findings or []):
                    if isinstance(f, dict):
                        index_finding(
                            finding_id=f"reactive_{query_id}_{aid}_{f_idx}",
                            agent_id=aid,
                            summary=f.get("finding", f.get("summary", out.summary)),
                            detail=f,
                            site_id=f.get("site_id"),
                            finding_type=out.finding_type,
                            severity=f.get("severity", out.severity),
                        )
            # Force synthesis if rerouting added agents and total > 1
            if len(agent_outputs) > 1:
                requires_synthesis = True

        # 3. Synthesize if multiple agents returned results
        if requires_synthesis and len(agent_outputs) > 1:
            if on_step:
                await on_step("synthesize", "conductor", {"agents": list(agent_outputs.keys())})
            synthesis = await self._synthesize(query, agent_outputs)
        else:
            single_output = next(iter(agent_outputs.values()), None)
            # Build single_domain_findings matching the prompt schema:
            # each entry has agent, site_ids, finding (string), recommendation
            single_findings = []
            if single_output and single_output.findings:
                for f in single_output.findings:
                    if isinstance(f, dict):
                        single_findings.append({
                            "agent": single_output.agent_id,
                            "site_ids": [f.get("site_id")] if f.get("site_id") else [],
                            "finding": f.get("finding") or f.get("summary") or str(f),
                            "recommendation": f.get("recommendation", ""),
                        })
                    else:
                        single_findings.append({
                            "agent": single_output.agent_id,
                            "site_ids": [],
                            "finding": str(f),
                            "recommendation": "",
                        })
            elif single_output:
                single_findings.append({
                    "agent": single_output.agent_id,
                    "site_ids": [],
                    "finding": single_output.summary,
                    "recommendation": "",
                })

            synthesis = {
                "executive_summary": single_output.summary if single_output else "No results.",
                "signal_detection": signal_detection,
                "cross_domain_findings": [],
                "single_domain_findings": single_findings,
                "next_best_actions": [],
                "priority_actions": [],
            }

        # Ensure signal_detection is always present in synthesis
        if "signal_detection" not in synthesis:
            synthesis["signal_detection"] = signal_detection

        return {
            "query_id": query_id,
            "query": query,
            "routing": routing,
            "signal_detection": signal_detection,
            "agent_outputs": {
                aid: {
                    "agent_id": out.agent_id,
                    "finding_type": out.finding_type,
                    "severity": out.severity,
                    "summary": out.summary,
                    "detail": out.detail,
                    "confidence": out.confidence,
                    "reasoning_trace": out.reasoning_trace,
                    "findings": out.findings,
                    "investigation_complete": out.investigation_complete,
                    "remaining_gaps": out.remaining_gaps,
                }
                for aid, out in agent_outputs.items()
            },
            "synthesis": synthesis,
            "adaptive_reroute": {
                "triggered": bool(additional_outputs),
                "agents_added": list(additional_outputs.keys()) if additional_outputs else [],
                "rationale": reroute_rationale,
            },
        }

    async def _adaptive_reroute(
        self,
        query: str,
        agent_outputs: dict[str, AgentOutput],
        already_run: set[str],
        on_step: OnStepCallback | None,
    ) -> tuple[dict[str, AgentOutput], str]:
        """Check cross_domain_followup from completed agents and route additional agents if needed.

        Returns (agent_outputs_dict, rationale_string). Empty dict + empty string if no reroute.
        """
        from backend.config import SessionLocal

        # Collect cross_domain_followup entries from each agent's detail
        followups = []
        for aid, out in agent_outputs.items():
            detail = out.detail if isinstance(out.detail, dict) else {}
            cdf = detail.get("cross_domain_followup", [])
            if isinstance(cdf, list):
                for item in cdf:
                    if isinstance(item, dict) and item.get("question"):
                        followups.append({
                            "original_agent": aid,
                            "question": item["question"],
                            "target_agent": item.get("target_agent"),
                        })

        if not followups:
            return {}, ""

        # Compute available agents
        all_agents = self.agent_registry.list_agents()
        available = [a for a in all_agents if a["agent_id"] not in already_run]
        if not available:
            return {}, ""

        # Ask LLM whether to reroute
        prompt = self.prompts.render(
            "conductor_adaptive_reroute",
            query=query,
            completed_agent_followups=json.dumps(followups, default=str),
            available_agents=json.dumps(available, default=str),
        )

        try:
            response = await self.llm.generate_structured(
                prompt,
                system="You are a clinical operations intelligence conductor. Respond with valid JSON only.",
            )
            decision = parse_llm_json(response.text)
        except Exception as e:
            logger.error("Adaptive reroute LLM call failed: %s", e)
            return {}, ""

        if not decision.get("should_reroute"):
            return {}, ""

        # Cap at 2 additional agents, filter out already-run
        additional_ids = [
            aid for aid in decision.get("additional_agents", [])
            if aid not in already_run
        ][:2]

        if not additional_ids:
            return {}, ""

        rationale = decision.get("routing_rationale", "")
        logger.info("Adaptive reroute: adding agents %s — %s", additional_ids, rationale)

        if on_step:
            await on_step("adaptive_reroute", "conductor", {
                "additional_agents": additional_ids,
                "rationale": rationale,
            })

        # Run each additional agent
        results: dict[str, AgentOutput] = {}
        for aid in additional_ids:
            agent_cls = self.agent_registry.get(aid)
            if not agent_cls:
                continue
            agent_db = SessionLocal()
            try:
                agent = agent_cls(
                    llm_client=self.llm,
                    tool_registry=self.tool_registry,
                    prompt_manager=self.prompts,
                    db_session=agent_db,
                )
                output = await agent.run(query, session_id=str(uuid.uuid4()), on_step=on_step)
                results[aid] = output
            except Exception as e:
                logger.error("Adaptive reroute agent %s failed: %s", aid, e)
            finally:
                agent_db.close()

        return results, rationale

    async def _synthesize(self, query: str, agent_outputs: dict[str, AgentOutput]) -> dict:
        """Cross-domain synthesis: LLM identifies shared root causes across agents."""
        data_quality_findings = ""
        enrollment_funnel_findings = ""
        clinical_trials_gov_findings = ""
        phantom_compliance_findings = ""
        site_rescue_findings = ""
        vendor_performance_findings = ""
        financial_intelligence_findings = ""

        for aid, out in agent_outputs.items():
            data = json.dumps({
                "summary": out.summary,
                "findings": out.findings,
                "detail": out.detail,
                "agent_confidence": out.confidence,
                "severity": out.severity,
                "investigation_complete": out.investigation_complete,
                "remaining_gaps": out.remaining_gaps,
            }, default=str)
            if aid == "data_quality":
                data_quality_findings = data
            elif aid == "enrollment_funnel":
                enrollment_funnel_findings = data
            elif aid == "clinical_trials_gov":
                clinical_trials_gov_findings = data
            elif aid == "phantom_compliance":
                phantom_compliance_findings = data
            elif aid == "site_rescue":
                site_rescue_findings = data
            elif aid == "vendor_performance":
                vendor_performance_findings = data
            elif aid == "financial_intelligence":
                financial_intelligence_findings = data

        prompt = self.prompts.render(
            "conductor_synthesize",
            query=query,
            data_quality_findings=data_quality_findings or "Not invoked.",
            enrollment_funnel_findings=enrollment_funnel_findings or "Not invoked.",
            clinical_trials_gov_findings=clinical_trials_gov_findings or "Not invoked.",
            phantom_compliance_findings=phantom_compliance_findings or "Not invoked.",
            site_rescue_findings=site_rescue_findings or "Not invoked.",
            vendor_performance_findings=vendor_performance_findings or "Not invoked.",
            financial_intelligence_findings=financial_intelligence_findings or "Not invoked.",
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical operations intelligence synthesizer. Respond with valid JSON only.",
        )
        try:
            return parse_llm_json(response.text)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Synthesis parse failed: %s", e)
            return {
                "executive_summary": "Synthesis could not be completed.",
                "signal_detection": "",
                "cross_domain_findings": [],
                "single_domain_findings": [],
                "next_best_actions": [],
                "priority_actions": [],
                "error": str(e),
            }
