"""Agent router: invoke agents directly, retrieve findings."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_settings_dep
from backend.config import Settings
from backend.schemas.agent import AgentInvokeRequest, AgentInvokeResponse, AgentFindingSchema, AgentInfo
from backend.schemas.errors import ErrorResponse
from backend.models.governance import AgentFinding
from backend.agents.registry import build_agent_registry
from backend.tools.sql_tools import build_tool_registry
from backend.llm.failover import FailoverLLMClient
from backend.prompts.manager import get_prompt_manager
from backend.services.alert_service import AlertService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


@router.get(
    "/",
    response_model=list[AgentInfo],
    summary="List registered agents",
    description="Return metadata for every agent available in the registry.",
    response_description="Array of agent info objects.",
)
def list_agents():
    """List all registered agents."""
    registry = build_agent_registry()
    return registry.list_agents()


@router.post(
    "/{agent_id}/invoke",
    response_model=AgentInvokeResponse,
    summary="Invoke an agent",
    description="Run a specific agent with a natural-language query. "
    "The agent investigates the data, persists findings, and creates alerts.",
    response_description="Finding result including reasoning trace.",
    responses={404: {"model": ErrorResponse, "description": "Agent not found"}},
)
async def invoke_agent(
    agent_id: str,
    request: AgentInvokeRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    """Invoke a specific agent with a query."""
    registry = build_agent_registry()
    agent_cls = registry.get(agent_id)
    if not agent_cls:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    llm = FailoverLLMClient(settings)
    tools = build_tool_registry()
    prompts = get_prompt_manager()

    agent = agent_cls(
        llm_client=llm,
        tool_registry=tools,
        prompt_manager=prompts,
        db_session=db,
    )
    output = await agent.run(request.query, session_id=request.session_id or "direct")

    # Persist finding
    finding = AgentFinding(
        agent_id=output.agent_id,
        finding_type=output.finding_type,
        severity=output.severity,
        summary=output.summary,
        detail=output.detail,
        data_signals={},  # Omit large data signals from persistence
        reasoning_trace=output.reasoning_trace,
        confidence=output.confidence,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    # Create alerts from findings
    alert_svc = AlertService()
    alert_svc.create_alerts_from_findings(finding.id, db)

    return {
        "finding_id": finding.id,
        "agent_id": output.agent_id,
        "finding_type": output.finding_type,
        "severity": output.severity,
        "summary": output.summary,
        "detail": output.detail,
        "confidence": output.confidence,
        "reasoning_trace": output.reasoning_trace,
        "findings": output.findings,
    }


@router.get(
    "/{agent_id}/findings",
    response_model=list[AgentFindingSchema],
    summary="Get agent findings",
    description="Retrieve recent findings produced by a specific agent, ordered newest first.",
    response_description="Array of finding objects.",
    responses={404: {"model": ErrorResponse, "description": "Agent not found"}},
)
def get_agent_findings(
    agent_id: str,
    limit: int = QueryParam(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve recent findings for a specific agent."""
    findings = db.query(AgentFinding).filter_by(
        agent_id=agent_id
    ).order_by(AgentFinding.created_at.desc()).limit(limit).all()
    return findings
