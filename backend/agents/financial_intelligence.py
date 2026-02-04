"""Financial Intelligence Agent — investigates budget health, cost efficiency,
vendor spending patterns, and financial impact of operational delays.

Provides risk-adjusted forecasting and budget reallocation recommendations.
All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import logging

from backend.agents.base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class FinancialIntelligenceAgent(BaseAgent):
    agent_id = "financial_intelligence"
    agent_name = "Financial Intelligence Agent"
    description = (
        "Investigates budget health, cost efficiency, vendor spending patterns, "
        "and financial impact of operational delays. Provides risk-adjusted "
        "forecasting and budget reallocation recommendations."
    )

    finding_type = "financial_intelligence_analysis"
    prompt_prefix = "financial_intelligence"
    system_prompt_reason = "You are a clinical trial financial operations expert. Respond with valid JSON only."
    system_prompt_plan = "You are a clinical trial financial investigator. Respond with valid JSON only."
    system_prompt_reflect = "You are a clinical trial financial operations expert. Respond with valid JSON only."
    fallback_summary = "No significant financial issues detected."

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
