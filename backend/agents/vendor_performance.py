"""Agent: Vendor Performance Agent — investigates CRO/vendor performance including
site activation timelines, query resolution speed, monitoring completion, and
contractual KPI adherence.

All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import logging

from backend.agents.base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class VendorPerformanceAgent(BaseAgent):
    agent_id = "vendor_performance"
    agent_name = "Vendor Performance Agent"
    description = (
        "Investigates CRO/vendor performance — site activation timelines, query resolution speed, "
        "monitoring completion, contractual KPI adherence. Identifies vendor-attributable root causes "
        "for operational issues."
    )

    finding_type = "vendor_performance_analysis"
    prompt_prefix = "vendor_performance"
    system_prompt_reason = "You are a clinical operations vendor management expert. Respond with valid JSON only."
    system_prompt_plan = "You are a clinical operations investigator. Respond with valid JSON only."
    system_prompt_reflect = "You are a clinical operations vendor management expert. Respond with valid JSON only."
    fallback_summary = "No significant vendor performance issues detected."

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad SQL queries to gather raw vendor performance signals across all sites."""
        logger.info("[%s] PERCEIVE: gathering raw vendor performance signals", self.agent_id)

        vendor_kpis = await self.tools.invoke("vendor_kpi_analysis", self.db)
        site_comparison = await self.tools.invoke("vendor_site_comparison", self.db)
        milestones = await self.tools.invoke("vendor_milestone_tracker", self.db)
        issues = await self.tools.invoke("vendor_issue_log", self.db)
        sites = await self.tools.invoke("site_summary", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "vendor_kpis": vendor_kpis.data if vendor_kpis.success else [],
            "site_comparison": site_comparison.data if site_comparison.success else [],
            "milestones": milestones.data if milestones.success else [],
            "issues": issues.data if issues.success else [],
        }
        logger.info(
            "[%s] PERCEIVE: gathered %d sites, %d vendor KPIs, %d site comparisons, %d milestones, %d issues",
            self.agent_id,
            len(perceptions["site_metadata"]),
            len(perceptions["vendor_kpis"]),
            len(perceptions["site_comparison"]),
            len(perceptions["milestones"]),
            len(perceptions["issues"]),
        )
        return perceptions
