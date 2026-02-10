"""Shared data service for dashboard endpoints and agent tools.

Pure functions that query the CODM tables — no HTTP, no Pydantic, no caching.
Both dashboard endpoints and agent tools call these to ensure data consistency.
"""

import logging
from sqlalchemy import func, case, desc
from sqlalchemy.orm import Session

from data_generators.models import (
    Site, ECRFEntry, Query, RandomizationLog, MonitoringVisitReport,
)
from backend.models.governance import AlertLog, SiteIntelligenceBrief, SiteRiskAssessment

logger = logging.getLogger(__name__)


def get_attention_sites_data(db: Session, settings) -> dict:
    """Return sites needing attention with severity, issue type, and metrics.

    Sources: SiteIntelligenceBrief (validated briefs), Query (open queries),
    ECRFEntry (entry lag), Site (anomaly flags).

    Returns dict with keys: sites (list of dicts), critical_count, warning_count.
    """
    attention_list = []
    existing_ids = set()
    site_map = {s.site_id: s for s in db.query(Site).all()}

    # Load LLM risk assessments for severity enrichment
    risk_map: dict[str, SiteRiskAssessment] = {}
    risk_rows = (
        db.query(SiteRiskAssessment)
        .order_by(SiteRiskAssessment.created_at.desc())
        .all()
    )
    for r in risk_rows:
        if r.site_id not in risk_map:
            risk_map[r.site_id] = r

    # Identify sites with MVR (Monitoring Visit Report) narrative evidence
    mvr_site_ids = set(
        row[0] for row in db.query(MonitoringVisitReport.site_id).distinct().all()
    )

    # PRIORITY 0a: MVR-backed sites (high-confidence narrative evidence) — always shown
    for site_id in mvr_site_ids:
        assessment = risk_map.get(site_id)
        site = site_map.get(site_id)
        if assessment and site and site_id not in existing_ids:
            attention_list.append({
                "site_id": site_id,
                "site_name": getattr(site, 'name', None) or f"Site {site_id}",
                "country": site.country,
                "city": site.city,
                "issue": assessment.status_rationale[:100] if assessment.status_rationale else "MVR narrative analysis",
                "severity": assessment.status if assessment.status in ("critical", "warning") else "warning",
                "metric": f"Risk score: {assessment.risk_score:.2f}",
                "metric_value": assessment.risk_score,
                "risk_level": assessment.status if assessment.status in ("critical", "warning") else "warning",
                "primary_issue": (assessment.key_drivers or ["MVR-backed risk"])[0],
                "issue_detail": assessment.status_rationale,
            })
            existing_ids.add(site_id)

    # PRIORITY 0b: Other sites classified critical/warning by LLM risk assessment
    for site_id, assessment in risk_map.items():
        if assessment.status in ("critical", "warning") and site_id not in existing_ids:
            site = site_map.get(site_id)
            if site and len(attention_list) < 10:
                attention_list.append({
                    "site_id": site_id,
                    "site_name": getattr(site, 'name', None) or f"Site {site_id}",
                    "country": site.country,
                    "city": site.city,
                    "issue": assessment.status_rationale[:100] if assessment.status_rationale else "LLM risk assessment",
                    "severity": assessment.status,
                    "metric": f"Risk score: {assessment.risk_score:.2f}",
                    "metric_value": assessment.risk_score,
                    "risk_level": assessment.status,
                    "primary_issue": (assessment.key_drivers or ["Risk identified"])[0],
                    "issue_detail": assessment.status_rationale,
                })
                existing_ids.add(site_id)

    # PRIORITY 1: Sites with validated intelligence briefs (not already from risk assessment)
    recent_briefs = (
        db.query(
            SiteIntelligenceBrief.site_id,
            func.max(SiteIntelligenceBrief.created_at).label('latest'),
        )
        .group_by(SiteIntelligenceBrief.site_id)
        .order_by(desc('latest'))
        .limit(10)
        .all()
    )
    validated_brief_sites = [row.site_id for row in recent_briefs if row.site_id]

    for site_id in validated_brief_sites[:5]:
        site = site_map.get(site_id)
        if site:
            attention_list.append({
                "site_id": site_id,
                "site_name": getattr(site, 'name', None) or f"Site {site_id}",
                "country": site.country,
                "city": site.city,
                "issue": "Validated AI insights available",
                "severity": "critical",
                "metric": "View validated brief",
                "metric_value": None,
                "risk_level": "critical",
                "primary_issue": "AI-validated intelligence brief available",
                "issue_detail": "Click to view grounded insights",
            })
            existing_ids.add(site_id)

    # Sites with high open query counts
    high_query_sites = (
        db.query(
            Query.site_id,
            func.count(Query.id).filter(Query.status == "Open").label("open_queries"),
        )
        .group_by(Query.site_id)
        .having(
            func.count(Query.id).filter(Query.status == "Open") > settings.attention_open_query_threshold
        )
        .all()
    )

    for row in high_query_sites:
        if row.site_id not in existing_ids:
            site = site_map.get(row.site_id)
            if site:
                # Use LLM risk assessment severity if available, else fallback to threshold
                risk_a = risk_map.get(row.site_id)
                severity = risk_a.status if risk_a else (
                    "critical" if row.open_queries > settings.attention_open_query_critical else "warning"
                )
                attention_list.append({
                    "site_id": row.site_id,
                    "site_name": getattr(site, 'name', None),
                    "country": site.country,
                    "city": site.city,
                    "issue": "High open query count",
                    "severity": severity,
                    "metric": f"{row.open_queries} open queries",
                    "metric_value": float(row.open_queries),
                    "risk_level": severity,
                    "primary_issue": "High open query burden",
                    "issue_detail": f"{row.open_queries} unresolved queries indicating data collection or monitoring gaps",
                })
                existing_ids.add(row.site_id)

    # Sites with high entry lag
    high_lag_sites = (
        db.query(
            ECRFEntry.site_id,
            func.avg(ECRFEntry.entry_lag_days).label("avg_lag"),
        )
        .group_by(ECRFEntry.site_id)
        .having(func.avg(ECRFEntry.entry_lag_days) > settings.attention_entry_lag_threshold)
        .all()
    )
    for row in high_lag_sites:
        if row.site_id not in existing_ids:
            site = site_map.get(row.site_id)
            if site:
                risk_a = risk_map.get(row.site_id)
                severity = risk_a.status if risk_a else "warning"
                attention_list.append({
                    "site_id": row.site_id,
                    "site_name": getattr(site, 'name', None),
                    "country": site.country,
                    "city": site.city,
                    "issue": "Elevated entry lag",
                    "severity": severity,
                    "metric": f"{round(row.avg_lag, 1)} day lag",
                    "metric_value": float(row.avg_lag),
                    "risk_level": severity,
                    "primary_issue": "Elevated data entry lag",
                    "issue_detail": f"Average {round(row.avg_lag, 1)}-day delay between patient visits and eCRF data entry",
                })
                existing_ids.add(row.site_id)

    # Sites with anomaly types
    anomaly_sites = db.query(Site).filter(Site.anomaly_type.isnot(None)).limit(5).all()
    for site in anomaly_sites:
        if site.site_id not in existing_ids:
            anomaly_desc = site.anomaly_type or "Anomaly detected"
            attention_list.append({
                "site_id": site.site_id,
                "site_name": getattr(site, 'name', None),
                "country": site.country,
                "city": site.city,
                "issue": anomaly_desc,
                "severity": "critical",
                "metric": "Flagged for review",
                "metric_value": None,
                "risk_level": "critical",
                "primary_issue": anomaly_desc,
                "issue_detail": f"Site flagged with anomaly: {anomaly_desc}",
            })
            existing_ids.add(site.site_id)

    # Sort: MVR-backed sites first (validated narrative evidence), then severity, then risk_score
    attention_list.sort(key=lambda x: (
        0 if x["site_id"] in mvr_site_ids else 1,
        0 if x["severity"] == "critical" else 1,
        -(x.get("metric_value") or 0),
    ))
    attention_list = attention_list[:10]

    critical_count = sum(1 for s in attention_list if s["severity"] == "critical")
    warning_count = sum(1 for s in attention_list if s["severity"] == "warning")

    return {
        "sites": attention_list,
        "critical_count": critical_count,
        "warning_count": warning_count,
    }


def get_sites_overview_data(db: Session, settings) -> dict:
    """Return all sites with enrollment %, data quality score, alert count, and status.

    Sources: Site, RandomizationLog, Query, AlertLog.

    Returns dict with keys: sites (list of dicts), total (int).
    """
    sites = db.query(Site).all()

    # Enrollment counts per site
    enrollment_counts = dict(
        db.query(RandomizationLog.site_id, func.count(RandomizationLog.id))
        .group_by(RandomizationLog.site_id)
        .all()
    )

    # Open query counts per site
    query_counts = dict(
        db.query(Query.site_id, func.count(Query.id))
        .filter(Query.status == "Open")
        .group_by(Query.site_id)
        .all()
    )

    # Alert counts per site — use "open" status (not "active")
    alert_counts = dict(
        db.query(AlertLog.site_id, func.count(AlertLog.id))
        .filter(AlertLog.status == "open")
        .group_by(AlertLog.site_id)
        .all()
    )

    # Load LLM-driven risk assessments (most recent per site)
    latest_assessments: dict[str, SiteRiskAssessment] = {}
    all_assessments = (
        db.query(SiteRiskAssessment)
        .order_by(SiteRiskAssessment.created_at.desc())
        .all()
    )
    for a in all_assessments:
        if a.site_id not in latest_assessments:
            latest_assessments[a.site_id] = a

    site_list = []
    for site in sites:
        site_target = site.target_enrollment or 0
        enrolled = enrollment_counts.get(site.site_id, 0)
        enrollment_pct = min(100.0, round((enrolled / site_target) * 100, 1)) if site_target else 0

        open_queries = query_counts.get(site.site_id, 0)
        alert_count = alert_counts.get(site.site_id, 0)

        # Prefer LLM risk assessment over deterministic logic
        assessment = latest_assessments.get(site.site_id)
        if assessment:
            status = assessment.status
            dq_dim = (assessment.dimension_scores or {}).get("data_quality", 0)
            dq_score = round((1 - dq_dim) * 100)
            finding = assessment.status_rationale
        else:
            # Fallback: deterministic logic (used only before first proactive scan)
            dq_score = max(0, settings.dq_score_base - (open_queries * settings.dq_score_penalty_per_query))

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

        site_list.append({
            "site_id": site.site_id,
            "site_name": getattr(site, 'name', None),
            "country": site.country,
            "city": site.city,
            "enrollment_percent": enrollment_pct,
            "data_quality_score": dq_score,
            "alert_count": alert_count,
            "status": status,
            "finding": finding,
        })

    return {"sites": site_list, "total": len(site_list)}
