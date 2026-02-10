"""BaseAgent with PRPA (Perceive-Reason-Plan-Act-Reflect) loop."""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from sqlalchemy.orm import Session

from backend.llm.client import LLMClient
from backend.llm.utils import parse_llm_json, safe_json_str
from backend.tools.base import ToolRegistry
from backend.prompts.manager import PromptManager

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Mutable context flowing through the PRPA loop."""
    query: str
    session_id: str
    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    perceptions: dict = field(default_factory=dict)
    hypotheses: list = field(default_factory=list)
    plan_steps: list = field(default_factory=list)
    action_results: list = field(default_factory=list)
    reflection: dict = field(default_factory=dict)
    is_goal_satisfied: bool = False
    iteration: int = 0
    max_iterations: int = 3
    reasoning_trace: list = field(default_factory=list)
    investigation_steps: list = field(default_factory=list)  # Detailed tool invocations for UI display


@dataclass
class AgentOutput:
    """Structured output from an agent run."""
    agent_id: str
    finding_type: str
    severity: str
    summary: str
    detail: dict
    data_signals: dict
    reasoning_trace: dict  # Changed to dict with "phases" and "steps" keys
    confidence: float
    findings: list = field(default_factory=list)
    investigation_complete: bool = True
    remaining_gaps: list = field(default_factory=list)


# Type for the on_step callback used for WebSocket streaming
OnStepCallback = Callable[[str, str, Any], Coroutine[Any, Any, None]]


class BaseAgent(ABC):
    """Abstract agent implementing the PRPA reasoning loop.

    Subclasses implement perceive() for their domain. The reason/plan/act/reflect
    and _build_output methods have concrete defaults that use class-level
    configuration attributes. Subclasses can override any method if needed.

    The on_step callback is invoked at each phase for WebSocket streaming.
    """

    agent_id: str = ""
    agent_name: str = ""
    description: str = ""

    # Subclass configuration for the default reason/plan/reflect/_build_output
    finding_type: str = ""
    prompt_prefix: str = ""
    system_prompt_reason: str = ""
    system_prompt_plan: str = ""
    system_prompt_reflect: str = ""
    fallback_summary: str = "No significant issues detected."

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        prompt_manager: PromptManager,
        db_session: Session,
        fast_llm_client: LLMClient | None = None,
    ):
        self.llm = llm_client
        self.fast_llm = fast_llm_client or llm_client
        self.tools = tool_registry
        self.prompts = prompt_manager
        self.db = db_session

    async def run(
        self,
        query: str,
        session_id: str,
        on_step: OnStepCallback | None = None,
    ) -> AgentOutput:
        """Execute the PRPA loop until goal satisfied or max iterations reached."""
        ctx = AgentContext(query=query, session_id=session_id)
        logger.info("[%s] Starting PRPA loop for query: %s", self.agent_id, query[:100])

        # Wrap on_step to be resilient to WebSocket disconnects
        safe_on_step = self._make_safe_callback(on_step) if on_step else None

        while not ctx.is_goal_satisfied and ctx.iteration < ctx.max_iterations:
            ctx.iteration += 1
            logger.info("[%s] PRPA iteration %d/%d", self.agent_id, ctx.iteration, ctx.max_iterations)

            # ── PERCEIVE ──
            if safe_on_step:
                await safe_on_step("perceive", self.agent_id, {"iteration": ctx.iteration})
            ctx.perceptions = await self.perceive(ctx)
            if safe_on_step:
                await safe_on_step("perceive_done", self.agent_id, {
                    "iteration": ctx.iteration,
                    "tables_queried": list(ctx.perceptions.keys()) if isinstance(ctx.perceptions, dict) else [],
                })
            ctx.reasoning_trace.append({"phase": "perceive", "iteration": ctx.iteration, "summary": f"Gathered {len(str(ctx.perceptions))} chars of signals"})

            # ── REASON ──
            if safe_on_step:
                await safe_on_step("reason", self.agent_id, {"iteration": ctx.iteration})
            ctx.hypotheses = await self.reason(ctx)
            if safe_on_step:
                _non_dict = [h for h in ctx.hypotheses if not isinstance(h, dict)]
                if _non_dict:
                    logger.warning("[%s] reason_done: %d non-dict hypotheses dropped", self.agent_id, len(_non_dict))
                await safe_on_step("reason_done", self.agent_id, {
                    "iteration": ctx.iteration,
                    "hypotheses": [
                        {
                            "id": h.get("hypothesis_id", f"H{i+1}"),
                            "description": h.get("description", ""),
                            "site_ids": h.get("site_ids", []),
                            "causal_chain": h.get("causal_chain", ""),
                            "confidence": h.get("confidence", 0),
                        }
                        for i, h in enumerate(ctx.hypotheses)
                        if isinstance(h, dict)
                    ],
                })
            ctx.reasoning_trace.append({"phase": "reason", "iteration": ctx.iteration, "hypotheses_count": len(ctx.hypotheses)})

            # ── PLAN ──
            if safe_on_step:
                await safe_on_step("plan", self.agent_id, {"iteration": ctx.iteration})
            ctx.plan_steps = await self.plan(ctx)
            if safe_on_step:
                _non_dict = [s for s in ctx.plan_steps if not isinstance(s, dict)]
                if _non_dict:
                    logger.warning("[%s] plan_done: %d non-dict plan_steps dropped", self.agent_id, len(_non_dict))
                await safe_on_step("plan_done", self.agent_id, {
                    "iteration": ctx.iteration,
                    "plan_steps": [
                        {
                            "tool_name": s.get("tool_name", ""),
                            "purpose": s.get("purpose", ""),
                            "hypothesis_ids": s.get("hypothesis_ids", []),
                        }
                        for s in ctx.plan_steps
                        if isinstance(s, dict)
                    ],
                })
            ctx.reasoning_trace.append({"phase": "plan", "iteration": ctx.iteration, "steps_count": len(ctx.plan_steps)})

            # ── ACT ──
            if safe_on_step:
                await safe_on_step("act", self.agent_id, {"iteration": ctx.iteration})
            results = await self.act(ctx)
            ctx.action_results.extend(results)
            if safe_on_step:
                _non_dict = [r for r in results if not isinstance(r, dict)]
                if _non_dict:
                    logger.warning("[%s] act_done: %d non-dict action results dropped", self.agent_id, len(_non_dict))
                await safe_on_step("act_done", self.agent_id, {
                    "iteration": ctx.iteration,
                    "action_results": [
                        {
                            "tool_name": r.get("tool_name", ""),
                            "purpose": r.get("purpose", ""),
                            "success": r.get("success", False),
                            "row_count": r.get("row_count", 0),
                        }
                        for r in results
                        if isinstance(r, dict)
                    ],
                })
            ctx.reasoning_trace.append({"phase": "act", "iteration": ctx.iteration, "results_count": len(results)})

            # ── REFLECT ──
            if safe_on_step:
                await safe_on_step("reflect", self.agent_id, {"iteration": ctx.iteration})
            ctx.reflection = await self.reflect(ctx)
            ctx.is_goal_satisfied = ctx.reflection.get("is_goal_satisfied", False)
            if safe_on_step:
                await safe_on_step("reflect_done", self.agent_id, {
                    "iteration": ctx.iteration,
                    "goal_satisfied": ctx.is_goal_satisfied,
                    "should_iterate": ctx.reflection.get("should_iterate", False),
                    "remaining_gaps": ctx.reflection.get("remaining_gaps", []),
                    "iteration_focus": ctx.reflection.get("iteration_focus", ""),
                    "findings_count": len(ctx.reflection.get("findings_summary", [])),
                })
            ctx.reasoning_trace.append({"phase": "reflect", "iteration": ctx.iteration, "goal_satisfied": ctx.is_goal_satisfied})

        output = await self._build_output(ctx)
        output.investigation_complete = ctx.is_goal_satisfied
        output.remaining_gaps = ctx.reflection.get("remaining_gaps", [])
        logger.info("[%s] Completed in %d iterations, findings: %d, satisfied: %s", self.agent_id, ctx.iteration, len(output.findings), ctx.is_goal_satisfied)
        return output

    @staticmethod
    def _make_safe_callback(on_step: OnStepCallback) -> OnStepCallback:
        """Wrap on_step to swallow errors (e.g., WebSocket disconnect)."""
        async def safe(phase: str, agent_id: str, data: Any):
            try:
                await on_step(phase, agent_id, data)
            except Exception:
                logger.warning("on_step callback failed for %s/%s — continuing agent execution", agent_id, phase)
        return safe

    # ── PERCEIVE (abstract — each agent must implement) ──

    @abstractmethod
    async def perceive(self, ctx: AgentContext) -> dict:
        """Gather raw data signals broadly."""
        ...

    # ── REASON (concrete default — uses prompt_prefix + system_prompt_reason) ──

    async def reason(self, ctx: AgentContext) -> list:
        """LLM-driven hypothesis generation from perceptions."""
        logger.info("[%s] REASON: generating hypotheses via LLM", self.agent_id)

        site_directory = json.dumps(
            [{"site_id": s["site_id"], "name": s["name"]}
             for s in ctx.perceptions.get("site_metadata", [])
             if isinstance(s, dict) and "site_id" in s and "name" in s],
            default=str,
        )

        prompt = self.prompts.render(
            f"{self.prompt_prefix}_reason",
            perceptions=self._safe_json_str(ctx.perceptions),
            query=ctx.query,
            site_directory=site_directory,
        )
        response = await self.llm.generate_structured(
            prompt,
            system=self.system_prompt_reason,
        )
        try:
            parsed = self._parse_json(response.text)
            hypotheses = parsed.get("hypotheses", [])
            logger.info("[%s] REASON: generated %d hypotheses", self.agent_id, len(hypotheses))
            return hypotheses
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] REASON: failed to parse LLM response: %s\nRaw text: %s", self.agent_id, e, response.text[:500])
            raise RuntimeError(f"[{self.agent_id}] REASON phase failed to parse LLM response: {e}") from e

    # ── PLAN (concrete default — uses prompt_prefix + system_prompt_plan) ──

    async def plan(self, ctx: AgentContext) -> list:
        """LLM-driven investigation plan — the LLM chooses tools and order."""
        logger.info("[%s] PLAN: generating investigation plan via LLM", self.agent_id)

        prompt = self.prompts.render(
            f"{self.prompt_prefix}_plan",
            hypotheses=self._safe_json_str(ctx.hypotheses),
            tool_descriptions=self.tools.list_tools_text(),
            prior_results=self._safe_json_str(ctx.action_results) if ctx.iteration > 1 else "First iteration — no prior results.",
            iteration=str(ctx.iteration),
            reflection_gaps=self._safe_json_str(ctx.reflection.get("remaining_gaps", [])) if ctx.iteration > 1 else "N/A",
        )
        response = await self.fast_llm.generate_structured(
            prompt,
            system=self.system_prompt_plan,
        )
        try:
            parsed = self._parse_json(response.text)
            steps = parsed.get("plan_steps", [])
            logger.info("[%s] PLAN: %d investigation steps planned", self.agent_id, len(steps))
            return steps
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] PLAN: failed to parse LLM response: %s", self.agent_id, e)
            return []

    # ── ACT (concrete default — identical across all agents) ──

    async def act(self, ctx: AgentContext) -> list:
        """Execute each LLM-planned tool invocation."""
        logger.info("[%s] ACT: executing %d planned steps", self.agent_id, len(ctx.plan_steps))
        results = []

        for step in ctx.plan_steps:
            tool_name = step.get("tool_name", "")
            tool_args = step.get("tool_args", {})
            purpose = step.get("purpose", "")
            hypothesis_ids = step.get("hypothesis_ids", [])
            logger.info("[%s] ACT: invoking %s for: %s", self.agent_id, tool_name, purpose)

            result = await self.tools.invoke(tool_name, self.db, **tool_args)
            results.append({
                "step_id": step.get("step_id"),
                "tool_name": tool_name,
                "purpose": purpose,
                "success": result.success,
                "data": result.data,
                "row_count": result.row_count,
                "error": result.error,
            })

            # Capture detailed investigation step for UI display
            ctx.investigation_steps.append({
                "icon": self._get_tool_icon(tool_name),
                "step": purpose if purpose else f"Analyzed data using {tool_name}",
                "tool": tool_name,
                "success": result.success,
                "row_count": result.row_count,
                "iteration": ctx.iteration,
                "hypothesis_ids": hypothesis_ids,
            })

        return results

    def _get_tool_icon(self, tool_name: str) -> str:
        """Get an icon for a tool based on its name."""
        icons = {
            "entry_lag_analysis": "clock",
            "query_burden": "help-circle",
            "monitoring_visit_history": "calendar",
            "monitoring_visit_report": "file-text",
            "cra_assignment_history": "users",
            "data_correction_analysis": "edit-3",
            "screening_funnel": "filter",
            "enrollment_velocity": "trending-up",
            "screen_failure_root_cause": "alert-triangle",
            "site_summary": "map-pin",
            "regional_comparison": "globe",
            "budget_variance_analysis": "dollar-sign",
            "cost_per_patient_analysis": "pie-chart",
            "burn_rate_projection": "activity",
            "vendor_kpi_analysis": "bar-chart-2",
            "vendor_issue_log": "alert-circle",
            "vendor_milestone_tracker": "flag",
            "data_variance_analysis": "bar-chart",
            "weekday_entry_pattern": "calendar",
            "entry_date_clustering": "grid",
            "cra_portfolio_analysis": "briefcase",
            "cra_oversight_gap": "eye-off",
            "correction_provenance": "git-commit",
            "query_lifecycle_anomaly": "rotate-cw",
            "context_search": "search",
            "study_operational_snapshot": "activity",
            "visit_compliance_analysis": "check-square",
            "overdue_action_summary": "alert-octagon",
            "mvr_narrative_search": "file-text",
            "mvr_cra_portfolio": "briefcase",
            "mvr_recurrence_analysis": "repeat",
            "mvr_temporal_pattern": "trending-up",
            "mvr_cross_site_comparison": "bar-chart-2",
        }
        return icons.get(tool_name, "search")

    # ── REFLECT (concrete default — uses prompt_prefix + system_prompt_reflect) ──

    async def reflect(self, ctx: AgentContext) -> dict:
        """LLM evaluates whether the investigation reached root cause."""
        logger.info("[%s] REFLECT: evaluating completeness via LLM", self.agent_id)

        prompt = self.prompts.render(
            f"{self.prompt_prefix}_reflect",
            query=ctx.query,
            hypotheses=self._safe_json_str(ctx.hypotheses),
            action_results=self._safe_json_str(ctx.action_results),
            iteration=str(ctx.iteration),
            max_iterations=str(ctx.max_iterations),
        )
        response = await self.fast_llm.generate_structured(
            prompt,
            system=self.system_prompt_reflect,
        )
        try:
            parsed = self._parse_json(response.text)
            logger.info("[%s] REFLECT: goal_satisfied=%s, findings=%d",
                        self.agent_id,
                        parsed.get("is_goal_satisfied"),
                        len(parsed.get("findings_summary", [])))
            return parsed
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] REFLECT: failed to parse: %s\nRaw text: %s", self.agent_id, e, response.text[:500])
            raise RuntimeError(f"[{self.agent_id}] REFLECT phase failed to parse LLM response: {e}") from e

    # ── BUILD OUTPUT (concrete default — uses finding_type + fallback_summary) ──

    async def _build_output(self, ctx: AgentContext) -> AgentOutput:
        """Build structured output from the completed PRPA context."""
        findings_raw = ctx.reflection.get("findings_summary", [])
        # Guard against non-dict items (LLM sometimes returns nested lists)
        findings = [f for f in findings_raw if isinstance(f, dict)]
        if len(findings) < len(findings_raw):
            logger.warning("[%s] _build_output: dropped %d non-dict findings_summary items",
                           self.agent_id, len(findings_raw) - len(findings))

        # Build structured reasoning trace with phases and detailed steps
        reasoning_trace = {
            "phases": ctx.reasoning_trace,  # High-level phase summaries
            "steps": ctx.investigation_steps,  # Detailed tool invocations
            "iterations": ctx.iteration,
            "goal_satisfied": ctx.is_goal_satisfied,
        }

        confidences = [f.get("confidence", 0) for f in findings]
        if not confidences:
            # No findings is a legitimate outcome — agent found nothing wrong.
            logger.info("[%s] PRPA loop completed with no findings", self.agent_id)
            return AgentOutput(
                agent_id=self.agent_id,
                finding_type=self.finding_type,
                severity=ctx.reflection.get("overall_severity", "low"),
                summary=self.fallback_summary,
                detail={
                    "findings": [],
                    "remaining_gaps": ctx.reflection.get("remaining_gaps", []),
                    "cross_domain_followup": ctx.reflection.get("cross_domain_followup", []),
                },
                data_signals=ctx.perceptions,
                reasoning_trace=reasoning_trace,
                confidence=0.0,
                findings=[],
            )
        avg_confidence = sum(confidences) / len(confidences)
        severity = ctx.reflection.get("overall_severity")
        if not severity:
            raise RuntimeError(f"[{self.agent_id}] _build_output: LLM reflect phase did not return overall_severity")

        summary_parts = []
        for f in findings:
            site = f.get("site_id", "unknown")
            finding = f.get("finding", "")
            summary_parts.append(f"{site}: {finding}")

        return AgentOutput(
            agent_id=self.agent_id,
            finding_type=self.finding_type,
            severity=severity,
            summary="; ".join(summary_parts) if summary_parts else self.fallback_summary,
            detail={
                "findings": findings,
                "remaining_gaps": ctx.reflection.get("remaining_gaps", []),
                "cross_domain_followup": ctx.reflection.get("cross_domain_followup", []),
            },
            data_signals=ctx.perceptions,
            reasoning_trace=reasoning_trace,
            confidence=avg_confidence,
            findings=findings,
        )

    # ── Utility methods ──

    def _parse_json(self, text: str) -> dict | list:
        """Extract JSON from LLM response, handling markdown fences."""
        return parse_llm_json(text)

    def _safe_json_str(self, data: Any, max_chars: int = 30000) -> str:
        """Serialize data to JSON with structural truncation."""
        return safe_json_str(data, max_chars)
