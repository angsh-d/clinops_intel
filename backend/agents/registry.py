"""Agent registry: lookup agents by ID."""

import logging
from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Dict-based registry for looking up agents by agent_id."""

    def __init__(self):
        self._agents: dict[str, type[BaseAgent]] = {}

    def register(self, agent_cls: type[BaseAgent]):
        self._agents[agent_cls.agent_id] = agent_cls
        logger.debug("Registered agent: %s (%s)", agent_cls.agent_id, agent_cls.agent_name)

    def get(self, agent_id: str) -> type[BaseAgent] | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[dict]:
        return [
            {"agent_id": cls.agent_id, "name": cls.agent_name, "description": cls.description}
            for cls in self._agents.values()
        ]


def build_agent_registry() -> AgentRegistry:
    """Create and populate the default agent registry."""
    from backend.agents.data_quality import DataQualityAgent
    from backend.agents.enrollment_funnel import EnrollmentFunnelAgent
    from backend.agents.clinical_trials_gov import ClinicalTrialsGovAgent
    from backend.agents.phantom_compliance import PhantomComplianceAgent
    from backend.agents.site_rescue import SiteRescueAgent
    from backend.agents.vendor_performance import VendorPerformanceAgent
    from backend.agents.financial_intelligence import FinancialIntelligenceAgent
    from backend.agents.mvr_analysis import MVRAnalysisAgent

    registry = AgentRegistry()
    registry.register(DataQualityAgent)
    registry.register(EnrollmentFunnelAgent)
    registry.register(ClinicalTrialsGovAgent)
    registry.register(PhantomComplianceAgent)
    registry.register(SiteRescueAgent)
    registry.register(VendorPerformanceAgent)
    registry.register(FinancialIntelligenceAgent)
    registry.register(MVRAnalysisAgent)
    return registry
