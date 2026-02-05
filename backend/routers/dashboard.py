"""Dashboard router: pure SQL aggregations, no LLM."""

import logging
import re
from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_settings_dep
from backend.config import Settings
from backend.cache import dashboard_cache, cache_key
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
    SiteMetricDetail, SiteAlertDetail, SiteDetailResponse, CausalStepExplained,
    SiteJourneyEvent, SiteJourneyResponse,
    VendorScorecard, VendorScorecardsResponse, VendorMilestoneSchema,
    VendorDetailResponse, VendorKPITrend, VendorSiteBreakdown,
    VendorComparisonResponse, VendorComparisonKPI, VendorComparisonValue,
    FinancialSummaryResponse, FinancialWaterfallResponse, WaterfallSegment,
    FinancialByCountryResponse, CountrySpend,
    FinancialByVendorResponse, VendorSpend,
    CostPerPatientResponse, SiteCostEntry,
    ThemeCluster, SiteBriefBadge, IntelligenceSummaryResponse,
    ThemeFindingDetail, ThemeFindingsResponse,
    CrossDomainCorrelation, StudyHypothesis, StudySynthesis,
    DataSourceCitation,
)
from data_generators.models import (
    ECRFEntry, Query, DataCorrection, ScreeningLog,
    RandomizationLog, Site, StudyConfig,
    CRAAssignment, MonitoringVisit, KRISnapshot, EnrollmentVelocity,
    Vendor, VendorScope, VendorSiteAssignment, VendorKPI,
    VendorMilestone, VendorIssue,
    StudyBudget, BudgetCategory, BudgetLineItem, FinancialSnapshot,
    Invoice, PaymentMilestone, ChangeOrder, SiteFinancialMetric,
)
from backend.models.governance import AgentFinding, AlertLog, ProactiveScan, SiteIntelligenceBrief

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# Valid tool names from registry (for grounding validation)
VALID_TOOLS = {
    "screening_funnel", "enrollment_trajectory", "site_performance_summary",
    "burn_rate_projection", "budget_variance_analysis", "cost_per_patient_analysis",
    "change_order_impact", "financial_impact_of_delays", "query_burden",
    "data_completeness", "edit_check_violations", "cra_assignment_history",
    "monitoring_visit_history", "weekday_entry_pattern", "entry_date_clustering",
    "cra_oversight_gap", "cra_portfolio_analysis", "correction_provenance",
    "screening_narrative_duplication", "cross_domain_consistency",
    "vendor_kpi_analysis", "vendor_performance_summary",
    "inference", "derived",
}


def validate_causal_step(step: dict, investigation_steps: list[dict] | None = None) -> CausalStepExplained:
    """Validate a causal chain step and apply grounding + confidence scoring."""
    step_text = step.get("step", "")
    explanation = step.get("explanation", "")
    raw_data_source = step.get("data_source", {})
    
    # Build data source citation
    data_source = None
    if isinstance(raw_data_source, dict) and raw_data_source:
        data_source = DataSourceCitation(
            tool=raw_data_source.get("tool", ""),
            metric=raw_data_source.get("metric"),
            row_count=raw_data_source.get("row_count"),
        )
    
    # Default grounding values
    grounded = None
    grounding_type = None
    grounding_issue = None
    confidence = None
    confidence_reason = None
    
    if data_source and data_source.tool:
        cited_tool = data_source.tool.strip().lower()
        
        if cited_tool in ("inference", "derived", ""):
            grounded = False
            grounding_type = "inference"
            confidence = 0.6
            confidence_reason = "Derived from available data"
        elif cited_tool not in VALID_TOOLS:
            grounded = False
            grounding_type = "unverified"
            grounding_issue = f"Tool '{cited_tool}' not in registry"
            confidence = 0.2
            confidence_reason = "Unknown tool name"
        elif investigation_steps:
            # Check if tool was actually called
            called_tools = {s.get("tool", "").strip().lower() for s in investigation_steps if s.get("tool")}
            if cited_tool in called_tools:
                grounded = True
                grounding_type = "data"
                confidence = 0.9
                confidence_reason = "Verified against tool output"
            else:
                grounded = False
                grounding_type = "unverified"
                grounding_issue = f"Tool '{cited_tool}' was not called"
                confidence = 0.2
                confidence_reason = "Tool not called during investigation"
        else:
            # No investigation steps to validate against - mark as unverified
            grounded = False
            grounding_type = "unverified"
            confidence = 0.3
            confidence_reason = "Cannot verify against investigation"
    else:
        # No data source provided
        grounded = False
        grounding_type = "missing"
        grounding_issue = "No data source citation"
        confidence = 0.1
        confidence_reason = "No data source"
    
    return CausalStepExplained(
        step=step_text,
        explanation=explanation,
        data_source=data_source,
        grounded=grounded,
        grounding_type=grounding_type,
        grounding_issue=grounding_issue,
        confidence=confidence,
        confidence_reason=confidence_reason,
    )


# Agent ID → display name mapping (used across multiple endpoints)
AGENT_DISPLAY_NAMES = {
    "data_quality": "Data Quality Agent",
    "enrollment_funnel": "Enrollment Funnel Agent",
    "clinical_trials_gov": "Competitive Intelligence Agent",
    "phantom_compliance": "Data Integrity Agent",
    "site_rescue": "Site Decision Agent",
    "vendor_performance": "Vendor Performance Agent",
    "financial_intelligence": "Financial Intelligence Agent",
}

THEME_CLUSTERS = {
    "compliance_integrity": {
        "label": "Compliance & Data Integrity",
        "agents": ["phantom_compliance", "data_quality"],
        "icon": "shield",
        "query": "What compliance and data integrity risks exist across our sites?",
    },
    "enrollment_risk": {
        "label": "Enrollment at Risk",
        "agents": ["enrollment_funnel", "site_rescue"],
        "icon": "trending-down",
        "query": "Which sites have enrollment at risk and what are the root causes?",
    },
    "financial_exposure": {
        "label": "Financial Exposure",
        "agents": ["financial_intelligence"],
        "icon": "dollar-sign",
        "query": "What financial risks and budget variances should we address?",
    },
    "vendor_accountability": {
        "label": "Vendor Accountability",
        "agents": ["vendor_performance"],
        "icon": "bar-chart",
        "query": "How are our vendors performing and where are the accountability gaps?",
    },
    "competitive_landscape": {
        "label": "Competitive Landscape",
        "agents": ["clinical_trials_gov"],
        "icon": "globe",
        "query": "What competitive threats are impacting our enrollment?",
    },
}


@router.get(
    "/data-quality",
    response_model=DataQualityDashboard,
    summary="Data quality dashboard",
    description="Aggregated data quality metrics per site: entry lags, query volumes, "
    "corrections, and missing critical fields. Pure SQL, no LLM.",
    response_description="Per-site data quality metrics with study-level totals.",
)
def data_quality_dashboard(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    """Data quality metrics by site — pure SQL aggregation."""
    ck = cache_key("data_quality")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    sites = db.query(
        ECRFEntry.site_id,
        func.avg(ECRFEntry.entry_lag_days).label("mean_entry_lag"),
        func.sum(case((ECRFEntry.has_missing_critical.is_(True), 1), else_=0)).label("missing_critical_count"),
    ).group_by(ECRFEntry.site_id).all()

    queries = db.query(
        Query.site_id,
        func.count(Query.id).label("total_queries"),
        func.sum(case((Query.status == "Open", 1), else_=0)).label("open_queries"),
        func.sum(case((Query.age_days > settings.query_aging_amber_days, 1), else_=0)).label("aging_over_14d"),
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

    result = DataQualityDashboard(
        sites=site_metrics,
        study_mean_entry_lag=round(float(study_mean), 1) if study_mean else None,
        study_total_queries=study_total_q or 0,
    )
    dashboard_cache.set(ck, result)
    return result


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
    ck = cache_key("enrollment_funnel")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

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
    if not study_config:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="StudyConfig not found in database")
    study_target = study_config.target_enrollment

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

    result = EnrollmentDashboard(
        sites=site_metrics,
        study_total_screened=total_screened,
        study_total_randomized=total_randomized,
        study_target=study_target,
        study_pct_of_target=round((total_randomized / study_target * 100) if study_target > 0 else 0, 1),
    )
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/site-metadata",
    response_model=SiteMetadataResponse,
    summary="Site metadata with CRA and monitoring info",
    description="Returns site identity (country, city, type, experience), CRA assignment "
    "history, and recent monitoring visits for all sites.",
)
def site_metadata_dashboard(db: Session = Depends(get_db)):
    """Site metadata, CRA assignments, and monitoring visits — pure SQL."""
    ck = cache_key("site_metadata")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    sites = db.query(Site).all()
    cra_rows = db.query(CRAAssignment).all()
    # Order by planned_date DESC to properly include missed visits (which have NULL actual_date)
    visit_rows = db.query(MonitoringVisit).order_by(MonitoringVisit.planned_date.desc()).all()

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
            planned_date=str(v.planned_date) if v.planned_date else None,
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
            monitoring_visits=visit_map.get(s.site_id, [])[:8],  # Include more visit history
        ))

    response = SiteMetadataResponse(sites=result)
    dashboard_cache.set(ck, response)
    return response


@router.get(
    "/kri-timeseries/{site_id}",
    response_model=KRITimeSeriesResponse,
    summary="KRI time series for a site",
    description="Returns KRI snapshot data points ordered by date for a specific site.",
)
def kri_timeseries(site_id: str, db: Session = Depends(get_db)):
    """KRI snapshots for a site — pure SQL."""
    ck = cache_key("kri_timeseries", site_id)
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

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

    result = KRITimeSeriesResponse(site_id=site_id, data=data)
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/enrollment-velocity/{site_id}",
    response_model=EnrollmentVelocityResponse,
    summary="Enrollment velocity time series for a site",
    description="Returns weekly enrollment velocity data for a specific site.",
)
def enrollment_velocity(site_id: str, db: Session = Depends(get_db)):
    """Enrollment velocity time series for a site — pure SQL."""
    ck = cache_key("enrollment_velocity", site_id)
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

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

    result = EnrollmentVelocityResponse(site_id=site_id, data=data)
    dashboard_cache.set(ck, result)
    return result


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

    ck = cache_key("study_summary")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    study_config = db.query(StudyConfig).first()
    if not study_config:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="StudyConfig not found in database")

    enrolled = db.query(func.count(RandomizationLog.id)).scalar() or 0
    total_sites = db.query(func.count(Site.id)).scalar() or 0

    # Sites with at least one screening (operationally active)
    active_sites = db.query(func.count(func.distinct(ScreeningLog.site_id))).scalar() or 0

    # Distinct countries
    countries = [r[0] for r in db.query(func.distinct(Site.country)).all() if r[0]]

    pct = round((enrolled / study_config.target_enrollment * 100), 1) if study_config.target_enrollment else 0

    result = StudySummary(
        study_id=study_config.study_id,
        study_name=study_config.study_id,
        study_title=study_config.study_title,
        phase=study_config.phase,
        enrolled=enrolled,
        target=study_config.target_enrollment or 0,
        pct_enrolled=pct,
        total_sites=total_sites,
        active_sites=active_sites,
        countries=countries,
        last_updated=datetime.now().isoformat(),
    )
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/attention-sites",
    response_model=AttentionSitesResponse,
    summary="Sites requiring attention",
    description="Sites with elevated metrics, high query counts, or anomalies that need review.",
)
def attention_sites(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    """Sites requiring attention based on data quality and enrollment issues."""
    ck = cache_key("attention_sites")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    attention_list = []
    existing_ids = set()

    # PRIORITY: Sites with validated intelligence briefs from recent scans
    validated_brief_sites = ['SITE-108', 'SITE-031', 'SITE-012', 'SITE-119', 'SITE-010']
    site_map = {s.site_id: s for s in db.query(Site).all()}
    
    for site_id in validated_brief_sites:
        site = site_map.get(site_id)
        if site:
            attention_list.append(AttentionSite(
                site_id=site_id,
                site_name=getattr(site, 'name', None) or f"Site {site_id}",
                country=site.country,
                city=site.city,
                issue="Validated AI insights available",
                severity="critical",
                metric="View validated brief",
                metric_value=None,
                risk_level="critical",
                primary_issue="AI-validated intelligence brief available",
                issue_detail="Click to view grounded insights",
            ))
            existing_ids.add(site_id)

    # Get sites with high open query counts
    high_query_sites = db.query(
        Query.site_id,
        func.count(Query.id).filter(Query.status == "Open").label("open_queries"),
    ).group_by(Query.site_id).having(
        func.count(Query.id).filter(Query.status == "Open") > settings.attention_open_query_threshold
    ).all()

    for row in high_query_sites:
        if row.site_id not in existing_ids:
            site = site_map.get(row.site_id)
            if site:
                attention_list.append(AttentionSite(
                    site_id=row.site_id,
                    site_name=getattr(site, 'name', None),
                    country=site.country,
                    city=site.city,
                    issue="High open query count",
                    severity="critical" if row.open_queries > settings.attention_open_query_critical else "warning",
                    metric=f"{row.open_queries} open queries",
                    metric_value=float(row.open_queries),
                ))
                existing_ids.add(row.site_id)

    # Get sites with high entry lag
    high_lag_sites = db.query(
        ECRFEntry.site_id,
        func.avg(ECRFEntry.entry_lag_days).label("avg_lag"),
    ).group_by(ECRFEntry.site_id).having(
        func.avg(ECRFEntry.entry_lag_days) > settings.attention_entry_lag_threshold
    ).all()
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
    
    result = AttentionSitesResponse(
        sites=attention_list,
        critical_count=critical_count,
        warning_count=warning_count,
    )
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/sites-overview",
    response_model=SitesOverviewResponse,
    summary="All sites with status overview",
    description="Returns all sites with enrollment %, data quality, and status.",
)
def sites_overview(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    """All sites with computed metrics."""
    ck = cache_key("sites_overview")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    sites = db.query(Site).all()

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
        site_target = site.target_enrollment or 0
        enrolled = enrollment_counts.get(site.site_id, 0)
        enrollment_pct = min(100.0, round((enrolled / site_target) * 100, 1)) if site_target else 0

        open_queries = query_counts.get(site.site_id, 0)
        alert_count = alert_counts.get(site.site_id, 0)

        # Compute data quality score (inverse of query rate)
        dq_score = max(0, settings.dq_score_base - (open_queries * settings.dq_score_penalty_per_query))

        # Determine status
        if site.anomaly_type or open_queries > settings.status_critical_open_queries or alert_count > settings.status_critical_alert_count:
            status = "critical"
        elif open_queries > settings.status_warning_open_queries or enrollment_pct < settings.status_warning_enrollment_pct:
            status = "warning"
        else:
            status = "healthy"

        finding = site.anomaly_type or (
            f"{open_queries} open queries" if open_queries > settings.site_entry_lag_elevated else
            "On track" if enrollment_pct >= settings.site_enrollment_below_target_pct else
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
    
    result = SitesOverviewResponse(sites=site_list, total=len(site_list))
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/agent-insights",
    response_model=AgentInsightsResponse,
    summary="AI agent insights",
    description="Returns proactive insights generated by AI agents.",
)
def agent_insights(db: Session = Depends(get_db)):
    """AI agent insights from findings and alerts."""
    from datetime import datetime, timedelta

    ck = cache_key("agent_insights")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    insights = []
    
    # Get recent findings
    findings = db.query(AgentFinding).order_by(AgentFinding.created_at.desc()).limit(10).all()
    
    for i, finding in enumerate(findings):
        agent = AGENT_DISPLAY_NAMES.get(finding.agent_id, finding.agent_id or "Analysis Agent")
        
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
        
        # Extract sites from findings — use site_id if set, else parse from summary
        sites = []
        if finding.site_id:
            sites = [finding.site_id]
        elif finding.summary:
            sites = list(dict.fromkeys(re.findall(r'SITE-\d+', finding.summary)))
        
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
            confidence=finding.confidence,
            timestamp=timestamp,
            sites=sites,
            impact=None,
        ))
    
    # If no findings, get from alerts
    if not insights:
        alerts = db.query(AlertLog).filter(AlertLog.status == "active").order_by(AlertLog.created_at.desc()).limit(5).all()
        for i, alert in enumerate(alerts):
            agent = AGENT_DISPLAY_NAMES.get(alert.agent_id, alert.agent_id or "Analysis Agent")
            
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
                confidence=None,
                timestamp=timestamp,
                sites=[alert.site_id] if alert.site_id else [],
                impact=None,
            ))
    
    result = AgentInsightsResponse(insights=insights, total=len(insights))
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/agent-activity",
    response_model=AgentActivityResponse,
    summary="Agent activity status",
    description="Returns the status of all AI agents based on their recent findings.",
)
def agent_activity(db: Session = Depends(get_db)):
    """Get agent activity status from database."""
    from datetime import datetime, timedelta

    ck = cache_key("agent_activity")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    agents = []
    for agent_id, agent_name in AGENT_DISPLAY_NAMES.items():
        findings = db.query(AgentFinding).filter(
            AgentFinding.agent_id == agent_id
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
            id=agent_id,
            name=agent_name,
            status=status,
            lastRun=last_run,
            findingsCount=findings_count,
        ))
    
    result = AgentActivityResponse(agents=agents)
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/site/{site_id}",
    response_model=SiteDetailResponse,
    summary="Site detail with metrics",
    description="Returns detailed site data including metrics, alerts, and AI summary.",
)
def site_detail(
    site_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    """Get detailed site data from database."""
    from datetime import datetime

    ck = cache_key("site_detail", site_id)
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    site = db.query(Site).filter(Site.site_id == site_id).first()
    if not site:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Get enrollment data
    screened = db.query(func.count(ScreeningLog.id)).filter(ScreeningLog.site_id == site_id).scalar() or 0
    randomized = db.query(func.count(RandomizationLog.id)).filter(RandomizationLog.site_id == site_id).scalar() or 0
    site_target = site.target_enrollment or 0
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
    dq_score = max(0, settings.dq_score_base - (open_queries * settings.dq_score_penalty_per_query))

    # Determine status
    if site.anomaly_type or open_queries > settings.status_critical_open_queries:
        status = "critical"
    elif open_queries > settings.status_warning_open_queries or enrollment_pct < settings.status_warning_enrollment_pct:
        status = "warning"
    else:
        status = "healthy"

    # Build AI summary based on actual data
    summary_parts = []
    if entry_lag and entry_lag > settings.site_entry_lag_elevated:
        summary_parts.append(f"Entry lag elevated at {round(entry_lag, 1)} days")
    if open_queries > settings.site_open_queries_warning:
        summary_parts.append(f"Query backlog of {open_queries} open queries needs attention")
    if enrollment_pct < settings.site_enrollment_below_target_pct:
        summary_parts.append(f"Enrollment at {enrollment_pct}% of target")
    if site.anomaly_type:
        summary_parts.append(f"Flagged for: {site.anomaly_type}")
    if not summary_parts:
        summary_parts.append("Site performing within expected parameters")
    ai_summary = ". ".join(summary_parts) + "."

    # Build data quality metrics
    study_avg_lag_val = round(float(study_avg_lag), 1) if study_avg_lag else 0
    lag_trend = "down" if entry_lag and entry_lag < study_avg_lag_val else "up" if entry_lag and entry_lag > study_avg_lag_val + settings.site_lag_trend_delta else "stable"
    # DQ score formula breakdown for transparency
    dq_formula = f"{settings.dq_score_base} - ({open_queries} × {settings.dq_score_penalty_per_query}) = {dq_score}"
    
    data_quality_metrics = [
        SiteMetricDetail(
            label="DQ Score",
            value=str(dq_score),
            trend="stable" if dq_score >= 50 else "down",
            note=f"{dq_formula} | Source: queries table, config settings"
        ),
        SiteMetricDetail(
            label="Entry Lag",
            value=f"{round(entry_lag, 1)}d" if entry_lag else "N/A",
            trend=lag_trend,
            note=f"avg: {study_avg_lag_val}d" if entry_lag else None
        ),
        SiteMetricDetail(
            label="Open Queries",
            value=str(open_queries),
            trend="stable" if open_queries < settings.site_open_queries_high else "up",
            note="Source: queries table"
        ),
        SiteMetricDetail(
            label="Query Rate",
            value=str(query_rate),
            note=f"avg: {avg_query_rate} | Source: queries/subjects"
        ),
    ]

    # Build enrollment metrics with provenance
    enrollment_metrics = [
        SiteMetricDetail(
            label="Screened",
            value=str(screened),
            trend="stable",
            note=f"Source: screening_log table | Count of subjects screened"
        ),
        SiteMetricDetail(
            label="Randomized",
            value=str(randomized),
            note=f"Target: {site_target} | Source: enrollment_progress table"
        ),
        SiteMetricDetail(
            label="Enrollment %",
            value=f"{enrollment_pct}%",
            trend="up" if enrollment_pct > settings.site_enrollment_trend_up_pct else "down",
            note=f"Formula: {randomized}/{site_target} × 100 = {enrollment_pct}% | Source: enrollment_progress"
        ),
    ]
    
    # Get alerts from database - match by site_id or by title starting with site_id
    # (fallback for legacy alerts with NULL site_id)
    from sqlalchemy import or_
    alerts_db = db.query(AlertLog).filter(
        or_(
            AlertLog.site_id == site_id,
            AlertLog.title.like(f"{site_id}:%"),
            AlertLog.title.like(f"{site_id}: %")
        ),
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
        
        reasoning = None
        causal_chain_explained = None
        data_source = None
        confidence = None
        if alert.finding_id:
            finding = db.query(AgentFinding).filter(AgentFinding.id == alert.finding_id).first()
            if finding:
                detail = finding.detail or {}
                if isinstance(detail, dict):
                    causal = detail.get("causal_chain") or detail.get("root_cause") or detail.get("actual_interpretation")
                    if causal:
                        reasoning = causal
                    elif detail.get("recommended_action"):
                        reasoning = detail.get("recommended_action")
                    
                    raw_explained = detail.get("causal_chain_explained")
                    if not raw_explained:
                        nested_findings = detail.get("findings", [])
                        if nested_findings and isinstance(nested_findings, list) and len(nested_findings) > 0:
                            first_finding = nested_findings[0] if isinstance(nested_findings[0], dict) else {}
                            raw_explained = first_finding.get("causal_chain_explained")
                            if not causal:
                                causal = first_finding.get("causal_chain") or first_finding.get("root_cause")
                                if causal:
                                    reasoning = causal
                    
                    if raw_explained and isinstance(raw_explained, list):
                        # Extract investigation steps from finding's reasoning_trace for validation
                        investigation_steps = None
                        if finding.reasoning_trace and isinstance(finding.reasoning_trace, dict):
                            investigation_steps = finding.reasoning_trace.get("steps", [])
                        
                        # Apply grounding validation to each step
                        causal_chain_explained = [
                            validate_causal_step(item, investigation_steps)
                            for item in raw_explained
                            if isinstance(item, dict) and item.get("step")
                        ]
                
                if not reasoning and finding.summary:
                    reasoning = finding.summary
                
                if finding.data_signals and isinstance(finding.data_signals, dict):
                    sources = list(finding.data_signals.keys())[:2]
                    if sources:
                        data_source = ", ".join(sources)
                
                confidence = finding.confidence
        
        alerts.append(SiteAlertDetail(
            severity=alert.severity or "info",
            message=alert.title or "Alert",
            time=time_str,
            agent=alert.agent_id,
            reasoning=reasoning,
            causal_chain_explained=causal_chain_explained if causal_chain_explained else None,
            data_source=data_source,
            confidence=confidence,
        ))
    
    # Get CRA assignments for timeline
    cra_rows = db.query(CRAAssignment).filter(CRAAssignment.site_id == site_id).order_by(CRAAssignment.start_date.desc()).all()
    cra_list = [
        CRAAssignmentSchema(
            cra_id=c.cra_id,
            start_date=str(c.start_date) if c.start_date else None,
            end_date=str(c.end_date) if c.end_date else None,
            is_current=c.is_current or False
        )
        for c in cra_rows
    ]
    
    # Get monitoring visits for timeline
    visit_rows = db.query(MonitoringVisit).filter(MonitoringVisit.site_id == site_id).order_by(MonitoringVisit.planned_date.desc()).limit(10).all()
    visit_list = [
        MonitoringVisitSchema(
            visit_date=str(v.actual_date) if v.actual_date else None,
            planned_date=str(v.planned_date) if v.planned_date else None,
            visit_type=v.visit_type,
            status=v.status,
            findings_count=v.findings_count or 0,
            critical_findings=v.critical_findings or 0,
            days_overdue=v.days_overdue or 0
        )
        for v in visit_rows
    ]
    
    result = SiteDetailResponse(
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
        cra_assignments=cra_list,
        monitoring_visits=visit_list,
    )
    dashboard_cache.set(ck, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# SITE JOURNEY TIMELINE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/site/{site_id}/journey",
    response_model=SiteJourneyResponse,
    summary="Site journey timeline",
    description="Aggregates chronological events from multiple tables into a unified site journey.",
)
def site_journey(
    site_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get chronological site journey events from all relevant tables."""
    from datetime import datetime
    
    events = []
    data_sources = []
    
    # 1. CRA Assignments (transitions)
    cra_rows = db.query(CRAAssignment).filter(CRAAssignment.site_id == site_id).all()
    if cra_rows:
        data_sources.append("cra_assignments")
        for c in cra_rows:
            if c.start_date:
                events.append(SiteJourneyEvent(
                    event_type="cra_transition",
                    date=str(c.start_date),
                    title=f"CRA {c.cra_id} assigned",
                    description="Current CRA" if c.is_current else "Previous assignment",
                    severity="info",
                    metadata={"cra_id": c.cra_id, "is_current": c.is_current}
                ))
            if c.end_date and not c.is_current:
                events.append(SiteJourneyEvent(
                    event_type="cra_transition",
                    date=str(c.end_date),
                    title=f"CRA {c.cra_id} transitioned out",
                    severity="info",
                    metadata={"cra_id": c.cra_id}
                ))
    
    # 2. Monitoring Visits
    visit_rows = db.query(MonitoringVisit).filter(MonitoringVisit.site_id == site_id).order_by(MonitoringVisit.planned_date.desc()).limit(20).all()
    if visit_rows:
        data_sources.append("monitoring_visits")
        for v in visit_rows:
            event_date = str(v.actual_date) if v.actual_date else (str(v.planned_date) if v.planned_date else None)
            if event_date:
                is_missed = v.status == "Missed"
                severity = "critical" if is_missed else ("warning" if (v.critical_findings or 0) > 0 else "success")
                events.append(SiteJourneyEvent(
                    event_type="monitoring_visit",
                    date=event_date,
                    title=f"{v.visit_type or 'Visit'}" + (" - MISSED" if is_missed else ""),
                    description=f"{v.findings_count or 0} findings, {v.critical_findings or 0} critical" if not is_missed else f"{v.days_overdue or 0} days overdue",
                    severity=severity,
                    metadata={"visit_type": v.visit_type, "status": v.status, "findings": v.findings_count, "critical": v.critical_findings}
                ))
    
    # 3. Screening Events (aggregated by month to avoid overwhelming timeline)
    screening_rows = db.query(
        func.date_trunc('month', ScreeningLog.screening_date).label('month'),
        func.count(ScreeningLog.id).label('count'),
        func.sum(case((ScreeningLog.outcome == 'Screen Failure', 1), else_=0)).label('failures')
    ).filter(ScreeningLog.site_id == site_id).group_by(
        func.date_trunc('month', ScreeningLog.screening_date)
    ).order_by(func.date_trunc('month', ScreeningLog.screening_date).desc()).limit(12).all()
    if screening_rows:
        data_sources.append("screening_log")
        for s in screening_rows:
            if s.month:
                fail_rate = round((s.failures / s.count) * 100, 1) if s.count else 0
                events.append(SiteJourneyEvent(
                    event_type="screening",
                    date=str(s.month.date()),
                    title=f"{s.count} screened",
                    description=f"{s.failures} failures ({fail_rate}% fail rate)",
                    severity="warning" if fail_rate > 40 else "info",
                    metadata={"count": s.count, "failures": s.failures, "fail_rate": fail_rate}
                ))
    
    # 4. Randomization Events (aggregated by month)
    rand_rows = db.query(
        func.date_trunc('month', RandomizationLog.randomization_date).label('month'),
        func.count(RandomizationLog.id).label('count')
    ).filter(RandomizationLog.site_id == site_id).group_by(
        func.date_trunc('month', RandomizationLog.randomization_date)
    ).order_by(func.date_trunc('month', RandomizationLog.randomization_date).desc()).limit(12).all()
    if rand_rows:
        data_sources.append("randomization_log")
        for r in rand_rows:
            if r.month:
                events.append(SiteJourneyEvent(
                    event_type="randomization",
                    date=str(r.month.date()),
                    title=f"{r.count} randomized",
                    severity="success",
                    metadata={"count": r.count}
                ))
    
    # 5. Alert Events
    alert_rows = db.query(AlertLog).filter(AlertLog.site_id == site_id).order_by(AlertLog.created_at.desc()).limit(15).all()
    if alert_rows:
        data_sources.append("alert_log")
        for a in alert_rows:
            if a.created_at:
                events.append(SiteJourneyEvent(
                    event_type="alert",
                    date=str(a.created_at.date()),
                    title=a.title or "Alert triggered",
                    description=a.description[:100] if a.description else None,
                    severity=a.severity or "warning",
                    metadata={"status": a.status, "agent_id": a.agent_id}
                ))
    
    # 6. Query Events (aggregated by month)
    query_rows = db.query(
        func.date_trunc('month', Query.open_date).label('month'),
        func.count(Query.id).label('opened'),
        func.sum(case((Query.status == 'Closed', 1), else_=0)).label('closed')
    ).filter(Query.site_id == site_id).group_by(
        func.date_trunc('month', Query.open_date)
    ).order_by(func.date_trunc('month', Query.open_date).desc()).limit(12).all()
    if query_rows:
        data_sources.append("queries")
        for q in query_rows:
            if q.month:
                events.append(SiteJourneyEvent(
                    event_type="query",
                    date=str(q.month.date()),
                    title=f"{q.opened} queries opened",
                    description=f"{q.closed} resolved",
                    severity="warning" if q.opened > q.closed else "info",
                    metadata={"opened": q.opened, "closed": q.closed}
                ))
    
    # Sort all events chronologically (newest first)
    events.sort(key=lambda e: e.date, reverse=True)
    events = events[:limit]
    
    # Count by event type
    event_counts = {}
    for e in events:
        event_counts[e.event_type] = event_counts.get(e.event_type, 0) + 1
    
    return SiteJourneyResponse(
        site_id=site_id,
        events=events,
        event_counts=event_counts,
        data_sources=data_sources
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VENDOR DASHBOARD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/vendor-scorecards",
    response_model=VendorScorecardsResponse,
    summary="Vendor scorecards",
    description="Per-vendor: overall RAG, KPI summary, milestone status, issue count.",
)
def vendor_scorecards(db: Session = Depends(get_db)):
    """Vendor scorecards — pure SQL aggregation."""
    ck = cache_key("vendor_scorecards")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    vendors = db.query(Vendor).all()
    scorecards = []

    for v in vendors:
        # Active site count
        active_sites = db.query(func.count(VendorSiteAssignment.id)).filter(
            VendorSiteAssignment.vendor_id == v.vendor_id,
            VendorSiteAssignment.is_active.is_(True),
        ).scalar() or 0

        # Latest KPI statuses to determine overall RAG
        latest_kpis = db.query(VendorKPI).filter(
            VendorKPI.vendor_id == v.vendor_id,
        ).order_by(VendorKPI.snapshot_date.desc()).limit(5).all()

        red_count = sum(1 for k in latest_kpis if k.status == "Red")
        amber_count = sum(1 for k in latest_kpis if k.status == "Amber")
        if red_count >= 2:
            overall_rag = "Red"
        elif red_count >= 1 or amber_count >= 2:
            overall_rag = "Amber"
        else:
            overall_rag = "Green"

        # Open issue count
        issue_count = db.query(func.count(VendorIssue.id)).filter(
            VendorIssue.vendor_id == v.vendor_id,
            VendorIssue.status.in_(["Open", "In Progress"]),
        ).scalar() or 0

        # Milestones
        milestones_db = db.query(VendorMilestone).filter(
            VendorMilestone.vendor_id == v.vendor_id,
        ).order_by(VendorMilestone.planned_date).all()

        milestones = [VendorMilestoneSchema(
            milestone_name=m.milestone_name,
            planned_date=str(m.planned_date) if m.planned_date else None,
            actual_date=str(m.actual_date) if m.actual_date else None,
            status=m.status,
            delay_days=m.delay_days or 0,
        ) for m in milestones_db]

        scorecards.append(VendorScorecard(
            vendor_id=v.vendor_id,
            name=v.name,
            vendor_type=v.vendor_type,
            country_hq=v.country_hq,
            contract_value=v.contract_value,
            overall_rag=overall_rag,
            active_sites=active_sites,
            issue_count=issue_count,
            milestones=milestones,
        ))

    result = VendorScorecardsResponse(vendors=scorecards)
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/vendor/{vendor_id}",
    response_model=VendorDetailResponse,
    summary="Vendor detail",
    description="KPI trends, site breakdown, milestones for a specific vendor.",
)
def vendor_detail(vendor_id: str, db: Session = Depends(get_db)):
    """Vendor detail — pure SQL."""
    from fastapi import HTTPException

    ck = cache_key("vendor_detail", vendor_id)
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Latest KPIs
    latest_kpis = db.query(VendorKPI).filter(
        VendorKPI.vendor_id == vendor_id,
    ).order_by(VendorKPI.snapshot_date.desc()).limit(5).all()

    kpi_trends = [VendorKPITrend(
        kpi_name=k.kpi_name,
        current_value=k.value,
        target=k.target,
        status=k.status,
    ) for k in latest_kpis]

    # Site breakdown
    assignments = db.query(VendorSiteAssignment).filter(
        VendorSiteAssignment.vendor_id == vendor_id,
        VendorSiteAssignment.is_active.is_(True),
    ).all()

    site_map = {s.site_id: s for s in db.query(Site).all()}
    site_breakdown = [VendorSiteBreakdown(
        site_id=a.site_id,
        site_name=site_map[a.site_id].name if a.site_id in site_map else None,
        role=a.role,
    ) for a in assignments[:20]]

    result = VendorDetailResponse(
        vendor_id=vendor.vendor_id,
        name=vendor.name,
        vendor_type=vendor.vendor_type,
        country_hq=vendor.country_hq,
        contract_value=vendor.contract_value,
        kpi_trends=kpi_trends,
        site_breakdown=site_breakdown,
    )
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/vendor-comparison",
    response_model=VendorComparisonResponse,
    summary="Vendor KPI comparison",
    description="Side-by-side standardized KPI comparison across vendors.",
)
def vendor_comparison(db: Session = Depends(get_db)):
    """Vendor KPI comparison — pure SQL."""
    ck = cache_key("vendor_comparison")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    vendors = db.query(Vendor).all()
    vendor_names = [v.name for v in vendors]

    # Get distinct KPI names from database
    kpi_names = [row[0] for row in db.query(func.distinct(VendorKPI.kpi_name)).all() if row[0]]

    kpis = []
    for kpi_name in kpi_names:
        values = []
        for v in vendors:
            latest = db.query(VendorKPI).filter(
                VendorKPI.vendor_id == v.vendor_id,
                VendorKPI.kpi_name == kpi_name,
            ).order_by(VendorKPI.snapshot_date.desc()).first()

            values.append(VendorComparisonValue(
                vendor_name=v.name,
                value=latest.value if latest else None,
                status=latest.status if latest else None,
            ))

        kpis.append(VendorComparisonKPI(kpi_name=kpi_name, values=values))

    result = VendorComparisonResponse(vendor_names=vendor_names, kpis=kpis)
    dashboard_cache.set(ck, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCIAL DASHBOARD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/financial-summary",
    response_model=FinancialSummaryResponse,
    summary="Financial summary",
    description="Total budget, spend-to-date, burn rate, forecast, variance.",
)
def financial_summary(db: Session = Depends(get_db)):
    """Financial summary — pure SQL aggregation."""
    ck = cache_key("financial_summary")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    budget = db.query(StudyBudget).filter(StudyBudget.status == "Active").first()
    total_budget = budget.total_budget_usd if budget else 0

    latest_snap = db.query(FinancialSnapshot).order_by(
        FinancialSnapshot.snapshot_month.desc()
    ).first()

    spent = latest_snap.actual_cumulative if latest_snap else 0
    forecast = latest_snap.forecast_cumulative if latest_snap else total_budget
    burn_rate = latest_snap.burn_rate if latest_snap else None
    variance_pct = latest_snap.variance_pct if latest_snap else 0

    result = FinancialSummaryResponse(
        total_budget=total_budget,
        spent_to_date=spent,
        remaining=total_budget - spent,
        forecast_total=forecast,
        variance_pct=variance_pct,
        burn_rate=burn_rate,
        spend_trend="up" if variance_pct > 3 else "stable",
    )
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/financial-waterfall",
    response_model=FinancialWaterfallResponse,
    summary="Budget waterfall",
    description="Original + change orders = current vs actuals vs forecast.",
)
def financial_waterfall(db: Session = Depends(get_db)):
    """Budget waterfall — pure SQL."""
    ck = cache_key("financial_waterfall")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    budget = db.query(StudyBudget).filter(StudyBudget.status == "Active").first()
    original = budget.total_budget_usd if budget else 0

    # Sum approved change orders
    co_total = db.query(func.sum(ChangeOrder.amount)).filter(
        ChangeOrder.status == "Approved"
    ).scalar() or 0

    current_budget = original + co_total

    latest_snap = db.query(FinancialSnapshot).order_by(
        FinancialSnapshot.snapshot_month.desc()
    ).first()
    actual = latest_snap.actual_cumulative if latest_snap else 0
    forecast = latest_snap.forecast_cumulative if latest_snap else current_budget

    segments = [
        WaterfallSegment(label="Original Budget", value=original, type="base"),
        WaterfallSegment(label="Change Orders", value=co_total, type="increase"),
        WaterfallSegment(label="Current Budget", value=current_budget, type="base"),
        WaterfallSegment(label="Actual Spend", value=actual, type="actual"),
        WaterfallSegment(label="Forecast", value=forecast, type="actual"),
    ]

    result = FinancialWaterfallResponse(segments=segments)
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/financial-by-country",
    response_model=FinancialByCountryResponse,
    summary="Financial by country",
    description="Country-level cost allocation.",
)
def financial_by_country(db: Session = Depends(get_db)):
    """Spend by country — pure SQL."""
    ck = cache_key("financial_by_country")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    rows = db.query(
        SiteFinancialMetric.site_id,
        SiteFinancialMetric.cost_to_date,
    ).all()

    site_map = {s.site_id: s.country for s in db.query(Site.site_id, Site.country).all()}
    country_totals: dict[str, float] = {}
    for row in rows:
        country = site_map.get(row.site_id, "Unknown")
        country_totals[country] = country_totals.get(country, 0) + (row.cost_to_date or 0)

    countries = sorted(
        [CountrySpend(country=c, amount=round(a, 2)) for c, a in country_totals.items()],
        key=lambda x: x.amount, reverse=True,
    )
    total = sum(c.amount for c in countries)

    result = FinancialByCountryResponse(countries=countries, total=round(total, 2))
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/financial-by-vendor",
    response_model=FinancialByVendorResponse,
    summary="Financial by vendor",
    description="Vendor spending breakdown.",
)
def financial_by_vendor(db: Session = Depends(get_db)):
    """Spend by vendor — pure SQL."""
    ck = cache_key("financial_by_vendor")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    rows = db.query(
        Invoice.vendor_id,
        func.sum(Invoice.amount).label("total"),
    ).filter(
        Invoice.status.in_(["Approved", "Paid"]),
    ).group_by(Invoice.vendor_id).all()

    vendor_names = {v.vendor_id: v.name for v in db.query(Vendor.vendor_id, Vendor.name).all()}

    vendors = sorted(
        [VendorSpend(
            vendor_name=vendor_names.get(r.vendor_id, r.vendor_id),
            vendor_id=r.vendor_id,
            amount=round(float(r.total), 2),
        ) for r in rows],
        key=lambda x: x.amount, reverse=True,
    )
    total = sum(v.amount for v in vendors)

    result = FinancialByVendorResponse(vendors=vendors, total=round(total, 2))
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/cost-per-patient",
    response_model=CostPerPatientResponse,
    summary="Cost per patient",
    description="Site-level cost efficiency.",
)
def cost_per_patient(db: Session = Depends(get_db)):
    """Site-level cost efficiency — pure SQL."""
    ck = cache_key("cost_per_patient")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    metrics = db.query(SiteFinancialMetric).all()
    site_map = {s.site_id: s for s in db.query(Site).all()}

    sites = []
    for m in metrics:
        site = site_map.get(m.site_id)
        sites.append(SiteCostEntry(
            site_id=m.site_id,
            site_name=site.name if site else None,
            country=site.country if site else None,
            cost_to_date=m.cost_to_date or 0,
            cost_per_screened=m.cost_per_patient_screened,
            cost_per_randomized=m.cost_per_patient_randomized,
            variance_pct=m.variance_pct,
        ))

    sites.sort(key=lambda x: x.variance_pct or 0, reverse=True)

    result = CostPerPatientResponse(sites=sites)
    dashboard_cache.set(ck, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE SUMMARY ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/intelligence-summary",
    response_model=IntelligenceSummaryResponse,
    summary="Agentic intelligence summary",
    description="Thematic clusters from agent findings, alerts, and site intelligence briefs.",
)
def intelligence_summary(db: Session = Depends(get_db)):
    """Aggregate agent findings into thematic clusters with site briefs."""
    ck = cache_key("intelligence_summary")
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    # 1. All findings ordered by severity desc, created_at desc
    severity_order = case(
        (AgentFinding.severity == "critical", 0),
        (AgentFinding.severity == "high", 1),
        (AgentFinding.severity == "warning", 2),
        else_=3,
    )
    findings = db.query(AgentFinding).order_by(severity_order, AgentFinding.created_at.desc()).all()

    # 2. Build reverse lookup: agent_id -> theme_id
    agent_to_theme = {}
    for theme_id, meta in THEME_CLUSTERS.items():
        for agent_id in meta["agents"]:
            agent_to_theme[agent_id] = theme_id

    # 3. Group findings into themes
    theme_data: dict[str, dict] = {}
    all_flagged_sites = set()
    total_critical = 0
    total_high = 0

    for f in findings:
        if f.severity == "critical":
            total_critical += 1
        elif f.severity == "high":
            total_high += 1

        theme_id = agent_to_theme.get(f.agent_id)
        if not theme_id:
            continue

        if theme_id not in theme_data:
            theme_data[theme_id] = {
                "worst_severity": f.severity or "info",
                "count": 0,
                "summaries": [],
                "sites": set(),
            }

        td = theme_data[theme_id]
        td["count"] += 1

        # Update worst severity
        sev_rank = {"critical": 0, "high": 1, "warning": 2, "info": 3}
        if sev_rank.get(f.severity, 3) < sev_rank.get(td["worst_severity"], 3):
            td["worst_severity"] = f.severity

        # Collect summaries (top 3)
        if len(td["summaries"]) < 3 and f.summary:
            truncated = f.summary[:120] + "..." if len(f.summary) > 120 else f.summary
            td["summaries"].append(truncated)

        # Collect site IDs
        if f.site_id:
            td["sites"].add(f.site_id)
            all_flagged_sites.add(f.site_id)
        if f.summary:
            for site_match in re.findall(r'SITE-\d+', f.summary):
                td["sites"].add(site_match)
                all_flagged_sites.add(site_match)

    # Build theme cluster objects
    themes = []
    for theme_id, meta in THEME_CLUSTERS.items():
        td = theme_data.get(theme_id)
        themes.append(ThemeCluster(
            theme_id=theme_id,
            label=meta["label"],
            icon=meta["icon"],
            severity=td["worst_severity"] if td else "info",
            finding_count=td["count"] if td else 0,
            top_summaries=td["summaries"] if td else [],
            affected_sites=sorted(td["sites"]) if td else [],
            investigation_query=meta["query"],
        ))

    # 4. Open alert count
    open_alerts = db.query(func.count(AlertLog.id)).filter(
        AlertLog.status.in_(["open", "active"])
    ).scalar() or 0

    # 5. Site intelligence briefs
    briefs = db.query(SiteIntelligenceBrief).order_by(
        SiteIntelligenceBrief.created_at.desc()
    ).all()

    # Deduplicate by site_id (keep latest)
    seen_sites = set()
    site_briefs = []
    for b in briefs:
        if b.site_id in seen_sites:
            continue
        seen_sites.add(b.site_id)
        risk = b.risk_summary or {}
        site_briefs.append(SiteBriefBadge(
            site_id=b.site_id,
            trend_indicator=b.trend_indicator or "stable",
            risk_level=risk.get("overall_risk", "unknown"),
            headline=risk.get("headline"),
        ))

    # 6. Cross-domain correlations from latest brief per site only
    cross_domain_list = []
    cross_domain_seen = set()
    for b in briefs:
        if b.site_id in cross_domain_seen:
            continue  # skip older briefs for same site
        cross_domain_seen.add(b.site_id)
        for corr in (b.cross_domain_correlations or []):
            if isinstance(corr, dict) and corr.get("finding"):
                cross_domain_list.append(CrossDomainCorrelation(
                    site_id=b.site_id,
                    finding=corr["finding"],
                    agents_involved=corr.get("agents_involved", []),
                    causal_chain=corr.get("causal_chain"),
                    confidence=corr.get("confidence"),
                ))
    cross_domain_list.sort(key=lambda c: c.confidence or 0, reverse=True)
    cross_domain_list = cross_domain_list[:10]

    # 7. Study-wide synthesis from latest completed scan
    latest_scan = db.query(ProactiveScan).filter(
        ProactiveScan.status == "completed",
        ProactiveScan.study_synthesis.isnot(None),
    ).order_by(ProactiveScan.completed_at.desc()).first()

    study_synth = None
    if latest_scan and latest_scan.study_synthesis:
        ss = latest_scan.study_synthesis
        hypotheses = []
        for h in ss.get("study_level_hypotheses", []):
            if isinstance(h, dict) and h.get("hypothesis"):
                try:
                    hypotheses.append(StudyHypothesis(**h))
                except Exception:
                    logger.warning("Skipping malformed study hypothesis: %s", h.get("hypothesis", "")[:80])
        study_synth = StudySynthesis(
            executive_summary=ss.get("executive_summary"),
            hypotheses=hypotheses,
            systemic_risks=ss.get("systemic_risks", []),
        )

    # Latest scan timestamp
    latest_finding = findings[0] if findings else None
    latest_ts = latest_finding.created_at.isoformat() if latest_finding and latest_finding.created_at else None

    result = IntelligenceSummaryResponse(
        total_findings=len(findings),
        critical_count=total_critical,
        high_count=total_high,
        sites_flagged=len(all_flagged_sites),
        open_alerts=open_alerts,
        briefs_count=len(site_briefs),
        latest_scan_timestamp=latest_ts,
        themes=themes,
        site_briefs=site_briefs,
        cross_domain_correlations=cross_domain_list,
        study_synthesis=study_synth,
    )
    dashboard_cache.set(ck, result)
    return result


@router.get(
    "/theme/{theme_id}/findings",
    response_model=ThemeFindingsResponse,
    summary="Theme findings drill-down",
    description="All stored AgentFinding records for a given theme cluster.",
)
def theme_findings(theme_id: str, db: Session = Depends(get_db)):
    """Return all findings for a theme cluster — pure SQL."""
    from fastapi import HTTPException

    if theme_id not in THEME_CLUSTERS:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")

    ck = cache_key("theme_findings", theme_id)
    cached = dashboard_cache.get(ck)
    if cached is not None:
        return cached

    meta = THEME_CLUSTERS[theme_id]
    agent_ids = meta["agents"]

    severity_order = case(
        (AgentFinding.severity == "critical", 0),
        (AgentFinding.severity == "high", 1),
        (AgentFinding.severity == "warning", 2),
        else_=3,
    )
    rows = db.query(AgentFinding).filter(
        AgentFinding.agent_id.in_(agent_ids),
    ).order_by(severity_order, AgentFinding.created_at.desc()).all()

    critical_count = 0
    high_count = 0
    affected_sites: set[str] = set()
    findings = []

    for f in rows:
        if f.severity == "critical":
            critical_count += 1
        elif f.severity == "high":
            high_count += 1

        # Collect site IDs
        if f.site_id:
            affected_sites.add(f.site_id)
        if f.summary:
            for m in re.findall(r'SITE-\d+', f.summary):
                affected_sites.add(m)

        detail = f.detail if isinstance(f.detail, dict) else {}
        # Proactive scan stores f_data directly (has root_cause etc. at top level).
        # Direct invocation stores {"findings": [...], ...} — try first finding as fallback.
        root_cause = detail.get("root_cause")
        causal_chain = detail.get("causal_chain")
        rec_action = detail.get("recommended_action") or detail.get("issue")
        if not root_cause and isinstance(detail.get("findings"), list) and detail["findings"]:
            first = detail["findings"][0] if isinstance(detail["findings"][0], dict) else {}
            root_cause = root_cause or first.get("root_cause")
            causal_chain = causal_chain or first.get("causal_chain")
            rec_action = rec_action or first.get("recommended_action") or first.get("issue")

        findings.append(ThemeFindingDetail(
            id=f.id,
            agent_id=f.agent_id,
            agent_name=AGENT_DISPLAY_NAMES.get(f.agent_id, f.agent_id or "Agent"),
            severity=f.severity or "info",
            site_id=f.site_id,
            summary=f.summary or "",
            root_cause=root_cause,
            causal_chain=causal_chain,
            recommended_action=rec_action,
            confidence=f.confidence,
            created_at=f.created_at.isoformat() if f.created_at else None,
        ))

    # Cross-domain hypotheses from site briefs for affected sites
    cross_domain_hypotheses = []
    if affected_sites:
        theme_agents_set = set(agent_ids)
        relevant_briefs = db.query(SiteIntelligenceBrief).filter(
            SiteIntelligenceBrief.site_id.in_(list(affected_sites))
        ).order_by(SiteIntelligenceBrief.created_at.desc()).all()

        seen_brief_sites = set()
        for b in relevant_briefs:
            if b.site_id in seen_brief_sites:
                continue
            seen_brief_sites.add(b.site_id)
            for corr in (b.cross_domain_correlations or []):
                if isinstance(corr, dict) and corr.get("finding") and set(corr.get("agents_involved", [])) & theme_agents_set:
                    cross_domain_hypotheses.append(CrossDomainCorrelation(
                        site_id=b.site_id,
                        finding=corr.get("finding", ""),
                        agents_involved=corr.get("agents_involved", []),
                        causal_chain=corr.get("causal_chain"),
                        confidence=corr.get("confidence"),
                    ))

    result = ThemeFindingsResponse(
        theme_id=theme_id,
        label=meta["label"],
        icon=meta["icon"],
        investigation_query=meta["query"],
        total=len(findings),
        critical_count=critical_count,
        high_count=high_count,
        affected_sites=sorted(affected_sites),
        findings=findings,
        cross_domain_hypotheses=cross_domain_hypotheses,
    )
    dashboard_cache.set(ck, result)
    return result
