"""MVR Analysis Agent — extracts hard-to-find patterns from Monitoring Visit
Report narratives that are invisible in structured operational data.

Detects: zombie findings, CRA rubber-stamping, PI engagement decline,
post-gap debt, CRA transition quality gaps, data integrity red flags,
hidden systemic compliance risks, cross-CRA behavioral contrasts.
"""

import logging

from backend.agents.base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class MVRAnalysisAgent(BaseAgent):
    agent_id = "mvr_analysis"
    agent_name = "MVR Analysis Agent"
    description = (
        "Analyzes Monitoring Visit Report narratives to detect patterns invisible "
        "in structured data: cross-visit finding recurrence (zombie findings), CRA behavioral "
        "signals (rubber-stamping, quality gaps), PI engagement deterioration, hidden systemic "
        "compliance risks, data integrity red flags, post-gap monitoring debt, and cross-site "
        "CRA portfolio inconsistencies."
    )

    finding_type = "mvr_analysis"
    prompt_prefix = "mvr_analysis"
    system_prompt_reason = "You are a clinical monitoring intelligence expert specializing in MVR narrative pattern analysis. Respond with valid JSON only."
    system_prompt_plan = "You are a clinical monitoring intelligence investigator planning MVR narrative analysis. Respond with valid JSON only."
    system_prompt_reflect = "You are a clinical monitoring intelligence expert evaluating MVR narrative findings. Respond with valid JSON only."
    fallback_summary = "No significant MVR narrative patterns detected."

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad MVR narrative and CRA portfolio analysis across sites."""
        logger.info("[%s] PERCEIVE: gathering MVR narrative signals", self.agent_id)

        # Site metadata for directory
        sites = await self.tools.invoke("site_summary", self.db)

        # All MVR narratives (broad search)
        mvr_reports = await self.tools.invoke("mvr_narrative_search", self.db)

        # CRA portfolio analysis
        cra_portfolio = await self.tools.invoke("mvr_cra_portfolio", self.db)

        # Monitoring visit history for gap detection
        monitoring = await self.tools.invoke("monitoring_visit_history", self.db)

        # Cross-site MVR comparison
        cross_site = await self.tools.invoke("mvr_cross_site_comparison", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "mvr_reports": mvr_reports.data if mvr_reports.success else [],
            "cra_portfolio": cra_portfolio.data if cra_portfolio.success else [],
            "monitoring_visits": monitoring.data if monitoring.success else [],
            "cross_site_comparison": cross_site.data if cross_site.success else [],
        }
        logger.info(
            "[%s] PERCEIVE: gathered %d sites, %d MVRs, %d CRA portfolios, %d monitoring, %d cross-site",
            self.agent_id,
            len(perceptions["site_metadata"]),
            len(perceptions["mvr_reports"]),
            len(perceptions["cra_portfolio"]),
            len(perceptions["monitoring_visits"]),
            len(perceptions["cross_site_comparison"]),
        )
        return perceptions
