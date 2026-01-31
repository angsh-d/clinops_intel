"""Generate EDC tables: subject_visits, ecrf_entries, queries, data_corrections.

IMPORTANT: This generator must run AFTER monitoring_visits have been created
so that monitoring-triggered queries can be temporally aligned with actual
monitoring visit dates and post-monitoring query spikes can be generated.
"""

from datetime import date, timedelta

import numpy as np
from numpy.random import Generator
from sqlalchemy.orm import Session

from data_generators.anomaly_profiles import ANOMALY_PROFILES, REGIONAL_CLUSTER_SITES
from data_generators.config import SNAPSHOT_DATE, STUDY_START
from data_generators.distributions import (
    CRF_FIELD_NAMES, CRF_PAGE_WEIGHTS, CRF_PAGES,
    QUERY_TYPE_WEIGHTS, entry_lag_sample, is_holiday_window,
)
from data_generators.models import (
    DataCorrection, ECRFEntry, MonitoringVisit, Query,
    RandomizationLog, Site, SubjectVisit,
)
from data_generators.protocol_reader import ProtocolContext

_TREATMENT_VISITS = [
    ("ENC-002", "Cycle 1 Day -2", 1, -2),
    ("ENC-003", "Cycle 1 Day 1", 1, 1),
    ("ENC-004", "Cycle 1 Day 15", 1, 15),
]
for c in range(2, 7):
    _TREATMENT_VISITS.append(("ENC-005", f"Cycle {c} Day 1", c, 1))
_TREATMENT_VISITS.append(("ENC-006", "Final Visit", None, None))
_TREATMENT_VISITS.append(("ENC-007", "30-Day Follow-up", None, 30))


def _build_monitoring_index(session: Session) -> dict[str, list[date]]:
    """Build site_id → sorted list of completed monitoring visit dates."""
    mv_index: dict[str, list[date]] = {}
    for mv in session.query(MonitoringVisit).filter(
        MonitoringVisit.status == "Completed",
        MonitoringVisit.actual_date.isnot(None),
    ).all():
        mv_index.setdefault(mv.site_id, []).append(mv.actual_date)
    for dates in mv_index.values():
        dates.sort()
    return mv_index


def _is_post_monitoring_window(visit_date: date, mv_dates: list[date]) -> bool:
    """Check if visit_date falls within 14 days after any monitoring visit."""
    for md in mv_dates:
        if md <= visit_date <= md + timedelta(days=14):
            return True
    return False


def _nearest_monitoring_date(visit_date: date, mv_dates: list[date]) -> date | None:
    """Find the most recent monitoring visit on or before visit_date."""
    best = None
    for md in mv_dates:
        if md <= visit_date:
            best = md
        else:
            break
    return best


def generate_edc_telemetry(
    session: Session, ctx: ProtocolContext, rng: Generator
) -> dict[str, int]:
    """Generate subject_visits, ecrf_entries, queries, data_corrections.

    Queries are aware of monitoring visit dates:
    - Queries triggered_by='Monitoring Visit' are only generated during the
      14-day window after an actual monitoring visit.
    - Post-monitoring periods see 3x query rate increase for 2 weeks.
    - During monitoring gaps (no visits), NO monitoring-triggered queries are
      generated — the ABSENCE of these queries is the signal for Chain 3.
    """
    subjects = session.query(RandomizationLog).all()
    site_map = {s.site_id: s for s in session.query(Site).all()}
    mv_index = _build_monitoring_index(session)

    sv_rows: list[dict] = []
    ecrf_rows: list[dict] = []
    query_rows: list[dict] = []
    correction_rows: list[dict] = []
    sv_id_counter = 0

    for subj in subjects:
        site = site_map.get(subj.site_id)
        if not site:
            continue

        country = site.country
        prof = ANOMALY_PROFILES.get(subj.site_id)
        regional = REGIONAL_CLUSTER_SITES.get(subj.site_id)
        site_mv_dates = mv_index.get(subj.site_id, [])
        rand_date = subj.randomization_date

        disc_roll = rng.random()
        if disc_roll < 0.15:
            max_cycle = 3
        elif disc_roll < 0.25:
            max_cycle = 4
        else:
            max_cycle = 6

        for visit_id, visit_name, cycle_num, day_offset in _TREATMENT_VISITS:
            if cycle_num is not None and cycle_num > max_cycle:
                break

            if cycle_num is not None and day_offset is not None:
                planned = rand_date + timedelta(days=(cycle_num - 1) * ctx.cycle_length_days + day_offset)
            elif visit_name == "Final Visit":
                planned = rand_date + timedelta(days=max_cycle * ctx.cycle_length_days + 7)
            elif visit_name == "30-Day Follow-up":
                planned = rand_date + timedelta(days=max_cycle * ctx.cycle_length_days + 37)
            else:
                continue

            if planned > SNAPSHOT_DATE:
                break

            actual = planned + timedelta(days=int(rng.integers(-2, 4)))
            actual = min(actual, SNAPSHOT_DATE)

            status = "Completed"
            if rng.random() < 0.02:
                status = "Missed"

            sv_id_counter += 1
            sv_rows.append({
                "subject_id": subj.subject_id,
                "visit_id": visit_id,
                "cycle_number": cycle_num,
                "planned_date": planned,
                "actual_date": actual if status != "Missed" else None,
                "visit_status": status,
            })

            if status == "Missed":
                continue

            # eCRF entries
            n_pages = int(rng.integers(5, 8))
            page_indices = rng.choice(
                len(CRF_PAGES), size=n_pages, replace=False,
                p=np.array(CRF_PAGE_WEIGHTS) / sum(CRF_PAGE_WEIGHTS[:len(CRF_PAGES)]),
            )

            for pi in page_indices:
                page_name = CRF_PAGES[pi]
                lag = int(entry_lag_sample(rng, country, 1)[0])

                # Anomaly: entry lag spike
                if prof and prof.get("lag_spike_start"):
                    spike_start = prof["lag_spike_start"]
                    spike_end = spike_start + timedelta(weeks=prof["lag_spike_duration_weeks"])
                    if spike_start <= actual <= spike_end:
                        lag += prof["lag_spike_days"]

                # Regional cluster (Chain 5)
                if regional:
                    r_start = regional["lag_start"]
                    r_end = r_start + timedelta(weeks=regional["lag_weeks"])
                    if r_start <= actual <= r_end:
                        lag += int(regional["lag_extra_days"])

                if is_holiday_window(actual):
                    lag += 3

                # CRA transition spike
                if prof and prof.get("cra_transition_date"):
                    cra_date = prof["cra_transition_date"]
                    cra_end = cra_date + timedelta(weeks=6)
                    if cra_date <= actual <= cra_end:
                        lag += int(rng.integers(5, 8))

                entry_date = actual + timedelta(days=lag)
                if entry_date > SNAPSHOT_DATE:
                    entry_date = SNAPSHOT_DATE

                completeness = float(rng.beta(15, 1.5) * 100)
                if prof and prof.get("completeness_offset"):
                    completeness = max(50, completeness + prof["completeness_offset"])
                completeness = min(100.0, completeness)
                has_missing = completeness < 85
                missing_count = 0 if not has_missing else int(rng.integers(1, 5))

                ecrf_rows.append({
                    "subject_visit_id": sv_id_counter,
                    "subject_id": subj.subject_id,
                    "site_id": subj.site_id,
                    "crf_page_name": page_name,
                    "visit_date": actual,
                    "entry_date": entry_date,
                    "entry_lag_days": lag,
                    "completeness_pct": round(completeness, 1),
                    "has_missing_critical": has_missing,
                    "missing_field_count": missing_count,
                })

                # Generate queries (monitoring-aware)
                _generate_queries_for_entry(
                    rng, subj, site, prof, actual, page_name,
                    query_rows, correction_rows, site_mv_dates,
                )

    session.bulk_insert_mappings(SubjectVisit, sv_rows)
    session.flush()
    session.bulk_insert_mappings(ECRFEntry, ecrf_rows)
    session.bulk_insert_mappings(Query, query_rows)
    session.bulk_insert_mappings(DataCorrection, correction_rows)
    session.flush()

    return {
        "subject_visits": len(sv_rows),
        "ecrf_entries": len(ecrf_rows),
        "queries": len(query_rows),
        "data_corrections": len(correction_rows),
    }


def _generate_queries_for_entry(
    rng: Generator, subj, site, prof: dict | None,
    visit_date: date, page_name: str,
    query_rows: list[dict], correction_rows: list[dict],
    site_mv_dates: list[date],
) -> None:
    """Generate queries with monitoring-visit awareness.

    - Monitoring-triggered queries ONLY appear within 14 days of a real monitoring visit.
    - Post-monitoring window: 3x query rate increase for 2 weeks.
    - Non-monitoring queries use normal triggered_by distribution.
    """
    exp = site.experience_level
    base_lambda = {"High": 0.3, "Medium": 0.5, "Low": 0.8}.get(exp, 0.5)

    # Anomaly multiplier
    if prof:
        mult = prof.get("query_rate_multiplier", 1.0)
        if prof.get("query_rate_multiplier_during_spike") and prof.get("cra_transition_date"):
            cra_date = prof["cra_transition_date"]
            spike_end = cra_date + timedelta(weeks=prof.get("lag_spike_duration_weeks", 6))
            if cra_date <= visit_date <= spike_end:
                mult = prof["query_rate_multiplier_during_spike"]
        if prof.get("concentrated_pages") and page_name in prof["concentrated_pages"]:
            mult *= 1.5
        if mult > 1.0:
            # Apply against a standardized base so the anomaly is clearly visible
            # regardless of site experience level (High=0.3 would suppress the signal)
            base_lambda = 0.5 * mult
        else:
            base_lambda *= mult

    # Post-monitoring spike: 3x for 2 weeks after monitoring visit
    in_post_mv = _is_post_monitoring_window(visit_date, site_mv_dates)
    if in_post_mv:
        base_lambda *= 3.0

    n_queries = int(rng.poisson(base_lambda))
    if n_queries == 0:
        return

    query_types = list(QUERY_TYPE_WEIGHTS.keys())
    query_type_probs = list(QUERY_TYPE_WEIGHTS.values())

    for _ in range(n_queries):
        q_type = str(rng.choice(query_types, p=query_type_probs))
        open_date = visit_date + timedelta(days=int(rng.integers(1, 14)))
        if open_date > SNAPSHOT_DATE:
            open_date = SNAPSHOT_DATE

        # Determine triggered_by: monitoring-triggered ONLY if we're in
        # a post-monitoring window; otherwise use non-monitoring distribution
        if in_post_mv and rng.random() < 0.50:
            # 50% of queries in post-monitoring window are monitoring-triggered
            triggered_by = "Monitoring Visit"
            # Align open_date with the nearest monitoring visit
            nearest_mv = _nearest_monitoring_date(visit_date, site_mv_dates)
            if nearest_mv:
                open_date = nearest_mv + timedelta(days=int(rng.integers(1, 14)))
                if open_date > SNAPSHOT_DATE:
                    open_date = SNAPSHOT_DATE
        else:
            triggered_by = str(rng.choice(
                ["Auto-validation", "Manual Review", "Edit Check"],
                p=[0.45, 0.35, 0.20],
            ))

        response_lag = int(rng.integers(2, 15))
        close_lag = int(rng.integers(1, 7))

        # Chain 3: monitoring gap → queries stay open longer
        if prof and prof.get("gap_start"):
            gap_start = prof["gap_start"]
            gap_end = prof["gap_end"]
            if gap_start <= open_date <= gap_end:
                response_lag += int(rng.integers(10, 25))
                close_lag += int(rng.integers(5, 15))

        response_date = open_date + timedelta(days=response_lag)
        close_date = response_date + timedelta(days=close_lag)

        if response_date > SNAPSHOT_DATE:
            status = "Open"
            response_date = None
            close_date = None
            age = (SNAPSHOT_DATE - open_date).days
        elif close_date > SNAPSHOT_DATE:
            status = "Answered"
            close_date = None
            age = (SNAPSHOT_DATE - open_date).days
        else:
            status = "Closed"
            age = (close_date - open_date).days

        priority = str(rng.choice(["High", "Medium", "Low"], p=[0.15, 0.50, 0.35]))

        q_id = len(query_rows) + 1
        query_rows.append({
            "site_id": subj.site_id,
            "subject_id": subj.subject_id,
            "crf_page_name": page_name,
            "query_type": q_type,
            "open_date": open_date,
            "response_date": response_date,
            "close_date": close_date,
            "status": status,
            "age_days": age,
            "priority": priority,
            "triggered_by": triggered_by,
        })

        # Data corrections
        corr_rate = 0.25
        if prof and prof.get("correction_rate"):
            corr_rate = prof["correction_rate"]

        if status == "Closed" and rng.random() < corr_rate:
            fields = CRF_FIELD_NAMES.get(page_name, ["field_1"])
            field_name = str(rng.choice(fields))
            correction_rows.append({
                "site_id": subj.site_id,
                "subject_id": subj.subject_id,
                "crf_page_name": page_name,
                "field_name": field_name,
                "old_value": f"original_{rng.integers(100, 999)}",
                "new_value": f"corrected_{rng.integers(100, 999)}",
                "correction_date": close_date if close_date else SNAPSHOT_DATE,
                "triggered_by_query_id": q_id,
            })
