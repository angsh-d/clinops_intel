"""Agent 3: Enrollment Funnel Agent — investigates screening volume, screen failure
rates, randomization, enrollment velocity, consent withdrawals, and regional patterns.

All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import json
import logging

from backend.agents.base import BaseAgent, AgentContext, AgentOutput

logger = logging.getLogger(__name__)


class EnrollmentFunnelAgent(BaseAgent):
    agent_id = "agent_3"
    agent_name = "Enrollment Funnel Agent"
    description = (
        "Investigates screening volume, screen failure rates, randomization velocity, "
        "consent withdrawals, and regional enrollment patterns. Detects competing trials, "
        "supply-chain-masked withdrawals, strict PI paradoxes, and funnel stage decomposition."
    )

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad data ingestion — screening, randomization, velocity, failure patterns."""
        logger.info("[%s] PERCEIVE: gathering enrollment funnel signals", self.agent_id)

        funnel = await self.tools.invoke("screening_funnel", self.db)
        velocity = await self.tools.invoke("enrollment_velocity", self.db)
        failures = await self.tools.invoke("screen_failure_pattern", self.db, include_narratives=True)
        regional = await self.tools.invoke("regional_comparison", self.db)
        sites = await self.tools.invoke("site_summary", self.db)
        kit_inv = await self.tools.invoke("kit_inventory", self.db)

        perceptions = {
            "screening_funnel": funnel.data if funnel.success else [],
            "enrollment_velocity": velocity.data if velocity.success else [],
            "failure_patterns": failures.data if failures.success else {},
            "regional_comparison": regional.data if regional.success else {},
            "site_metadata": sites.data if sites.success else [],
            "kit_inventory": kit_inv.data if kit_inv.success else [],
        }
        logger.info("[%s] PERCEIVE: gathered %d funnel, %d velocity records",
                     self.agent_id,
                     len(perceptions["screening_funnel"]),
                     len(perceptions["enrollment_velocity"]))
        return perceptions

    async def reason(self, ctx: AgentContext) -> list:
        """LLM-driven hypothesis generation for enrollment signals."""
        logger.info("[%s] REASON: generating hypotheses via LLM", self.agent_id)

        prompt = self.prompts.render(
            "agent3_reason",
            perceptions=self._safe_json_str(ctx.perceptions),
            query=ctx.query,
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical operations enrollment expert. Respond with valid JSON only.",
        )
        try:
            parsed = self._parse_json(response.text)
            hypotheses = parsed.get("hypotheses", [])
            logger.info("[%s] REASON: generated %d hypotheses", self.agent_id, len(hypotheses))
            return hypotheses
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] REASON: failed to parse LLM response: %s\nRaw text: %s", self.agent_id, e, response.text[:500])
            raise RuntimeError(f"[{self.agent_id}] REASON phase failed to parse LLM response: {e}") from e

    async def plan(self, ctx: AgentContext) -> list:
        """LLM decides which tools to invoke and in what order."""
        logger.info("[%s] PLAN: generating investigation plan via LLM", self.agent_id)

        prompt = self.prompts.render(
            "agent3_plan",
            hypotheses=self._safe_json_str(ctx.hypotheses),
            tool_descriptions=self.tools.list_tools_text(),
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical operations investigator. Respond with valid JSON only.",
        )
        try:
            parsed = self._parse_json(response.text)
            steps = parsed.get("plan_steps", [])
            logger.info("[%s] PLAN: %d investigation steps planned", self.agent_id, len(steps))
            return steps
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] PLAN: failed to parse: %s", self.agent_id, e)
            return []

    async def act(self, ctx: AgentContext) -> list:
        """Execute each LLM-planned tool invocation."""
        logger.info("[%s] ACT: executing %d planned steps", self.agent_id, len(ctx.plan_steps))
        results = []

        for step in ctx.plan_steps:
            tool_name = step.get("tool_name", "")
            tool_args = step.get("tool_args", {})
            purpose = step.get("purpose", "")
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

        return results

    async def reflect(self, ctx: AgentContext) -> dict:
        """LLM evaluates whether the investigation identified binding constraints."""
        logger.info("[%s] REFLECT: evaluating completeness via LLM", self.agent_id)

        prompt = self.prompts.render(
            "agent3_reflect",
            query=ctx.query,
            hypotheses=self._safe_json_str(ctx.hypotheses),
            action_results=self._safe_json_str(ctx.action_results),
            iteration=str(ctx.iteration),
            max_iterations=str(ctx.max_iterations),
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical operations enrollment expert. Respond with valid JSON only.",
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

    async def _build_output(self, ctx: AgentContext) -> AgentOutput:
        """Build structured output from completed PRPA context."""
        findings = ctx.reflection.get("findings_summary", [])

        confidences = [f.get("confidence", 0) for f in findings]
        if not confidences:
            raise RuntimeError(f"[{self.agent_id}] _build_output: no findings produced after PRPA loop")
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
            finding_type="enrollment_funnel_analysis",
            severity=severity,
            summary="; ".join(summary_parts) if summary_parts else "No significant enrollment issues detected.",
            detail={
                "findings": findings,
                "remaining_gaps": ctx.reflection.get("remaining_gaps", []),
                "cross_domain_followup": ctx.reflection.get("cross_domain_followup", []),
            },
            data_signals=ctx.perceptions,
            reasoning_trace=ctx.reasoning_trace,
            confidence=avg_confidence,
            findings=findings,
        )
