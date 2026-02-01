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
            logger.error("Conductor route parse failed: %s — defaulting to agent_1", e)
            return {
                "selected_agents": ["agent_1"],
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
                }
                for aid, out in agent_outputs.items()
            },
            "synthesis": synthesis,
        }

    async def _synthesize(self, query: str, agent_outputs: dict[str, AgentOutput]) -> dict:
        """Cross-domain synthesis: LLM identifies shared root causes across agents."""
        agent1_findings = ""
        agent3_findings = ""

        for aid, out in agent_outputs.items():
            data = json.dumps({
                "summary": out.summary,
                "findings": out.findings,
                "detail": out.detail,
            }, default=str)
            if aid == "agent_1":
                agent1_findings = data
            elif aid == "agent_3":
                agent3_findings = data

        prompt = self.prompts.render(
            "conductor_synthesize",
            query=query,
            agent1_findings=agent1_findings or "Not invoked.",
            agent3_findings=agent3_findings or "Not invoked.",
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
