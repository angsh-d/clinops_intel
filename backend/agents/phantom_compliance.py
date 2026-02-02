"""Phantom Compliance Detection Agent — detects suspiciously perfect data
that may indicate fabrication or variance suppression.

Cross-references entry lag variance, query aging, monitoring findings, and
randomization patterns. Near-zero variance across multiple domains simultaneously
is the key signal.
"""

import json
import logging

from backend.agents.base import BaseAgent, AgentContext, AgentOutput

logger = logging.getLogger(__name__)


class PhantomComplianceAgent(BaseAgent):
    agent_id = "phantom_compliance"
    agent_name = "Data Integrity Agent"
    description = (
        "Detects suspiciously perfect data that may indicate fabrication or variance suppression. "
        "Cross-references entry lag variance, query aging, monitoring findings, and randomization "
        "patterns across sites. Flags sites where multiple domains simultaneously show near-zero "
        "variance — a statistical impossibility in real clinical operations."
    )

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad variance analysis across sites to detect suppressed randomness."""
        logger.info("[%s] PERCEIVE: gathering data variance signals", self.agent_id)

        variance = await self.tools.invoke("data_variance_analysis", self.db)
        sites = await self.tools.invoke("site_summary", self.db)
        query_burden = await self.tools.invoke("query_burden", self.db)
        monitoring = await self.tools.invoke("monitoring_visit_history", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "data_variance": variance.data if variance.success else [],
            "query_burden": query_burden.data if query_burden.success else [],
            "monitoring_visits": monitoring.data if monitoring.success else [],
        }
        logger.info("[%s] PERCEIVE: gathered %d sites, %d variance, %d query, %d monitoring records",
                     self.agent_id,
                     len(perceptions["site_metadata"]),
                     len(perceptions["data_variance"]),
                     len(perceptions["query_burden"]),
                     len(perceptions["monitoring_visits"]))
        return perceptions

    async def reason(self, ctx: AgentContext) -> list:
        """LLM identifies sites with suppressed variance across multiple domains."""
        logger.info("[%s] REASON: generating hypotheses via LLM", self.agent_id)

        site_directory = json.dumps(
            [{"site_id": s["site_id"], "name": s["name"]}
             for s in ctx.perceptions.get("site_metadata", [])
             if isinstance(s, dict) and "site_id" in s and "name" in s],
            default=str,
        )

        prompt = self.prompts.render(
            "phantom_compliance_reason",
            perceptions=self._safe_json_str(ctx.perceptions),
            query=ctx.query,
            site_directory=site_directory,
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical data integrity expert specializing in fraud detection. Respond with valid JSON only.",
        )
        try:
            parsed = self._parse_json(response.text)
            hypotheses = parsed.get("hypotheses", [])
            logger.info("[%s] REASON: generated %d hypotheses", self.agent_id, len(hypotheses))
            return hypotheses
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] REASON: failed to parse LLM response: %s", self.agent_id, e)
            raise RuntimeError(f"[{self.agent_id}] REASON phase failed: {e}") from e

    async def plan(self, ctx: AgentContext) -> list:
        """LLM plans deep-dive tools for suspect sites."""
        logger.info("[%s] PLAN: generating investigation plan via LLM", self.agent_id)

        prompt = self.prompts.render(
            "phantom_compliance_plan",
            hypotheses=self._safe_json_str(ctx.hypotheses),
            tool_descriptions=self.tools.list_tools_text(),
            prior_results=self._safe_json_str(ctx.action_results) if ctx.iteration > 1 else "First iteration — no prior results.",
            iteration=str(ctx.iteration),
            reflection_gaps=self._safe_json_str(ctx.reflection.get("remaining_gaps", [])) if ctx.iteration > 1 else "N/A",
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical data integrity investigator. Respond with valid JSON only.",
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
        """LLM evaluates whether the integrity investigation is complete."""
        logger.info("[%s] REFLECT: evaluating completeness via LLM", self.agent_id)

        prompt = self.prompts.render(
            "phantom_compliance_reflect",
            query=ctx.query,
            hypotheses=self._safe_json_str(ctx.hypotheses),
            action_results=self._safe_json_str(ctx.action_results),
            iteration=str(ctx.iteration),
            max_iterations=str(ctx.max_iterations),
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical data integrity expert. Respond with valid JSON only.",
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
            raise RuntimeError(f"[{self.agent_id}] REFLECT phase failed: {e}") from e

    async def _build_output(self, ctx: AgentContext) -> AgentOutput:
        """Build structured output from the completed PRPA context."""
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
            finding_type="phantom_compliance_analysis",
            severity=severity,
            summary="; ".join(summary_parts) if summary_parts else "No data integrity concerns detected.",
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
