"""Generate monitoring tables: monitoring_visits, kri_snapshots, overdue_actions.

Split into two phases:
  Phase A (generate_monitoring_visits): Creates monitoring_visits + overdue_actions.
          Must run BEFORE EDC telemetry so queries can reference monitoring dates.
  Phase B (generate_kri_snapshots): Computes KRI snapshots from actual EDC/enrollment
          data using 60-day trailing windows. Must run AFTER EDC telemetry.
  Phase C (update_monitoring_query_counts): Updates monitoring_visits.queries_generated
          to match actual count of monitoring-triggered queries. Must run AFTER EDC.
"""

from datetime import date, timedelta

import numpy as np
from numpy.random import Generator
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from data_generators.anomaly_profiles import ANOMALY_PROFILES
from data_generators.config import SNAPSHOT_DATE, STUDY_START
from data_generators.models import (
    CRAAssignment, ECRFEntry, KRISnapshot,
    MonitoringVisit, OverdueAction, Query, RandomizationLog,
    ScreeningLog, Site, SubjectVisit,
)
from data_generators.protocol_reader import ProtocolContext

# Recalibrated KRI thresholds: (name, amber_threshold, red_threshold)
# For "lower is worse" KRIs (Enrollment, Compliance, Completeness): value < red → Red
# For "higher is worse" KRIs (Query Rate, Age, etc.): value > red → Red
_KRI_DEFS = [
    ("Query Rate", 0.8, 1.5),                     # queries per eCRF page entry
    ("Open Query Age (days)", 14, 28),              # wider margins
    ("Entry Lag Median (days)", 5, 12),             # red at 12+ days
    ("Screen Failure Rate (%)", 38, 50),            # wider red threshold
    ("Enrollment vs Target (%)", 60, 40),           # cumulative-based
    ("Monitoring Visit Compliance (%)", 80, 60),    # more lenient
    ("Critical Findings Rate", 0.8, 1.5),           # wider
    ("Data Completeness (%)", 88, 75),              # slightly lenient
    ("Correction Rate (%)", 8, 15),                 # much wider than original (5,10)
    ("Protocol Deviation Rate", 0.5, 1.2),          # data-driven with variation
]

_ACTION_DESCRIPTIONS = [
    "Resolve outstanding queries on Lab Results CRF",
    "Complete missing AE follow-up documentation",
    "Update drug accountability log",
    "Correct informed consent date discrepancy",
    "Submit overdue SAE report",
    "Reconcile IP dispensation records",
    "Review and sign source documents",
    "Update screening log entries",
    "Address protocol deviation documentation",
    "Complete CRF data entry backlog",
]


def generate_monitoring_visits(
    session: Session, ctx: ProtocolContext, rng: Generator
) -> dict[str, int]:
    """Phase A: Generate monitoring_visits and overdue_actions."""
    sites = session.query(Site).all()
    mv_rows: list[dict] = []
    overdue_rows: list[dict] = []

    for site in sites:
        prof = ANOMALY_PROFILES.get(site.site_id)
        act = site.activation_date

        cras = session.query(CRAAssignment).filter(
            CRAAssignment.site_id == site.site_id,
        ).order_by(CRAAssignment.start_date).all()
        current_cra = cras[-1].cra_id if cras else "CRA-UNKNOWN"

        # Determine monitoring interval based on anomaly type
        is_suspicious_perfection = prof and prof.get("anomaly_type") == "suspicious_perfection"
        is_monitoring_anxiety = prof and prof.get("anomaly_type") == "monitoring_anxiety"

        interval_weeks = int(rng.integers(6, 9))
        visit_date = act + timedelta(weeks=interval_weeks)
        visit_counter = 0

        while visit_date <= SNAPSHOT_DATE:
            planned_date = visit_date

            cra_id = current_cra
            for cra in cras:
                if cra.start_date <= planned_date and (cra.end_date is None or planned_date <= cra.end_date):
                    cra_id = cra.cra_id
                    break

            is_missed = False
            if prof and prof.get("gap_start"):
                if prof["gap_start"] <= planned_date <= prof["gap_end"]:
                    is_missed = True

            if prof and prof.get("monitoring_delay_weeks") and prof.get("cra_transition_date"):
                cra_date = prof["cra_transition_date"]
                delay_end = cra_date + timedelta(weeks=prof["monitoring_delay_weeks"])
                if cra_date <= planned_date <= delay_end:
                    is_missed = True

            if is_missed:
                mv_rows.append({
                    "site_id": site.site_id,
                    "cra_id": cra_id,
                    "planned_date": planned_date,
                    "actual_date": None,
                    "visit_type": "On-Site" if visit_counter % 2 == 0 else "Remote",
                    "findings_count": 0,
                    "critical_findings": 0,
                    "queries_generated": 0,  # will stay 0 for missed
                    "days_overdue": (SNAPSHOT_DATE - planned_date).days,
                    "status": "Missed",
                })
            elif is_suspicious_perfection:
                # All visits completed exactly on planned date with minimal findings
                mv_rows.append({
                    "site_id": site.site_id,
                    "cra_id": cra_id,
                    "planned_date": planned_date,
                    "actual_date": planned_date,
                    "visit_type": "On-Site" if visit_counter % 3 != 2 else "Remote",
                    "findings_count": int(rng.integers(0, 2)),  # 0-1 findings
                    "critical_findings": 0,
                    "queries_generated": 0,
                    "days_overdue": 0,
                    "status": "Completed",
                })
            else:
                actual = planned_date + timedelta(days=int(rng.integers(-3, 5)))
                actual = min(actual, SNAPSHOT_DATE)
                days_overdue = max(0, (actual - planned_date).days)
                visit_type = "On-Site" if visit_counter % 3 != 2 else "Remote"
                findings = int(rng.poisson(3))
                critical = min(int(rng.poisson(0.3)), findings)

                # Monitoring anxiety: after frequency increase, fewer findings (PI extra careful)
                if is_monitoring_anxiety and planned_date >= prof["monitoring_frequency_change_date"]:
                    findings = int(rng.poisson(1.0))
                    critical = 0

                mv_rows.append({
                    "site_id": site.site_id,
                    "cra_id": cra_id,
                    "planned_date": planned_date,
                    "actual_date": actual,
                    "visit_type": visit_type,
                    "findings_count": findings,
                    "critical_findings": critical,
                    "queries_generated": 0,  # will be updated in Phase C
                    "days_overdue": days_overdue,
                    "status": "Completed",
                })

                # Overdue actions (~30% of visits with findings generate 1 action)
                if findings > 1 and rng.random() < 0.30:
                    due = actual + timedelta(days=int(rng.integers(7, 30)))
                    comp = due + timedelta(days=int(rng.integers(-5, 15)))
                    if comp > SNAPSHOT_DATE:
                        action_status = "Overdue" if due < SNAPSHOT_DATE else "Open"
                        comp = None
                    else:
                        action_status = "Completed"

                    overdue_rows.append({
                        "site_id": site.site_id,
                        "monitoring_visit_id": len(mv_rows),
                        "action_description": str(rng.choice(_ACTION_DESCRIPTIONS)),
                        "category": str(rng.choice([
                            "Data Quality", "Safety Reporting", "IP Management",
                            "Regulatory", "Documentation",
                        ])),
                        "due_date": due,
                        "completion_date": comp,
                        "status": action_status,
                    })

            # Monitoring anxiety: shortened interval after change date
            if is_monitoring_anxiety and planned_date >= prof["monitoring_frequency_change_date"]:
                visit_date += timedelta(weeks=prof["monitoring_interval_after_weeks"])
            else:
                visit_date += timedelta(weeks=int(rng.integers(6, 9)))
            visit_counter += 1

    session.bulk_insert_mappings(MonitoringVisit, mv_rows)
    session.bulk_insert_mappings(OverdueAction, overdue_rows)
    session.flush()

    return {
        "monitoring_visits": len(mv_rows),
        "overdue_actions": len(overdue_rows),
    }


def update_monitoring_query_counts(session: Session) -> None:
    """Phase C: Update monitoring_visits.queries_generated to match actual
    count of queries with triggered_by='Monitoring Visit' within 14 days."""
    completed_visits = session.query(MonitoringVisit).filter(
        MonitoringVisit.status == "Completed",
        MonitoringVisit.actual_date.isnot(None),
    ).all()

    for mv in completed_visits:
        actual_count = session.query(func.count(Query.id)).filter(
            Query.site_id == mv.site_id,
            Query.triggered_by == "Monitoring Visit",
            Query.open_date >= mv.actual_date,
            Query.open_date <= mv.actual_date + timedelta(days=14),
        ).scalar() or 0
        mv.queries_generated = actual_count

    session.flush()


def generate_kri_snapshots(
    session: Session, ctx: ProtocolContext, rng: Generator
) -> dict[str, int]:
    """Phase B: Compute monthly KRI snapshots using 60-day trailing windows
    from actual EDC/enrollment data. This ensures KRIs reflect temporal
    dynamics — spikes, drifts, and seasonal effects become visible."""
    sites = session.query(Site).all()
    rows: list[dict] = []

    # Pre-load all data for windowed computation
    all_ecrf = session.query(ECRFEntry).all()
    all_queries = session.query(Query).all()
    all_screening = session.query(ScreeningLog).all()
    all_rand = session.query(RandomizationLog).all()
    all_mv = session.query(MonitoringVisit).all()

    # Index by site
    ecrf_by_site: dict[str, list] = {}
    for e in all_ecrf:
        ecrf_by_site.setdefault(e.site_id, []).append(e)

    queries_by_site: dict[str, list] = {}
    for q in all_queries:
        queries_by_site.setdefault(q.site_id, []).append(q)

    screen_by_site: dict[str, list] = {}
    for s in all_screening:
        screen_by_site.setdefault(s.site_id, []).append(s)

    rand_by_site: dict[str, list] = {}
    for r in all_rand:
        rand_by_site.setdefault(r.site_id, []).append(r)

    mv_by_site: dict[str, list] = {}
    for mv in all_mv:
        mv_by_site.setdefault(mv.site_id, []).append(mv)

    snapshot_date = STUDY_START + timedelta(days=90)
    while snapshot_date <= SNAPSHOT_DATE:
        window_start = snapshot_date - timedelta(days=60)

        for site in sites:
            if site.activation_date > snapshot_date:
                continue

            sid = site.site_id

            # 60-day windowed data
            w_ecrf = [e for e in ecrf_by_site.get(sid, [])
                       if window_start <= e.visit_date <= snapshot_date]
            w_queries = [q for q in queries_by_site.get(sid, [])
                          if q.open_date and window_start <= q.open_date <= snapshot_date]
            w_open_queries = [q for q in queries_by_site.get(sid, [])
                              if q.status in ("Open", "Answered") or
                              (q.close_date and q.close_date > snapshot_date)]
            w_screen = [s for s in screen_by_site.get(sid, [])
                         if window_start <= s.screening_date <= snapshot_date]
            w_rand = [r for r in rand_by_site.get(sid, [])
                       if window_start <= r.randomization_date <= snapshot_date]
            w_mv = [m for m in mv_by_site.get(sid, [])
                     if m.planned_date and window_start <= m.planned_date <= snapshot_date]

            # Count subject-visits in window (approximate: 1 ecrf per page)
            n_sv_window = len(w_ecrf)

            # Full site randomization list for cumulative enrollment KRI
            all_rand_site = rand_by_site.get(sid, [])

            for kri_name, amber_thresh, red_thresh in _KRI_DEFS:
                value = float(_compute_windowed_kri(
                    kri_name, w_ecrf, w_queries, w_open_queries, w_screen,
                    w_rand, w_mv, site, n_sv_window, rng,
                    all_rand_site=all_rand_site,
                    snapshot_date=snapshot_date,
                ))

                if kri_name in ("Enrollment vs Target (%)", "Monitoring Visit Compliance (%)", "Data Completeness (%)"):
                    if value < red_thresh:
                        status = "Red"
                    elif value < amber_thresh:
                        status = "Amber"
                    else:
                        status = "Green"
                else:
                    if value > red_thresh:
                        status = "Red"
                    elif value > amber_thresh:
                        status = "Amber"
                    else:
                        status = "Green"

                rows.append({
                    "site_id": sid,
                    "snapshot_date": snapshot_date,
                    "kri_name": kri_name,
                    "kri_value": round(value, 2),
                    "amber_threshold": amber_thresh,
                    "red_threshold": red_thresh,
                    "status": status,
                })

        snapshot_date += timedelta(days=30)

    session.bulk_insert_mappings(KRISnapshot, rows)
    session.flush()
    return {"kri_snapshots": len(rows)}


def _compute_windowed_kri(
    kri_name: str,
    w_ecrf: list, w_queries: list, w_open_queries: list,
    w_screen: list, w_rand: list, w_mv: list,
    site, n_sv: int, rng: Generator,
    all_rand_site: list = None,
    snapshot_date: date = None,
) -> float:
    """Compute a KRI value from 60-day windowed data."""
    noise = float(rng.normal(0, 0.05))

    if kri_name == "Query Rate":
        # Queries per eCRF entry (no artificial multiplier)
        denom = max(n_sv, 1)
        return max(0, len(w_queries) / denom + noise)

    elif kri_name == "Open Query Age (days)":
        if not w_open_queries:
            return max(0, 3 + noise)
        ages = [q.age_days for q in w_open_queries if q.age_days is not None]
        return float(max(0, float(np.mean(ages)) + noise)) if ages else 3.0

    elif kri_name == "Entry Lag Median (days)":
        if not w_ecrf:
            return max(0, 2 + noise)
        lags = [e.entry_lag_days for e in w_ecrf]
        return max(0, float(np.median(lags)) + noise * 0.5)

    elif kri_name == "Screen Failure Rate (%)":
        if not w_screen:
            return 30 + noise * 3
        failed = sum(1 for s in w_screen if s.outcome == "Failed")
        return max(0, min(100, failed / len(w_screen) * 100 + noise * 2))

    elif kri_name == "Enrollment vs Target (%)":
        target = site.target_enrollment
        if target == 0:
            return 100.0
        # Cumulative enrollment up to snapshot_date
        if all_rand_site and snapshot_date:
            cum_rand = sum(1 for r in all_rand_site if r.randomization_date <= snapshot_date)
        else:
            cum_rand = len(w_rand)
        # Expected: linear ramp from activation to end of study
        months_active = max(1, (snapshot_date - site.activation_date).days / 30.0)
        total_months = max(1, (SNAPSHOT_DATE - site.activation_date).days / 30.0)
        expected = target * min(1.0, months_active / total_months)
        return max(0, min(200, cum_rand / max(expected, 0.3) * 100 + noise * 5))

    elif kri_name == "Monitoring Visit Compliance (%)":
        if not w_mv:
            return 90 + noise * 3
        completed = sum(1 for m in w_mv if m.status == "Completed")
        return max(50, min(100, completed / len(w_mv) * 100 + noise * 2))

    elif kri_name == "Critical Findings Rate":
        if not w_mv:
            return max(0, 0.2 + noise * 0.1)
        completed_mv = [m for m in w_mv if m.status == "Completed"]
        if not completed_mv:
            return max(0, 0.2 + noise * 0.1)
        return max(0, sum(m.critical_findings for m in completed_mv) / len(completed_mv) + noise * 0.1)

    elif kri_name == "Data Completeness (%)":
        if not w_ecrf:
            return 95 + noise * 2
        return float(max(60, min(100, float(np.mean([e.completeness_pct for e in w_ecrf])) + noise * 2)))

    elif kri_name == "Correction Rate (%)":
        if n_sv == 0:
            return max(0, 2 + noise)
        corr_count = len(w_queries) * 0.15  # conservative proxy
        return max(0, min(25, corr_count / max(n_sv, 1) * 100 + noise * 2))

    elif kri_name == "Protocol Deviation Rate":
        # Data-driven: based on monitoring findings ratio
        if w_mv:
            completed_mv = [m for m in w_mv if m.status == "Completed"]
            if completed_mv:
                total_findings = sum(m.findings_count for m in completed_mv)
                return max(0, total_findings / max(len(completed_mv), 1) * 0.12 + noise * 0.15)
        return max(0, 0.15 + abs(noise) * 0.2)

    return 0.0
