"""Alert router: list, suppress, acknowledge alerts."""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.alert import AlertActionResponse, AlertDetail, AlertResponse, SuppressRequest, AcknowledgeRequest
from backend.schemas.errors import ErrorResponse
from backend.models.governance import AlertLog, SuppressionRule

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])


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
    return AlertResponse(alerts=alerts, total=total)


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
