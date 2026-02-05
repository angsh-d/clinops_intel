"""Proactive intelligence router: scans, directives, and site briefs."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.models.governance import ProactiveScan, SiteIntelligenceBrief
from backend.schemas.proactive import (
    DirectiveCreateRequest,
    DirectiveResponse,
    DirectiveToggleRequest,
    ScanListItem,
    ScanRequest,
    ScanStatusResponse,
    SiteBriefResponse,
)
from backend.services.directive_catalog import DirectiveCatalog
from backend.services.proactive_scan import ProactiveScanOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["proactive"])


# ── Scan endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/proactive/scan",
    response_model=ScanStatusResponse,
    status_code=202,
    summary="Trigger a proactive scan",
    description="Launch an autonomous proactive scan across all enabled directives. "
    "Processing happens asynchronously; poll the status endpoint for results.",
)
async def trigger_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger a proactive scan. Returns immediately with scan_id."""
    import uuid

    scan_id = str(uuid.uuid4())

    # Create scan record so status is immediately pollable
    scan = ProactiveScan(
        scan_id=scan_id,
        status="pending",
        trigger_type=request.trigger_type,
    )
    db.add(scan)
    db.commit()

    async def _run():
        orchestrator = ProactiveScanOrchestrator()
        await orchestrator.run_scan(
            trigger_type=request.trigger_type,
            agent_filter=request.agent_filter,
            scan_id=scan_id,
        )

    background_tasks.add_task(_run)

    return ScanStatusResponse(
        scan_id=scan_id,
        status="pending",
        trigger_type=request.trigger_type,
    )


@router.get(
    "/proactive/scan/{scan_id}",
    response_model=ScanStatusResponse,
    summary="Get scan status and results",
)
def get_scan_status(scan_id: str, db: Session = Depends(get_db)):
    """Get the status and results of a proactive scan."""
    scan = db.query(ProactiveScan).filter_by(scan_id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    brief_count = db.query(SiteIntelligenceBrief).filter_by(scan_id=scan_id).count()

    return ScanStatusResponse(
        scan_id=scan.scan_id,
        status=scan.status,
        trigger_type=scan.trigger_type,
        directives_executed=scan.directives_executed,
        agent_results=scan.agent_results,
        findings_count=scan.findings_count or 0,
        alerts_count=scan.alerts_count or 0,
        briefs_count=brief_count,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        error_detail=scan.error_detail,
        created_at=scan.created_at,
    )


@router.get(
    "/proactive/scans",
    response_model=list[ScanListItem],
    summary="List recent scans",
)
def list_scans(
    limit: int = QueryParam(20, ge=1, le=100),
    offset: int = QueryParam(0, ge=0),
    db: Session = Depends(get_db),
):
    """List recent proactive scans."""
    scans = (
        db.query(ProactiveScan)
        .order_by(ProactiveScan.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        ScanListItem(
            scan_id=s.scan_id,
            status=s.status,
            trigger_type=s.trigger_type,
            findings_count=s.findings_count or 0,
            alerts_count=s.alerts_count or 0,
            started_at=s.started_at,
            completed_at=s.completed_at,
            created_at=s.created_at,
        )
        for s in scans
    ]


# ── Brief endpoints ─────────────────────────────────────────────────────────
# NOTE: /briefs/scan/{scan_id} MUST be defined before /briefs/{site_id}
# to prevent FastAPI from matching "scan" as a site_id.

@router.get(
    "/proactive/briefs/scan/{scan_id}",
    response_model=list[SiteBriefResponse],
    summary="Get all briefs from a scan",
)
def get_scan_briefs(scan_id: str, db: Session = Depends(get_db)):
    """Get all site intelligence briefs from a specific scan."""
    briefs = (
        db.query(SiteIntelligenceBrief)
        .filter_by(scan_id=scan_id)
        .order_by(SiteIntelligenceBrief.site_id)
        .all()
    )
    return [_brief_to_response(b) for b in briefs]


@router.get(
    "/proactive/briefs/{site_id}",
    response_model=list[SiteBriefResponse],
    summary="Get recent briefs for a site",
)
def get_site_briefs(
    site_id: str,
    limit: int = QueryParam(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get recent intelligence briefs for a specific site."""
    briefs = (
        db.query(SiteIntelligenceBrief)
        .filter_by(site_id=site_id)
        .order_by(SiteIntelligenceBrief.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_brief_to_response(b) for b in briefs]


def _brief_to_response(b: SiteIntelligenceBrief) -> SiteBriefResponse:
    return SiteBriefResponse(
        id=b.id,
        scan_id=b.scan_id,
        site_id=b.site_id,
        risk_summary=b.risk_summary,
        vendor_accountability=b.vendor_accountability,
        cross_domain_correlations=b.cross_domain_correlations,
        recommended_actions=b.recommended_actions,
        trend_indicator=b.trend_indicator,
        agent=b.agent,
        contributing_agents=b.contributing_agents,
        investigation_steps=b.investigation_steps,
        created_at=b.created_at,
    )


# ── Directive endpoints ─────────────────────────────────────────────────────

@router.get(
    "/proactive/directives",
    response_model=list[DirectiveResponse],
    summary="List all directives",
)
def list_directives():
    """List all investigation directives from the catalog."""
    catalog = DirectiveCatalog()
    directives = catalog.load_catalog()
    return [
        DirectiveResponse(
            directive_id=d["directive_id"],
            agent_id=d["agent_id"],
            name=d["name"],
            description=d["description"],
            enabled=d.get("enabled", True),
            priority=d.get("priority", "medium"),
        )
        for d in directives
    ]


@router.put(
    "/proactive/directives/{directive_id}/toggle",
    response_model=DirectiveResponse,
    summary="Enable or disable a directive",
)
def toggle_directive(directive_id: str, request: DirectiveToggleRequest):
    """Enable or disable a specific directive."""
    catalog = DirectiveCatalog()
    try:
        updated = catalog.set_enabled(directive_id, request.enabled)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DirectiveResponse(
        directive_id=updated["directive_id"],
        agent_id=updated["agent_id"],
        name=updated["name"],
        description=updated["description"],
        enabled=updated.get("enabled", True),
        priority=updated.get("priority", "medium"),
    )


@router.post(
    "/proactive/directives",
    response_model=DirectiveResponse,
    status_code=201,
    summary="Create a new directive",
)
def create_directive(request: DirectiveCreateRequest):
    """Create a new investigation directive with prompt text."""
    catalog = DirectiveCatalog()
    try:
        created = catalog.add_directive(
            directive={
                "directive_id": request.directive_id,
                "agent_id": request.agent_id,
                "name": request.name,
                "description": request.description,
                "enabled": True,
                "priority": request.priority,
            },
            prompt_text=request.prompt_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return DirectiveResponse(
        directive_id=created["directive_id"],
        agent_id=created["agent_id"],
        name=created["name"],
        description=created["description"],
        enabled=created.get("enabled", True),
        priority=created.get("priority", "medium"),
    )
