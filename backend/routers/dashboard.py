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
    StudySummary, AttentionSite, AttentionSitesResponse,
    SiteOverview, SitesOverviewResponse,
    AgentInsight, AgentInsightsResponse,
    AgentActivityStatus, AgentActivityResponse,
    SiteMetricDetail, SiteAlertDetail, SiteDetailResponse,
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


@router.get(
    "/study-summary",
    response_model=StudySummary,
    summary="Study summary dashboard",
    description="High-level study metrics: enrollment progress, site counts, and countries.",
)
def study_summary(db: Session = Depends(get_db)):
    """Study summary metrics — pure SQL aggregation."""
    from datetime import datetime
    
    study_config = db.query(StudyConfig).first()
    if not study_config:
        return StudySummary(
            study_id="Unknown",
            study_name="Unknown Study",
            phase="Unknown",
            enrolled=0,
            target=0,
            pct_enrolled=0.0,
            total_sites=0,
            active_sites=0,
            countries=[],
            last_updated=datetime.now().isoformat(),
        )
    
    enrolled = db.query(func.count(RandomizationLog.id)).scalar() or 0
    total_sites = db.query(func.count(Site.id)).scalar() or 0
    
    # Sites with at least one randomization
    active_sites = db.query(func.count(func.distinct(RandomizationLog.site_id))).scalar() or 0
    
    # Distinct countries
    countries = [r[0] for r in db.query(func.distinct(Site.country)).all() if r[0]]
    
    pct = round((enrolled / study_config.target_enrollment * 100), 1) if study_config.target_enrollment else 0
    
    return StudySummary(
        study_id=study_config.study_id,
        study_name=study_config.study_id,
        phase=study_config.phase or "Phase 3",
        enrolled=enrolled,
        target=study_config.target_enrollment or 0,
        pct_enrolled=pct,
        total_sites=total_sites,
        active_sites=active_sites,
        countries=countries,
        last_updated=datetime.now().isoformat(),
    )


@router.get(
    "/attention-sites",
    response_model=AttentionSitesResponse,
    summary="Sites requiring attention",
    description="Sites with elevated metrics, high query counts, or anomalies that need review.",
)
def attention_sites(db: Session = Depends(get_db)):
    """Sites requiring attention based on data quality and enrollment issues."""
    attention_list = []
    
    # Get sites with high open query counts
    high_query_sites = db.query(
        Query.site_id,
        func.count(Query.id).filter(Query.status == "Open").label("open_queries"),
    ).group_by(Query.site_id).having(
        func.count(Query.id).filter(Query.status == "Open") > 15
    ).all()
    
    # Get site details
    site_map = {s.site_id: s for s in db.query(Site).all()}
    
    for row in high_query_sites:
        site = site_map.get(row.site_id)
        if site:
            attention_list.append(AttentionSite(
                site_id=row.site_id,
                site_name=getattr(site, 'name', None),
                country=site.country,
                city=site.city,
                issue="High open query count",
                severity="critical" if row.open_queries > 25 else "warning",
                metric=f"{row.open_queries} open queries",
                metric_value=float(row.open_queries),
            ))
    
    # Get sites with high entry lag
    high_lag_sites = db.query(
        ECRFEntry.site_id,
        func.avg(ECRFEntry.entry_lag_days).label("avg_lag"),
    ).group_by(ECRFEntry.site_id).having(
        func.avg(ECRFEntry.entry_lag_days) > 5
    ).all()
    
    existing_ids = {s.site_id for s in attention_list}
    for row in high_lag_sites:
        if row.site_id not in existing_ids:
            site = site_map.get(row.site_id)
            if site:
                attention_list.append(AttentionSite(
                    site_id=row.site_id,
                    site_name=getattr(site, 'name', None),
                    country=site.country,
                    city=site.city,
                    issue="Elevated entry lag",
                    severity="warning",
                    metric=f"{round(row.avg_lag, 1)} day lag",
                    metric_value=float(row.avg_lag),
                ))
                existing_ids.add(row.site_id)
    
    # Get sites with anomaly types
    anomaly_sites = db.query(Site).filter(Site.anomaly_type.isnot(None)).limit(5).all()
    for site in anomaly_sites:
        if site.site_id not in existing_ids:
            attention_list.append(AttentionSite(
                site_id=site.site_id,
                site_name=getattr(site, 'name', None),
                country=site.country,
                city=site.city,
                issue=site.anomaly_type or "Anomaly detected",
                severity="critical",
                metric="Flagged for review",
                metric_value=None,
            ))
            existing_ids.add(site.site_id)
    
    # Sort by severity (critical first) and limit
    attention_list.sort(key=lambda x: (0 if x.severity == "critical" else 1, x.site_id))
    attention_list = attention_list[:10]
    
    critical_count = sum(1 for s in attention_list if s.severity == "critical")
    warning_count = sum(1 for s in attention_list if s.severity == "warning")
    
    return AttentionSitesResponse(
        sites=attention_list,
        critical_count=critical_count,
        warning_count=warning_count,
    )


@router.get(
    "/sites-overview",
    response_model=SitesOverviewResponse,
    summary="All sites with status overview",
    description="Returns all sites with enrollment %, data quality, and status.",
)
def sites_overview(db: Session = Depends(get_db)):
    """All sites with computed metrics."""
    from datetime import datetime, timedelta
    
    sites = db.query(Site).all()
    study_config = db.query(StudyConfig).first()
    
    # Get enrollment counts per site
    enrollment_counts = dict(
        db.query(RandomizationLog.site_id, func.count(RandomizationLog.id))
        .group_by(RandomizationLog.site_id)
        .all()
    )
    
    # Get open query counts per site
    query_counts = dict(
        db.query(Query.site_id, func.count(Query.id))
        .filter(Query.status == "Open")
        .group_by(Query.site_id)
        .all()
    )
    
    # Get alert counts per site
    alert_counts = dict(
        db.query(AlertLog.site_id, func.count(AlertLog.id))
        .filter(AlertLog.status == "active")
        .group_by(AlertLog.site_id)
        .all()
    )
    
    site_list = []
    for site in sites:
        site_target = site.target_enrollment or 4
        enrolled = enrollment_counts.get(site.site_id, 0)
        enrollment_pct = min(100.0, round((enrolled / site_target) * 100, 1)) if site_target else 0
        
        open_queries = query_counts.get(site.site_id, 0)
        alert_count = alert_counts.get(site.site_id, 0)
        
        # Compute data quality score (inverse of query rate)
        dq_score = max(0, 100 - (open_queries * 5))
        
        # Determine status
        if site.anomaly_type or open_queries > 20 or alert_count > 2:
            status = "critical"
        elif open_queries > 10 or enrollment_pct < 50:
            status = "warning"
        else:
            status = "healthy"
        
        finding = site.anomaly_type or (
            f"{open_queries} open queries" if open_queries > 5 else 
            "On track" if enrollment_pct >= 75 else
            "Below target"
        )
        
        site_list.append(SiteOverview(
            site_id=site.site_id,
            site_name=getattr(site, 'name', None),
            country=site.country,
            city=site.city,
            enrollment_percent=enrollment_pct,
            data_quality_score=dq_score,
            alert_count=alert_count,
            status=status,
            finding=finding,
        ))
    
    return SitesOverviewResponse(sites=site_list, total=len(site_list))


@router.get(
    "/agent-insights",
    response_model=AgentInsightsResponse,
    summary="AI agent insights",
    description="Returns proactive insights generated by AI agents.",
)
def agent_insights(db: Session = Depends(get_db)):
    """AI agent insights from findings and alerts."""
    from datetime import datetime, timedelta
    
    insights = []
    
    # Get recent findings
    findings = db.query(AgentFinding).order_by(AgentFinding.created_at.desc()).limit(10).all()
    
    for i, finding in enumerate(findings):
        # Map agent type
        agent_map = {
            "enrollment": "Enrollment Agent",
            "data_quality": "Data Quality Agent",
            "supply_chain": "Supply Chain Agent",
            "compliance": "Compliance Agent",
        }
        agent = agent_map.get(finding.agent_id, finding.agent_id or "Analysis Agent")
        
        # Calculate time ago
        if finding.created_at:
            delta = datetime.now() - finding.created_at
            if delta.days > 0:
                timestamp = f"{delta.days}d ago"
            elif delta.seconds > 3600:
                timestamp = f"{delta.seconds // 3600}h ago"
            else:
                timestamp = f"{max(1, delta.seconds // 60)} min ago"
        else:
            timestamp = "Recently"
        
        # Extract sites from findings
        sites = []
        if finding.site_id:
            sites = [finding.site_id]
        
        # Get recommendation from detail JSON
        rec = None
        if finding.detail:
            try:
                detail = finding.detail if isinstance(finding.detail, dict) else {}
                rec = detail.get("issue")
            except:
                pass
        
        # Extract title from summary (first sentence or full summary)
        title = finding.summary or "Analysis complete"
        if title and len(title) > 60:
            title = title[:60] + "..."
        
        insights.append(AgentInsight(
            id=finding.id,
            agent=agent,
            severity=finding.severity or "warning",
            title=title,
            summary=finding.summary or "",
            recommendation=rec,
            confidence=finding.confidence or 85.0,
            timestamp=timestamp,
            sites=sites,
            impact=None,
        ))
    
    # If no findings, get from alerts
    if not insights:
        alerts = db.query(AlertLog).filter(AlertLog.status == "active").order_by(AlertLog.created_at.desc()).limit(5).all()
        for i, alert in enumerate(alerts):
            agent_map = {
                "enrollment": "Enrollment Agent",
                "data_quality": "Data Quality Agent",
                "supply_chain": "Supply Chain Agent",
            }
            agent = agent_map.get(alert.agent_id, alert.agent_id or "Analysis Agent")
            
            if alert.created_at:
                delta = datetime.now() - alert.created_at
                if delta.days > 0:
                    timestamp = f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    timestamp = f"{delta.seconds // 3600}h ago"
                else:
                    timestamp = f"{max(1, delta.seconds // 60)} min ago"
            else:
                timestamp = "Recently"
            
            insights.append(AgentInsight(
                id=alert.id,
                agent=agent,
                severity=alert.severity or "warning",
                title=alert.title or "Alert",
                summary=alert.description or "",
                recommendation=None,
                confidence=85.0,
                timestamp=timestamp,
                sites=[alert.site_id] if alert.site_id else [],
                impact=None,
            ))
    
    return AgentInsightsResponse(insights=insights, total=len(insights))


@router.get(
    "/agent-activity",
    response_model=AgentActivityResponse,
    summary="Agent activity status",
    description="Returns the status of all AI agents based on their recent findings.",
)
def agent_activity(db: Session = Depends(get_db)):
    """Get agent activity status from database."""
    from datetime import datetime, timedelta
    
    agent_definitions = [
        {"id": "enrollment", "name": "Enrollment Agent"},
        {"id": "data_quality", "name": "Data Quality Agent"},
        {"id": "compliance", "name": "Compliance Agent"},
        {"id": "risk", "name": "Risk Agent"},
    ]
    
    agents = []
    for agent_def in agent_definitions:
        findings = db.query(AgentFinding).filter(
            AgentFinding.agent_id == agent_def["id"]
        ).order_by(AgentFinding.created_at.desc()).all()
        
        findings_count = len(findings)
        
        if findings_count > 0 and findings[0].created_at:
            last_finding = findings[0]
            delta = datetime.now() - last_finding.created_at
            if delta.days > 0:
                last_run = f"{delta.days}d ago"
            elif delta.seconds > 3600:
                last_run = f"{delta.seconds // 3600}h ago"
            else:
                last_run = f"{max(1, delta.seconds // 60)} min ago"
            status = "idle"
        else:
            last_run = "Ready"
            status = "idle"
        
        agents.append(AgentActivityStatus(
            id=agent_def["id"],
            name=agent_def["name"],
            status=status,
            lastRun=last_run,
            findingsCount=findings_count,
        ))
    
    return AgentActivityResponse(agents=agents)


@router.get(
    "/site/{site_id}",
    response_model=SiteDetailResponse,
    summary="Site detail with metrics",
    description="Returns detailed site data including metrics, alerts, and AI summary.",
)
def site_detail(site_id: str, db: Session = Depends(get_db)):
    """Get detailed site data from database."""
    from datetime import datetime, timedelta
    
    site = db.query(Site).filter(Site.site_id == site_id).first()
    if not site:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Get enrollment data
    screened = db.query(func.count(ScreeningLog.id)).filter(ScreeningLog.site_id == site_id).scalar() or 0
    randomized = db.query(func.count(RandomizationLog.id)).filter(RandomizationLog.site_id == site_id).scalar() or 0
    site_target = site.target_enrollment or 4
    enrollment_pct = min(100.0, round((randomized / site_target) * 100, 1)) if site_target else 0
    
    # Get data quality metrics
    entry_lag = db.query(func.avg(ECRFEntry.entry_lag_days)).filter(ECRFEntry.site_id == site_id).scalar()
    open_queries = db.query(func.count(Query.id)).filter(Query.site_id == site_id, Query.status == "Open").scalar() or 0
    total_queries = db.query(func.count(Query.id)).filter(Query.site_id == site_id).scalar() or 0
    
    # Calculate query rate (queries per subject)
    query_rate = round(total_queries / max(1, screened), 2) if screened else 0
    
    # Compute study-level averages from database
    study_avg_lag = db.query(func.avg(ECRFEntry.entry_lag_days)).scalar()
    study_total_screened = db.query(func.count(ScreeningLog.id)).scalar() or 1
    study_total_queries = db.query(func.count(Query.id)).scalar() or 0
    avg_query_rate = round(study_total_queries / max(1, study_total_screened), 2)
    
    # Data quality score
    dq_score = max(0, 100 - (open_queries * 5))
    
    # Determine status
    if site.anomaly_type or open_queries > 20:
        status = "critical"
    elif open_queries > 10 or enrollment_pct < 50:
        status = "warning"
    else:
        status = "healthy"
    
    # Build AI summary based on actual data
    summary_parts = []
    if entry_lag and entry_lag > 5:
        summary_parts.append(f"Entry lag elevated at {round(entry_lag, 1)} days")
    if open_queries > 10:
        summary_parts.append(f"Query backlog of {open_queries} open queries needs attention")
    if enrollment_pct < 75:
        summary_parts.append(f"Enrollment at {enrollment_pct}% of target")
    if site.anomaly_type:
        summary_parts.append(f"Flagged for: {site.anomaly_type}")
    if not summary_parts:
        summary_parts.append("Site performing within expected parameters")
    ai_summary = ". ".join(summary_parts) + "."
    
    # Build data quality metrics
    study_avg_lag_val = round(float(study_avg_lag), 1) if study_avg_lag else 0
    lag_trend = "down" if entry_lag and entry_lag < study_avg_lag_val else "up" if entry_lag and entry_lag > study_avg_lag_val + 2 else "stable"
    data_quality_metrics = [
        SiteMetricDetail(
            label="Entry Lag",
            value=f"{round(entry_lag, 1)}d" if entry_lag else "N/A",
            trend=lag_trend,
            note=f"avg: {study_avg_lag_val}d" if entry_lag else None
        ),
        SiteMetricDetail(
            label="Open Queries",
            value=str(open_queries),
            trend="stable" if open_queries < 15 else "up"
        ),
        SiteMetricDetail(
            label="Query Rate",
            value=str(query_rate),
            note=f"avg: {avg_query_rate}"
        ),
    ]
    
    # Build enrollment metrics
    enrollment_metrics = [
        SiteMetricDetail(
            label="Screened",
            value=str(screened),
            trend="stable"
        ),
        SiteMetricDetail(
            label="Randomized",
            value=str(randomized),
            note=f"Target: {site_target}"
        ),
        SiteMetricDetail(
            label="Enrollment %",
            value=f"{enrollment_pct}%",
            trend="up" if enrollment_pct > 75 else "down"
        ),
    ]
    
    # Get alerts from database
    alerts_db = db.query(AlertLog).filter(
        AlertLog.site_id == site_id,
        AlertLog.status.in_(["open", "active"])
    ).order_by(AlertLog.created_at.desc()).limit(5).all()
    
    alerts = []
    for alert in alerts_db:
        if alert.created_at:
            delta = datetime.now() - alert.created_at
            if delta.days > 0:
                time_str = f"{delta.days}d ago"
            elif delta.seconds > 3600:
                time_str = f"{delta.seconds // 3600}h ago"
            else:
                time_str = f"{max(1, delta.seconds // 60)} min ago"
        else:
            time_str = "Recently"
        
        alerts.append(SiteAlertDetail(
            severity=alert.severity or "info",
            message=alert.title or "Alert",
            time=time_str,
        ))
    
    return SiteDetailResponse(
        site_id=site_id,
        site_name=site.name,
        country=site.country,
        city=site.city,
        status=status,
        ai_summary=ai_summary,
        data_quality_metrics=data_quality_metrics,
        enrollment_metrics=enrollment_metrics,
        alerts=alerts,
        enrollment_percent=enrollment_pct,
        data_quality_score=float(dq_score),
    )
