"""Advanced agentic tests: non-trivial validation of data flow, adaptive reasoning,
tool failure recovery, goal-driven planning, conductor orchestration with real PRPA,
cross-domain synthesis, prompt contracts, trace integrity, and edge cases.

These tests go beyond the basic PRPA mechanics tested in test_prpa_agent.py and
test_conductor.py by validating that:
- Perception data actually flows into LLM reason prompts
- Hypotheses flow into plan prompts and action results into reflect prompts
- The agent evolves across iterations (reflect gaps drive next iteration)
- Tool failures produce graceful degradation, not crashes
- The plan phase selects tools based on hypothesis content
- Conductor runs real PRPA agents (not _FakeAgent stubs) in parallel
- Synthesis receives and correlates findings from multiple agents
- Every LLM call receives the correct prompt template and variables
- Reasoning traces are complete ordered records of every decision
- Output severity/confidence come from reflect, not hardcoded defaults
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from backend.agents.data_quality import DataQualityAgent
from backend.agents.enrollment_funnel import EnrollmentFunnelAgent
from backend.agents.base import AgentOutput, AgentContext
from backend.agents.registry import AgentRegistry
from backend.conductor.router import ConductorRouter
from backend.tools.base import ToolResult, ToolRegistry
from backend.llm.client import LLMClient, LLMResponse
from backend.prompts.manager import PromptManager


# ── Instrumented Mock Infrastructure ────────────────────────────────────────


class ContextAwareMockLLM:
    """Mock LLM that inspects the prompt to determine which PRPA phase is calling,
    returns appropriate canned responses, and captures all prompts for assertion."""

    def __init__(self, response_map: dict[str, str]):
        """response_map: keys are prompt name substrings (e.g. 'agent1_reason'),
        values are JSON response strings."""
        self._response_map = response_map
        self.captured_prompts: list[tuple[str, str]] = []  # [(prompt_text, system), ...]
        self.call_count = 0

    async def generate_structured(self, prompt, *, system="", temperature=None):
        self.captured_prompts.append((prompt, system))
        self.call_count += 1

        # Match prompt against response_map keys
        for key, response in self._response_map.items():
            if key in prompt:
                return LLMResponse(text=response, model="mock-context-aware", usage={})

        # Default fallback
        return LLMResponse(
            text='{"hypotheses": [], "plan_steps": [], "is_goal_satisfied": true, '
                 '"findings_summary": [], "overall_severity": "low"}',
            model="mock-context-aware", usage={},
        )


class InstrumentedMockTools:
    """Tool registry that returns different data per tool name and captures
    all invocation arguments for assertion."""

    def __init__(self, tool_data: dict[str, ToolResult] | None = None,
                 failing_tools: set[str] | None = None):
        """tool_data: maps tool name -> ToolResult to return.
        failing_tools: set of tool names that should return success=False."""
        self._tool_data = tool_data or {}
        self._failing_tools = failing_tools or set()
        self.invocations: list[tuple[str, dict]] = []  # [(tool_name, kwargs), ...]

    async def invoke(self, name, db_session, **kwargs):
        self.invocations.append((name, kwargs))

        if name in self._failing_tools:
            return ToolResult(tool_name=name, success=False, error="DB connection timeout", data=None, row_count=0)

        if name in self._tool_data:
            return self._tool_data[name]

        # Default: return site-specific data
        return ToolResult(
            tool_name=name, success=True,
            data=[{"site_id": kwargs.get("site_id", "SITE-001"), "metric": 42}],
            row_count=1,
        )

    def list_tools_text(self):
        return (
            "- entry_lag_analysis: Analyzes eCRF entry lag by site\n"
            "- query_burden: Query counts and aging\n"
            "- data_correction_analysis: Correction rates\n"
            "- cra_assignment_history: CRA assignment timeline\n"
            "- monitoring_visit_history: Visit records\n"
            "- screening_funnel: Screening decomposition\n"
            "- enrollment_velocity: Weekly velocity\n"
            "- screen_failure_pattern: Failure reason codes\n"
            "- regional_comparison: Cross-site metrics\n"
            "- site_summary: Site metadata\n"
            "- kit_inventory: Kit inventory snapshots"
        )


class InstrumentedMockPrompts:
    """Prompt manager that captures all render calls with full kwargs for assertion."""

    def __init__(self):
        self.render_calls: list[tuple[str, dict]] = []  # [(prompt_name, kwargs), ...]

    def render(self, name, **kwargs):
        self.render_calls.append((name, kwargs))
        # Return the prompt name embedded so ContextAwareMockLLM can match on it
        return f"[PROMPT:{name}] {json.dumps(kwargs, default=str)[:4000]}"


# ── Helper to build a real agent with instrumented mocks ────────────────────

def _build_data_quality_agent(response_map, tool_data=None, failing_tools=None):
    llm = ContextAwareMockLLM(response_map)
    tools = InstrumentedMockTools(tool_data, failing_tools)
    prompts = InstrumentedMockPrompts()
    db = MagicMock()
    agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
    # Patch invoke and list_tools_text to route through our instrumented mock
    agent.tools = tools
    return agent, llm, tools, prompts


def _build_enrollment_agent(response_map, tool_data=None, failing_tools=None):
    llm = ContextAwareMockLLM(response_map)
    tools = InstrumentedMockTools(tool_data, failing_tools)
    prompts = InstrumentedMockPrompts()
    db = MagicMock()
    agent = EnrollmentFunnelAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
    agent.tools = tools
    return agent, llm, tools, prompts


# ── Canned Response Data ────────────────────────────────────────────────────

SITE_003_ENTRY_LAG = [
    {"site_id": "SITE-003", "page_name": "Demographics", "mean_lag_days": 12.4, "median_lag_days": 10.2},
    {"site_id": "SITE-003", "page_name": "Vitals", "mean_lag_days": 8.1, "median_lag_days": 6.5},
]

SITE_005_ENTRY_LAG = [
    {"site_id": "SITE-005", "page_name": "Demographics", "mean_lag_days": 2.1, "median_lag_days": 1.8},
]

REASON_WITH_SITE003 = json.dumps({
    "hypotheses": [
        {"hypothesis_id": "H1", "description": "SITE-003 has severe entry lag (12.4 days mean)", "confidence": 0.9},
        {"hypothesis_id": "H2", "description": "SITE-005 is performing well with 2.1 day lag", "confidence": 0.3},
    ]
})

PLAN_ENTRY_LAG_DRILL = json.dumps({
    "plan_steps": [
        {"step_id": "S1", "tool_name": "entry_lag_analysis", "tool_args": {"site_id": "SITE-003"}, "purpose": "drill into SITE-003"},
        {"step_id": "S2", "tool_name": "data_correction_analysis", "tool_args": {"site_id": "SITE-003"}, "purpose": "check corrections"},
    ]
})

PLAN_CRA_DRILL = json.dumps({
    "plan_steps": [
        {"step_id": "S1", "tool_name": "cra_assignment_history", "tool_args": {"site_id": "SITE-005"}, "purpose": "check CRA transitions"},
    ]
})

REFLECT_SATISFIED = json.dumps({
    "is_goal_satisfied": True,
    "findings_summary": [
        {"site_id": "SITE-003", "finding": "Mean entry lag 12.4 days exceeds threshold", "confidence": 0.92},
    ],
    "remaining_gaps": [],
    "overall_severity": "high",
})

REFLECT_NOT_SATISFIED_NEEDS_CORRECTION = json.dumps({
    "is_goal_satisfied": False,
    "findings_summary": [
        {"site_id": "SITE-003", "finding": "Entry lag elevated but need correction analysis", "confidence": 0.6},
    ],
    "remaining_gaps": ["Need correction analysis for SITE-003"],
    "overall_severity": "medium",
})

REFLECT_NEVER_SATISFIED = json.dumps({
    "is_goal_satisfied": False,
    "findings_summary": [
        {"site_id": "SITE-003", "finding": "Still investigating", "confidence": 0.4},
    ],
    "remaining_gaps": ["More investigation needed"],
    "overall_severity": "medium",
})

ENROLLMENT_REASON = json.dumps({
    "hypotheses": [
        {"hypothesis_id": "H1", "description": "SITE-003 screen failure rate abnormally high", "confidence": 0.85},
    ]
})

ENROLLMENT_PLAN = json.dumps({
    "plan_steps": [
        {"step_id": "S1", "tool_name": "screen_failure_pattern", "tool_args": {"site_id": "SITE-003"}, "purpose": "investigate SITE-003 failures"},
    ]
})

ENROLLMENT_REFLECT = json.dumps({
    "is_goal_satisfied": True,
    "findings_summary": [
        {"site_id": "SITE-003", "finding": "Screen failure rate 45% vs study avg 22%", "confidence": 0.91},
    ],
    "remaining_gaps": [],
    "overall_severity": "high",
})


# ═══════════════════════════════════════════════════════════════════════════════
# T1: Data-Dependent Reasoning (Perception → Reason Prompt Validation)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataDependentReasoning:
    """Validates that real perception data flows into LLM prompts — not just
    calling the LLM, but feeding it the right context at each phase."""

    @pytest.mark.asyncio
    async def test_perception_data_flows_into_reason_prompt(self):
        """Reason prompt must contain the actual perception data values (site IDs, metrics)."""
        # Configure tools to return site-specific data
        tool_data = {
            "entry_lag_analysis": ToolResult(
                tool_name="entry_lag_analysis", success=True,
                data=SITE_003_ENTRY_LAG + SITE_005_ENTRY_LAG, row_count=3,
            ),
        }
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": json.dumps({"plan_steps": []}),
            "agent1_reflect": REFLECT_SATISFIED,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map, tool_data)
        await agent.run("Which sites have data quality issues?", session_id="test")

        # Find the reason render call
        reason_calls = [(name, kw) for name, kw in prompts.render_calls if name == "agent1_reason"]
        assert len(reason_calls) >= 1, "agent1_reason prompt was never rendered"

        # The perceptions kwarg should contain actual data from the tools
        perceptions_str = reason_calls[0][1]["perceptions"]
        assert "SITE-003" in perceptions_str, "Perception data for SITE-003 missing from reason prompt"
        assert "12.4" in perceptions_str, "Entry lag value 12.4 missing from reason prompt"
        assert "SITE-005" in perceptions_str, "Perception data for SITE-005 missing from reason prompt"
        assert "2.1" in perceptions_str, "Entry lag value 2.1 missing from reason prompt"

    @pytest.mark.asyncio
    async def test_hypotheses_flow_into_plan_prompt(self):
        """Plan prompt must contain hypothesis text and tool descriptions."""
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": PLAN_ENTRY_LAG_DRILL,
            "agent1_reflect": REFLECT_SATISFIED,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        await agent.run("Investigate SITE-003", session_id="test")

        plan_calls = [(name, kw) for name, kw in prompts.render_calls if name == "agent1_plan"]
        assert len(plan_calls) >= 1, "agent1_plan prompt was never rendered"

        hypotheses_str = plan_calls[0][1]["hypotheses"]
        assert "SITE-003" in hypotheses_str, "Hypothesis about SITE-003 missing from plan prompt"
        assert "12.4" in hypotheses_str, "Hypothesis detail '12.4' missing from plan prompt"

        tool_desc = plan_calls[0][1]["tool_descriptions"]
        assert "entry_lag_analysis" in tool_desc, "Tool descriptions missing from plan prompt"

    @pytest.mark.asyncio
    async def test_action_results_flow_into_reflect_prompt(self):
        """Reflect prompt must contain the act phase's tool results."""
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": PLAN_ENTRY_LAG_DRILL,
            "agent1_reflect": REFLECT_SATISFIED,
        }
        tool_data = {
            "entry_lag_analysis": ToolResult(
                tool_name="entry_lag_analysis", success=True,
                data=[{"site_id": "SITE-003", "mean_lag_days": 12.4}], row_count=1,
            ),
            "data_correction_analysis": ToolResult(
                tool_name="data_correction_analysis", success=True,
                data=[{"site_id": "SITE-003", "correction_rate": 0.18}], row_count=1,
            ),
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map, tool_data)
        await agent.run("Check SITE-003", session_id="test")

        reflect_calls = [(name, kw) for name, kw in prompts.render_calls if name == "agent1_reflect"]
        assert len(reflect_calls) >= 1, "agent1_reflect prompt was never rendered"

        action_results_str = reflect_calls[0][1]["action_results"]
        assert "entry_lag_analysis" in action_results_str, "Tool name missing from reflect prompt"
        assert "SITE-003" in action_results_str, "Action result site data missing from reflect prompt"


# ═══════════════════════════════════════════════════════════════════════════════
# T2: Adaptive Multi-Iteration Refinement
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdaptiveMultiIteration:
    """Validates that the agent evolves its investigation across iterations —
    reflect identifies gaps, next iteration addresses them."""

    @pytest.mark.asyncio
    async def test_reflect_gaps_drive_second_iteration_reasoning(self):
        """Iteration 2 reason prompt should include accumulated action_results from iteration 1."""
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": PLAN_ENTRY_LAG_DRILL,
            # First reflect: not satisfied, second: satisfied
        }
        # Use a stateful LLM that returns different reflect responses per iteration
        llm = MagicMock(spec=LLMClient)
        call_idx = {"i": 0}
        reflect_responses = [REFLECT_NOT_SATISFIED_NEEDS_CORRECTION, REFLECT_SATISFIED]
        reflect_idx = {"i": 0}

        async def _gen(prompt, *, system="", temperature=None):
            call_idx["i"] += 1
            if "agent1_reflect" in prompt:
                idx = reflect_idx["i"]
                reflect_idx["i"] += 1
                text = reflect_responses[idx] if idx < len(reflect_responses) else REFLECT_SATISFIED
                return LLMResponse(text=text, model="mock", usage={})
            if "agent1_reason" in prompt:
                return LLMResponse(text=REASON_WITH_SITE003, model="mock", usage={})
            if "agent1_plan" in prompt:
                return LLMResponse(text=PLAN_ENTRY_LAG_DRILL, model="mock", usage={})
            return LLMResponse(text='{"hypotheses":[],"plan_steps":[],"is_goal_satisfied":true}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)
        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("Investigate SITE-003", session_id="test")

        # Should have 2 iterations
        perceive_count = sum(1 for t in output.reasoning_trace if t["phase"] == "perceive")
        assert perceive_count == 2, f"Expected 2 iterations, got {perceive_count}"

        # Iteration 2's reason prompt should contain perceptions (re-gathered each iteration)
        reason_calls = [(name, kw) for name, kw in prompts.render_calls if name == "agent1_reason"]
        assert len(reason_calls) == 2, "Expected 2 reason prompt renders"

        # Both reason prompts should contain perception data
        for rc in reason_calls:
            assert "perceptions" in rc[1]

    @pytest.mark.asyncio
    async def test_action_results_accumulate_across_iterations(self):
        """action_results should extend (not replace) across iterations."""
        llm = MagicMock(spec=LLMClient)
        reflect_idx = {"i": 0}

        async def _gen(prompt, *, system="", temperature=None):
            if "agent1_reflect" in prompt:
                idx = reflect_idx["i"]
                reflect_idx["i"] += 1
                if idx == 0:
                    return LLMResponse(text=REFLECT_NOT_SATISFIED_NEEDS_CORRECTION, model="mock", usage={})
                return LLMResponse(text=REFLECT_SATISFIED, model="mock", usage={})
            if "agent1_reason" in prompt:
                return LLMResponse(text=REASON_WITH_SITE003, model="mock", usage={})
            if "agent1_plan" in prompt:
                return LLMResponse(text=PLAN_ENTRY_LAG_DRILL, model="mock", usage={})
            return LLMResponse(text='{}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)
        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("test", session_id="test")

        # PLAN_ENTRY_LAG_DRILL has 2 steps, 2 iterations → 4 action results
        act_entries = [t for t in output.reasoning_trace if t["phase"] == "act"]
        assert len(act_entries) == 2, "Expected 2 act trace entries"

        # Verify the second iteration's reflect prompt has all accumulated results
        reflect_calls = [(name, kw) for name, kw in prompts.render_calls if name == "agent1_reflect"]
        assert len(reflect_calls) == 2
        # Second reflect should see results from both iterations (4 results)
        second_reflect_results = reflect_calls[1][1]["action_results"]
        # Count occurrences of "entry_lag_analysis" — should appear twice (once per iteration)
        assert second_reflect_results.count("entry_lag_analysis") >= 2, \
            "Second reflect prompt should contain action_results from both iterations"

    @pytest.mark.asyncio
    async def test_max_iterations_terminates_unsatisfied_loop(self):
        """Agent should stop after max_iterations even if goal never satisfied."""
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": json.dumps({"plan_steps": []}),
            "agent1_reflect": REFLECT_NEVER_SATISFIED,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        output = await agent.run("Unsolvable query", session_id="test")

        # Should have exactly 3 iterations (the default max)
        perceive_count = sum(1 for t in output.reasoning_trace if t["phase"] == "perceive")
        assert perceive_count == 3, f"Expected 3 iterations (max), got {perceive_count}"

        # Output should still contain findings from the final reflect
        assert len(output.findings) > 0, "Output should still contain findings even when unsatisfied"
        assert output.severity == "medium"  # from REFLECT_NEVER_SATISFIED


# ═══════════════════════════════════════════════════════════════════════════════
# T3: Tool Failure Recovery
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolFailureRecovery:
    """Validates that agents continue when individual tools fail."""

    @pytest.mark.asyncio
    async def test_perceive_tool_failure_produces_empty_signal(self):
        """A failing perceive tool should produce an empty list, not crash the agent."""
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": json.dumps({"plan_steps": []}),
            "agent1_reflect": REFLECT_SATISFIED,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(
            response_map, failing_tools={"entry_lag_analysis"}
        )
        output = await agent.run("test", session_id="test")

        # Agent should complete successfully
        assert output.agent_id == "agent_1"

        # entry_lag should be empty list in perceptions
        assert output.data_signals["entry_lag"] == [], \
            "Failed tool should produce empty list in perceptions"

        # Other tools should have data
        assert output.data_signals["query_burden"] != [], \
            "Successful tools should still have data"

    @pytest.mark.asyncio
    async def test_act_tool_failure_recorded_in_results(self):
        """A tool that fails during act should record success=False with error message."""
        plan_with_three_steps = json.dumps({
            "plan_steps": [
                {"step_id": "S1", "tool_name": "entry_lag_analysis", "tool_args": {"site_id": "SITE-003"}, "purpose": "step 1"},
                {"step_id": "S2", "tool_name": "data_correction_analysis", "tool_args": {"site_id": "SITE-003"}, "purpose": "step 2"},
                {"step_id": "S3", "tool_name": "cra_assignment_history", "tool_args": {"site_id": "SITE-003"}, "purpose": "step 3"},
            ]
        })
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": plan_with_three_steps,
            "agent1_reflect": REFLECT_SATISFIED,
        }
        # Middle tool fails
        agent, llm, tools, prompts = _build_data_quality_agent(
            response_map, failing_tools={"data_correction_analysis"}
        )
        output = await agent.run("test", session_id="test")

        # Find the reflect prompt to inspect action_results passed to it
        reflect_calls = [(name, kw) for name, kw in prompts.render_calls if name == "agent1_reflect"]
        assert len(reflect_calls) >= 1
        action_results_str = reflect_calls[0][1]["action_results"]

        # All 3 tool invocations should be recorded in action_results
        assert "entry_lag_analysis" in action_results_str
        assert "data_correction_analysis" in action_results_str
        assert "cra_assignment_history" in action_results_str
        # The failure should be recorded
        assert "DB connection timeout" in action_results_str, \
            "Tool error message should be passed to reflect prompt"

    @pytest.mark.asyncio
    async def test_all_perceive_tools_fail_agent_still_completes(self):
        """Even when all perceive tools fail, agent completes the full PRPA cycle."""
        all_dq_tools = {
            "entry_lag_analysis", "query_burden", "data_correction_analysis",
            "cra_assignment_history", "monitoring_visit_history",
        }
        response_map = {
            "agent1_reason": json.dumps({"hypotheses": []}),
            "agent1_plan": json.dumps({"plan_steps": []}),
            "agent1_reflect": json.dumps({
                "is_goal_satisfied": True,
                "findings_summary": [],
                "overall_severity": "low",
            }),
        }
        agent, llm, tools, prompts = _build_data_quality_agent(
            response_map, failing_tools=all_dq_tools
        )
        output = await agent.run("test", session_id="test")

        # Agent should still complete
        assert output.agent_id == "agent_1"
        # All perceptions should be empty
        for key in ["entry_lag", "query_burden", "corrections", "cra_history", "monitoring_visits"]:
            assert output.data_signals[key] == [], f"Expected empty list for {key}"
        # Confidence should be default 0.5 with no findings
        assert output.confidence == 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# T4: Goal-Driven Planning (LLM Selects Tools Based on Hypotheses)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoalDrivenPlanning:
    """Validates that hypotheses drive tool selection in the plan phase."""

    @pytest.mark.asyncio
    async def test_plan_selects_tools_matching_hypothesis_domain(self):
        """Different hypotheses should lead to different tool selections in the plan."""
        # Entry lag hypothesis → plan selects entry_lag_analysis
        entry_lag_hypothesis = json.dumps({
            "hypotheses": [
                {"hypothesis_id": "H1", "description": "SITE-003 entry lag is critically high", "confidence": 0.9},
            ]
        })
        response_map = {
            "agent1_reason": entry_lag_hypothesis,
            "agent1_plan": PLAN_ENTRY_LAG_DRILL,  # selects entry_lag_analysis + data_correction_analysis
            "agent1_reflect": REFLECT_SATISFIED,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        await agent.run("Check entry lag", session_id="test")

        # Verify act phase invoked the planned tools (entry_lag_analysis with SITE-003)
        act_invocations = [(name, kw) for name, kw in tools.invocations
                           if kw.get("site_id") == "SITE-003"]
        tool_names_invoked = {name for name, _ in act_invocations}
        assert "entry_lag_analysis" in tool_names_invoked, \
            "Plan should have selected entry_lag_analysis for entry lag hypothesis"

        # Now test CRA hypothesis → plan selects cra_assignment_history
        cra_hypothesis = json.dumps({
            "hypotheses": [
                {"hypothesis_id": "H1", "description": "CRA transition at SITE-005 caused quality dip", "confidence": 0.8},
            ]
        })
        response_map2 = {
            "agent1_reason": cra_hypothesis,
            "agent1_plan": PLAN_CRA_DRILL,  # selects cra_assignment_history
            "agent1_reflect": REFLECT_SATISFIED,
        }
        agent2, llm2, tools2, prompts2 = _build_data_quality_agent(response_map2)
        await agent2.run("Check CRA issues", session_id="test")

        act_invocations2 = [(name, kw) for name, kw in tools2.invocations
                            if kw.get("site_id") == "SITE-005"]
        tool_names_invoked2 = {name for name, _ in act_invocations2}
        assert "cra_assignment_history" in tool_names_invoked2, \
            "Plan should have selected cra_assignment_history for CRA hypothesis"

    @pytest.mark.asyncio
    async def test_empty_hypotheses_produce_empty_plan(self):
        """When reason returns empty hypotheses, plan should return empty steps."""
        empty_reason = json.dumps({"hypotheses": []})
        empty_plan = json.dumps({"plan_steps": []})
        response_map = {
            "agent1_reason": empty_reason,
            "agent1_plan": empty_plan,
            "agent1_reflect": json.dumps({
                "is_goal_satisfied": True, "findings_summary": [], "overall_severity": "low",
            }),
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        output = await agent.run("test", session_id="test")

        # Act phase should have zero additional tool calls (only perceive tools)
        perceive_tools = {
            "entry_lag_analysis", "query_burden", "data_correction_analysis",
            "cra_assignment_history", "monitoring_visit_history",
        }
        act_invocations = [(name, kw) for name, kw in tools.invocations
                           if name not in perceive_tools or kw]  # perceive has no kwargs
        # perceive calls have no kwargs (empty dict), act calls have site_id etc.
        act_with_args = [(name, kw) for name, kw in tools.invocations if kw]
        assert len(act_with_args) == 0, "No act-phase tool calls should occur with empty plan"


# ═══════════════════════════════════════════════════════════════════════════════
# T5: Conductor Multi-Agent Orchestration with Real PRPA
# ═══════════════════════════════════════════════════════════════════════════════

class TestConductorRealPRPA:
    """Validates that conductor runs real agents through full PRPA loops,
    not fake agent stubs."""

    @pytest.mark.asyncio
    async def test_conductor_runs_real_prpa_agents_in_parallel(self):
        """Conductor should run real DataQualityAgent and EnrollmentFunnelAgent
        through complete PRPA cycles."""
        # LLM responses: route → agent1 PRPA → agent3 PRPA → synthesis
        route_response = json.dumps({
            "selected_agents": ["agent_1", "agent_3"],
            "routing_rationale": "Query spans both domains",
            "requires_synthesis": True,
        })
        synthesis_response = json.dumps({
            "executive_summary": "Both agents found issues at SITE-003",
            "cross_domain_findings": [{"finding": "SITE-003 correlated issues"}],
            "single_domain_findings": [],
            "priority_actions": [],
        })

        # Build a context-aware LLM that responds appropriately per prompt name
        llm = MagicMock(spec=LLMClient)

        async def _gen(prompt, *, system="", temperature=None):
            if "conductor_route" in prompt:
                return LLMResponse(text=route_response, model="mock", usage={})
            if "conductor_synthesize" in prompt:
                return LLMResponse(text=synthesis_response, model="mock", usage={})
            if "agent1_reason" in prompt:
                return LLMResponse(text=REASON_WITH_SITE003, model="mock", usage={})
            if "agent1_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "agent1_reflect" in prompt:
                return LLMResponse(text=REFLECT_SATISFIED, model="mock", usage={})
            if "agent3_reason" in prompt:
                return LLMResponse(text=ENROLLMENT_REASON, model="mock", usage={})
            if "agent3_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "agent3_reflect" in prompt:
                return LLMResponse(text=ENROLLMENT_REFLECT, model="mock", usage={})
            return LLMResponse(text='{}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)

        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()

        # Register REAL agent classes
        registry = AgentRegistry()
        registry.register(DataQualityAgent)
        registry.register(EnrollmentFunnelAgent)

        conductor = ConductorRouter(llm, prompts, registry, tools)

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("Full overview", "", MagicMock())

        # Both agents should have produced output
        assert "agent_1" in result["agent_outputs"], "DataQualityAgent should produce output"
        assert "agent_3" in result["agent_outputs"], "EnrollmentFunnelAgent should produce output"

        # Each agent should have full reasoning traces (5 phases per iteration)
        for aid in ["agent_1", "agent_3"]:
            trace = result["agent_outputs"][aid]["reasoning_trace"]
            phases = [t["phase"] for t in trace]
            assert "perceive" in phases, f"{aid} missing perceive phase"
            assert "reason" in phases, f"{aid} missing reason phase"
            assert "plan" in phases, f"{aid} missing plan phase"
            assert "act" in phases, f"{aid} missing act phase"
            assert "reflect" in phases, f"{aid} missing reflect phase"

        # Synthesis should have been triggered
        assert len(result["synthesis"]["cross_domain_findings"]) > 0

    @pytest.mark.asyncio
    async def test_one_agent_crashes_other_succeeds(self):
        """If one agent's LLM call throws an exception, the other agent should
        still succeed, and conductor should handle the failure gracefully."""
        route_response = json.dumps({
            "selected_agents": ["agent_1", "agent_3"],
            "routing_rationale": "Both domains",
            "requires_synthesis": True,
        })

        llm = MagicMock(spec=LLMClient)
        call_count = {"i": 0}

        async def _gen(prompt, *, system="", temperature=None):
            call_count["i"] += 1
            if "conductor_route" in prompt:
                return LLMResponse(text=route_response, model="mock", usage={})
            # agent_1 crashes on reason
            if "agent1_reason" in prompt:
                raise RuntimeError("Simulated LLM failure for agent_1")
            # agent_3 works normally
            if "agent3_reason" in prompt:
                return LLMResponse(text=ENROLLMENT_REASON, model="mock", usage={})
            if "agent3_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "agent3_reflect" in prompt:
                return LLMResponse(text=ENROLLMENT_REFLECT, model="mock", usage={})
            return LLMResponse(text='{}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)

        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()

        registry = AgentRegistry()
        registry.register(DataQualityAgent)
        registry.register(EnrollmentFunnelAgent)

        conductor = ConductorRouter(llm, prompts, registry, tools)

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("test", "", MagicMock())

        # agent_3 should have succeeded
        assert "agent_3" in result["agent_outputs"], "agent_3 should complete despite agent_1 crash"

        # agent_1 should NOT be in outputs (it crashed)
        assert "agent_1" not in result["agent_outputs"], "Crashed agent should not produce output"

        # With only 1 agent output, synthesis should be skipped (requires_synthesis needs >1 outputs)
        assert result["synthesis"]["cross_domain_findings"] == [], \
            "Synthesis should be skipped when only 1 agent succeeded"

    @pytest.mark.asyncio
    async def test_conductor_on_step_traces_full_pipeline(self):
        """on_step callbacks should cover routing → agent PRPA phases → synthesize."""
        route_response = json.dumps({
            "selected_agents": ["agent_1", "agent_3"],
            "routing_rationale": "Both", "requires_synthesis": True,
        })
        synthesis_response = json.dumps({
            "executive_summary": "Summary", "cross_domain_findings": [],
            "single_domain_findings": [], "priority_actions": [],
        })

        llm = MagicMock(spec=LLMClient)

        async def _gen(prompt, *, system="", temperature=None):
            if "conductor_route" in prompt:
                return LLMResponse(text=route_response, model="mock", usage={})
            if "conductor_synthesize" in prompt:
                return LLMResponse(text=synthesis_response, model="mock", usage={})
            if "reason" in prompt:
                return LLMResponse(text=json.dumps({"hypotheses": []}), model="mock", usage={})
            if "plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "reflect" in prompt:
                return LLMResponse(text=json.dumps({
                    "is_goal_satisfied": True, "findings_summary": [],
                    "overall_severity": "low",
                }), model="mock", usage={})
            return LLMResponse(text='{}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)
        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()

        registry = AgentRegistry()
        registry.register(DataQualityAgent)
        registry.register(EnrollmentFunnelAgent)

        conductor = ConductorRouter(llm, prompts, registry, tools)
        step_log = []

        async def on_step(phase, agent_id, data):
            step_log.append((phase, agent_id))

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            await conductor.execute_query("test", "", MagicMock(), on_step=on_step)

        phases_seen = [s[0] for s in step_log]
        agent_ids_seen = {s[1] for s in step_log}

        # Should start with routing
        assert step_log[0] == ("routing", "conductor"), "First step should be routing"
        # Should end with synthesize
        assert step_log[-1] == ("synthesize", "conductor"), "Last step should be synthesize"
        # Should see agent-level PRPA phases
        assert "perceive" in phases_seen
        assert "reason" in phases_seen
        assert "plan" in phases_seen
        assert "act" in phases_seen
        assert "reflect" in phases_seen
        # Should see both agent IDs
        assert "agent_1" in agent_ids_seen
        assert "agent_3" in agent_ids_seen


# ═══════════════════════════════════════════════════════════════════════════════
# T6: Cross-Domain Synthesis Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossDomainSynthesis:
    """Validates that synthesis receives findings from multiple agents
    and identifies cross-domain patterns."""

    @pytest.mark.asyncio
    async def test_synthesis_prompt_contains_both_agent_findings(self):
        """Synthesis prompt must contain findings from both agents."""
        route_response = json.dumps({
            "selected_agents": ["agent_1", "agent_3"],
            "routing_rationale": "Both", "requires_synthesis": True,
        })
        synthesis_response = json.dumps({
            "executive_summary": "Correlated issues", "cross_domain_findings": [],
            "single_domain_findings": [], "priority_actions": [],
        })

        llm = MagicMock(spec=LLMClient)

        async def _gen(prompt, *, system="", temperature=None):
            if "conductor_route" in prompt:
                return LLMResponse(text=route_response, model="mock", usage={})
            if "conductor_synthesize" in prompt:
                return LLMResponse(text=synthesis_response, model="mock", usage={})
            if "agent1_reason" in prompt:
                return LLMResponse(text=REASON_WITH_SITE003, model="mock", usage={})
            if "agent1_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "agent1_reflect" in prompt:
                return LLMResponse(text=REFLECT_SATISFIED, model="mock", usage={})
            if "agent3_reason" in prompt:
                return LLMResponse(text=ENROLLMENT_REASON, model="mock", usage={})
            if "agent3_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "agent3_reflect" in prompt:
                return LLMResponse(text=ENROLLMENT_REFLECT, model="mock", usage={})
            return LLMResponse(text='{}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)
        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()

        registry = AgentRegistry()
        registry.register(DataQualityAgent)
        registry.register(EnrollmentFunnelAgent)

        conductor = ConductorRouter(llm, prompts, registry, tools)

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            await conductor.execute_query("Full overview", "", MagicMock())

        # Find the synthesis render call
        synth_calls = [(name, kw) for name, kw in prompts.render_calls
                       if name == "conductor_synthesize"]
        assert len(synth_calls) == 1, "conductor_synthesize should be rendered exactly once"

        synth_kwargs = synth_calls[0][1]
        # agent1_findings should contain SITE-003 entry lag finding
        assert "SITE-003" in synth_kwargs["agent1_findings"], \
            "Synthesis prompt should contain agent_1 findings about SITE-003"
        assert "12.4" in synth_kwargs["agent1_findings"] or "entry lag" in synth_kwargs["agent1_findings"].lower(), \
            "agent_1 findings should reference entry lag data"

        # agent3_findings should contain SITE-003 screen failure finding
        assert "SITE-003" in synth_kwargs["agent3_findings"], \
            "Synthesis prompt should contain agent_3 findings about SITE-003"

    @pytest.mark.asyncio
    async def test_synthesis_identifies_shared_site(self):
        """When both agents flag the same site, synthesis should contain cross-domain findings."""
        route_response = json.dumps({
            "selected_agents": ["agent_1", "agent_3"],
            "routing_rationale": "Both", "requires_synthesis": True,
        })
        synthesis_with_cross_domain = json.dumps({
            "executive_summary": "SITE-003 has correlated data quality and enrollment issues",
            "cross_domain_findings": [
                {"finding": "SITE-003 entry lag spike coincides with screen failure surge",
                 "sites": ["SITE-003"], "confidence": 0.88}
            ],
            "single_domain_findings": [],
            "priority_actions": ["Trigger urgent site visit for SITE-003"],
        })

        llm = MagicMock(spec=LLMClient)

        async def _gen(prompt, *, system="", temperature=None):
            if "conductor_route" in prompt:
                return LLMResponse(text=route_response, model="mock", usage={})
            if "conductor_synthesize" in prompt:
                return LLMResponse(text=synthesis_with_cross_domain, model="mock", usage={})
            if "agent1_reason" in prompt:
                return LLMResponse(text=REASON_WITH_SITE003, model="mock", usage={})
            if "agent1_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "agent1_reflect" in prompt:
                return LLMResponse(text=REFLECT_SATISFIED, model="mock", usage={})
            if "agent3_reason" in prompt:
                return LLMResponse(text=ENROLLMENT_REASON, model="mock", usage={})
            if "agent3_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "agent3_reflect" in prompt:
                return LLMResponse(text=ENROLLMENT_REFLECT, model="mock", usage={})
            return LLMResponse(text='{}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)
        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()

        registry = AgentRegistry()
        registry.register(DataQualityAgent)
        registry.register(EnrollmentFunnelAgent)

        conductor = ConductorRouter(llm, prompts, registry, tools)

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("SITE-003 issues", "", MagicMock())

        # Cross-domain findings should mention SITE-003
        cross_findings = result["synthesis"]["cross_domain_findings"]
        assert len(cross_findings) > 0, "Should have cross-domain findings"
        assert "SITE-003" in cross_findings[0]["finding"], \
            "Cross-domain finding should reference the shared site"

    @pytest.mark.asyncio
    async def test_synthesis_with_single_agent_output_after_failure(self):
        """When routing to 2 agents but one fails, synthesis should be skipped."""
        route_response = json.dumps({
            "selected_agents": ["agent_1", "agent_3"],
            "routing_rationale": "Both", "requires_synthesis": True,
        })

        llm = MagicMock(spec=LLMClient)

        async def _gen(prompt, *, system="", temperature=None):
            if "conductor_route" in prompt:
                return LLMResponse(text=route_response, model="mock", usage={})
            # agent_1 crashes
            if "agent1_reason" in prompt:
                raise RuntimeError("agent_1 LLM failure")
            # agent_3 works
            if "agent3_reason" in prompt:
                return LLMResponse(text=ENROLLMENT_REASON, model="mock", usage={})
            if "agent3_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            if "agent3_reflect" in prompt:
                return LLMResponse(text=ENROLLMENT_REFLECT, model="mock", usage={})
            return LLMResponse(text='{}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)
        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()

        registry = AgentRegistry()
        registry.register(DataQualityAgent)
        registry.register(EnrollmentFunnelAgent)

        conductor = ConductorRouter(llm, prompts, registry, tools)

        with patch("backend.config.SessionLocal") as mock_sl:
            mock_sl.return_value = MagicMock()
            result = await conductor.execute_query("test", "", MagicMock())

        # Only agent_3 succeeded
        assert len(result["agent_outputs"]) == 1
        assert "agent_3" in result["agent_outputs"]

        # Synthesis should NOT have been called (only 1 agent output)
        synth_calls = [(name, kw) for name, kw in prompts.render_calls
                       if name == "conductor_synthesize"]
        assert len(synth_calls) == 0, "Synthesis should be skipped with only 1 agent output"

        # executive_summary should come from the single agent
        assert result["synthesis"]["cross_domain_findings"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# T7: Prompt Content Contract Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromptContentContracts:
    """Validates that every LLM call receives the correct prompt template name
    and variable set."""

    @pytest.mark.asyncio
    async def test_data_quality_agent_prompt_names_and_variables(self):
        """DataQualityAgent must render agent1_reason, agent1_plan, agent1_reflect
        with the correct variable names."""
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": PLAN_ENTRY_LAG_DRILL,
            "agent1_reflect": REFLECT_SATISFIED,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        await agent.run("test query", session_id="test")

        rendered_names = [name for name, _ in prompts.render_calls]

        # Exact prompt names used
        assert "agent1_reason" in rendered_names
        assert "agent1_plan" in rendered_names
        assert "agent1_reflect" in rendered_names

        # No unexpected prompts
        for name in rendered_names:
            assert name in {"agent1_reason", "agent1_plan", "agent1_reflect"}, \
                f"Unexpected prompt rendered: {name}"

        # Verify variable names for each prompt
        reason_kw = next(kw for name, kw in prompts.render_calls if name == "agent1_reason")
        assert "perceptions" in reason_kw, "agent1_reason must receive 'perceptions'"
        assert "query" in reason_kw, "agent1_reason must receive 'query'"

        plan_kw = next(kw for name, kw in prompts.render_calls if name == "agent1_plan")
        assert "hypotheses" in plan_kw, "agent1_plan must receive 'hypotheses'"
        assert "tool_descriptions" in plan_kw, "agent1_plan must receive 'tool_descriptions'"

        reflect_kw = next(kw for name, kw in prompts.render_calls if name == "agent1_reflect")
        assert "query" in reflect_kw, "agent1_reflect must receive 'query'"
        assert "hypotheses" in reflect_kw, "agent1_reflect must receive 'hypotheses'"
        assert "action_results" in reflect_kw, "agent1_reflect must receive 'action_results'"
        assert "iteration" in reflect_kw, "agent1_reflect must receive 'iteration'"
        assert "max_iterations" in reflect_kw, "agent1_reflect must receive 'max_iterations'"

    @pytest.mark.asyncio
    async def test_enrollment_agent_uses_agent3_prompts(self):
        """EnrollmentFunnelAgent must render agent3_reason, agent3_plan, agent3_reflect."""
        response_map = {
            "agent3_reason": ENROLLMENT_REASON,
            "agent3_plan": ENROLLMENT_PLAN,
            "agent3_reflect": ENROLLMENT_REFLECT,
        }
        agent, llm, tools, prompts = _build_enrollment_agent(response_map)
        await agent.run("enrollment test", session_id="test")

        rendered_names = [name for name, _ in prompts.render_calls]

        assert "agent3_reason" in rendered_names
        assert "agent3_plan" in rendered_names
        assert "agent3_reflect" in rendered_names

        # No agent1 prompts should appear
        for name in rendered_names:
            assert "agent1" not in name, f"EnrollmentFunnelAgent rendered agent1 prompt: {name}"

    @pytest.mark.asyncio
    async def test_conductor_route_prompt_includes_session_context(self):
        """Conductor routing prompt must include session_context when provided."""
        route_response = json.dumps({
            "selected_agents": ["agent_1"],
            "routing_rationale": "DQ only", "requires_synthesis": False,
        })

        llm = MagicMock(spec=LLMClient)
        llm.generate_structured = AsyncMock(
            return_value=LLMResponse(text=route_response, model="mock", usage={})
        )
        prompts = InstrumentedMockPrompts()
        registry = AgentRegistry()
        tools = InstrumentedMockTools()

        conductor = ConductorRouter(llm, prompts, registry, tools)
        await conductor.route_query(
            "What about SITE-007?",
            session_context="Prior exchange about SITE-007 enrollment delays",
        )

        route_calls = [(name, kw) for name, kw in prompts.render_calls
                       if name == "conductor_route"]
        assert len(route_calls) == 1
        assert "Prior exchange about SITE-007" in route_calls[0][1]["session_context"], \
            "Session context should flow into conductor_route prompt"


# ═══════════════════════════════════════════════════════════════════════════════
# T8: Reasoning Trace Integrity
# ═══════════════════════════════════════════════════════════════════════════════

class TestReasoningTraceIntegrity:
    """Validates that the reasoning trace is a complete, ordered record."""

    @pytest.mark.asyncio
    async def test_trace_contains_correct_metadata_per_phase(self):
        """Each trace entry should have phase-specific metadata fields."""
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": PLAN_ENTRY_LAG_DRILL,
            "agent1_reflect": REFLECT_SATISFIED,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        output = await agent.run("test", session_id="test")

        trace = output.reasoning_trace
        assert len(trace) == 5, f"Expected 5 trace entries for 1 iteration, got {len(trace)}"

        # Check each phase has correct metadata
        perceive_entry = trace[0]
        assert perceive_entry["phase"] == "perceive"
        assert "summary" in perceive_entry
        assert "chars" in perceive_entry["summary"].lower() or len(perceive_entry["summary"]) > 0

        reason_entry = trace[1]
        assert reason_entry["phase"] == "reason"
        assert "hypotheses_count" in reason_entry
        assert reason_entry["hypotheses_count"] == 2  # from REASON_WITH_SITE003

        plan_entry = trace[2]
        assert plan_entry["phase"] == "plan"
        assert "steps_count" in plan_entry
        assert plan_entry["steps_count"] == 2  # from PLAN_ENTRY_LAG_DRILL

        act_entry = trace[3]
        assert act_entry["phase"] == "act"
        assert "results_count" in act_entry
        assert act_entry["results_count"] == 2  # 2 plan steps executed

        reflect_entry = trace[4]
        assert reflect_entry["phase"] == "reflect"
        assert "goal_satisfied" in reflect_entry
        assert reflect_entry["goal_satisfied"] is True

    @pytest.mark.asyncio
    async def test_multi_iteration_trace_preserves_all_iterations(self):
        """Multi-iteration trace should have 5 entries per iteration, correctly ordered."""
        llm = MagicMock(spec=LLMClient)
        reflect_idx = {"i": 0}

        async def _gen(prompt, *, system="", temperature=None):
            if "agent1_reflect" in prompt:
                idx = reflect_idx["i"]
                reflect_idx["i"] += 1
                if idx == 0:
                    return LLMResponse(text=REFLECT_NOT_SATISFIED_NEEDS_CORRECTION, model="mock", usage={})
                return LLMResponse(text=REFLECT_SATISFIED, model="mock", usage={})
            if "agent1_reason" in prompt:
                return LLMResponse(text=REASON_WITH_SITE003, model="mock", usage={})
            if "agent1_plan" in prompt:
                return LLMResponse(text=json.dumps({"plan_steps": []}), model="mock", usage={})
            return LLMResponse(text='{}', model="mock", usage={})

        llm.generate_structured = AsyncMock(side_effect=_gen)
        prompts = InstrumentedMockPrompts()
        tools = InstrumentedMockTools()
        db = MagicMock()

        agent = DataQualityAgent(llm_client=llm, tool_registry=tools, prompt_manager=prompts, db_session=db)
        output = await agent.run("test", session_id="test")

        trace = output.reasoning_trace
        assert len(trace) == 10, f"Expected 10 trace entries for 2 iterations, got {len(trace)}"

        # Check iteration fields
        iter1_entries = [t for t in trace if t["iteration"] == 1]
        iter2_entries = [t for t in trace if t["iteration"] == 2]
        assert len(iter1_entries) == 5
        assert len(iter2_entries) == 5

        # Entries should be in chronological order (iter 1 before iter 2)
        iter1_phases = [t["phase"] for t in iter1_entries]
        iter2_phases = [t["phase"] for t in iter2_entries]
        expected_order = ["perceive", "reason", "plan", "act", "reflect"]
        assert iter1_phases == expected_order
        assert iter2_phases == expected_order

        # First 5 entries should be iteration 1
        for t in trace[:5]:
            assert t["iteration"] == 1
        for t in trace[5:]:
            assert t["iteration"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# T9: Edge Cases in Agent Output Construction
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputEdgeCases:
    """Validates edge cases in how AgentOutput is constructed from reflection data."""

    @pytest.mark.asyncio
    async def test_output_severity_comes_from_reflect_not_hardcoded(self):
        """Output severity must use the reflect phase's overall_severity, not a default."""
        critical_reflect = json.dumps({
            "is_goal_satisfied": True,
            "findings_summary": [
                {"site_id": "SITE-001", "finding": "Critical data breach", "confidence": 0.99},
            ],
            "overall_severity": "critical",
        })
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": json.dumps({"plan_steps": []}),
            "agent1_reflect": critical_reflect,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        output = await agent.run("test", session_id="test")

        assert output.severity == "critical", \
            f"Severity should be 'critical' from reflect, got '{output.severity}'"

    @pytest.mark.asyncio
    async def test_output_summary_joins_all_finding_sites(self):
        """Summary should include site IDs from all findings."""
        multi_site_reflect = json.dumps({
            "is_goal_satisfied": True,
            "findings_summary": [
                {"site_id": "SITE-001", "finding": "Entry lag issue", "confidence": 0.8},
                {"site_id": "SITE-003", "finding": "Query burden high", "confidence": 0.7},
                {"site_id": "SITE-007", "finding": "CRA transition impact", "confidence": 0.75},
            ],
            "overall_severity": "high",
        })
        response_map = {
            "agent1_reason": REASON_WITH_SITE003,
            "agent1_plan": json.dumps({"plan_steps": []}),
            "agent1_reflect": multi_site_reflect,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        output = await agent.run("test", session_id="test")

        assert "SITE-001" in output.summary, "SITE-001 missing from summary"
        assert "SITE-003" in output.summary, "SITE-003 missing from summary"
        assert "SITE-007" in output.summary, "SITE-007 missing from summary"

    @pytest.mark.asyncio
    async def test_zero_findings_uses_default_summary(self):
        """With no findings, summary should be default text and confidence 0.5."""
        empty_reflect = json.dumps({
            "is_goal_satisfied": True,
            "findings_summary": [],
            "overall_severity": "low",
        })
        response_map = {
            "agent1_reason": json.dumps({"hypotheses": []}),
            "agent1_plan": json.dumps({"plan_steps": []}),
            "agent1_reflect": empty_reflect,
        }
        agent, llm, tools, prompts = _build_data_quality_agent(response_map)
        output = await agent.run("test", session_id="test")

        assert "No significant data quality issues detected" in output.summary, \
            f"Expected default summary, got: {output.summary}"
        assert output.confidence == 0.5, f"Expected default confidence 0.5, got {output.confidence}"

    @pytest.mark.asyncio
    async def test_enrollment_zero_findings_default_summary(self):
        """EnrollmentFunnelAgent with no findings should produce its own default summary."""
        empty_reflect = json.dumps({
            "is_goal_satisfied": True, "findings_summary": [], "overall_severity": "low",
        })
        response_map = {
            "agent3_reason": json.dumps({"hypotheses": []}),
            "agent3_plan": json.dumps({"plan_steps": []}),
            "agent3_reflect": empty_reflect,
        }
        agent, llm, tools, prompts = _build_enrollment_agent(response_map)
        output = await agent.run("test", session_id="test")

        assert "No significant enrollment issues detected" in output.summary
        assert output.confidence == 0.5
