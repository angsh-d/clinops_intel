"""SQL query tools against the 24 CODM tables.

Agent 1 tools: data quality domain
Agent 3 tools: enrollment funnel domain
"""

from datetime import date
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from data_generators.models import (
    Site, ECRFEntry, Query, DataCorrection, CRAAssignment,
    MonitoringVisit, ScreeningLog, RandomizationLog, EnrollmentVelocity,
    ScreenFailureReasonCode, KitInventory, KRISnapshot,
    RandomizationEvent,
    Vendor, VendorScope, VendorSiteAssignment, VendorKPI,
    VendorMilestone, VendorIssue,
    StudyBudget, BudgetLineItem, FinancialSnapshot,
    Invoice, ChangeOrder, SiteFinancialMetric,
)
from backend.tools.base import BaseTool, ToolResult
from backend.config import get_settings


def _serialize_rows(rows) -> list[dict]:
    """Convert SQLAlchemy Row objects to JSON-serializable dicts."""
    result = []
    for row in rows:
        if hasattr(row, "_asdict"):
            d = row._asdict()
        elif hasattr(row, "__dict__"):
            d = {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
        else:
            d = dict(row)
        # Convert date objects
        for k, v in d.items():
            if isinstance(v, date):
                d[k] = v.isoformat()
        result.append(d)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 1 TOOLS (Data Quality)
# ═══════════════════════════════════════════════════════════════════════════════

class EntryLagAnalysisTool(BaseTool):
    name = "entry_lag_analysis"
    description = (
        "Analyzes eCRF entry lag by site, CRF page, and time period. "
        "Returns mean, median, p90 entry lag days and distribution. "
        "Args: site_id (optional, for specific site), period_start/period_end (optional date filters)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        period_start = kwargs.get("period_start")
        period_end = kwargs.get("period_end")
        q = db_session.query(
            ECRFEntry.site_id,
            ECRFEntry.crf_page_name,
            func.count(ECRFEntry.id).label("entry_count"),
            func.avg(ECRFEntry.entry_lag_days).label("mean_lag"),
            func.percentile_cont(0.5).within_group(ECRFEntry.entry_lag_days).label("median_lag"),
            func.percentile_cont(0.9).within_group(ECRFEntry.entry_lag_days).label("p90_lag"),
            func.max(ECRFEntry.entry_lag_days).label("max_lag"),
            func.sum(case((ECRFEntry.has_missing_critical.is_(True), 1), else_=0)).label("missing_critical_count"),
        ).group_by(ECRFEntry.site_id, ECRFEntry.crf_page_name)

        if site_id:
            q = q.filter(ECRFEntry.site_id == site_id)
        if period_start:
            q = q.filter(ECRFEntry.visit_date >= period_start)
        if period_end:
            q = q.filter(ECRFEntry.visit_date <= period_end)

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class QueryBurdenTool(BaseTool):
    name = "query_burden"
    description = (
        "Analyzes query counts, aging, types, and status by site. "
        "Returns open/answered/closed counts, aging distribution, query types. "
        "Args: site_id (optional), period_start/period_end (optional date filters)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        settings = get_settings()
        site_id = kwargs.get("site_id")
        period_start = kwargs.get("period_start")
        period_end = kwargs.get("period_end")
        q = db_session.query(
            Query.site_id,
            Query.status,
            Query.query_type,
            Query.priority,
            func.count(Query.id).label("query_count"),
            func.avg(Query.age_days).label("mean_age"),
            func.max(Query.age_days).label("max_age"),
            func.sum(case((Query.age_days > settings.query_aging_amber_days, 1), else_=0)).label("aging_over_14d"),
            func.sum(case((Query.age_days > settings.query_aging_red_days, 1), else_=0)).label("aging_over_30d"),
        ).group_by(Query.site_id, Query.status, Query.query_type, Query.priority)

        if site_id:
            q = q.filter(Query.site_id == site_id)
        if period_start:
            q = q.filter(Query.open_date >= period_start)
        if period_end:
            q = q.filter(Query.open_date <= period_end)

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class DataCorrectionAnalysisTool(BaseTool):
    name = "data_correction_analysis"
    description = (
        "Analyzes data corrections by site — correction rates, query-triggered vs unprompted, "
        "field/page concentration. Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        q = db_session.query(
            DataCorrection.site_id,
            DataCorrection.crf_page_name,
            func.count(DataCorrection.id).label("correction_count"),
            func.sum(case((DataCorrection.triggered_by_query_id.isnot(None), 1), else_=0)).label("query_triggered"),
            func.sum(case((DataCorrection.triggered_by_query_id.is_(None), 1), else_=0)).label("unprompted"),
        ).group_by(DataCorrection.site_id, DataCorrection.crf_page_name)

        if site_id:
            q = q.filter(DataCorrection.site_id == site_id)

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class CRAAssignmentHistoryTool(BaseTool):
    name = "cra_assignment_history"
    description = (
        "Returns CRA assignment history for sites — CRA IDs, assignment date ranges, transitions. "
        "Use to detect CRA transitions that may correlate with data quality changes. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        q = db_session.query(
            CRAAssignment.site_id,
            CRAAssignment.cra_id,
            CRAAssignment.start_date,
            CRAAssignment.end_date,
            CRAAssignment.is_current,
        ).order_by(CRAAssignment.site_id, CRAAssignment.start_date)

        if site_id:
            q = q.filter(CRAAssignment.site_id == site_id)

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class MonitoringVisitHistoryTool(BaseTool):
    name = "monitoring_visit_history"
    description = (
        "Returns monitoring visit records by site — visit dates, type (On-Site/Remote), "
        "findings count, critical findings, queries generated, days overdue. "
        "Use to detect monitoring gaps and correlate with data quality signals. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        q = db_session.query(
            MonitoringVisit.site_id,
            MonitoringVisit.cra_id,
            MonitoringVisit.planned_date,
            MonitoringVisit.actual_date,
            MonitoringVisit.visit_type,
            MonitoringVisit.findings_count,
            MonitoringVisit.critical_findings,
            MonitoringVisit.queries_generated,
            MonitoringVisit.days_overdue,
            MonitoringVisit.status,
        ).order_by(MonitoringVisit.site_id, MonitoringVisit.planned_date)

        if site_id:
            q = q.filter(MonitoringVisit.site_id == site_id)

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class SiteSummaryTool(BaseTool):
    name = "site_summary"
    description = (
        "Returns site metadata — country, city, type, experience level, activation date, "
        "target enrollment. Args: site_id (optional), country (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        country = kwargs.get("country")
        q = db_session.query(
            Site.site_id, Site.name, Site.country, Site.city, Site.site_type,
            Site.experience_level, Site.activation_date, Site.target_enrollment,
        )
        if site_id:
            q = q.filter(Site.site_id == site_id)
        if country:
            q = q.filter(Site.country == country)

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 3 TOOLS (Enrollment Funnel)
# ═══════════════════════════════════════════════════════════════════════════════

class ScreeningFunnelTool(BaseTool):
    name = "screening_funnel"
    description = (
        "Decomposes the screening funnel by site — total screened, passed, failed, withdrawn, "
        "failure rate. Provides per-site funnel decomposition. "
        "Args: site_id (optional), period_start/period_end (optional date filters)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        period_start = kwargs.get("period_start")
        period_end = kwargs.get("period_end")
        q = db_session.query(
            ScreeningLog.site_id,
            func.count(ScreeningLog.id).label("total_screened"),
            func.sum(case((ScreeningLog.outcome == "Passed", 1), else_=0)).label("passed"),
            func.sum(case((ScreeningLog.outcome == "Failed", 1), else_=0)).label("failed"),
            func.sum(case((ScreeningLog.outcome == "Withdrawn", 1), else_=0)).label("withdrawn"),
        ).group_by(ScreeningLog.site_id)

        if site_id:
            q = q.filter(ScreeningLog.site_id == site_id)
        if period_start:
            q = q.filter(ScreeningLog.screening_date >= period_start)
        if period_end:
            q = q.filter(ScreeningLog.screening_date <= period_end)

        rows = q.all()
        data = _serialize_rows(rows)
        # Compute failure rate
        for d in data:
            total = d.get("total_screened", 0)
            failed = d.get("failed", 0)
            d["failure_rate_pct"] = round((failed / total * 100) if total > 0 else 0, 1)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class EnrollmentVelocityTool(BaseTool):
    name = "enrollment_velocity"
    description = (
        "Returns weekly enrollment velocity by site — screened, failed, randomized per week, "
        "cumulative vs target. Use to detect velocity trends and stalls. "
        "Args: site_id (optional), last_n_weeks (optional, default all)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        last_n_weeks = kwargs.get("last_n_weeks")

        q = db_session.query(
            EnrollmentVelocity.site_id,
            EnrollmentVelocity.week_number,
            EnrollmentVelocity.week_start,
            EnrollmentVelocity.screened_count,
            EnrollmentVelocity.screen_failed_count,
            EnrollmentVelocity.randomized_count,
            EnrollmentVelocity.cumulative_randomized,
            EnrollmentVelocity.target_cumulative,
        ).order_by(EnrollmentVelocity.site_id, EnrollmentVelocity.week_number)

        if site_id:
            q = q.filter(EnrollmentVelocity.site_id == site_id)
        if last_n_weeks:
            max_week = db_session.query(func.max(EnrollmentVelocity.week_number)).scalar() or 0
            q = q.filter(EnrollmentVelocity.week_number > max_week - int(last_n_weeks))

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class ScreenFailurePatternTool(BaseTool):
    name = "screen_failure_pattern"
    description = (
        "Analyzes screen failure reason codes and narratives by site — code distribution, "
        "overrepresented codes vs study average, raw failure narratives for NLP analysis. "
        "Args: site_id (optional), include_narratives (bool, default false), "
        "period_start/period_end (optional date filters)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        include_narratives = kwargs.get("include_narratives", False)
        period_start = kwargs.get("period_start")
        period_end = kwargs.get("period_end")

        # Code distribution
        q = db_session.query(
            ScreeningLog.site_id,
            ScreeningLog.failure_reason_code,
            func.count(ScreeningLog.id).label("count"),
        ).filter(
            ScreeningLog.outcome == "Failed",
            ScreeningLog.failure_reason_code.isnot(None),
        ).group_by(ScreeningLog.site_id, ScreeningLog.failure_reason_code)

        if site_id:
            q = q.filter(ScreeningLog.site_id == site_id)
        if period_start:
            q = q.filter(ScreeningLog.screening_date >= period_start)
        if period_end:
            q = q.filter(ScreeningLog.screening_date <= period_end)

        rows = q.all()
        data = _serialize_rows(rows)

        # Study-wide averages for comparison
        study_avg = db_session.query(
            ScreeningLog.failure_reason_code,
            func.count(ScreeningLog.id).label("study_count"),
        ).filter(
            ScreeningLog.outcome == "Failed",
            ScreeningLog.failure_reason_code.isnot(None),
        ).group_by(ScreeningLog.failure_reason_code).all()
        study_avg_data = _serialize_rows(study_avg)

        result = {"site_failure_codes": data, "study_average_codes": study_avg_data}

        if include_narratives:
            nq = db_session.query(
                ScreeningLog.site_id,
                ScreeningLog.failure_reason_code,
                ScreeningLog.failure_reason_narrative,
            ).filter(
                ScreeningLog.outcome == "Failed",
                ScreeningLog.failure_reason_narrative.isnot(None),
            )
            if site_id:
                nq = nq.filter(ScreeningLog.site_id == site_id)
            if period_start:
                nq = nq.filter(ScreeningLog.screening_date >= period_start)
            if period_end:
                nq = nq.filter(ScreeningLog.screening_date <= period_end)
            settings = get_settings()
            narratives = nq.limit(settings.narrative_fetch_limit).all()
            result["narratives"] = _serialize_rows(narratives)

        return ToolResult(tool_name=self.name, success=True, data=result, row_count=len(data))


class RegionalComparisonTool(BaseTool):
    name = "regional_comparison"
    description = (
        "Compares enrollment, screening, and data quality metrics across sites in the same country/region. "
        "Includes entry lag statistics for detecting regional cluster patterns. "
        "Args: country (optional), site_ids (optional, comma-separated), "
        "period_start/period_end (optional date filters for temporal comparison)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        country = kwargs.get("country")
        site_ids_str = kwargs.get("site_ids")
        period_start = kwargs.get("period_start")
        period_end = kwargs.get("period_end")

        # Get sites
        sq = db_session.query(Site.site_id, Site.country, Site.city)
        if country:
            sq = sq.filter(Site.country == country)
        if site_ids_str:
            ids = [s.strip() for s in site_ids_str.split(",")]
            sq = sq.filter(Site.site_id.in_(ids))
        sites = sq.all()
        site_list = [s.site_id for s in sites]

        if not site_list:
            return ToolResult(tool_name=self.name, success=True, data=[], row_count=0)

        # Screening summary per site
        screening_q = db_session.query(
            ScreeningLog.site_id,
            func.count(ScreeningLog.id).label("total_screened"),
            func.sum(case((ScreeningLog.outcome == "Failed", 1), else_=0)).label("failed"),
            func.sum(case((ScreeningLog.outcome == "Passed", 1), else_=0)).label("passed"),
        ).filter(ScreeningLog.site_id.in_(site_list))
        if period_start:
            screening_q = screening_q.filter(ScreeningLog.screening_date >= period_start)
        if period_end:
            screening_q = screening_q.filter(ScreeningLog.screening_date <= period_end)
        screening = screening_q.group_by(ScreeningLog.site_id).all()

        # Randomization counts
        rand_q = db_session.query(
            RandomizationLog.site_id,
            func.count(RandomizationLog.id).label("randomized"),
        ).filter(RandomizationLog.site_id.in_(site_list))
        if period_start:
            rand_q = rand_q.filter(RandomizationLog.randomization_date >= period_start)
        if period_end:
            rand_q = rand_q.filter(RandomizationLog.randomization_date <= period_end)
        randomization = rand_q.group_by(RandomizationLog.site_id).all()

        # Entry lag per site (for regional cluster detection)
        lag_q = db_session.query(
            ECRFEntry.site_id,
            func.count(ECRFEntry.id).label("entry_count"),
            func.avg(ECRFEntry.entry_lag_days).label("mean_lag"),
            func.percentile_cont(0.5).within_group(ECRFEntry.entry_lag_days).label("median_lag"),
        ).filter(ECRFEntry.site_id.in_(site_list))
        if period_start:
            lag_q = lag_q.filter(ECRFEntry.visit_date >= period_start)
        if period_end:
            lag_q = lag_q.filter(ECRFEntry.visit_date <= period_end)
        entry_lag = lag_q.group_by(ECRFEntry.site_id).all()

        data = {
            "sites": _serialize_rows(sites),
            "screening": _serialize_rows(screening),
            "randomization": _serialize_rows(randomization),
            "entry_lag": _serialize_rows(entry_lag),
        }
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(site_list))


class KitInventoryTool(BaseTool):
    name = "kit_inventory"
    description = (
        "Returns kit inventory snapshots for sites — quantity on hand, below-reorder flags. "
        "Use to detect supply constraints that may cause consent withdrawals. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        q = db_session.query(
            KitInventory.site_id,
            KitInventory.kit_type_id,
            KitInventory.snapshot_date,
            KitInventory.quantity_on_hand,
            KitInventory.reorder_level,
            KitInventory.is_below_reorder,
        ).order_by(KitInventory.site_id, KitInventory.snapshot_date)

        if site_id:
            q = q.filter(KitInventory.site_id == site_id)

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class KRISnapshotTool(BaseTool):
    name = "kri_snapshot"
    description = (
        "Returns Key Risk Indicator snapshots — KRI values, thresholds, and status (Green/Amber/Red) by site. "
        "Args: site_id (optional), kri_name (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        kri_name = kwargs.get("kri_name")
        q = db_session.query(
            KRISnapshot.site_id,
            KRISnapshot.snapshot_date,
            KRISnapshot.kri_name,
            KRISnapshot.kri_value,
            KRISnapshot.amber_threshold,
            KRISnapshot.red_threshold,
            KRISnapshot.status,
        ).order_by(KRISnapshot.site_id, KRISnapshot.snapshot_date)

        if site_id:
            q = q.filter(KRISnapshot.site_id == site_id)
        if kri_name:
            q = q.filter(KRISnapshot.kri_name == kri_name)

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


# ═══════════════════════════════════════════════════════════════════════════════
# PHANTOM COMPLIANCE TOOLS (Data Integrity)
# ═══════════════════════════════════════════════════════════════════════════════

class DataVarianceAnalysisTool(BaseTool):
    name = "data_variance_analysis"
    description = (
        "Per-site variance analysis: stddev of entry_lag_days, stddev of completeness_pct, "
        "correction rate, and entry count. Near-zero stddev across domains = suppressed randomness. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        q = db_session.query(
            ECRFEntry.site_id,
            func.count(ECRFEntry.id).label("entry_count"),
            func.avg(ECRFEntry.entry_lag_days).label("mean_entry_lag"),
            func.stddev(ECRFEntry.entry_lag_days).label("stddev_entry_lag"),
            func.avg(ECRFEntry.completeness_pct).label("mean_completeness"),
            func.stddev(ECRFEntry.completeness_pct).label("stddev_completeness"),
        ).group_by(ECRFEntry.site_id)

        if site_id:
            q = q.filter(ECRFEntry.site_id == site_id)

        ecrf_rows = q.all()
        ecrf_data = _serialize_rows(ecrf_rows)

        # Correction rate per site
        corr_q = db_session.query(
            DataCorrection.site_id,
            func.count(DataCorrection.id).label("correction_count"),
        ).group_by(DataCorrection.site_id)
        if site_id:
            corr_q = corr_q.filter(DataCorrection.site_id == site_id)
        corr_data = {r.site_id: r.correction_count for r in corr_q.all()}

        for row in ecrf_data:
            sid = row["site_id"]
            entry_count = row.get("entry_count", 0)
            row["correction_count"] = corr_data.get(sid, 0)
            row["correction_rate"] = round(corr_data.get(sid, 0) / entry_count, 4) if entry_count > 0 else 0

        return ToolResult(tool_name=self.name, success=True, data=ecrf_data, row_count=len(ecrf_data))


class TimestampClusteringTool(BaseTool):
    name = "timestamp_clustering"
    description = (
        "Per-site coefficient of variation for entry_lag_days and inter-randomization-date intervals. "
        "CV < 0.1 = unnaturally uniform timing. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # Entry lag CV per site
        lag_q = db_session.query(
            ECRFEntry.site_id,
            func.avg(ECRFEntry.entry_lag_days).label("mean_entry_lag"),
            func.stddev(ECRFEntry.entry_lag_days).label("stddev_entry_lag"),
            func.count(ECRFEntry.id).label("entry_count"),
        ).group_by(ECRFEntry.site_id)
        if site_id:
            lag_q = lag_q.filter(ECRFEntry.site_id == site_id)
        lag_rows = _serialize_rows(lag_q.all())

        for row in lag_rows:
            mean = row.get("mean_entry_lag") or 0
            std = row.get("stddev_entry_lag") or 0
            row["entry_lag_cv"] = round(std / mean, 4) if mean > 0 else 0

        # Randomization date intervals per site
        rand_q = db_session.query(
            RandomizationLog.site_id,
            RandomizationLog.randomization_date,
        ).order_by(RandomizationLog.site_id, RandomizationLog.randomization_date)
        if site_id:
            rand_q = rand_q.filter(RandomizationLog.site_id == site_id)
        rand_rows = rand_q.all()

        # Compute inter-randomization intervals
        site_intervals: dict[str, list] = {}
        for r in rand_rows:
            sid = r.site_id
            if sid not in site_intervals:
                site_intervals[sid] = []
            site_intervals[sid].append(r.randomization_date)

        rand_cv_data = {}
        for sid, dates in site_intervals.items():
            if len(dates) < 3:
                rand_cv_data[sid] = {"randomization_count": len(dates), "inter_rand_cv": None}
                continue
            intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            mean_iv = sum(intervals) / len(intervals) if intervals else 0
            if mean_iv > 0 and len(intervals) > 1:
                var = sum((x - mean_iv) ** 2 for x in intervals) / (len(intervals) - 1)
                std_iv = var ** 0.5
                cv = round(std_iv / mean_iv, 4)
            else:
                cv = 0
            rand_cv_data[sid] = {"randomization_count": len(dates), "inter_rand_cv": cv, "mean_interval_days": round(mean_iv, 1)}

        # Merge
        for row in lag_rows:
            sid = row["site_id"]
            row.update(rand_cv_data.get(sid, {"randomization_count": 0, "inter_rand_cv": None}))

        return ToolResult(tool_name=self.name, success=True, data=lag_rows, row_count=len(lag_rows))


class QueryLifecycleAnomalyTool(BaseTool):
    name = "query_lifecycle_anomaly"
    description = (
        "Per-site query lifecycle analysis: mean/stddev age_days, % monitoring-triggered queries, "
        "open/answered/closed counts. Zero aging variance + no monitoring-triggered queries = phantom. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        q = db_session.query(
            Query.site_id,
            func.count(Query.id).label("total_queries"),
            func.avg(Query.age_days).label("mean_age"),
            func.stddev(Query.age_days).label("stddev_age"),
            func.sum(case((Query.status == "Open", 1), else_=0)).label("open_count"),
            func.sum(case((Query.status == "Answered", 1), else_=0)).label("answered_count"),
            func.sum(case((Query.status == "Closed", 1), else_=0)).label("closed_count"),
            func.sum(case((Query.triggered_by == "Monitoring", 1), else_=0)).label("monitoring_triggered"),
        ).group_by(Query.site_id)

        if site_id:
            q = q.filter(Query.site_id == site_id)

        rows = q.all()
        data = _serialize_rows(rows)

        for row in data:
            total = row.get("total_queries", 0)
            mon = row.get("monitoring_triggered", 0)
            row["pct_monitoring_triggered"] = round(mon / total * 100, 1) if total > 0 else 0

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class MonitoringFindingsVarianceTool(BaseTool):
    name = "monitoring_findings_variance"
    description = (
        "Per-site monitoring findings analysis: mean/stddev findings_count, % visits with 0 findings, "
        "mean/stddev days_overdue. Always 0-1 findings + zero schedule variance = phantom. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        q = db_session.query(
            MonitoringVisit.site_id,
            func.count(MonitoringVisit.id).label("visit_count"),
            func.avg(MonitoringVisit.findings_count).label("mean_findings"),
            func.stddev(MonitoringVisit.findings_count).label("stddev_findings"),
            func.sum(case((MonitoringVisit.findings_count == 0, 1), else_=0)).label("zero_findings_visits"),
            func.avg(MonitoringVisit.days_overdue).label("mean_days_overdue"),
            func.stddev(MonitoringVisit.days_overdue).label("stddev_days_overdue"),
        ).group_by(MonitoringVisit.site_id)

        if site_id:
            q = q.filter(MonitoringVisit.site_id == site_id)

        rows = q.all()
        data = _serialize_rows(rows)

        for row in data:
            total = row.get("visit_count", 0)
            zero = row.get("zero_findings_visits", 0)
            row["pct_zero_findings"] = round(zero / total * 100, 1) if total > 0 else 0

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


# ═══════════════════════════════════════════════════════════════════════════════
# SITE RESCUE TOOLS (Site Decision)
# ═══════════════════════════════════════════════════════════════════════════════

class EnrollmentTrajectoryTool(BaseTool):
    name = "enrollment_trajectory"
    description = (
        "Per-site enrollment trajectory: 4-week average velocity, velocity trend (slope), "
        "gap to target, projected weeks to complete at current rate. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # Get last 8 weeks of velocity data for trend calculation
        max_week = db_session.query(func.max(EnrollmentVelocity.week_number)).scalar() or 0

        q = db_session.query(
            EnrollmentVelocity.site_id,
            EnrollmentVelocity.week_number,
            EnrollmentVelocity.randomized_count,
            EnrollmentVelocity.cumulative_randomized,
            EnrollmentVelocity.target_cumulative,
        ).filter(
            EnrollmentVelocity.week_number > max_week - 8,
        ).order_by(EnrollmentVelocity.site_id, EnrollmentVelocity.week_number)

        if site_id:
            q = q.filter(EnrollmentVelocity.site_id == site_id)

        rows = q.all()

        # Group by site and compute trajectory metrics
        site_weeks: dict[str, list] = {}
        for r in rows:
            if r.site_id not in site_weeks:
                site_weeks[r.site_id] = []
            site_weeks[r.site_id].append(r)

        data = []
        for sid, weeks in site_weeks.items():
            velocities = [w.randomized_count for w in weeks]
            last_4 = velocities[-4:] if len(velocities) >= 4 else velocities
            avg_velocity = sum(last_4) / len(last_4) if last_4 else 0

            # Simple linear slope over available weeks
            if len(velocities) >= 3:
                n = len(velocities)
                x_mean = (n - 1) / 2
                y_mean = sum(velocities) / n
                num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(velocities))
                denom = sum((i - x_mean) ** 2 for i in range(n))
                slope = round(num / denom, 3) if denom > 0 else 0
            else:
                slope = 0

            latest = weeks[-1]
            gap = (latest.target_cumulative or 0) - (latest.cumulative_randomized or 0)
            projected_weeks = round(gap / avg_velocity, 1) if avg_velocity > 0 and gap > 0 else None

            data.append({
                "site_id": sid,
                "avg_velocity_4wk": round(avg_velocity, 2),
                "velocity_slope": slope,
                "cumulative_randomized": latest.cumulative_randomized,
                "target_cumulative": latest.target_cumulative,
                "gap_to_target": max(gap, 0),
                "projected_weeks_to_complete": projected_weeks,
                "trend": "declining" if slope < -0.1 else "improving" if slope > 0.1 else "flat",
            })

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class ScreenFailureRootCauseTool(BaseTool):
    name = "screen_failure_root_cause"
    description = (
        "Per-site screen failure root cause analysis: failure codes with counts, study-wide comparison, "
        "top failure narratives. Distinguishes fixable (PI interpretation) from structural (population) causes. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # Site-level failure code breakdown
        site_q = db_session.query(
            ScreeningLog.site_id,
            ScreeningLog.failure_reason_code,
            func.count(ScreeningLog.id).label("count"),
        ).filter(
            ScreeningLog.outcome == "Failed",
            ScreeningLog.failure_reason_code.isnot(None),
        ).group_by(ScreeningLog.site_id, ScreeningLog.failure_reason_code)

        if site_id:
            site_q = site_q.filter(ScreeningLog.site_id == site_id)

        site_data = _serialize_rows(site_q.all())

        # Study-wide averages
        study_total = db_session.query(func.count(ScreeningLog.id)).filter(
            ScreeningLog.outcome == "Failed",
            ScreeningLog.failure_reason_code.isnot(None),
        ).scalar() or 1

        study_q = db_session.query(
            ScreeningLog.failure_reason_code,
            func.count(ScreeningLog.id).label("study_count"),
        ).filter(
            ScreeningLog.outcome == "Failed",
            ScreeningLog.failure_reason_code.isnot(None),
        ).group_by(ScreeningLog.failure_reason_code)
        study_data = _serialize_rows(study_q.all())
        for row in study_data:
            row["study_pct"] = round(row["study_count"] / study_total * 100, 1)

        # Top narratives (limited)
        narr_q = db_session.query(
            ScreeningLog.site_id,
            ScreeningLog.failure_reason_code,
            ScreeningLog.failure_reason_narrative,
        ).filter(
            ScreeningLog.outcome == "Failed",
            ScreeningLog.failure_reason_narrative.isnot(None),
        )
        if site_id:
            narr_q = narr_q.filter(ScreeningLog.site_id == site_id)
        narratives = _serialize_rows(narr_q.limit(30).all())

        result = {
            "site_failure_codes": site_data,
            "study_average_codes": study_data,
            "narratives": narratives,
        }
        return ToolResult(tool_name=self.name, success=True, data=result, row_count=len(site_data))


class SupplyConstraintImpactTool(BaseTool):
    name = "supply_constraint_impact"
    description = (
        "Per-site supply constraint analysis: randomization delay events by reason, stockout episodes "
        "from kit inventory (with date ranges), and consent withdrawal counts. "
        "Returns three separate datasets for LLM-driven temporal cross-referencing. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # Randomization delay events
        delay_q = db_session.query(
            RandomizationEvent.site_id,
            RandomizationEvent.event_type,
            RandomizationEvent.delay_reason,
            func.count(RandomizationEvent.id).label("event_count"),
            func.avg(RandomizationEvent.delay_duration_hours).label("avg_delay_hours"),
        ).group_by(
            RandomizationEvent.site_id,
            RandomizationEvent.event_type,
            RandomizationEvent.delay_reason,
        )
        if site_id:
            delay_q = delay_q.filter(RandomizationEvent.site_id == site_id)
        delay_data = _serialize_rows(delay_q.all())

        # Stockout episodes (below reorder)
        stock_q = db_session.query(
            KitInventory.site_id,
            func.count(KitInventory.id).label("stockout_snapshots"),
            func.min(KitInventory.snapshot_date).label("first_stockout"),
            func.max(KitInventory.snapshot_date).label("last_stockout"),
        ).filter(
            KitInventory.is_below_reorder.is_(True),
        ).group_by(KitInventory.site_id)
        if site_id:
            stock_q = stock_q.filter(KitInventory.site_id == site_id)
        stockout_data = _serialize_rows(stock_q.all())

        # Consent withdrawals
        withdrawal_q = db_session.query(
            ScreeningLog.site_id,
            func.count(ScreeningLog.id).label("withdrawal_count"),
        ).filter(
            ScreeningLog.outcome == "Withdrawn",
        ).group_by(ScreeningLog.site_id)
        if site_id:
            withdrawal_q = withdrawal_q.filter(ScreeningLog.site_id == site_id)
        withdrawal_data = _serialize_rows(withdrawal_q.all())

        result = {
            "randomization_delays": delay_data,
            "stockout_episodes": stockout_data,
            "consent_withdrawals": withdrawal_data,
        }
        return ToolResult(tool_name=self.name, success=True, data=result, row_count=len(delay_data))


# ═══════════════════════════════════════════════════════════════════════════════
# VENDOR PERFORMANCE TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

class VendorKPIAnalysisTool(BaseTool):
    name = "vendor_kpi_analysis"
    description = (
        "Analyzes vendor KPI trends, threshold breaches, and target comparisons. "
        "Returns KPI snapshots with status (Green/Amber/Red) per vendor. "
        "Args: vendor_id (optional, for specific vendor)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        vendor_id = kwargs.get("vendor_id")
        q = db_session.query(
            VendorKPI.vendor_id,
            VendorKPI.kpi_name,
            VendorKPI.snapshot_date,
            VendorKPI.value,
            VendorKPI.target,
            VendorKPI.status,
        ).order_by(VendorKPI.vendor_id, VendorKPI.kpi_name, VendorKPI.snapshot_date.desc())

        if vendor_id:
            q = q.filter(VendorKPI.vendor_id == vendor_id)

        # Get latest 3 months per vendor-KPI combo
        rows = q.limit(200).all()
        data = _serialize_rows(rows)

        # Add vendor names
        vendor_names = {v.vendor_id: v.name for v in db_session.query(Vendor.vendor_id, Vendor.name).all()}
        for d in data:
            d["vendor_name"] = vendor_names.get(d.get("vendor_id"), "")

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class VendorSiteComparisonTool(BaseTool):
    name = "vendor_site_comparison"
    description = (
        "Compares operational metrics at sites managed by different vendors. "
        "Returns entry lag, query burden, enrollment metrics grouped by vendor. "
        "Args: vendor_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        vendor_id = kwargs.get("vendor_id")

        # Get vendor-site assignments
        assign_q = db_session.query(VendorSiteAssignment).filter(
            VendorSiteAssignment.is_active.is_(True),
            VendorSiteAssignment.role == "Primary Monitor",
        )
        if vendor_id:
            assign_q = assign_q.filter(VendorSiteAssignment.vendor_id == vendor_id)
        assignments = assign_q.all()

        vendor_sites: dict[str, list[str]] = {}
        for a in assignments:
            vendor_sites.setdefault(a.vendor_id, []).append(a.site_id)

        vendor_names = {v.vendor_id: v.name for v in db_session.query(Vendor.vendor_id, Vendor.name).all()}
        results = []
        for vid, site_ids in vendor_sites.items():
            avg_lag = db_session.query(func.avg(ECRFEntry.entry_lag_days)).filter(
                ECRFEntry.site_id.in_(site_ids)
            ).scalar()
            open_queries = db_session.query(func.count(Query.id)).filter(
                Query.site_id.in_(site_ids), Query.status == "Open"
            ).scalar()
            randomized = db_session.query(func.count(RandomizationLog.id)).filter(
                RandomizationLog.site_id.in_(site_ids)
            ).scalar()

            results.append({
                "vendor_id": vid,
                "vendor_name": vendor_names.get(vid, ""),
                "site_count": len(site_ids),
                "avg_entry_lag": round(float(avg_lag), 1) if avg_lag else None,
                "total_open_queries": open_queries or 0,
                "total_randomized": randomized or 0,
            })

        return ToolResult(tool_name=self.name, success=True, data=results, row_count=len(results))


class VendorMilestoneTrackerTool(BaseTool):
    name = "vendor_milestone_tracker"
    description = (
        "Tracks planned vs actual milestone dates, delays, and at-risk milestones. "
        "Args: vendor_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        vendor_id = kwargs.get("vendor_id")
        q = db_session.query(VendorMilestone).order_by(VendorMilestone.planned_date)
        if vendor_id:
            q = q.filter(VendorMilestone.vendor_id == vendor_id)

        rows = q.all()
        vendor_names = {v.vendor_id: v.name for v in db_session.query(Vendor.vendor_id, Vendor.name).all()}
        data = []
        for m in rows:
            data.append({
                "vendor_id": m.vendor_id,
                "vendor_name": vendor_names.get(m.vendor_id, ""),
                "milestone_name": m.milestone_name,
                "planned_date": m.planned_date.isoformat() if m.planned_date else None,
                "actual_date": m.actual_date.isoformat() if m.actual_date else None,
                "status": m.status,
                "delay_days": m.delay_days or 0,
            })
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class VendorIssueLogTool(BaseTool):
    name = "vendor_issue_log"
    description = (
        "Retrieves vendor issue patterns, severity distribution, resolution rates. "
        "Args: vendor_id (optional), status (optional: Open/Resolved)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        vendor_id = kwargs.get("vendor_id")
        status = kwargs.get("status")
        q = db_session.query(VendorIssue).order_by(VendorIssue.open_date.desc())
        if vendor_id:
            q = q.filter(VendorIssue.vendor_id == vendor_id)
        if status:
            q = q.filter(VendorIssue.status == status)

        rows = q.limit(100).all()
        vendor_names = {v.vendor_id: v.name for v in db_session.query(Vendor.vendor_id, Vendor.name).all()}
        data = []
        for issue in rows:
            data.append({
                "vendor_id": issue.vendor_id,
                "vendor_name": vendor_names.get(issue.vendor_id, ""),
                "category": issue.category,
                "severity": issue.severity,
                "description": issue.description,
                "open_date": issue.open_date.isoformat() if issue.open_date else None,
                "resolution_date": issue.resolution_date.isoformat() if issue.resolution_date else None,
                "status": issue.status,
            })
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCIAL INTELLIGENCE TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

class BudgetVarianceAnalysisTool(BaseTool):
    name = "budget_variance_analysis"
    description = (
        "Analyzes planned vs actual vs forecast by category, country, and vendor. "
        "Args: category_code (optional), country (optional), vendor_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        category = kwargs.get("category_code")
        country = kwargs.get("country")
        vendor_id = kwargs.get("vendor_id")

        q = db_session.query(
            BudgetLineItem.category_code,
            BudgetLineItem.country,
            BudgetLineItem.vendor_id,
            func.sum(BudgetLineItem.planned_amount).label("planned"),
            func.sum(BudgetLineItem.actual_amount).label("actual"),
            func.sum(BudgetLineItem.forecast_amount).label("forecast"),
        ).group_by(BudgetLineItem.category_code, BudgetLineItem.country, BudgetLineItem.vendor_id)

        if category:
            q = q.filter(BudgetLineItem.category_code == category)
        if country:
            q = q.filter(BudgetLineItem.country == country)
        if vendor_id:
            q = q.filter(BudgetLineItem.vendor_id == vendor_id)

        rows = q.all()
        data = _serialize_rows(rows)
        for d in data:
            planned = d.get("planned") or 0
            actual = d.get("actual") or 0
            d["variance"] = round(actual - planned, 2)
            d["variance_pct"] = round(((actual - planned) / planned) * 100, 2) if planned else 0

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class CostPerPatientAnalysisTool(BaseTool):
    name = "cost_per_patient_analysis"
    description = (
        "Analyzes site-level cost efficiency cross-referenced with enrollment. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        q = db_session.query(SiteFinancialMetric)
        if site_id:
            q = q.filter(SiteFinancialMetric.site_id == site_id)

        rows = q.all()
        site_names = {s.site_id: s.name for s in db_session.query(Site.site_id, Site.name).all()}
        data = []
        for m in rows:
            data.append({
                "site_id": m.site_id,
                "site_name": site_names.get(m.site_id),
                "cost_to_date": m.cost_to_date,
                "cost_per_screened": m.cost_per_patient_screened,
                "cost_per_randomized": m.cost_per_patient_randomized,
                "planned_cost_to_date": m.planned_cost_to_date,
                "variance_pct": m.variance_pct,
            })
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class BurnRateProjectionTool(BaseTool):
    name = "burn_rate_projection"
    description = (
        "Projects total cost and months of funding remaining based on current burn rate. "
        "Returns monthly financial snapshots with trend data."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        snapshots = db_session.query(FinancialSnapshot).order_by(
            FinancialSnapshot.snapshot_month
        ).all()

        budget = db_session.query(StudyBudget).filter(StudyBudget.status == "Active").first()
        total_budget = budget.total_budget_usd if budget else 0

        data = []
        for s in snapshots:
            remaining = total_budget - (s.actual_cumulative or 0)
            months_remaining = remaining / s.burn_rate if s.burn_rate and s.burn_rate > 0 else None
            data.append({
                "month": s.snapshot_month.isoformat() if s.snapshot_month else None,
                "planned_cumulative": s.planned_cumulative,
                "actual_cumulative": s.actual_cumulative,
                "forecast_cumulative": s.forecast_cumulative,
                "burn_rate": s.burn_rate,
                "variance_pct": s.variance_pct,
                "remaining_budget": round(remaining, 2),
                "months_of_funding": round(months_remaining, 1) if months_remaining else None,
            })
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class ChangeOrderImpactTool(BaseTool):
    name = "change_order_impact"
    description = (
        "Analyzes cumulative scope creep from change orders. "
        "Returns change orders with amounts, timeline impact, and approval status."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        vendor_id = kwargs.get("vendor_id")
        q = db_session.query(ChangeOrder).order_by(ChangeOrder.submitted_date)
        if vendor_id:
            q = q.filter(ChangeOrder.vendor_id == vendor_id)

        rows = q.all()
        vendor_names = {v.vendor_id: v.name for v in db_session.query(Vendor.vendor_id, Vendor.name).all()}
        data = []
        cumulative = 0
        for co in rows:
            if co.status == "Approved":
                cumulative += co.amount or 0
            data.append({
                "change_order_number": co.change_order_number,
                "vendor_id": co.vendor_id,
                "vendor_name": vendor_names.get(co.vendor_id, ""),
                "category": co.category,
                "amount": co.amount,
                "timeline_impact_days": co.timeline_impact_days,
                "description": co.description,
                "status": co.status,
                "submitted_date": co.submitted_date.isoformat() if co.submitted_date else None,
                "cumulative_approved": round(cumulative, 2),
            })
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class FinancialImpactOfDelaysTool(BaseTool):
    name = "financial_impact_of_delays"
    description = (
        "Calculates dollar cost of enrollment, activation, and monitoring delays. "
        "Cross-references operational delays with financial metrics. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # Get sites with financial metrics
        q = db_session.query(SiteFinancialMetric)
        if site_id:
            q = q.filter(SiteFinancialMetric.site_id == site_id)
        metrics = q.all()

        # Get enrollment data for context
        enrollment_counts = dict(
            db_session.query(RandomizationLog.site_id, func.count(RandomizationLog.id))
            .group_by(RandomizationLog.site_id).all()
        )
        site_targets = {s.site_id: s.target_enrollment for s in db_session.query(Site.site_id, Site.target_enrollment).all()}
        site_names = {s.site_id: s.name for s in db_session.query(Site.site_id, Site.name).all()}

        data = []
        for m in metrics:
            enrolled = enrollment_counts.get(m.site_id, 0)
            target = site_targets.get(m.site_id, 0)
            enrollment_gap = max(0, target - enrolled)
            # Estimate delay cost: additional months of site maintenance
            monthly_site_cost = (m.cost_to_date or 0) / max(18, 1)  # approx 18 months of study
            estimated_delay_cost = enrollment_gap * monthly_site_cost * 0.1 if enrollment_gap > 0 else 0

            if m.variance_pct and m.variance_pct > 5:
                data.append({
                    "site_id": m.site_id,
                    "site_name": site_names.get(m.site_id),
                    "cost_to_date": m.cost_to_date,
                    "variance_pct": m.variance_pct,
                    "enrolled": enrolled,
                    "target": target,
                    "enrollment_gap": enrollment_gap,
                    "estimated_delay_cost": round(estimated_delay_cost, 2),
                    "cost_per_randomized": m.cost_per_patient_randomized,
                })

        data.sort(key=lambda x: x.get("estimated_delay_cost", 0), reverse=True)
        return ToolResult(tool_name=self.name, success=True, data=data[:30], row_count=len(data))


def build_tool_registry() -> "ToolRegistry":
    """Create and populate the default tool registry with all tool types."""
    from backend.tools.base import ToolRegistry
    from backend.tools.vector_tools import ContextSearchTool
    from backend.tools.forecast_tools import TrendProjectionTool

    registry = ToolRegistry()
    # Agent 1 tools (Data Quality)
    registry.register(EntryLagAnalysisTool())
    registry.register(QueryBurdenTool())
    registry.register(DataCorrectionAnalysisTool())
    registry.register(CRAAssignmentHistoryTool())
    registry.register(MonitoringVisitHistoryTool())
    registry.register(SiteSummaryTool())
    # Agent 3 tools (Enrollment Funnel)
    registry.register(ScreeningFunnelTool())
    registry.register(EnrollmentVelocityTool())
    registry.register(ScreenFailurePatternTool())
    registry.register(RegionalComparisonTool())
    registry.register(KitInventoryTool())
    registry.register(KRISnapshotTool())
    # Phantom Compliance tools (Data Integrity)
    registry.register(DataVarianceAnalysisTool())
    registry.register(TimestampClusteringTool())
    registry.register(QueryLifecycleAnomalyTool())
    registry.register(MonitoringFindingsVarianceTool())
    # Site Rescue tools (Site Decision)
    registry.register(EnrollmentTrajectoryTool())
    registry.register(ScreenFailureRootCauseTool())
    registry.register(SupplyConstraintImpactTool())
    # Cross-domain tools
    registry.register(ContextSearchTool())
    registry.register(TrendProjectionTool())
    # Vendor Performance tools
    registry.register(VendorKPIAnalysisTool())
    registry.register(VendorSiteComparisonTool())
    registry.register(VendorMilestoneTrackerTool())
    registry.register(VendorIssueLogTool())
    # Financial Intelligence tools
    registry.register(BudgetVarianceAnalysisTool())
    registry.register(CostPerPatientAnalysisTool())
    registry.register(BurnRateProjectionTool())
    registry.register(ChangeOrderImpactTool())
    registry.register(FinancialImpactOfDelaysTool())
    # Competitive intelligence tools (external API)
    from backend.tools.ctgov_tools import CompetingTrialSearchTool
    registry.register(CompetingTrialSearchTool())
    return registry
