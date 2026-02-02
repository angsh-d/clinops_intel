"""Tests for the ConductorRouter: LLM-driven routing, parallel agent execution, synthesis.

Verifies:
- Semantic routing dispatches to correct agents
- Single-agent queries bypass synthesis
- Multi-agent queries trigger cross-domain synthesis
- Agent failures are handled gracefully
- Route parse failures fall back to default
- Synthesis parse failures return structured error
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.conductor.router import ConductorRouter
from backend.agents.base import AgentOutput, BaseAgent, AgentContext
from backend.agents.registry import AgentRegistry
from backend.tools.base import ToolRegistry, ToolResult
from backend.llm.client import LLMClient, LLMResponse
from backend.prompts.manager import PromptManager


# ── Canned responses ─────────────────────────────────────────────────────────

ROUTE_SINGLE_AGENT = json.dumps({
    "selected_agents": ["data_quality"],
    "routing_rationale": "Query is about data quality only",
    "requires_synthesis": False,
})

ROUTE_MULTI_AGENT = json.dumps({
    "selected_agents": ["data_quality", "enrollment_funnel"],
    "routing_rationale": "Query spans data quality and enrollment",
    "requires_synthesis": True,
})

SYNTHESIS_RESPONSE = json.dumps({
    "executive_summary": "Sites SITE-003 and SITE-007 have correlated data quality and enrollment issues.",
    "cross_domain_findings": [
        {"finding": "SITE-003 entry lag spike coincides with enrollment slowdown", "confidence": 0.88}
    ],
    "single_domain_findings": [],
    "priority_actions": ["Trigger site visit for SITE-003"],
})


# ── Fake agent that completes instantly ──────────────────────────────────────

class _FakeAgent(BaseAgent):
    """Minimal agent for testing conductor orchestration."""

    def __init__(self, agent_id_val, **kwargs):
        super().__init__(**kwargs)
        self.__class__.agent_id = agent_id_val

    async def perceive(self, ctx): return {}
    async def reason(self, ctx): return []
    async def plan(self, ctx): return []
    async def act(self, ctx): return []

    async def reflect(self, ctx):
        return {
            "is_goal_satisfied": True,
            "findings_summary": [{"site_id": "SITE-001", "finding": f"Finding from {self.agent_id}", "confidence": 0.9}],
            "overall_severity": "medium",
        }

    async def _build_output(self, ctx):
        findings = ctx.reflection.get("findings_summary", [])
        return AgentOutput(
            agent_id=self.agent_id,
            finding_type="test_analysis",
            severity="medium",
            summary=f"Test finding from {self.agent_id}",
            detail={"findings": findings},
            data_signals={},
            reasoning_trace=ctx.reasoning_trace,
            confidence=0.9,
            findings=findings,
        )


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_conductor(llm_responses: list[str]) -> ConductorRouter:
    """Build ConductorRouter with mocked LLM, real-ish agent registry."""
    llm = MagicMock(spec=LLMClient)
    call_idx = {"i": 0}

    async def _gen(prompt, *, system="", temperature=None):
        idx = call_idx["i"]
        call_idx["i"] += 1
        text = llm_responses[idx] if idx < len(llm_responses) else '{"error": "exhausted"}'
        return LLMResponse(text=text, model="mock", usage={})

    llm.generate_structured = AsyncMock(side_effect=_gen)

    prompts = MagicMock(spec=PromptManager)
    prompts.render = MagicMock(side_effect=lambda name, **kw: f"[{name}]")

    tools = MagicMock(spec=ToolRegistry)
    tools.list_tools_text = MagicMock(return_value="- tool1: desc")
    tools.invoke = AsyncMock(return_value=ToolResult(tool_name="mock", success=True, data=[], row_count=0))

    # Build registry with fake agents
    registry = AgentRegistry()

    class FakeAgent1(_FakeAgent):
        agent_id = "data_quality"
        agent_name = "Data Quality Agent"
        description = "Test DQ agent"

        def __init__(self, **kwargs):
            super().__init__(agent_id_val="data_quality", **kwargs)

    class FakeAgent3(_FakeAgent):
        agent_id = "enrollment_funnel"
        agent_name = "Enrollment Funnel Agent"
        description = "Test enrollment agent"

        def __init__(self, **kwargs):
            super().__init__(agent_id_val="enrollment_funnel", **kwargs)

    registry.register(FakeAgent1)
    registry.register(FakeAgent3)

    return ConductorRouter(llm, prompts, registry, tools)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestConductorRouting:

    @pytest.mark.asyncio
    async def test_route_single_agent(self):
        conductor = _make_conductor([ROUTE_SINGLE_AGENT])
        routing = await conductor.route_query("How is data quality?")
        assert routing["selected_agents"] == ["data_quality"]
        assert routing["requires_synthesis"] is False

    @pytest.mark.asyncio
    async def test_route_multi_agent(self):
        conductor = _make_conductor([ROUTE_MULTI_AGENT])
        routing = await conductor.route_query("Overview of data quality and enrollment")
        assert set(routing["selected_agents"]) == {"data_quality", "enrollment_funnel"}
        assert routing["requires_synthesis"] is True

    @pytest.mark.asyncio
    async def test_route_parse_failure_defaults_to_data_quality(self):
        """If LLM returns garbage, conductor defaults to data_quality."""
        conductor = _make_conductor(["not json at all !!!"])
        routing = await conductor.route_query("test")
        assert routing["selected_agents"] == ["data_quality"]
        assert "parse error" in routing["routing_rationale"].lower()


class TestConductorExecution:

    @pytest.mark.asyncio
    async def test_single_agent_bypasses_synthesis(self):
        """Single-agent routing should not call _synthesize."""
        conductor = _make_conductor([ROUTE_SINGLE_AGENT])

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("DQ question", "", MagicMock())

        assert "synthesis" in result
        # Single agent: executive_summary comes from agent, not LLM synthesis
        assert result["synthesis"]["cross_domain_findings"] == []
        assert len(result["agent_outputs"]) == 1
        assert "data_quality" in result["agent_outputs"]

    @pytest.mark.asyncio
    async def test_multi_agent_triggers_synthesis(self):
        """Multi-agent routing should invoke LLM synthesis."""
        conductor = _make_conductor([ROUTE_MULTI_AGENT, SYNTHESIS_RESPONSE])

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("Full overview", "", MagicMock())

        assert len(result["agent_outputs"]) == 2
        assert "data_quality" in result["agent_outputs"]
        assert "enrollment_funnel" in result["agent_outputs"]
        # Synthesis was called
        assert "cross_domain_findings" in result["synthesis"]
        assert len(result["synthesis"]["cross_domain_findings"]) > 0

    @pytest.mark.asyncio
    async def test_synthesis_parse_failure_returns_error(self):
        """If synthesis LLM returns garbage, result includes structured error."""
        conductor = _make_conductor([ROUTE_MULTI_AGENT, "not valid json"])

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("test", "", MagicMock())

        assert "error" in result["synthesis"]
        assert result["synthesis"]["executive_summary"] == "Synthesis could not be completed."

    @pytest.mark.asyncio
    async def test_unknown_agent_in_routing_is_skipped(self):
        """If LLM routes to a nonexistent agent, it is silently skipped."""
        bad_route = json.dumps({
            "selected_agents": ["data_quality", "nonexistent_agent"],
            "routing_rationale": "test",
            "requires_synthesis": False,
        })
        conductor = _make_conductor([bad_route])

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("test", "", MagicMock())

        # Only data_quality should produce output
        assert "data_quality" in result["agent_outputs"]
        assert "nonexistent_agent" not in result["agent_outputs"]

    @pytest.mark.asyncio
    async def test_on_step_called_for_routing_phase(self):
        """on_step should be called with 'routing' phase at start."""
        conductor = _make_conductor([ROUTE_SINGLE_AGENT])
        phases = []

        async def on_step(phase, agent_id, data):
            phases.append((phase, agent_id))

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            await conductor.execute_query("test", "", MagicMock(), on_step=on_step)

        assert ("routing", "conductor") in phases

    @pytest.mark.asyncio
    async def test_result_structure_has_all_expected_keys(self):
        """execute_query result must contain query_id, query, routing, agent_outputs, synthesis."""
        conductor = _make_conductor([ROUTE_SINGLE_AGENT])

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("test", "", MagicMock())

        assert "query_id" in result
        assert "query" in result
        assert "routing" in result
        assert "agent_outputs" in result
        assert "synthesis" in result

    @pytest.mark.asyncio
    async def test_agent_output_contains_reasoning_trace(self):
        """Each agent_output entry should contain a reasoning_trace list."""
        conductor = _make_conductor([ROUTE_SINGLE_AGENT])

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("test", "", MagicMock())

        for aid, out in result["agent_outputs"].items():
            assert "reasoning_trace" in out
            assert isinstance(out["reasoning_trace"], list)
