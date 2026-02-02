"""Agent 1: Data Quality Agent — investigates eCRF entry lags, query burden,
data corrections, CRA assignments, and monitoring-related data quality signals.

All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import json
import logging

from backend.agents.base import BaseAgent, AgentContext, AgentOutput

logger = logging.getLogger(__name__)


class DataQualityAgent(BaseAgent):
    agent_id = "data_quality"
    agent_name = "Data Quality Agent"
    description = (
        "Investigates eCRF entry lags, query burden, data corrections, CRA assignments, "
        "and monitoring-related data quality signals. Detects non-obvious patterns like "
        "CRA transition impacts, monitoring gap hidden debt, and strict PI paradoxes."
    )

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad SQL queries to gather raw data quality signals across all sites."""
        logger.info("[%s] PERCEIVE: gathering raw data quality signals", self.agent_id)

        # Gather from multiple tools in parallel-ish fashion
        entry_lag = await self.tools.invoke("entry_lag_analysis", self.db)
        query_burden = await self.tools.invoke("query_burden", self.db)
        corrections = await self.tools.invoke("data_correction_analysis", self.db)
        cra_history = await self.tools.invoke("cra_assignment_history", self.db)
        monitoring = await self.tools.invoke("monitoring_visit_history", self.db)
        sites = await self.tools.invoke("site_summary", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "entry_lag": entry_lag.data if entry_lag.success else [],
            "query_burden": query_burden.data if query_burden.success else [],
            "corrections": corrections.data if corrections.success else [],
            "cra_history": cra_history.data if cra_history.success else [],
            "monitoring_visits": monitoring.data if monitoring.success else [],
        }
        logger.info("[%s] PERCEIVE: gathered %d sites, %d entry lag, %d query, %d correction, %d CRA, %d monitoring records",
                     self.agent_id,
                     len(perceptions["site_metadata"]),
                     len(perceptions["entry_lag"]), len(perceptions["query_burden"]),
                     len(perceptions["corrections"]), len(perceptions["cra_history"]),
                     len(perceptions["monitoring_visits"]))
        return perceptions

    async def reason(self, ctx: AgentContext) -> list:
        """LLM-driven hypothesis generation from perception data."""
        logger.info("[%s] REASON: generating hypotheses via LLM", self.agent_id)

        # Compact site directory (site_id + name only) passed separately to avoid
        # truncation by _safe_json_str — the full perceptions dict gets trimmed to
        # ~30K chars which can drop sites beyond the first 10-20, making entity
        # resolution impossible for mid/high-numbered site IDs.
        site_directory = json.dumps(
            [{"site_id": s["site_id"], "name": s["name"]}
             for s in ctx.perceptions.get("site_metadata", [])
             if isinstance(s, dict) and "site_id" in s and "name" in s],
            default=str,
        )

        prompt = self.prompts.render(
            "data_quality_reason",
            perceptions=self._safe_json_str(ctx.perceptions),
            query=ctx.query,
            site_directory=site_directory,
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical operations data quality expert. Respond with valid JSON only.",
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
            "data_quality_plan",
            hypotheses=self._safe_json_str(ctx.hypotheses),
            tool_descriptions=self.tools.list_tools_text(),
            prior_results=self._safe_json_str(ctx.action_results) if ctx.iteration > 1 else "First iteration — no prior results.",
            iteration=str(ctx.iteration),
            reflection_gaps=self._safe_json_str(ctx.reflection.get("remaining_gaps", [])) if ctx.iteration > 1 else "N/A",
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
            "data_quality_reflect",
            query=ctx.query,
            hypotheses=self._safe_json_str(ctx.hypotheses),
            action_results=self._safe_json_str(ctx.action_results),
            iteration=str(ctx.iteration),
            max_iterations=str(ctx.max_iterations),
        )
        response = await self.llm.generate_structured(
            prompt,
            system="You are a clinical operations data quality expert. Respond with valid JSON only.",
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
            finding_type="data_quality_analysis",
            severity=severity,
            summary="; ".join(summary_parts) if summary_parts else "No significant data quality issues detected.",
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
