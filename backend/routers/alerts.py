"""Alert router: list, suppress, acknowledge alerts."""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.alert import AlertActionResponse, AlertDetail, AlertResponse, SuppressRequest, AcknowledgeRequest
from backend.schemas.errors import ErrorResponse
from backend.models.governance import AlertLog, SuppressionRule, AgentFinding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])

AGENT_DISPLAY_NAMES = {
    "enrollment_funnel": "Enrollment Funnel Agent",
    "data_quality": "Data Quality Agent",
    "financial": "Financial Agent",
    "phantom_compliance": "Data Integrity Agent",
    "site_risk": "Site Risk Agent",
    "vendor_ops": "Vendor Ops Agent",
}


def _enrich_alert_with_finding(alert: AlertLog, db: Session) -> dict:
    """Enrich alert with reasoning data from linked finding."""
    alert_dict = {
        "id": alert.id,
        "finding_id": alert.finding_id,
        "agent_id": alert.agent_id,
        "severity": alert.severity,
        "site_id": alert.site_id,
        "title": alert.title,
        "description": alert.description,
        "status": alert.status,
        "suppressed": alert.suppressed,
        "created_at": alert.created_at,
        "agent": AGENT_DISPLAY_NAMES.get(alert.agent_id, alert.agent_id),
        "reasoning": None,
        "data_source": None,
        "confidence": None,
    }
    
    if alert.finding_id:
        finding = db.query(AgentFinding).filter_by(id=alert.finding_id).first()
        if finding:
            reasoning_trace = finding.reasoning_trace or []
            if isinstance(reasoning_trace, list) and reasoning_trace:
                phases = []
                for item in reasoning_trace:
                    if isinstance(item, dict):
                        phase = item.get("phase", "")
                        summary = item.get("summary", "")
                        if phase and summary:
                            phases.append(f"{phase.title()}: {summary[:60]}")
                        elif phase:
                            phases.append(phase.title())
                if phases:
                    alert_dict["reasoning"] = " → ".join(phases[:3])
            elif isinstance(reasoning_trace, dict):
                phases = reasoning_trace.get("phases", [])
                if phases:
                    alert_dict["reasoning"] = " → ".join(str(p) for p in phases[:3])
            
            data_signals = finding.data_signals or {}
            if isinstance(data_signals, dict):
                sources = list(data_signals.keys())[:2]
                if sources:
                    alert_dict["data_source"] = ", ".join(sources)
            
            alert_dict["confidence"] = finding.confidence
    
    return alert_dict


@router.get(
    "/",
    response_model=AlertResponse,
    summary="List alerts",
    description="Return alerts with optional filters for status, severity, and site.",
    response_description="Paginated alert list with total count.",
)
def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    site_id: str | None = None,
    limit: int = QueryParam(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List alerts with optional filters."""
    q = db.query(AlertLog)
    if status:
        q = q.filter(AlertLog.status == status)
    if severity:
        q = q.filter(AlertLog.severity == severity)
    if site_id:
        q = q.filter(AlertLog.site_id == site_id)

    total = q.count()
    alerts = q.order_by(AlertLog.created_at.desc()).limit(limit).all()
    
    enriched = [_enrich_alert_with_finding(a, db) for a in alerts]
    return AlertResponse(alerts=enriched, total=total)


@router.get(
    "/{alert_id}",
    response_model=AlertDetail,
    summary="Get alert by ID",
    description="Return a single alert by its numeric ID.",
    response_description="Full alert detail.",
    responses={404: {"model": ErrorResponse, "description": "Alert not found"}},
)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get a specific alert by ID."""
    alert = db.query(AlertLog).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post(
    "/{alert_id}/suppress",
    response_model=AlertActionResponse,
    summary="Suppress an alert",
    description="Mark an alert as suppressed and create a suppression rule.",
    response_description="Confirmation with alert ID.",
    responses={404: {"model": ErrorResponse, "description": "Alert not found"}},
)
def suppress_alert(
    alert_id: int,
    request: SuppressRequest,
    db: Session = Depends(get_db),
):
    """Suppress an alert with a reason."""
    alert = db.query(AlertLog).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "suppressed"
    alert.suppressed = True

    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    rule = SuppressionRule(
        agent_id=alert.agent_id,
        site_id=alert.site_id,
        reason=request.reason,
        created_by=request.created_by,
        expires_at=expires_at,
    )
    db.add(rule)
    db.flush()  # Generate rule.id before assigning to alert
    alert.suppression_rule_id = rule.id
    db.commit()
    return {"status": "suppressed", "alert_id": alert_id}


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertActionResponse,
    summary="Acknowledge an alert",
    description="Mark an alert as acknowledged by a named user.",
    response_description="Confirmation with alert ID.",
    responses={404: {"model": ErrorResponse, "description": "Alert not found"}},
)
def acknowledge_alert(
    alert_id: int,
    request: AcknowledgeRequest,
    db: Session = Depends(get_db),
):
    """Acknowledge an alert."""
    alert = db.query(AlertLog).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "acknowledged"
    alert.acknowledged_by = request.acknowledged_by
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "acknowledged", "alert_id": alert_id}
