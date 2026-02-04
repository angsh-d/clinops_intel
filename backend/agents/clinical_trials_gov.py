"""Competitive Intelligence Agent — searches ClinicalTrials.gov for competing
trials near sites with unexplained enrollment decline.

All reasoning is LLM-driven. No hardcoded thresholds or pattern matching.
"""

import json
import logging

from backend.agents.base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class ClinicalTrialsGovAgent(BaseAgent):
    agent_id = "clinical_trials_gov"
    agent_name = "Competitive Intelligence Agent"
    description = (
        "Searches ClinicalTrials.gov for competing trials near sites with "
        "unexplained enrollment decline. Provides external evidence for enrollment "
        "cannibalization hypotheses."
    )

    finding_type = "competing_trial_analysis"
    prompt_prefix = "clinical_trials_gov"
    system_prompt_reason = "You are a competitive intelligence analyst for clinical trials. Respond with valid JSON only."
    system_prompt_plan = "You are a competitive intelligence investigator. Respond with valid JSON only."
    system_prompt_reflect = "You are a competitive intelligence analyst for clinical trials. Respond with valid JSON only."
    fallback_summary = "No competing trials detected."

    async def perceive(self, ctx: AgentContext) -> dict:
        """Gather site locations and enrollment velocity timelines."""
        logger.info("[%s] PERCEIVE: gathering site locations + enrollment velocity", self.agent_id)

        sites = await self.tools.invoke("site_summary", self.db)
        velocity = await self.tools.invoke("enrollment_velocity", self.db)

        perceptions = {
            "site_metadata": sites.data if sites.success else [],
            "enrollment_velocity": velocity.data if velocity.success else [],
        }
        logger.info("[%s] PERCEIVE: %d sites, %d velocity records",
                     self.agent_id,
                     len(perceptions["site_metadata"]),
                     len(perceptions["enrollment_velocity"]))
        return perceptions

    async def reason(self, ctx: AgentContext) -> list:
        """LLM identifies sites with enrollment decline — includes city/country for geo search."""
        logger.info("[%s] REASON: generating hypotheses via LLM", self.agent_id)

        site_directory = json.dumps(
            [{"site_id": s["site_id"], "name": s["name"], "city": s.get("city", ""), "country": s.get("country", "")}
             for s in ctx.perceptions.get("site_metadata", [])
             if isinstance(s, dict) and "site_id" in s and "name" in s],
            default=str,
        )

        prompt = self.prompts.render(
            "clinical_trials_gov_reason",
            perceptions=self._safe_json_str(ctx.perceptions),
            query=ctx.query,
            site_directory=site_directory,
        )
        response = await self.llm.generate_structured(
            prompt,
            system=self.system_prompt_reason,
        )
        try:
            parsed = self._parse_json(response.text)
            hypotheses = parsed.get("hypotheses", [])
            logger.info("[%s] REASON: generated %d hypotheses", self.agent_id, len(hypotheses))
            return hypotheses
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[%s] REASON: failed to parse LLM response: %s", self.agent_id, e)
            raise RuntimeError(f"[{self.agent_id}] REASON phase failed to parse LLM response: {e}") from e
