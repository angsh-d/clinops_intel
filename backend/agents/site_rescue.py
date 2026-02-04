"""Site Rescue vs Close Agent — recommends rescue or closure for underperforming
sites by synthesizing enrollment trajectory, screen failure root causes,
CRA staffing stability, supply constraints, and competitive landscape.

Distinguishes temporary (fixable) root causes from structural (unfixable) ones.
"""

import logging

from backend.agents.base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class SiteRescueAgent(BaseAgent):
    agent_id = "site_rescue"
    agent_name = "Site Decision Agent"
    description = (
        "Recommends rescue or closure for underperforming sites by synthesizing enrollment "
        "trajectory, screen failure root causes (fixable vs structural), CRA staffing stability, "
        "supply constraints, and competitive landscape. Produces a decision framework with "
        "rescue indicators, close indicators, and key decision factors."
    )

    finding_type = "site_rescue_analysis"
    prompt_prefix = "site_rescue"
    system_prompt_reason = "You are a clinical operations site management expert. Respond with valid JSON only."
    system_prompt_plan = "You are a clinical operations site management investigator. Respond with valid JSON only."
    system_prompt_reflect = "You are a clinical operations site management expert. Respond with valid JSON only."
    fallback_summary = "No site rescue/close recommendations generated."

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad data gathering on site enrollment performance and constraints."""
        logger.info("[%s] PERCEIVE: gathering site performance signals", self.agent_id)

        trajectory = await self.tools.invoke("enrollment_trajectory", self.db)
        sites = await self.tools.invoke("site_summary", self.db)
        funnel = await self.tools.invoke("screening_funnel", self.db)
        cra = await self.tools.invoke("cra_assignment_history", self.db)
        kit = await self.tools.invoke("kit_inventory", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "enrollment_trajectory": trajectory.data if trajectory.success else [],
            "screening_funnel": funnel.data if funnel.success else [],
            "cra_history": cra.data if cra.success else [],
            "kit_inventory": kit.data if kit.success else [],
        }
        logger.info("[%s] PERCEIVE: gathered %d sites, %d trajectories, %d funnel, %d CRA, %d kit records",
                     self.agent_id,
                     len(perceptions["site_metadata"]),
                     len(perceptions["enrollment_trajectory"]),
                     len(perceptions["screening_funnel"]),
                     len(perceptions["cra_history"]),
                     len(perceptions["kit_inventory"]))
        return perceptions
