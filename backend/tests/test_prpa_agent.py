"""Tests for the PRPA (Perceive-Reason-Plan-Act-Reflect) agent loop.

Exercises the full agent pipeline with mocked LLM and tools to verify:
- Correct PRPA phase sequencing
- LLM-driven reasoning produces hypotheses
- LLM-driven planning selects tools
- Act phase executes planned tools
- Reflect phase evaluates completeness
- Multi-iteration loop (reflect says goal NOT satisfied)
- Early termination (reflect says goal IS satisfied on iteration 1)
- Graceful handling of malformed LLM JSON
- on_step callback invocation for WebSocket streaming
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents.data_quality import DataQualityAgent
from backend.agents.enrollment_funnel import EnrollmentFunnelAgent
from backend.agents.base import AgentOutput
from backend.tools.base import ToolResult, ToolRegistry
from backend.llm.client import LLMClient, LLMResponse
from backend.prompts.manager import PromptManager


# ── Canned LLM responses ────────────────────────────────────────────────────

REASON_RESPONSE = json.dumps({
    "hypotheses": [
        {"hypothesis_id": "H1", "description": "SITE-003 has elevated entry lag", "confidence": 0.85},
        {"hypothesis_id": "H2", "description": "CRA transition at SITE-005 correlated with quality dip", "confidence": 0.7},
    ]
})

PLAN_RESPONSE = json.dumps({
    "plan_steps": [
        {"step_id": "S1", "tool_name": "entry_lag_analysis", "tool_args": {"site_id": "SITE-003"}, "purpose": "drill into SITE-003 lag"},
        {"step_id": "S2", "tool_name": "cra_assignment_history", "tool_args": {"site_id": "SITE-005"}, "purpose": "check CRA transitions"},
    ]
})

REFLECT_GOAL_SATISFIED = json.dumps({
    "is_goal_satisfied": True,
    "findings_summary": [
        {"site_id": "SITE-003", "finding": "Mean entry lag 12.4 days exceeds 7-day threshold", "confidence": 0.92},
        {"site_id": "SITE-005", "finding": "CRA transition 3 weeks ago, quality metrics degraded since", "confidence": 0.78},
    ],
    "remaining_gaps": [],
    "overall_severity": "high",
})

REFLECT_NOT_SATISFIED = json.dumps({
    "is_goal_satisfied": False,
    "findings_summary": [
        {"site_id": "SITE-003", "finding": "Entry lag is elevated but need more data", "confidence": 0.6},
    ],
    "remaining_gaps": ["Need correction analysis for SITE-003"],
    "overall_severity": "medium",
})

ENROLLMENT_REASON = json.dumps({
    "hypotheses": [
        {"hypothesis_id": "H1", "description": "SITE-007 has abnormally high screen failure rate", "confidence": 0.88},
    ]
})

ENROLLMENT_PLAN = json.dumps({
    "plan_steps": [
        {"step_id": "S1", "tool_name": "screen_failure_pattern", "tool_args": {"site_id": "SITE-007"}, "purpose": "investigate failure reasons"},
    ]
})

ENROLLMENT_REFLECT = json.dumps({
    "is_goal_satisfied": True,
    "findings_summary": [
        {"site_id": "SITE-007", "finding": "Screen failure rate 45% vs study avg 22%", "confidence": 0.91},
    ],
    "remaining_gaps": [],
    "overall_severity": "high",
})


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_mock_llm(responses: list[str]) -> LLMClient:
    """Create a mock LLM that returns responses in order."""
    llm = MagicMock(spec=LLMClient)
    call_idx = {"i": 0}

    async def _generate_structured(prompt, *, system="", temperature=None):
        idx = call_idx["i"]
        call_idx["i"] += 1
        text = responses[idx] if idx < len(responses) else '{"error": "no more responses"}'
        return LLMResponse(text=text, model="mock", usage={})

    llm.generate_structured = AsyncMock(side_effect=_generate_structured)
    return llm


def _make_mock_tools() -> ToolRegistry:
    """Create a tool registry where every invoke returns dummy data."""
    reg = ToolRegistry()

    async def _invoke(name, db_session, **kwargs):
        return ToolResult(
            tool_name=name,
            success=True,
            data=[{"site_id": kwargs.get("site_id", "SITE-001"), "metric": 42}],
            row_count=1,
        )

    reg.invoke = AsyncMock(side_effect=_invoke)
    reg.list_tools_text = MagicMock(return_value="- entry_lag_analysis: Analyzes entry lags\n- cra_assignment_history: CRA transitions")
    return reg


def _make_mock_prompts() -> PromptManager:
    """Create a prompt manager that returns the prompt name as the rendered text."""
    pm = MagicMock(spec=PromptManager)
    pm.render = MagicMock(side_effect=lambda name, **kw: f"[PROMPT:{name}] {json.dumps(kw, default=str)[:200]}")
    return pm


# ── DataQualityAgent Tests ───────────────────────────────────────────────────

class TestDataQualityAgentPRPA:

    @pytest.mark.asyncio
    async def test_single_iteration_goal_satisfied(self):
        """Agent completes in 1 iteration when reflect says goal is satisfied."""
        llm = _make_mock_llm([REASON_RESPONSE, PLAN_RESPONSE, REFLECT_GOAL_SATISFIED])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("Which sites have data quality issues?", session_id="test-sess")

        assert isinstance(output, AgentOutput)
        assert output.agent_id == "agent_1"
        assert output.finding_type == "data_quality_analysis"
        assert output.severity == "high"
        assert output.confidence > 0
        assert len(output.findings) == 2
        assert "SITE-003" in output.summary

    @pytest.mark.asyncio
    async def test_multi_iteration_loop(self):
        """Agent iterates twice when first reflect says goal NOT satisfied."""
        llm = _make_mock_llm([
            # Iteration 1: reason, plan, reflect (not satisfied)
            REASON_RESPONSE, PLAN_RESPONSE, REFLECT_NOT_SATISFIED,
            # Iteration 2: reason, plan, reflect (satisfied)
            REASON_RESPONSE, PLAN_RESPONSE, REFLECT_GOAL_SATISFIED,
        ])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("Deep investigation", session_id="test-sess")

        # Should have run 2 iterations
        phases = [t["phase"] for t in output.reasoning_trace]
        assert phases.count("perceive") == 2
        assert phases.count("reflect") == 2
        # Final output should use the second reflect's findings
        assert output.severity == "high"

    @pytest.mark.asyncio
    async def test_perceive_invokes_all_five_tools(self):
        """Perceive phase should invoke all 5 data quality tools."""
        llm = _make_mock_llm([REASON_RESPONSE, PLAN_RESPONSE, REFLECT_GOAL_SATISFIED])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        await agent.run("test", session_id="s")

        # First 5 calls are perceive, then act calls follow
        perceive_tools = {c[0][0] for c in tools.invoke.call_args_list[:5]}
        expected = {"entry_lag_analysis", "query_burden", "data_correction_analysis",
                    "cra_assignment_history", "monitoring_visit_history"}
        assert perceive_tools == expected

    @pytest.mark.asyncio
    async def test_act_executes_planned_tools(self):
        """Act phase should invoke each tool from the LLM's plan."""
        llm = _make_mock_llm([REASON_RESPONSE, PLAN_RESPONSE, REFLECT_GOAL_SATISFIED])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        await agent.run("test", session_id="s")

        # Plan has 2 steps — check they were invoked with correct args
        act_calls = [c for c in tools.invoke.call_args_list if c[0][0] == "entry_lag_analysis" and "site_id" in c[1]]
        assert any(c[1].get("site_id") == "SITE-003" for c in act_calls)

    @pytest.mark.asyncio
    async def test_on_step_callback_fires_for_all_phases(self):
        """WebSocket on_step callback should be invoked for each PRPA phase."""
        llm = _make_mock_llm([REASON_RESPONSE, PLAN_RESPONSE, REFLECT_GOAL_SATISFIED])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        phases_seen = []

        async def on_step(phase, agent_id, data):
            phases_seen.append(phase)

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        await agent.run("test", session_id="s", on_step=on_step)

        assert "perceive" in phases_seen
        assert "reason" in phases_seen
        assert "plan" in phases_seen
        assert "act" in phases_seen
        assert "reflect" in phases_seen

    @pytest.mark.asyncio
    async def test_on_step_callback_error_does_not_crash_agent(self):
        """on_step raising should not abort the agent — errors are swallowed."""
        llm = _make_mock_llm([REASON_RESPONSE, PLAN_RESPONSE, REFLECT_GOAL_SATISFIED])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        async def bad_callback(phase, agent_id, data):
            raise ConnectionError("WebSocket disconnected")

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("test", session_id="s", on_step=bad_callback)
        # Agent should still complete despite callback errors
        assert output.agent_id == "agent_1"

    @pytest.mark.asyncio
    async def test_malformed_llm_json_in_reason_returns_fallback(self):
        """If LLM returns invalid JSON in reason phase, agent should not crash."""
        llm = _make_mock_llm([
            "This is not valid JSON at all",  # reason fails
            PLAN_RESPONSE,
            REFLECT_GOAL_SATISFIED,
        ])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("test", session_id="s")
        # Should get fallback hypothesis
        assert output.agent_id == "agent_1"

    @pytest.mark.asyncio
    async def test_empty_plan_steps_skips_act(self):
        """If LLM returns empty plan, act should complete with no tool calls."""
        empty_plan = json.dumps({"plan_steps": []})
        llm = _make_mock_llm([REASON_RESPONSE, empty_plan, REFLECT_GOAL_SATISFIED])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("test", session_id="s")

        # Only perceive tools should have been called (5), no act tools
        act_calls = [c for c in tools.invoke.call_args_list if c[0][0] not in {
            "entry_lag_analysis", "query_burden", "data_correction_analysis",
            "cra_assignment_history", "monitoring_visit_history",
        }]
        assert len(act_calls) == 0

    @pytest.mark.asyncio
    async def test_reasoning_trace_records_all_phases(self):
        """reasoning_trace should contain entries for every PRPA phase."""
        llm = _make_mock_llm([REASON_RESPONSE, PLAN_RESPONSE, REFLECT_GOAL_SATISFIED])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("test", session_id="s")

        trace_phases = [entry["phase"] for entry in output.reasoning_trace]
        assert trace_phases == ["perceive", "reason", "plan", "act", "reflect"]

    @pytest.mark.asyncio
    async def test_confidence_computed_from_findings(self):
        """Output confidence should be average of finding confidences."""
        llm = _make_mock_llm([REASON_RESPONSE, PLAN_RESPONSE, REFLECT_GOAL_SATISFIED])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("test", session_id="s")

        expected = (0.92 + 0.78) / 2  # from REFLECT_GOAL_SATISFIED
        assert abs(output.confidence - expected) < 0.01


# ── EnrollmentFunnelAgent Tests ──────────────────────────────────────────────

class TestEnrollmentFunnelAgentPRPA:

    @pytest.mark.asyncio
    async def test_enrollment_agent_full_cycle(self):
        """Enrollment agent completes PRPA cycle and produces correct output."""
        llm = _make_mock_llm([ENROLLMENT_REASON, ENROLLMENT_PLAN, ENROLLMENT_REFLECT])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = EnrollmentFunnelAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("Which sites have high screen failure?", session_id="test-sess")

        assert output.agent_id == "agent_3"
        assert output.finding_type == "enrollment_funnel_analysis"
        assert output.severity == "high"
        assert len(output.findings) == 1
        assert "SITE-007" in output.summary

    @pytest.mark.asyncio
    async def test_enrollment_perceive_invokes_six_tools(self):
        """Perceive phase should invoke all 6 enrollment tools."""
        llm = _make_mock_llm([ENROLLMENT_REASON, ENROLLMENT_PLAN, ENROLLMENT_REFLECT])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = EnrollmentFunnelAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        await agent.run("test", session_id="s")

        # First 6 calls are perceive, then act calls follow
        perceive_tools = {c[0][0] for c in tools.invoke.call_args_list[:6]}
        expected = {"screening_funnel", "enrollment_velocity", "screen_failure_pattern",
                    "regional_comparison", "site_summary", "kit_inventory"}
        assert perceive_tools == expected

    @pytest.mark.asyncio
    async def test_no_findings_produces_default_summary(self):
        """Agent with no findings should produce a 'no issues' summary."""
        empty_reflect = json.dumps({
            "is_goal_satisfied": True,
            "findings_summary": [],
            "remaining_gaps": [],
            "overall_severity": "low",
        })
        llm = _make_mock_llm([ENROLLMENT_REASON, ENROLLMENT_PLAN, empty_reflect])
        tools = _make_mock_tools()
        prompts = _make_mock_prompts()
        db = MagicMock()

        agent = EnrollmentFunnelAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("test", session_id="s")

        assert "No significant enrollment issues" in output.summary
        assert output.confidence == 0.5  # default when no findings
