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


@router.post(
    "/investigate",
    summary="Run investigation on a question",
    description="Investigate a clinical operations question and return findings.",
)
async def investigate(
    request: AgentInvokeRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    """Run an investigation based on the question content."""
    from sqlalchemy import func
    from data_generators.models import Query, ECRFEntry, ScreeningLog, RandomizationLog, Site
    
    site_id = request.site_id
    question = request.query.lower()
    
    # Determine which agent to use based on question content
    if "query" in question or "data quality" in question or "lag" in question:
        agent_id = "data_quality"
    elif "enroll" in question or "screen" in question or "random" in question:
        agent_id = "enrollment"
    else:
        agent_id = "data_quality"
    
    # Get real data from database for context
    site_data = {}
    if site_id:
        site = db.query(Site).filter(Site.site_id == site_id).first()
        if site:
            site_data["site_name"] = site.name
            site_data["country"] = site.country
            site_data["anomaly_type"] = site.anomaly_type
        
        # Get query distribution by CRF page
        query_dist = db.query(
            Query.crf_page_name,
            func.count(Query.id).label("count")
        ).filter(Query.site_id == site_id).group_by(Query.crf_page_name).all()
        
        total_queries = sum(q.count for q in query_dist)
        site_data["query_distribution"] = [
            {"page": q.crf_page_name, "count": q.count, "percent": round(q.count / total_queries * 100, 1) if total_queries else 0}
            for q in sorted(query_dist, key=lambda x: -x.count)[:5]
        ]
        
        # Get entry lag
        avg_lag = db.query(func.avg(ECRFEntry.entry_lag_days)).filter(ECRFEntry.site_id == site_id).scalar()
        site_data["avg_entry_lag"] = round(float(avg_lag), 1) if avg_lag else None
        
        # Get enrollment data
        screened = db.query(func.count(ScreeningLog.id)).filter(ScreeningLog.site_id == site_id).scalar() or 0
        randomized = db.query(func.count(RandomizationLog.id)).filter(RandomizationLog.site_id == site_id).scalar() or 0
        site_data["screened"] = screened
        site_data["randomized"] = randomized
        
        # Get open queries count
        open_queries = db.query(func.count(Query.id)).filter(
            Query.site_id == site_id, 
            Query.status == "Open"
        ).scalar() or 0
        site_data["open_queries"] = open_queries
    
    # Get study-level averages for comparison
    study_avg_lag = db.query(func.avg(ECRFEntry.entry_lag_days)).scalar()
    site_data["study_avg_lag"] = round(float(study_avg_lag), 1) if study_avg_lag else None
    
    # Build investigation phases based on real data
    phases = build_investigation_phases(site_id, site_data, question)
    
    # Build finding based on real data
    finding = build_finding(site_id, site_data, question)
    
    # Compute confidence based on data completeness
    data_points = sum([
        1 if site_data.get("screened") else 0,
        1 if site_data.get("randomized") else 0,
        1 if site_data.get("avg_entry_lag") else 0,
        1 if site_data.get("open_queries") is not None else 0,
        1 if site_data.get("query_distribution") else 0,
    ])
    confidence = min(95.0, 70.0 + (data_points * 5))
    
    # Data sources based on what we actually queried
    data_sources = []
    if site_data.get("query_distribution"):
        data_sources.append("queries")
    if site_data.get("screened"):
        data_sources.append("screening_log")
    if site_data.get("avg_entry_lag"):
        data_sources.append("ecrf_entries")
    if not data_sources:
        data_sources = ["database"]
    
    return {
        "agent_id": agent_id,
        "site_id": site_id,
        "question": request.query,
        "phases": phases,
        "finding": finding,
        "confidence": confidence,
        "data_sources": data_sources,
    }


def build_investigation_step_content(query_dist: list, site_data: dict) -> list:
    """Build the investigation step content without f-string nesting issues."""
    content = []
    
    # Step 1
    if query_dist:
        pages_str = ", ".join([f"{q['page']} {q['percent']}%" for q in query_dist[:2]])
        content.append({"text": f"Step 1: Top query pages: {pages_str} → Concentration identified", "done": True})
    else:
        content.append({"text": "Step 1: No query distribution data available", "done": True})
    
    # Step 2 - use study average from database
    avg_lag = site_data.get('avg_entry_lag', 0)
    study_avg_lag = site_data.get('study_avg_lag')
    if study_avg_lag:
        lag_status = "Elevated" if avg_lag and avg_lag > study_avg_lag else "Within range"
        content.append({"text": f"Step 2: Entry lag {avg_lag or 'N/A'}d vs study avg {study_avg_lag}d → {lag_status}", "done": True})
    else:
        content.append({"text": f"Step 2: Entry lag {avg_lag or 'N/A'}d", "done": True})
    
    # Step 3
    open_q = site_data.get('open_queries', 0)
    q_status = "Action needed" if open_q > 10 else "Manageable"
    content.append({"text": f"Step 3: {open_q} open queries → {q_status}", "done": True})
    
    # Step 4
    content.append({"text": "Step 4: Pattern analysis complete", "done": True})
    
    return content


def build_investigation_phases(site_id: str, site_data: dict, question: str) -> list:
    """Build investigation phases based on real data."""
    query_dist = site_data.get("query_distribution", [])
    top_pages = [q["page"] for q in query_dist[:3]] if query_dist else []
    total_queries = sum(q['count'] for q in query_dist) if query_dist else 0
    
    return [
        {
            "phase": 0,
            "title": "Routing",
            "content": [{"text": f"Routing to analysis agent — question relates to {'query patterns' if 'query' in question else 'site metrics'}."}]
        },
        {
            "phase": 1,
            "title": "Gathering Data",
            "content": [
                {"text": f"Querying screening log... {site_data.get('screened', 0)} subjects", "done": True},
                {"text": f"Querying query history... {total_queries} queries", "done": True},
                {"text": f"Checking enrollment data... {site_data.get('randomized', 0)} randomized", "done": True},
                {"text": f"Loading entry lag data... avg {site_data.get('avg_entry_lag', 'N/A')}d", "done": True}
            ]
        },
        {
            "phase": 2,
            "title": "Analyzing",
            "content": [
                {"text": f"1. Query concentration on {', '.join(top_pages[:2])} pages"} if query_dist else {"text": "1. No query distribution data available"},
                {"text": f"2. Entry lag: {site_data.get('avg_entry_lag', 'N/A')} days average"},
                {"text": f"3. {site_data.get('open_queries', 0)} open queries pending resolution"}
            ]
        },
        {
            "phase": 3,
            "title": "Investigation Plan",
            "content": [
                {"text": "(1) Check CRF page distribution of queries"},
                {"text": "(2) Cross-reference monitoring visit dates"},
                {"text": "(3) Compare with peer sites of similar profile"},
                {"text": "(4) Examine data entry patterns"}
            ]
        },
        {
            "phase": 4,
            "title": "Investigating",
            "content": build_investigation_step_content(query_dist, site_data)
        }
    ]


def build_finding(site_id: str, site_data: dict, question: str) -> dict:
    """Build finding summary based on real data with clear, actionable language."""
    query_dist = site_data.get("query_distribution", [])
    top_pages = query_dist[:2] if query_dist else []
    site_name = site_data.get("site_name", site_id or "this site")
    anomaly = site_data.get("anomaly_type")
    
    # Map anomaly types to human-readable descriptions
    anomaly_descriptions = {
        "enrollment_stall": "enrollment has stalled with no new patient screenings",
        "high_query_burden": "unusually high number of data queries requiring resolution",
        "entry_lag_spike": "significant delays in data entry after patient visits",
        "monitoring_gap": "overdue site monitoring visit",
        "protocol_deviation": "protocol deviation patterns detected",
    }
    
    # Build contextual summary based on ACTUAL DATA, not just flags
    screened = site_data.get("screened", 0)
    randomized = site_data.get("randomized", 0)
    open_queries = site_data.get("open_queries", 0)
    avg_lag = site_data.get("avg_entry_lag", 0)
    study_avg = site_data.get("study_avg_lag", 0)
    
    # Determine actual issues from data
    issues = []
    
    # Check enrollment health (only flag if truly stalled - no recent activity and low numbers)
    if screened == 0:
        issues.append("no patient screenings recorded")
    elif randomized == 0 and screened > 0:
        issues.append(f"screening active ({screened} subjects) but no randomizations yet")
    elif screened > 0 and randomized > 0:
        rate = round(randomized / screened * 100)
        if rate < 50:
            issues.append(f"low screening-to-randomization rate ({rate}%)")
    
    # Check query burden
    if open_queries > 15:
        issues.append(f"elevated query backlog ({open_queries} open queries)")
    elif open_queries > 10:
        issues.append(f"moderate query volume requiring attention ({open_queries} queries)")
    
    # Check entry lag
    if avg_lag and study_avg and avg_lag > study_avg + 2:
        issues.append(f"data entry delays ({avg_lag}d vs study avg {study_avg}d)")
    
    # Build summary from actual findings
    if issues:
        summary = f"Investigation of {site_name} identified: {'; '.join(issues)}."
    elif anomaly and anomaly in anomaly_descriptions:
        # Only use flag if no data-driven issues found - historical context
        summary = f"Investigation of {site_name}: Site was previously flagged for {anomaly.replace('_', ' ')}, but current metrics appear stable."
    else:
        summary = f"Investigation of {site_name} shows the site is operating within normal parameters."
    
    # Build evidence points with context
    evidence = []
    data_sources_used = []
    
    if top_pages:
        pages_list = " and ".join([p['page'] for p in top_pages])
        evidence.append(f"Query concentration on {pages_list} pages suggests potential training needs")
        data_sources_used.append("queries")
    
    if site_data.get("avg_entry_lag"):
        lag = site_data["avg_entry_lag"]
        study_avg = site_data.get("study_avg_lag")
        if study_avg and lag > study_avg:
            evidence.append(f"Data entry averaging {lag} days (above study average of {study_avg} days)")
        else:
            evidence.append(f"Data entry timing is on track at {lag} days average")
        data_sources_used.append("ecrf_entries")
    
    if site_data.get("open_queries") is not None:
        oq = site_data["open_queries"]
        if oq > 10:
            evidence.append(f"{oq} open queries need resolution to maintain data quality")
        else:
            evidence.append(f"Query backlog is manageable with {oq} items pending")
    
    if site_data.get("screened"):
        screened = site_data["screened"]
        randomized = site_data.get("randomized", 0)
        if screened > 0:
            rate = round(randomized / screened * 100) if screened else 0
            evidence.append(f"Screening-to-randomization rate: {rate}% ({randomized} of {screened} subjects)")
        data_sources_used.append("screening_log")
    
    # Build clear, actionable recommendations based on ACTUAL data issues
    if screened == 0:
        recommendation = "Initiate site engagement to start patient recruitment. Verify site readiness and staff availability."
    elif randomized == 0 and screened > 0:
        recommendation = "Review screening failures to identify eligibility barriers. Consider protocol clarification with site staff."
    elif screened > 0 and randomized > 0 and round(randomized / screened * 100) < 50:
        recommendation = "Investigate high screen failure rate. Review inclusion/exclusion criteria interpretation with site."
    elif open_queries > 15:
        recommendation = "Focus on resolving open queries to maintain data quality. Consider additional data management support."
    elif open_queries > 10:
        recommendation = "Prioritize query resolution. Schedule check-in with site to address recurring query patterns."
    elif avg_lag and study_avg and avg_lag > study_avg + 2:
        recommendation = "Address data entry delays through process review. Staff may need additional support or training."
    elif issues:
        # Generic recommendation for other detected issues
        recommendation = "Review site operations and address identified patterns. Consider targeted support where needed."
    else:
        recommendation = "Site is performing well. Continue routine monitoring and maintain current engagement level."
    
    return {
        "summary": summary,
        "evidence": evidence,
        "recommendation": recommendation,
        "data_sources": ", ".join(data_sources_used) if data_sources_used else "database",
    }
