"""Agent 1: Data Quality Agent — investigates eCRF entry lags, query burden,
data corrections, CRA assignments, and monitoring-related data quality signals.

All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import logging

from backend.agents.base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class DataQualityAgent(BaseAgent):
    agent_id = "data_quality"
    agent_name = "Data Quality Agent"
    description = (
        "Investigates eCRF entry lags, query burden, data corrections, CRA assignments, "
        "and monitoring-related data quality signals. Detects non-obvious patterns like "
        "CRA transition impacts, monitoring gap hidden debt, and strict PI paradoxes."
    )

    finding_type = "data_quality_analysis"
    prompt_prefix = "data_quality"
    system_prompt_reason = "You are a clinical operations data quality expert. Respond with valid JSON only."
    system_prompt_plan = "You are a clinical operations investigator. Respond with valid JSON only."
    system_prompt_reflect = "You are a clinical operations data quality expert. Respond with valid JSON only."
    fallback_summary = "No significant data quality issues detected."

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad SQL queries to gather raw data quality signals across all sites."""
        logger.info("[%s] PERCEIVE: gathering raw data quality signals", self.agent_id)

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
