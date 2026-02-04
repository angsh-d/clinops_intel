"""Agent 3: Enrollment Funnel Agent — investigates screening volume, screen failure
rates, randomization, enrollment velocity, consent withdrawals, and regional patterns.

All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import logging

from backend.agents.base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class EnrollmentFunnelAgent(BaseAgent):
    agent_id = "enrollment_funnel"
    agent_name = "Enrollment Funnel Agent"
    description = (
        "Investigates screening volume, screen failure rates, randomization velocity, "
        "consent withdrawals, and regional enrollment patterns. Detects competing trials, "
        "supply-chain-masked withdrawals, strict PI paradoxes, and funnel stage decomposition."
    )

    finding_type = "enrollment_funnel_analysis"
    prompt_prefix = "enrollment_funnel"
    system_prompt_reason = "You are a clinical operations enrollment expert. Respond with valid JSON only."
    system_prompt_plan = "You are a clinical operations investigator. Respond with valid JSON only."
    system_prompt_reflect = "You are a clinical operations enrollment expert. Respond with valid JSON only."
    fallback_summary = "No significant enrollment issues detected."

    async def perceive(self, ctx: AgentContext) -> dict:
        """Broad data ingestion — screening, randomization, velocity, failure patterns."""
        logger.info("[%s] PERCEIVE: gathering enrollment funnel signals", self.agent_id)

        funnel = await self.tools.invoke("screening_funnel", self.db)
        velocity = await self.tools.invoke("enrollment_velocity", self.db)
        failures = await self.tools.invoke("screen_failure_pattern", self.db, include_narratives=True)
        regional = await self.tools.invoke("regional_comparison", self.db)
        sites = await self.tools.invoke("site_summary", self.db)
        kit_inv = await self.tools.invoke("kit_inventory", self.db)

        perceptions = {
            "screening_funnel": funnel.data if funnel.success else [],
            "enrollment_velocity": velocity.data if velocity.success else [],
            "failure_patterns": failures.data if failures.success else {},
            "regional_comparison": regional.data if regional.success else {},
            "site_metadata": sites.data if sites.success else [],
            "kit_inventory": kit_inv.data if kit_inv.success else [],
        }
        logger.info("[%s] PERCEIVE: gathered %d funnel, %d velocity records",
                     self.agent_id,
                     len(perceptions["screening_funnel"]),
                     len(perceptions["enrollment_velocity"]))
        return perceptions
