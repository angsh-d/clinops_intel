"""Competitive Intelligence Agent — searches ClinicalTrials.gov for competing
trials near sites with unexplained enrollment decline.

All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import json
import logging

from backend.agents.base import BaseAgent, AgentContext, AgentOutput

logger = logging.getLogger(__name__)


class ClinicalTrialsGovAgent(BaseAgent):
    agent_id = "clinical_trials_gov"
    agent_name = "Competitive Intelligence Agent"
    description = (
        "Searches ClinicalTrials.gov for competing trials near sites with "
        "unexplained enrollment decline. Provides external evidence for enrollment "
        "cannibalization hypotheses."
    )

    async def perceive(self, ctx: AgentContext) -> dict:
        """Gather site locations and enrollment velocity timelines."""
        logger.info("[%s] PERCEIVE: gathering site locations + enrollment velocity", self.agent_id)

        sites = await self.tools.invoke("site_summary", self.db)
        velocity = await self.tools.invoke("enrollment_velocity", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "enrollment_velocity": velocity.data if velocity.success else [],
        }
        logger.info("[%s] PERCEIVE: %d sites, %d velocity records",
                     self.agent_id,
                     len(perceptions["site_metadata"]),
                     len(perceptions["enrollment_velocity"]))
        return perceptions

    async def reason(self, ctx: AgentContext) -> list:
        """LLM identifies sites with enrollment decline and generates competing trial hypotheses."""
        logger.info("[%s] REASON: generating hypotheses via LLM", self.agent_id)

        site_directory = json.dumps(
            [{"site_id": s["site_id"], "name": s["name"], "city": s.get("city", ""), "country": s.get("country", "")}
             for s in ctx.perceptions.get("site_metadata", [])
             if isinstance(s, dict) and "site_id" in s and "name" in s],
            default=str,
        )

        prompt = self.prompts.render(
            "clinical_trials_gov_reason",
            perceptions=self._safe_json_str(ctx.perceptions),
            query=ctx.query,
            site_directory=site_directory,
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a competitive intelligence analyst for clinical trials. Respond with valid JSON only.",
        )
        try:
            parsed = self._parse_json(response.text)
            hypotheses = parsed.get("hypotheses", [])
            logger.info("[%s] REASON: generated %d hypotheses", self.agent_id, len(hypotheses))
            return hypotheses
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] REASON: failed to parse LLM response: %s", self.agent_id, e)
            raise RuntimeError(f"[{self.agent_id}] REASON phase failed to parse LLM response: {e}") from e

    async def plan(self, ctx: AgentContext) -> list:
        """LLM plans ClinicalTrials.gov API searches per site."""
        logger.info("[%s] PLAN: generating search plan via LLM", self.agent_id)

        prompt = self.prompts.render(
            "clinical_trials_gov_plan",
            hypotheses=self._safe_json_str(ctx.hypotheses),
            tool_descriptions=self.tools.list_tools_text(),
            prior_results=self._safe_json_str(ctx.action_results) if ctx.iteration > 1 else "First iteration — no prior results.",
            iteration=str(ctx.iteration),
            reflection_gaps=self._safe_json_str(ctx.reflection.get("remaining_gaps", [])) if ctx.iteration > 1 else "N/A",
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a competitive intelligence investigator. Respond with valid JSON only.",
        )
        try:
            parsed = self._parse_json(response.text)
            steps = parsed.get("plan_steps", [])
            logger.info("[%s] PLAN: %d search steps planned", self.agent_id, len(steps))
            return steps
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] PLAN: failed to parse: %s", self.agent_id, e)
            return []

    async def act(self, ctx: AgentContext) -> list:
        """Execute planned ClinicalTrials.gov API calls."""
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
        """LLM evaluates temporal alignment between competing trials and enrollment decline."""
        logger.info("[%s] REFLECT: evaluating competitive landscape findings", self.agent_id)

        prompt = self.prompts.render(
            "clinical_trials_gov_reflect",
            query=ctx.query,
            hypotheses=self._safe_json_str(ctx.hypotheses),
            action_results=self._safe_json_str(ctx.action_results),
            iteration=str(ctx.iteration),
            max_iterations=str(ctx.max_iterations),
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a competitive intelligence analyst for clinical trials. Respond with valid JSON only.",
        )
        try:
            parsed = self._parse_json(response.text)
            logger.info("[%s] REFLECT: goal_satisfied=%s, findings=%d",
                        self.agent_id,
                        parsed.get("is_goal_satisfied"),
                        len(parsed.get("findings_summary", [])))
            return parsed
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] REFLECT: failed to parse: %s", self.agent_id, e)
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
            finding_type="competing_trial_analysis",
            severity=severity,
            summary="; ".join(summary_parts) if summary_parts else "No competing trials detected.",
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
