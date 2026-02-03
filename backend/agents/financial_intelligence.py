"""Financial Intelligence Agent — investigates budget health, cost efficiency,
vendor spending patterns, and financial impact of operational delays.

Provides risk-adjusted forecasting and budget reallocation recommendations.
All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import json
import logging

from backend.agents.base import BaseAgent, AgentContext, AgentOutput

logger = logging.getLogger(__name__)


class FinancialIntelligenceAgent(BaseAgent):
    agent_id = "financial_intelligence"
    agent_name = "Financial Intelligence Agent"
    description = (
        "Investigates budget health, cost efficiency, vendor spending patterns, "
        "and financial impact of operational delays. Provides risk-adjusted "
        "forecasting and budget reallocation recommendations."
    )

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad SQL queries to gather raw financial signals across all sites."""
        logger.info("[%s] PERCEIVE: gathering raw financial signals", self.agent_id)

        budget_variance = await self.tools.invoke("budget_variance_analysis", self.db)
        cost_per_patient = await self.tools.invoke("cost_per_patient_analysis", self.db)
        burn_rate = await self.tools.invoke("burn_rate_projection", self.db)
        change_orders = await self.tools.invoke("change_order_impact", self.db)
        delay_impact = await self.tools.invoke("financial_impact_of_delays", self.db)
        sites = await self.tools.invoke("site_summary", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "budget_variance": budget_variance.data if budget_variance.success else [],
            "cost_per_patient": cost_per_patient.data if cost_per_patient.success else [],
            "burn_rate": burn_rate.data if burn_rate.success else [],
            "change_orders": change_orders.data if change_orders.success else [],
            "delay_impact": delay_impact.data if delay_impact.success else [],
        }
        logger.info("[%s] PERCEIVE: gathered %d sites, %d budget variance, %d cost/patient, %d burn rate, %d change order, %d delay impact records",
                     self.agent_id,
                     len(perceptions["site_metadata"]),
                     len(perceptions["budget_variance"]), len(perceptions["cost_per_patient"]),
                     len(perceptions["burn_rate"]), len(perceptions["change_orders"]),
                     len(perceptions["delay_impact"]))
        return perceptions

    async def reason(self, ctx: AgentContext) -> list:
        """LLM-driven hypothesis generation from perception data."""
        logger.info("[%s] REASON: generating hypotheses via LLM", self.agent_id)

        site_directory = json.dumps(
            [{"site_id": s["site_id"], "name": s["name"]}
             for s in ctx.perceptions.get("site_metadata", [])
             if isinstance(s, dict) and "site_id" in s and "name" in s],
            default=str,
        )

        prompt = self.prompts.render(
            "financial_intelligence_reason",
            perceptions=self._safe_json_str(ctx.perceptions),
            query=ctx.query,
            site_directory=site_directory,
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical trial financial operations expert. Respond with valid JSON only.",
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
        """LLM-driven investigation plan — the LLM chooses tools and order."""
        logger.info("[%s] PLAN: generating investigation plan via LLM", self.agent_id)

        prompt = self.prompts.render(
            "financial_intelligence_plan",
            hypotheses=self._safe_json_str(ctx.hypotheses),
            tool_descriptions=self.tools.list_tools_text(),
            prior_results=self._safe_json_str(ctx.action_results) if ctx.iteration > 1 else "First iteration — no prior results.",
            iteration=str(ctx.iteration),
            reflection_gaps=self._safe_json_str(ctx.reflection.get("remaining_gaps", [])) if ctx.iteration > 1 else "N/A",
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical trial financial investigator. Respond with valid JSON only.",
        )
        try:
            parsed = self._parse_json(response.text)
            steps = parsed.get("plan_steps", [])
            logger.info("[%s] PLAN: %d investigation steps planned", self.agent_id, len(steps))
            return steps
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] PLAN: failed to parse LLM response: %s", self.agent_id, e)
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
        """LLM evaluates whether the investigation reached root cause."""
        logger.info("[%s] REFLECT: evaluating completeness via LLM", self.agent_id)

        prompt = self.prompts.render(
            "financial_intelligence_reflect",
            query=ctx.query,
            hypotheses=self._safe_json_str(ctx.hypotheses),
            action_results=self._safe_json_str(ctx.action_results),
            iteration=str(ctx.iteration),
            max_iterations=str(ctx.max_iterations),
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical trial financial operations expert. Respond with valid JSON only.",
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
            finding_type="financial_intelligence_analysis",
            severity=severity,
            summary="; ".join(summary_parts) if summary_parts else "No significant financial issues detected.",
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
