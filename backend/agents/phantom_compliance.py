"""Phantom Compliance Detection Agent — detects suspiciously perfect data
that may indicate fabrication or variance suppression.

Cross-references entry lag variance, query aging, monitoring findings, and
randomization patterns. Near-zero variance across multiple domains simultaneously
is the key signal.
"""

import logging

from backend.agents.base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class PhantomComplianceAgent(BaseAgent):
    agent_id = "phantom_compliance"
    agent_name = "Data Integrity Agent"
    description = (
        "Detects data integrity risks including fabrication, batch backfill, and oversight gaps. "
        "Analyzes: (1) variance suppression across entry lag/query aging/monitoring, "
        "(2) CRA oversight gaps and rubber-stamp patterns, (3) weekday entry clustering, "
        "(4) correction provenance anomalies, (5) narrative duplication, (6) cross-domain inconsistencies. "
        "Flags sites where multiple fraud signals co-occur."
    )

    finding_type = "phantom_compliance_analysis"
    prompt_prefix = "phantom_compliance"
    system_prompt_reason = "You are a clinical data integrity expert specializing in fraud detection. Respond with valid JSON only."
    system_prompt_plan = "You are a clinical data integrity investigator. Respond with valid JSON only."
    system_prompt_reflect = "You are a clinical data integrity expert. Respond with valid JSON only."
    fallback_summary = "No data integrity concerns detected."

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad variance and fraud signal analysis across sites."""
        logger.info("[%s] PERCEIVE: gathering data integrity signals", self.agent_id)

        variance = await self.tools.invoke("data_variance_analysis", self.db)
        sites = await self.tools.invoke("site_summary", self.db)
        query_burden = await self.tools.invoke("query_burden", self.db)
        monitoring = await self.tools.invoke("monitoring_visit_history", self.db)

        cra_oversight = await self.tools.invoke("cra_oversight_gap", self.db)
        cra_portfolio = await self.tools.invoke("cra_portfolio_analysis", self.db)
        cross_domain = await self.tools.invoke("cross_domain_consistency", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "data_variance": variance.data if variance.success else [],
            "query_burden": query_burden.data if query_burden.success else [],
            "monitoring_visits": monitoring.data if monitoring.success else [],
            "cra_oversight_gaps": cra_oversight.data if cra_oversight.success else [],
            "cra_portfolio": cra_portfolio.data if cra_portfolio.success else [],
            "cross_domain_consistency": cross_domain.data if cross_domain.success else [],
        }
        logger.info("[%s] PERCEIVE: gathered %d sites, %d variance, %d query, %d monitoring, %d CRA oversight, %d cross-domain records",
                     self.agent_id,
                     len(perceptions["site_metadata"]),
                     len(perceptions["data_variance"]),
                     len(perceptions["query_burden"]),
                     len(perceptions["monitoring_visits"]),
                     len(perceptions["cra_oversight_gaps"]),
                     len(perceptions["cross_domain_consistency"]))
        return perceptions
