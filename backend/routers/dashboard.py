"""Dashboard router: pure SQL aggregations, no LLM."""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.schemas.dashboard import (
    DataQualityDashboard, SiteDataQualityMetrics,
    EnrollmentDashboard, SiteEnrollmentMetrics,
    SiteMetadata, SiteMetadataResponse, CRAAssignmentSchema, MonitoringVisitSchema,
    KRITimeSeriesResponse, KRIDataPoint,
    EnrollmentVelocityResponse, VelocityDataPoint,
    AlertDetailEnhanced,
)
from data_generators.models import (
    ECRFEntry, Query, DataCorrection, ScreeningLog,
    RandomizationLog, Site, StudyConfig,
    CRAAssignment, MonitoringVisit, KRISnapshot, EnrollmentVelocity,
)
from backend.models.governance import AgentFinding, AlertLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/data-quality",
    response_model=DataQualityDashboard,
    summary="Data quality dashboard",
    description="Aggregated data quality metrics per site: entry lags, query volumes, "
    "corrections, and missing critical fields. Pure SQL, no LLM.",
    response_description="Per-site data quality metrics with study-level totals.",
)
def data_quality_dashboard(db: Session = Depends(get_db)):
    """Data quality metrics by site — pure SQL aggregation."""
    sites = db.query(
        ECRFEntry.site_id,
        func.avg(ECRFEntry.entry_lag_days).label("mean_entry_lag"),
        func.sum(case((ECRFEntry.has_missing_critical.is_(True), 1), else_=0)).label("missing_critical_count"),
    ).group_by(ECRFEntry.site_id).all()

    queries = db.query(
        Query.site_id,
        func.count(Query.id).label("total_queries"),
        func.sum(case((Query.status == "Open", 1), else_=0)).label("open_queries"),
        func.sum(case((Query.age_days > 14, 1), else_=0)).label("aging_over_14d"),
    ).group_by(Query.site_id).all()

    corrections = db.query(
        DataCorrection.site_id,
        func.count(DataCorrection.id).label("correction_count"),
    ).group_by(DataCorrection.site_id).all()

    # Merge into per-site metrics
    query_map = {r.site_id: r for r in queries}
    correction_map = {r.site_id: r for r in corrections}

    site_metrics = []
    for s in sites:
        q = query_map.get(s.site_id)
        c = correction_map.get(s.site_id)
        site_metrics.append(SiteDataQualityMetrics(
            site_id=s.site_id,
            mean_entry_lag=round(float(s.mean_entry_lag), 1) if s.mean_entry_lag else None,
            total_queries=q.total_queries if q else 0,
            open_queries=q.open_queries if q else 0,
            aging_over_14d=q.aging_over_14d if q else 0,
            correction_count=c.correction_count if c else 0,
            missing_critical_count=s.missing_critical_count or 0,
        ))

    study_mean = db.query(func.avg(ECRFEntry.entry_lag_days)).scalar()
    study_total_q = db.query(func.count(Query.id)).scalar()

    return DataQualityDashboard(
        sites=site_metrics,
        study_mean_entry_lag=round(float(study_mean), 1) if study_mean else None,
        study_total_queries=study_total_q or 0,
    )


@router.get(
    "/enrollment-funnel",
    response_model=EnrollmentDashboard,
    summary="Enrollment funnel dashboard",
    description="Enrollment funnel metrics per site: screening, randomisation, and target progress. "
    "Pure SQL, no LLM.",
    response_description="Per-site enrollment funnel metrics with study-level totals.",
)
def enrollment_funnel_dashboard(db: Session = Depends(get_db)):
    """Enrollment funnel metrics by site — pure SQL aggregation."""
    screening = db.query(
        ScreeningLog.site_id,
        func.count(ScreeningLog.id).label("total_screened"),
        func.sum(case((ScreeningLog.outcome == "Passed", 1), else_=0)).label("passed"),
        func.sum(case((ScreeningLog.outcome == "Failed", 1), else_=0)).label("failed"),
    ).group_by(ScreeningLog.site_id).all()

    randomization = db.query(
        RandomizationLog.site_id,
        func.count(RandomizationLog.id).label("randomized"),
    ).group_by(RandomizationLog.site_id).all()

    rand_map = {r.site_id: r.randomized for r in randomization}

    # Get per-site targets
    site_targets = {s.site_id: s.target_enrollment for s in db.query(Site.site_id, Site.target_enrollment).all()}

    study_config = db.query(StudyConfig).first()
    study_target = study_config.target_enrollment if study_config else 595

    site_metrics = []
    total_screened = 0
    total_randomized = 0

    for s in screening:
        rand_count = rand_map.get(s.site_id, 0)
        target = site_targets.get(s.site_id, 0)
        failure_rate = round((s.failed / s.total_screened * 100) if s.total_screened > 0 else 0, 1)
        pct_target = round((rand_count / target * 100) if target > 0 else 0, 1)

        site_metrics.append(SiteEnrollmentMetrics(
            site_id=s.site_id,
            total_screened=s.total_screened,
            total_passed=s.passed or 0,
            total_failed=s.failed or 0,
            failure_rate_pct=failure_rate,
            randomized=rand_count,
            target=target,
            pct_of_target=pct_target,
        ))
        total_screened += s.total_screened
        total_randomized += rand_count

    return EnrollmentDashboard(
        sites=site_metrics,
        study_total_screened=total_screened,
        study_total_randomized=total_randomized,
        study_target=study_target,
        study_pct_of_target=round((total_randomized / study_target * 100) if study_target > 0 else 0, 1),
    )


@router.get(
    "/site-metadata",
    response_model=SiteMetadataResponse,
    summary="Site metadata with CRA and monitoring info",
    description="Returns site identity (country, city, type, experience), CRA assignment "
    "history, and recent monitoring visits for all sites.",
)
def site_metadata_dashboard(db: Session = Depends(get_db)):
    """Site metadata, CRA assignments, and monitoring visits — pure SQL."""
    sites = db.query(Site).all()
    cra_rows = db.query(CRAAssignment).all()
    visit_rows = db.query(MonitoringVisit).order_by(MonitoringVisit.actual_date.desc()).all()

    cra_map: dict[str, list[CRAAssignmentSchema]] = {}
    for c in cra_rows:
        cra_map.setdefault(c.site_id, []).append(CRAAssignmentSchema(
            cra_id=c.cra_id,
            start_date=str(c.start_date) if c.start_date else None,
            end_date=str(c.end_date) if c.end_date else None,
            is_current=bool(c.is_current),
        ))

    visit_map: dict[str, list[MonitoringVisitSchema]] = {}
    for v in visit_rows:
        visit_map.setdefault(v.site_id, []).append(MonitoringVisitSchema(
            visit_date=str(v.actual_date) if v.actual_date else None,
            visit_type=v.visit_type,
            findings_count=v.findings_count or 0,
            critical_findings=v.critical_findings or 0,
            days_overdue=v.days_overdue or 0,
            status=v.status,
        ))

    result = []
    for s in sites:
        result.append(SiteMetadata(
            site_id=s.site_id,
            country=s.country,
            city=s.city,
            site_type=s.site_type,
            experience_level=s.experience_level,
            activation_date=str(s.activation_date) if s.activation_date else None,
            target_enrollment=s.target_enrollment or 0,
            anomaly_type=s.anomaly_type,
            cra_assignments=cra_map.get(s.site_id, []),
            monitoring_visits=visit_map.get(s.site_id, [])[:5],
        ))

    return SiteMetadataResponse(sites=result)


@router.get(
    "/kri-timeseries/{site_id}",
    response_model=KRITimeSeriesResponse,
    summary="KRI time series for a site",
    description="Returns KRI snapshot data points ordered by date for a specific site.",
)
def kri_timeseries(site_id: str, db: Session = Depends(get_db)):
    """KRI snapshots for a site — pure SQL."""
    rows = db.query(KRISnapshot).filter(
        KRISnapshot.site_id == site_id,
    ).order_by(KRISnapshot.snapshot_date).all()

    data = [KRIDataPoint(
        snapshot_date=str(r.snapshot_date) if r.snapshot_date else "",
        kri_name=r.kri_name or "",
        kri_value=float(r.kri_value) if r.kri_value is not None else 0,
        amber_threshold=float(r.amber_threshold) if r.amber_threshold is not None else None,
        red_threshold=float(r.red_threshold) if r.red_threshold is not None else None,
        status=r.status,
    ) for r in rows]

    return KRITimeSeriesResponse(site_id=site_id, data=data)


@router.get(
    "/enrollment-velocity/{site_id}",
    response_model=EnrollmentVelocityResponse,
    summary="Enrollment velocity time series for a site",
    description="Returns weekly enrollment velocity data for a specific site.",
)
def enrollment_velocity(site_id: str, db: Session = Depends(get_db)):
    """Enrollment velocity time series for a site — pure SQL."""
    rows = db.query(EnrollmentVelocity).filter(
        EnrollmentVelocity.site_id == site_id,
    ).order_by(EnrollmentVelocity.week_number).all()

    data = [VelocityDataPoint(
        week_start=str(r.week_start) if r.week_start else "",
        week_number=r.week_number or 0,
        screened_count=r.screened_count or 0,
        randomized_count=r.randomized_count or 0,
        cumulative_screened=r.cumulative_screened or 0,
        cumulative_randomized=r.cumulative_randomized or 0,
        target_cumulative=r.target_cumulative or 0,
    ) for r in rows]

    return EnrollmentVelocityResponse(site_id=site_id, data=data)


@router.get(
    "/alert-enhanced/{alert_id}",
    response_model=AlertDetailEnhanced,
    summary="Alert with investigation trace",
    description="Returns alert detail enriched with the referenced finding's investigation "
    "summary, confidence, reasoning trace, and recommended actions.",
)
def alert_detail_enhanced(alert_id: int, db: Session = Depends(get_db)):
    """Alert detail with investigation trace from referenced finding."""
    from fastapi import HTTPException

    alert = db.query(AlertLog).filter(AlertLog.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    investigation_summary = None
    investigation_confidence = None
    investigation_reasoning = None
    investigation_findings = None
    recommended_actions = None

    if alert.finding_id:
        finding = db.query(AgentFinding).filter(AgentFinding.id == alert.finding_id).first()
        if finding:
            investigation_summary = finding.summary
            investigation_confidence = finding.confidence
            investigation_reasoning = finding.reasoning_trace
            detail = finding.detail or {}
            investigation_findings = detail.get("findings", [])
            recommended_actions = detail.get("recommended_actions", [])

    return AlertDetailEnhanced(
        id=alert.id,
        finding_id=alert.finding_id,
        agent_id=alert.agent_id,
        severity=alert.severity,
        site_id=alert.site_id,
        title=alert.title,
        description=alert.description,
        status=alert.status,
        suppressed=alert.suppressed or False,
        created_at=alert.created_at,
        investigation_summary=investigation_summary,
        investigation_confidence=investigation_confidence,
        investigation_reasoning=investigation_reasoning,
        investigation_findings=investigation_findings,
        recommended_actions=recommended_actions,
    )
