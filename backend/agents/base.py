"""BaseAgent with PRPA (Perceive-Reason-Plan-Act-Reflect) loop."""

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


@dataclass
class AgentOutput:
    """Structured output from an agent run."""
    agent_id: str
    finding_type: str
    severity: str
    summary: str
    detail: dict
    data_signals: dict
    reasoning_trace: list
    confidence: float
    findings: list = field(default_factory=list)
    investigation_complete: bool = True
    remaining_gaps: list = field(default_factory=list)


# Type for the on_step callback used for WebSocket streaming
OnStepCallback = Callable[[str, str, Any], Coroutine[Any, Any, None]]


class BaseAgent(ABC):
    """Abstract agent implementing the PRPA reasoning loop.

    Subclasses implement perceive/reason/plan/act/reflect for their domain.
    The on_step callback is invoked at each phase for WebSocket streaming.
    """

    agent_id: str = ""
    agent_name: str = ""
    description: str = ""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        prompt_manager: PromptManager,
        db_session: Session,
    ):
        self.llm = llm_client
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

    @abstractmethod
    async def perceive(self, ctx: AgentContext) -> dict:
        """Gather raw data signals broadly."""
        ...

    @abstractmethod
    async def reason(self, ctx: AgentContext) -> list:
        """LLM-driven hypothesis generation from perceptions."""
        ...

    @abstractmethod
    async def plan(self, ctx: AgentContext) -> list:
        """LLM-driven investigation plan from hypotheses."""
        ...

    @abstractmethod
    async def act(self, ctx: AgentContext) -> list:
        """Execute planned tool invocations."""
        ...

    @abstractmethod
    async def reflect(self, ctx: AgentContext) -> dict:
        """LLM-driven evaluation of investigation completeness."""
        ...

    @abstractmethod
    async def _build_output(self, ctx: AgentContext) -> AgentOutput:
        """Build structured output from completed context."""
        ...

    def _parse_json(self, text: str) -> dict | list:
        """Extract JSON from LLM response, handling markdown fences."""
        return parse_llm_json(text)

    def _safe_json_str(self, data: Any, max_chars: int = 30000) -> str:
        """Serialize data to JSON with structural truncation."""
        return safe_json_str(data, max_chars)
