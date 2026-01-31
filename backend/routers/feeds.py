"""Health/feeds router: data freshness checks."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.feeds import HealthCheckResponse
from data_generators.models import (
    ECRFEntry, Query, ScreeningLog, MonitoringVisit,
    KitInventory, EnrollmentVelocity,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feeds", tags=["feeds"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check data freshness and row counts for all core data sources. "
    "Returns 'healthy' when all tables have data, 'degraded' otherwise.",
    response_description="Health status with per-table row counts and latest dates.",
)
def health_check(db: Session = Depends(get_db)):
    """Data freshness and system health check."""
    checks = {}

    tables = {
        "ecrf_entries": (ECRFEntry, ECRFEntry.entry_date),
        "queries": (Query, Query.open_date),
        "screening_log": (ScreeningLog, ScreeningLog.screening_date),
        "monitoring_visits": (MonitoringVisit, MonitoringVisit.actual_date),
        "kit_inventory": (KitInventory, KitInventory.snapshot_date),
        "enrollment_velocity": (EnrollmentVelocity, EnrollmentVelocity.week_start),
    }

    for name, (model, date_col) in tables.items():
        row_count = db.query(func.count(model.id)).scalar()
        latest_date = db.query(func.max(date_col)).scalar()
        checks[name] = {
            "row_count": row_count or 0,
            "latest_date": latest_date.isoformat() if latest_date else None,
        }

    return {
        "status": "healthy" if all(c["row_count"] > 0 for c in checks.values()) else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_sources": checks,
    }
