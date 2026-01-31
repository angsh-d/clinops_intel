"""Master orchestrator: generates all clinical operations data.

Execution order ensures cross-generator consistency:
1. Protocol context (read-only)
2. DB tables (create/reset)
3. Static config (sites, CRAs, kits, depots)
4. Enrollment funnel (screening, randomization, velocity)
5. Monitoring visits + overdue actions (BEFORE EDC so queries can reference dates)
6. EDC telemetry (queries aware of monitoring dates → post-monitoring spikes)
7. Update monitoring_visits.queries_generated (from actual query counts)
8. KRI snapshots (computed from actual EDC/enrollment data, time-windowed)
9. IRT/supply
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_generators.config import SessionLocal, engine, rng
from data_generators.models import Base
from data_generators.protocol_reader import load_protocol_context

from data_generators.generators.static_config import generate_static_config
from data_generators.generators.enrollment_funnel import generate_enrollment
from data_generators.generators.edc_telemetry import generate_edc_telemetry
from data_generators.generators.monitoring import (
    generate_monitoring_visits,
    generate_kri_snapshots,
    update_monitoring_query_counts,
)
from data_generators.generators.irt_supply import generate_irt_supply


def main():
    t0 = time.time()
    print("=" * 60)
    print("Clinical Operations Intelligence - Data Generation")
    print("=" * 60)

    # 1. Load protocol context
    print("\n[1/9] Loading protocol context from USDM JSONs...")
    ctx = load_protocol_context()
    print(f"  Study: {ctx.study_id} | NCT: {ctx.nct_number}")
    print(f"  Target enrollment: {ctx.target_enrollment} | Sites: {ctx.planned_sites}")
    print(f"  Visits: {len(ctx.visits)} | Activities: {len(ctx.activities)} | Instances: {len(ctx.scheduled_instances)}")
    print(f"  Criteria: {len(ctx.inclusion_criteria)} inclusion + {len(ctx.exclusion_criteria)} exclusion")

    # 2. Create/reset all DB tables
    print("\n[2/9] Creating database tables (drop + recreate)...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("  All tables created.")

    session = SessionLocal()
    all_counts: dict[str, int] = {}

    try:
        # 3. Static config
        print("\n[3/9] Generating static config tables...")
        counts = generate_static_config(session, ctx, rng)
        all_counts.update(counts)
        session.commit()
        _print_counts(counts)

        # 4. Enrollment funnel
        print("\n[4/9] Generating enrollment funnel...")
        counts = generate_enrollment(session, ctx, rng)
        all_counts.update(counts)
        session.commit()
        _print_counts(counts)

        # 5. Monitoring visits + overdue actions (BEFORE EDC)
        print("\n[5/9] Generating monitoring visits & overdue actions...")
        counts = generate_monitoring_visits(session, ctx, rng)
        all_counts.update(counts)
        session.commit()
        _print_counts(counts)

        # 6. EDC telemetry (aware of monitoring dates)
        print("\n[6/9] Generating EDC telemetry (monitoring-aware queries)...")
        counts = generate_edc_telemetry(session, ctx, rng)
        all_counts.update(counts)
        session.commit()
        _print_counts(counts)

        # 7. Update monitoring query counts from actuals
        print("\n[7/9] Updating monitoring_visits.queries_generated from actuals...")
        update_monitoring_query_counts(session)
        session.commit()
        print("  Done.")

        # 8. KRI snapshots (time-windowed, from actual data)
        print("\n[8/9] Computing KRI snapshots (60-day trailing windows)...")
        counts = generate_kri_snapshots(session, ctx, rng)
        all_counts.update(counts)
        session.commit()
        _print_counts(counts)

        # 9. IRT/Supply
        print("\n[9/9] Generating IRT/Supply data...")
        counts = generate_irt_supply(session, ctx, rng)
        all_counts.update(counts)
        session.commit()
        _print_counts(counts)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        total = 0
        for table, count in sorted(all_counts.items()):
            print(f"  {table:<30} {count:>8,} rows")
            total += count
        print(f"  {'TOTAL':<30} {total:>8,} rows")
        print(f"\n  Time: {time.time() - t0:.1f}s")

        # Verification
        print("\n" + "-" * 60)
        print("ANOMALY SITE VERIFICATION")
        print("-" * 60)
        _verify_anomalies(session)

    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


def _print_counts(counts: dict[str, int]) -> None:
    for table, count in counts.items():
        print(f"  {table}: {count:,} rows")


def _verify_anomalies(session) -> None:
    from data_generators.models import (
        ScreeningLog, Query, RandomizationLog, Site,
        MonitoringVisit, KitInventory, ECRFEntry, KRISnapshot,
    )
    from sqlalchemy import func

    # Country distribution
    country_counts = session.query(
        Site.country, func.count(Site.id)
    ).group_by(Site.country).all()
    print("\n  Country distribution:")
    for country, cnt in sorted(country_counts):
        print(f"    {country}: {cnt}")

    total_rand = session.query(func.count(RandomizationLog.id)).scalar()
    print(f"\n  Total randomized: {total_rand}")

    # Sites with screenings
    sites_with_screen = session.query(func.count(func.distinct(ScreeningLog.site_id))).scalar()
    total_sites = session.query(func.count(Site.id)).scalar()
    print(f"  Sites with screenings: {sites_with_screen}/{total_sites}")

    # Overall SF rate
    total_screen = session.query(func.count(ScreeningLog.id)).scalar()
    total_failed = session.query(func.count(ScreeningLog.id)).filter(
        ScreeningLog.outcome == "Failed"
    ).scalar()
    if total_screen > 0:
        print(f"  Overall SF rate: {total_failed}/{total_screen} = {total_failed/total_screen*100:.1f}%")

    # Monitoring-query alignment
    total_mv_queries = session.query(func.count(Query.id)).filter(
        Query.triggered_by == "Monitoring Visit"
    ).scalar()
    aligned = 0
    completed_mvs = session.query(MonitoringVisit).filter(
        MonitoringVisit.status == "Completed",
        MonitoringVisit.actual_date.isnot(None),
    ).all()
    for mv in completed_mvs:
        cnt = session.query(func.count(Query.id)).filter(
            Query.site_id == mv.site_id,
            Query.triggered_by == "Monitoring Visit",
            Query.open_date >= mv.actual_date,
            Query.open_date <= mv.actual_date + __import__("datetime").timedelta(days=14),
        ).scalar() or 0
        aligned += cnt
    print(f"\n  Monitoring-triggered queries: {total_mv_queries} total, {aligned} aligned ({aligned*100/max(total_mv_queries,1):.0f}%)")

    # KRI temporal check: SITE-022 entry lag during vs outside CRA transition
    kri_during = session.query(KRISnapshot.kri_value).filter(
        KRISnapshot.site_id == "SITE-022",
        KRISnapshot.kri_name == "Entry Lag Median (days)",
        KRISnapshot.snapshot_date >= __import__("datetime").date(2024, 9, 15),
        KRISnapshot.snapshot_date <= __import__("datetime").date(2024, 12, 15),
    ).all()
    kri_outside = session.query(KRISnapshot.kri_value).filter(
        KRISnapshot.site_id == "SITE-022",
        KRISnapshot.kri_name == "Entry Lag Median (days)",
        KRISnapshot.snapshot_date < __import__("datetime").date(2024, 9, 1),
    ).all()
    if kri_during and kri_outside:
        avg_during = sum(v[0] for v in kri_during) / len(kri_during)
        avg_outside = sum(v[0] for v in kri_outside) / len(kri_outside)
        print(f"\n  SITE-022 KRI 'Entry Lag Median': during transition={avg_during:.1f}d, before={avg_outside:.1f}d")

    # SITE-033 monitoring gap
    missed_033 = session.query(func.count(MonitoringVisit.id)).filter(
        MonitoringVisit.site_id == "SITE-033", MonitoringVisit.status == "Missed"
    ).scalar()
    print(f"  SITE-033 missed monitoring visits: {missed_033}")

    # SITE-033 query age during vs outside gap
    from datetime import date
    gap_queries = session.query(func.avg(Query.age_days)).filter(
        Query.site_id == "SITE-033",
        Query.open_date >= date(2024, 12, 1),
        Query.open_date <= date(2025, 2, 28),
    ).scalar()
    nongap_queries = session.query(func.avg(Query.age_days)).filter(
        Query.site_id == "SITE-033",
        Query.open_date < date(2024, 12, 1),
    ).scalar()
    if gap_queries and nongap_queries:
        print(f"  SITE-033 query age: during gap={gap_queries:.1f}d, before gap={nongap_queries:.1f}d")

    # Entry lag by country
    from sqlalchemy.orm import aliased
    print("\n  Entry lag by country:")
    for country in ["JPN", "USA", "CAN", "AUS", "NZL"]:
        avg_lag = session.query(func.avg(ECRFEntry.entry_lag_days)).join(
            Site, ECRFEntry.site_id == Site.site_id
        ).filter(Site.country == country).scalar()
        if avg_lag:
            print(f"    {country}: {avg_lag:.1f} days")


if __name__ == "__main__":
    main()
