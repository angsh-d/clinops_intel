"""SQL query tools against the 24 CODM tables.

Agent 1 tools: data quality domain
Agent 3 tools: enrollment funnel domain
"""

from datetime import date
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from data_generators.models import (
    Site, ECRFEntry, Query, DataCorrection, CRAAssignment,
    MonitoringVisit, MonitoringVisitReport, OverdueAction, ScreeningLog, RandomizationLog, EnrollmentVelocity,
    ScreenFailureReasonCode, KitInventory, KRISnapshot,
    RandomizationEvent, SubjectVisit, StudyConfig,
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


class MonitoringVisitReportTool(BaseTool):
    name = "monitoring_visit_report"
    description = (
        "Returns the last N monitoring visit reports for a site with full detail: "
        "visit date, type, CRA, findings count, critical findings, queries generated, "
        "days overdue, AND linked follow-up action items (category, description, status). "
        "Use this for questions about monitoring visit findings, visit reports, or follow-up actions. "
        "Args: site_id (required), limit (optional, default 2)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        if not site_id:
            return ToolResult(tool_name=self.name, success=False, data=[], row_count=0,
                              error="site_id is required")
        limit = int(kwargs.get("limit", 2))

        visits = (
            db_session.query(MonitoringVisit)
            .filter(MonitoringVisit.site_id == site_id, MonitoringVisit.status == "Completed")
            .order_by(MonitoringVisit.actual_date.desc())
            .limit(limit)
            .all()
        )

        reports = []
        for v in visits:
            actions = (
                db_session.query(OverdueAction)
                .filter(OverdueAction.monitoring_visit_id == v.id)
                .all()
            )
            action_list = [
                {
                    "category": a.category,
                    "description": a.action_description,
                    "status": a.status,
                    "due_date": str(a.due_date) if a.due_date else None,
                }
                for a in actions
            ]

            # Pre-format findings summary for LLM consumption
            parts = [f"{v.findings_count} findings ({v.critical_findings} critical)"]
            if action_list:
                action_strs = [f"[{a['category']}] {a['description']} ({a['status']})" for a in action_list]
                parts.append("Actions: " + "; ".join(action_strs))
            else:
                parts.append("No follow-up actions recorded")
            if v.queries_generated:
                parts.append(f"{v.queries_generated} queries generated")

            reports.append({
                "visit_id": v.id,
                "site_id": v.site_id,
                "cra_id": v.cra_id,
                "visit_date": str(v.actual_date) if v.actual_date else None,
                "planned_date": str(v.planned_date) if v.planned_date else None,
                "visit_type": v.visit_type,
                "findings_count": v.findings_count,
                "critical_findings": v.critical_findings,
                "queries_generated": v.queries_generated,
                "days_overdue": v.days_overdue,
                "findings_summary": ". ".join(parts),
                "follow_up_actions": action_list,
            })

        return ToolResult(tool_name=self.name, success=True, data=reports, row_count=len(reports))


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
# FRAUD DETECTION TOOLS (Data Integrity Signals)
# ═══════════════════════════════════════════════════════════════════════════════

class WeekdayEntryPatternTool(BaseTool):
    name = "weekday_entry_pattern"
    description = (
        "Per-site weekday distribution of data entry. Detects unnatural patterns like "
        "all entries on Mondays (batch catchup) or no weekend entries despite patient visits. "
        "High concentration on single day (>40%) = suspicious. Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # Get day-of-week distribution for entry_date
        q = db_session.query(
            ECRFEntry.site_id,
            func.extract('dow', ECRFEntry.entry_date).label("day_of_week"),
            func.count(ECRFEntry.id).label("entry_count"),
        ).group_by(ECRFEntry.site_id, func.extract('dow', ECRFEntry.entry_date))

        if site_id:
            q = q.filter(ECRFEntry.site_id == site_id)

        rows = q.all()

        # Aggregate per site
        site_data: dict = {}
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for r in rows:
            sid = r.site_id
            dow = int(r.day_of_week) if r.day_of_week is not None else 0
            if sid not in site_data:
                site_data[sid] = {"site_id": sid, "total_entries": 0, "weekday_counts": {d: 0 for d in day_names}}
            site_data[sid]["weekday_counts"][day_names[dow]] = r.entry_count
            site_data[sid]["total_entries"] += r.entry_count

        # Calculate concentration metrics
        data = []
        for sid, info in site_data.items():
            total = info["total_entries"]
            if total == 0:
                continue
            counts = list(info["weekday_counts"].values())
            max_day_count = max(counts)
            max_day = [d for d, c in info["weekday_counts"].items() if c == max_day_count][0]
            pct_max_day = round(max_day_count / total * 100, 1)
            weekend_count = info["weekday_counts"]["Saturday"] + info["weekday_counts"]["Sunday"]
            pct_weekend = round(weekend_count / total * 100, 1)

            data.append({
                "site_id": sid,
                "total_entries": total,
                "dominant_day": max_day,
                "pct_dominant_day": pct_max_day,
                "pct_weekend": pct_weekend,
                "weekday_distribution": info["weekday_counts"],
                "concentration_flag": pct_max_day > 40,
            })

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class CRAOversightGapTool(BaseTool):
    name = "cra_oversight_gap"
    description = (
        "Detects periods without CRA coverage and gaps between monitoring visits. "
        "Sites with >60 days without monitoring or unassigned CRA periods = red flag. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # CRA assignment gaps
        cra_q = db_session.query(
            CRAAssignment.site_id,
            CRAAssignment.cra_id,
            CRAAssignment.start_date,
            CRAAssignment.end_date,
        ).order_by(CRAAssignment.site_id, CRAAssignment.start_date)
        if site_id:
            cra_q = cra_q.filter(CRAAssignment.site_id == site_id)
        cra_rows = cra_q.all()

        # Monitoring visit gaps
        mon_q = db_session.query(
            MonitoringVisit.site_id,
            MonitoringVisit.actual_date,
        ).filter(MonitoringVisit.status == "Completed").order_by(
            MonitoringVisit.site_id, MonitoringVisit.actual_date
        )
        if site_id:
            mon_q = mon_q.filter(MonitoringVisit.site_id == site_id)
        mon_rows = mon_q.all()

        # Compute CRA gaps per site
        site_cra_gaps: dict = {}
        current_site = None
        prev_end = None
        for r in cra_rows:
            if r.site_id != current_site:
                current_site = r.site_id
                prev_end = None
                site_cra_gaps[current_site] = {"cra_gap_days": 0, "cra_transitions": 0, "gap_periods": []}

            if prev_end and r.start_date:
                gap = (r.start_date - prev_end).days
                if gap > 0:
                    site_cra_gaps[current_site]["cra_gap_days"] += gap
                    site_cra_gaps[current_site]["gap_periods"].append({
                        "from": str(prev_end), "to": str(r.start_date), "days": gap
                    })
            site_cra_gaps[current_site]["cra_transitions"] += 1
            prev_end = r.end_date if r.end_date else r.start_date

        # Compute monitoring gaps per site
        site_mon_gaps: dict = {}
        current_site = None
        prev_date = None
        for r in mon_rows:
            if r.site_id != current_site:
                current_site = r.site_id
                prev_date = None
                site_mon_gaps[current_site] = {"max_monitoring_gap_days": 0, "mean_monitoring_gap_days": 0, "gaps": []}

            if prev_date and r.actual_date:
                gap = (r.actual_date - prev_date).days
                site_mon_gaps[current_site]["gaps"].append(gap)
                if gap > site_mon_gaps[current_site]["max_monitoring_gap_days"]:
                    site_mon_gaps[current_site]["max_monitoring_gap_days"] = gap
            prev_date = r.actual_date

        for sid, info in site_mon_gaps.items():
            if info["gaps"]:
                info["mean_monitoring_gap_days"] = round(sum(info["gaps"]) / len(info["gaps"]), 1)
            del info["gaps"]  # Don't return raw list

        # Merge
        all_sites = set(site_cra_gaps.keys()) | set(site_mon_gaps.keys())
        data = []
        for sid in all_sites:
            cra_info = site_cra_gaps.get(sid, {"cra_gap_days": 0, "cra_transitions": 0, "gap_periods": []})
            mon_info = site_mon_gaps.get(sid, {"max_monitoring_gap_days": 0, "mean_monitoring_gap_days": 0})
            data.append({
                "site_id": sid,
                "cra_gap_days": cra_info["cra_gap_days"],
                "cra_transitions": cra_info["cra_transitions"],
                "max_monitoring_gap_days": mon_info["max_monitoring_gap_days"],
                "mean_monitoring_gap_days": mon_info["mean_monitoring_gap_days"],
                "oversight_risk": cra_info["cra_gap_days"] > 30 or mon_info["max_monitoring_gap_days"] > 60,
            })

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class CRAPortfolioAnalysisTool(BaseTool):
    name = "cra_portfolio_analysis"
    description = (
        "Cross-site CRA analysis: per-CRA mean findings/visit, % zero-finding visits, "
        "sites monitored, queries generated. CRAs who never find issues across multiple sites = rubber-stamping. "
        "Args: cra_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        cra_id = kwargs.get("cra_id")

        q = db_session.query(
            MonitoringVisit.cra_id,
            func.count(func.distinct(MonitoringVisit.site_id)).label("sites_monitored"),
            func.count(MonitoringVisit.id).label("total_visits"),
            func.avg(MonitoringVisit.findings_count).label("mean_findings"),
            func.sum(MonitoringVisit.findings_count).label("total_findings"),
            func.sum(MonitoringVisit.queries_generated).label("total_queries_generated"),
            func.sum(case((MonitoringVisit.findings_count == 0, 1), else_=0)).label("zero_finding_visits"),
        ).filter(MonitoringVisit.cra_id.isnot(None)).group_by(MonitoringVisit.cra_id)

        if cra_id:
            q = q.filter(MonitoringVisit.cra_id == cra_id)

        rows = q.all()
        data = _serialize_rows(rows)

        for row in data:
            total = row.get("total_visits", 0)
            zero = row.get("zero_finding_visits", 0)
            row["pct_zero_findings"] = round(zero / total * 100, 1) if total > 0 else 0
            row["rubber_stamp_risk"] = (
                row["pct_zero_findings"] > 80 and
                row.get("sites_monitored", 0) >= 2 and
                row.get("total_visits", 0) >= 5
            )

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class CorrectionProvenanceTool(BaseTool):
    name = "correction_provenance"
    description = (
        "Analyzes data correction sources: % triggered by queries vs unprompted. "
        "High rate of unprompted corrections before monitoring visits = pre-emptive cleanup (suspicious). "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        q = db_session.query(
            DataCorrection.site_id,
            func.count(DataCorrection.id).label("total_corrections"),
            func.sum(case(
                (DataCorrection.triggered_by_query_id.isnot(None), 1), else_=0
            )).label("query_triggered"),
            func.sum(case(
                (DataCorrection.triggered_by_query_id.is_(None), 1), else_=0
            )).label("unprompted"),
        ).group_by(DataCorrection.site_id)

        if site_id:
            q = q.filter(DataCorrection.site_id == site_id)

        rows = q.all()
        data = _serialize_rows(rows)

        for row in data:
            total = row.get("total_corrections", 0)
            unprompted = row.get("unprompted", 0)
            row["pct_unprompted"] = round(unprompted / total * 100, 1) if total > 0 else 0
            # High unprompted rate with low total could indicate cleanup before detection
            row["preemptive_cleanup_risk"] = row["pct_unprompted"] > 70 and total >= 5

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class EntryDateClusteringTool(BaseTool):
    name = "entry_date_clustering"
    description = (
        "Detects batch entry by analyzing clustering of entry_dates. "
        "Sites where >30% of entries occur on <5% of calendar days = batch backfill pattern. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # Get entry counts per date per site
        q = db_session.query(
            ECRFEntry.site_id,
            ECRFEntry.entry_date,
            func.count(ECRFEntry.id).label("entries_on_date"),
        ).group_by(ECRFEntry.site_id, ECRFEntry.entry_date).order_by(
            ECRFEntry.site_id, ECRFEntry.entry_date
        )

        if site_id:
            q = q.filter(ECRFEntry.site_id == site_id)

        rows = q.all()

        # Aggregate per site
        site_data: dict = {}
        for r in rows:
            sid = r.site_id
            if sid not in site_data:
                site_data[sid] = {"dates": [], "counts": [], "total": 0}
            site_data[sid]["dates"].append(r.entry_date)
            site_data[sid]["counts"].append(r.entries_on_date)
            site_data[sid]["total"] += r.entries_on_date

        data = []
        for sid, info in site_data.items():
            total = info["total"]
            num_dates = len(info["dates"])
            if num_dates == 0 or total == 0:
                continue

            # Sort by count descending to find peak days
            sorted_counts = sorted(info["counts"], reverse=True)

            # Top 5% of dates
            top_n = max(1, int(num_dates * 0.05))
            top_entries = sum(sorted_counts[:top_n])
            pct_in_top_5pct_days = round(top_entries / total * 100, 1)

            # Find max single-day entries
            max_single_day = sorted_counts[0] if sorted_counts else 0
            pct_max_day = round(max_single_day / total * 100, 1) if total > 0 else 0

            # Determine operational date span
            if info["dates"]:
                date_span = (max(info["dates"]) - min(info["dates"])).days + 1
                active_day_ratio = round(num_dates / date_span * 100, 1) if date_span > 0 else 100
            else:
                date_span = 0
                active_day_ratio = 0

            data.append({
                "site_id": sid,
                "total_entries": total,
                "unique_entry_dates": num_dates,
                "calendar_span_days": date_span,
                "active_day_ratio": active_day_ratio,
                "pct_in_top_5pct_days": pct_in_top_5pct_days,
                "max_entries_single_day": max_single_day,
                "pct_max_single_day": pct_max_day,
                "batch_entry_flag": pct_in_top_5pct_days > 30 or pct_max_day > 15,
            })

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class ScreeningNarrativeDuplicationTool(BaseTool):
    name = "screening_narrative_duplication"
    description = (
        "Detects copy-paste screen failure narratives by measuring text similarity/duplication. "
        "Sites with >50% identical narratives = templated responses (may indicate fabrication). "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        q = db_session.query(
            ScreeningLog.site_id,
            ScreeningLog.failure_reason_narrative,
        ).filter(
            ScreeningLog.outcome == "Failed",
            ScreeningLog.failure_reason_narrative.isnot(None),
        )

        if site_id:
            q = q.filter(ScreeningLog.site_id == site_id)

        rows = q.all()

        # Group narratives by site
        site_narratives: dict = {}
        for r in rows:
            sid = r.site_id
            if sid not in site_narratives:
                site_narratives[sid] = []
            # Normalize: lowercase, strip whitespace
            narrative = (r.failure_reason_narrative or "").strip().lower()
            if narrative:
                site_narratives[sid].append(narrative)

        data = []
        for sid, narratives in site_narratives.items():
            if len(narratives) < 2:
                continue

            # Count unique vs total
            unique_narratives = set(narratives)
            total = len(narratives)
            unique_count = len(unique_narratives)
            duplication_rate = round((1 - unique_count / total) * 100, 1) if total > 0 else 0

            # Find most common narrative
            from collections import Counter
            counts = Counter(narratives)
            most_common, most_common_count = counts.most_common(1)[0]
            pct_most_common = round(most_common_count / total * 100, 1)

            data.append({
                "site_id": sid,
                "total_failure_narratives": total,
                "unique_narratives": unique_count,
                "duplication_rate": duplication_rate,
                "most_common_narrative": most_common[:100] + "..." if len(most_common) > 100 else most_common,
                "pct_most_common": pct_most_common,
                "templating_flag": duplication_rate > 50 or pct_most_common > 40,
            })

        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class CrossDomainConsistencyTool(BaseTool):
    name = "cross_domain_consistency"
    description = (
        "Validates consistency across data domains. Perfect metrics in one domain but gaps in another "
        "= suspicious (e.g., 100% entry completeness but 0% SDV coverage). "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # Entry completeness
        entry_q = db_session.query(
            ECRFEntry.site_id,
            func.avg(ECRFEntry.completeness_pct).label("mean_completeness"),
            func.count(ECRFEntry.id).label("entry_count"),
        ).group_by(ECRFEntry.site_id)
        if site_id:
            entry_q = entry_q.filter(ECRFEntry.site_id == site_id)
        entry_data = {r.site_id: {"mean_completeness": r.mean_completeness, "entry_count": r.entry_count}
                      for r in entry_q.all()}

        # Query rate
        query_q = db_session.query(
            Query.site_id,
            func.count(Query.id).label("query_count"),
        ).group_by(Query.site_id)
        if site_id:
            query_q = query_q.filter(Query.site_id == site_id)
        query_data = {r.site_id: r.query_count for r in query_q.all()}

        # Correction rate
        corr_q = db_session.query(
            DataCorrection.site_id,
            func.count(DataCorrection.id).label("correction_count"),
        ).group_by(DataCorrection.site_id)
        if site_id:
            corr_q = corr_q.filter(DataCorrection.site_id == site_id)
        corr_data = {r.site_id: r.correction_count for r in corr_q.all()}

        # Monitoring findings
        mon_q = db_session.query(
            MonitoringVisit.site_id,
            func.sum(MonitoringVisit.findings_count).label("total_findings"),
            func.count(MonitoringVisit.id).label("visit_count"),
        ).group_by(MonitoringVisit.site_id)
        if site_id:
            mon_q = mon_q.filter(MonitoringVisit.site_id == site_id)
        mon_data = {r.site_id: {"total_findings": r.total_findings or 0, "visit_count": r.visit_count}
                    for r in mon_q.all()}

        # Merge all domains
        all_sites = set(entry_data.keys()) | set(query_data.keys()) | set(corr_data.keys()) | set(mon_data.keys())
        data = []
        for sid in all_sites:
            ed = entry_data.get(sid, {"mean_completeness": 0, "entry_count": 0})
            qd = query_data.get(sid, 0)
            cd = corr_data.get(sid, 0)
            md = mon_data.get(sid, {"total_findings": 0, "visit_count": 0})

            entries = ed["entry_count"]
            completeness = round(ed["mean_completeness"] or 0, 1)
            queries_per_100_entries = round(qd / entries * 100, 2) if entries > 0 else 0
            corrections_per_100_entries = round(cd / entries * 100, 2) if entries > 0 else 0
            findings_per_visit = round(md["total_findings"] / md["visit_count"], 2) if md["visit_count"] > 0 else 0

            # Inconsistency detection
            # High completeness + low queries + low corrections + low findings = suspicious
            is_too_perfect = (
                completeness > 98 and
                queries_per_100_entries < 2 and
                corrections_per_100_entries < 1 and
                findings_per_visit < 0.5 and
                entries >= 100
            )

            data.append({
                "site_id": sid,
                "entry_count": entries,
                "mean_completeness": completeness,
                "queries_per_100_entries": queries_per_100_entries,
                "corrections_per_100_entries": corrections_per_100_entries,
                "findings_per_visit": findings_per_visit,
                "cross_domain_inconsistency": is_too_perfect,
            })

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
        total_rows = len(delay_data) + len(stockout_data) + len(withdrawal_data)
        return ToolResult(tool_name=self.name, success=True, data=result, row_count=total_rows)


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
            d["variance_formula"] = f"${round(actual, 2)} actual - ${round(planned, 2)} planned = ${round(actual - planned, 2)}"
            d["data_source"] = "budget_line_items table"

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
            planned = m.planned_cost_to_date or 0
            actual = m.cost_to_date or 0
            over_plan = actual - planned
            data.append({
                "site_id": m.site_id,
                "site_name": site_names.get(m.site_id),
                "cost_to_date": m.cost_to_date,
                "planned_cost_to_date": planned,
                "over_plan_amount": round(over_plan, 2),
                "over_plan_formula": f"${round(actual, 2)} - ${round(planned, 2)} = ${round(over_plan, 2)}",
                "cost_per_screened": m.cost_per_patient_screened,
                "cost_per_randomized": m.cost_per_patient_randomized,
                "variance_pct": m.variance_pct,
                "data_source": "site_financial_metrics table",
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


class StudyOperationalSnapshotTool(BaseTool):
    name = "study_operational_snapshot"
    description = (
        "Returns a study-wide operational snapshot: sites needing attention (with severity, "
        "issue type, and metrics), and per-site status overview (enrollment %, DQ score, "
        "alert count, status). This is the authoritative source for 'which sites need attention' "
        "and 'study health overview' questions. Use this FIRST for study-level operations queries. "
        "Args: none required."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        from backend.services.dashboard_data import get_attention_sites_data, get_sites_overview_data
        from backend.config import get_settings

        settings = get_settings()
        attention = get_attention_sites_data(db_session, settings)
        overview = get_sites_overview_data(db_session, settings)

        data = {
            "attention_sites": attention,
            "sites_overview": overview,
        }
        row_count = len(attention.get("sites", [])) + len(overview.get("sites", []))
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=row_count)


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

        # Get actual study duration from study_config for monthly cost calculation
        study_config = db_session.query(StudyConfig).first()
        study_start = study_config.study_start_date if study_config else None

        data = []
        for m in metrics:
            enrolled = enrollment_counts.get(m.site_id, 0)
            target = site_targets.get(m.site_id, 0)
            enrollment_gap = max(0, target - enrolled)

            # Calculate monthly cost from actual study duration, not a hardcoded assumption
            cost_to_date = m.cost_to_date or 0
            planned = m.planned_cost_to_date or 0
            over_plan = cost_to_date - planned
            months_active = 1
            if study_start and m.snapshot_date:
                delta = (m.snapshot_date - study_start).days
                months_active = max(delta / 30.44, 1)
            monthly_site_cost = cost_to_date / months_active

            # Estimated delay cost: each unfilled patient slot extends the site for
            # (1 / site's historical monthly enrollment rate) additional months
            monthly_enrollment = enrolled / months_active if months_active > 0 else 0
            if monthly_enrollment > 0 and enrollment_gap > 0:
                additional_months = enrollment_gap / monthly_enrollment
                estimated_delay_cost = additional_months * monthly_site_cost
                delay_formula = (
                    f"({enrollment_gap} gap ÷ {round(monthly_enrollment, 1)} pts/mo = "
                    f"{round(additional_months, 1)} extra months × "
                    f"${round(monthly_site_cost, 0)}/mo) = ${round(estimated_delay_cost, 0)}"
                )
            else:
                estimated_delay_cost = 0
                delay_formula = "Insufficient enrollment history for projection"

            # Include all sites with meaningful data (not just variance > 5%)
            if enrollment_gap > 0 or over_plan > 0:
                data.append({
                    "site_id": m.site_id,
                    "site_name": site_names.get(m.site_id),
                    "cost_to_date": cost_to_date,
                    "planned_cost_to_date": planned,
                    "over_plan_amount": round(over_plan, 2),
                    "variance_pct": m.variance_pct,
                    "months_active": round(months_active, 1),
                    "monthly_site_cost": round(monthly_site_cost, 2),
                    "enrolled": enrolled,
                    "target": target,
                    "enrollment_gap": enrollment_gap,
                    "monthly_enrollment_rate": round(monthly_enrollment, 2),
                    "estimated_delay_cost": round(estimated_delay_cost, 2),
                    "delay_cost_formula": delay_formula,
                    "cost_per_randomized": m.cost_per_patient_randomized,
                    "data_source": "site_financial_metrics + study_config tables",
                })

        data.sort(key=lambda x: x.get("estimated_delay_cost", 0), reverse=True)
        return ToolResult(tool_name=self.name, success=True, data=data[:30], row_count=len(data))


class VisitComplianceAnalysisTool(BaseTool):
    name = "visit_compliance_analysis"
    description = (
        "Per-site visit compliance analysis: completed, missed, and pending visit counts, "
        "compliance rate (% completed), and average visit delay (actual vs planned date). "
        "Joins SubjectVisit to ScreeningLog to resolve site_id. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        # SubjectVisit doesn't have site_id directly — join via subject_id → ScreeningLog
        q = db_session.query(
            ScreeningLog.site_id,
            func.count(SubjectVisit.id).label("total_visits"),
            func.sum(case((SubjectVisit.visit_status == "Completed", 1), else_=0)).label("completed"),
            func.sum(case((SubjectVisit.visit_status == "Missed", 1), else_=0)).label("missed"),
            func.sum(case((SubjectVisit.visit_status == "Pending", 1), else_=0)).label("pending"),
        ).join(
            ScreeningLog, SubjectVisit.subject_id == ScreeningLog.subject_id,
        ).group_by(ScreeningLog.site_id)
        if site_id:
            q = q.filter(ScreeningLog.site_id == site_id)
        rows = q.all()

        # Separate query for visit delay (only where both dates exist)
        delay_q = db_session.query(
            ScreeningLog.site_id,
            func.avg(SubjectVisit.actual_date - SubjectVisit.planned_date).label("avg_delay_days"),
        ).join(
            ScreeningLog, SubjectVisit.subject_id == ScreeningLog.subject_id,
        ).filter(
            SubjectVisit.actual_date.isnot(None),
            SubjectVisit.planned_date.isnot(None),
        ).group_by(ScreeningLog.site_id)
        if site_id:
            delay_q = delay_q.filter(ScreeningLog.site_id == site_id)
        delay_map = {r.site_id: r.avg_delay_days for r in delay_q.all()}

        data = []
        for r in rows:
            total = r.total_visits or 0
            completed = r.completed or 0
            missed = r.missed or 0
            compliance_rate = round(completed / total * 100, 1) if total > 0 else 0
            avg_delay = delay_map.get(r.site_id)
            if avg_delay is not None:
                try:
                    avg_delay = round(float(avg_delay), 1)
                except (TypeError, ValueError):
                    avg_delay = None
            data.append({
                "site_id": r.site_id,
                "total_visits": total,
                "completed": completed,
                "missed": missed,
                "pending": r.pending or 0,
                "compliance_rate_pct": compliance_rate,
                "avg_visit_delay_days": avg_delay,
                "missed_visit_flag": missed > total * 0.15,
            })
        data.sort(key=lambda x: x["compliance_rate_pct"])
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class OverdueActionSummaryTool(BaseTool):
    name = "overdue_action_summary"
    description = (
        "Study-wide overdue action analysis: per-site counts of total, overdue, and completed "
        "follow-up actions from monitoring visits, broken down by category. "
        "Identifies sites with chronic action item backlogs. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")

        q = db_session.query(
            OverdueAction.site_id,
            OverdueAction.category,
            func.count(OverdueAction.id).label("total_actions"),
            func.sum(case((OverdueAction.status == "Overdue", 1), else_=0)).label("overdue_count"),
            func.sum(case((OverdueAction.status == "Completed", 1), else_=0)).label("completed_count"),
            func.sum(case((OverdueAction.status == "Open", 1), else_=0)).label("open_count"),
        ).group_by(OverdueAction.site_id, OverdueAction.category)
        if site_id:
            q = q.filter(OverdueAction.site_id == site_id)
        rows = q.all()

        data = []
        for r in rows:
            total = r.total_actions or 0
            overdue = r.overdue_count or 0
            completed = r.completed_count or 0
            resolution_rate = round(completed / total * 100, 1) if total > 0 else 0
            data.append({
                "site_id": r.site_id,
                "category": r.category,
                "total_actions": total,
                "overdue_count": overdue,
                "open_count": r.open_count or 0,
                "completed_count": completed,
                "resolution_rate_pct": resolution_rate,
                "chronic_backlog_flag": overdue > 3,
            })
        data.sort(key=lambda x: x["overdue_count"], reverse=True)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


# ═══════════════════════════════════════════════════════════════════════════════
# MVR ANALYSIS TOOLS (Monitoring Visit Report narrative analysis)
# ═══════════════════════════════════════════════════════════════════════════════

class MVRNarrativeSearchTool(BaseTool):
    name = "mvr_narrative_search"
    description = (
        "Returns MVR narrative content: executive_summary, overall_impression, cra_assessment, "
        "findings (checklist items with action_required), urgent_issues, pi_engagement, sdv_findings, "
        "follow_up_from_prior, word_count, action_required_count for monitoring visit reports. "
        "Args: site_id (optional), cra_id (optional), limit (optional, default 50), "
        "date_from/date_to (optional date filters)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        cra_id = kwargs.get("cra_id")
        limit = kwargs.get("limit", 50)
        date_from = kwargs.get("date_from")
        date_to = kwargs.get("date_to")

        q = db_session.query(MonitoringVisitReport).order_by(
            MonitoringVisitReport.site_id, MonitoringVisitReport.visit_date
        )
        if site_id:
            q = q.filter(MonitoringVisitReport.site_id == site_id)
        if cra_id:
            q = q.filter(MonitoringVisitReport.cra_id == cra_id)
        if date_from:
            q = q.filter(MonitoringVisitReport.visit_date >= date_from)
        if date_to:
            q = q.filter(MonitoringVisitReport.visit_date <= date_to)

        rows = q.limit(limit).all()
        data = []
        for r in rows:
            data.append({
                "site_id": r.site_id,
                "cra_id": r.cra_id,
                "visit_date": r.visit_date.isoformat() if r.visit_date else "",
                "visit_number": r.visit_number,
                "visit_type": r.visit_type,
                "executive_summary": r.executive_summary,
                "overall_impression": r.overall_impression,
                "urgent_issues": r.urgent_issues or [],
                "findings": r.findings or [],
                "sdv_findings": r.sdv_findings or [],
                "pi_engagement": r.pi_engagement or {},
                "follow_up_from_prior": r.follow_up_from_prior or [],
                "cra_assessment": r.cra_assessment,
                "word_count": r.word_count,
                "action_required_count": r.action_required_count,
            })
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class MVRCRAPortfolioTool(BaseTool):
    name = "mvr_cra_portfolio"
    description = (
        "Per-CRA MVR aggregates: average word_count, average action_required_count, "
        "zero-finding visit percentage, total visits, sites monitored. "
        "Identifies CRAs with suspiciously uniform or superficial reports. "
        "Args: cra_id (optional — if omitted, returns all CRAs)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        cra_id = kwargs.get("cra_id")

        q = db_session.query(
            MonitoringVisitReport.cra_id,
            func.count(MonitoringVisitReport.id).label("total_visits"),
            func.avg(MonitoringVisitReport.word_count).label("avg_word_count"),
            func.avg(MonitoringVisitReport.action_required_count).label("avg_action_count"),
            func.sum(case((MonitoringVisitReport.action_required_count == 0, 1), else_=0)).label("zero_finding_visits"),
            func.count(func.distinct(MonitoringVisitReport.site_id)).label("sites_monitored"),
            func.min(MonitoringVisitReport.visit_date).label("first_visit"),
            func.max(MonitoringVisitReport.visit_date).label("last_visit"),
        ).group_by(MonitoringVisitReport.cra_id)

        if cra_id:
            q = q.filter(MonitoringVisitReport.cra_id == cra_id)

        rows = q.all()
        data = []
        for r in rows:
            total = r.total_visits or 1
            zero_pct = round((r.zero_finding_visits or 0) / total * 100, 1)
            data.append({
                "cra_id": r.cra_id,
                "total_visits": total,
                "avg_word_count": round(float(r.avg_word_count or 0), 0),
                "avg_action_required_count": round(float(r.avg_action_count or 0), 1),
                "zero_finding_visit_pct": zero_pct,
                "sites_monitored": r.sites_monitored,
                "first_visit": r.first_visit.isoformat() if r.first_visit else "",
                "last_visit": r.last_visit.isoformat() if r.last_visit else "",
                "rubber_stamp_flag": zero_pct > 80 and total >= 3,
            })
        data.sort(key=lambda x: x["zero_finding_visit_pct"], reverse=True)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class MVRRecurrenceAnalysisTool(BaseTool):
    name = "mvr_recurrence_analysis"
    description = (
        "Finds checklist items with action_required that recur in the same section across "
        "non-consecutive visits for a site — zombie findings that keep reappearing despite resolution. "
        "Args: site_id (required), section (optional — filter to specific checklist section)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        section_filter = kwargs.get("section")

        if not site_id:
            return ToolResult(tool_name=self.name, success=False, error="site_id is required")

        # Get all MVRs for this site ordered by visit date
        mvrs = db_session.query(MonitoringVisitReport).filter(
            MonitoringVisitReport.site_id == site_id
        ).order_by(MonitoringVisitReport.visit_date).all()

        if not mvrs:
            return ToolResult(tool_name=self.name, success=True, data=[], row_count=0)

        # Track findings by section across visits
        section_history: dict[str, list[dict]] = {}
        for mvr in mvrs:
            findings = mvr.findings or []
            for f in findings:
                if not f.get("action_required"):
                    continue
                section = f.get("section", "Unknown")
                if section_filter and section != section_filter:
                    continue
                if section not in section_history:
                    section_history[section] = []
                section_history[section].append({
                    "visit_date": mvr.visit_date.isoformat() if mvr.visit_date else "",
                    "visit_number": mvr.visit_number,
                    "item_number": f.get("item_number"),
                    "question": f.get("question"),
                    "action_required": f.get("action_required"),
                })

        # Detect recurrence: same section appearing in 2+ non-consecutive visits
        recurrences = []
        for section, occurrences in section_history.items():
            if len(occurrences) >= 2:
                recurrences.append({
                    "site_id": site_id,
                    "section": section,
                    "occurrence_count": len(occurrences),
                    "occurrences": occurrences,
                    "zombie_flag": len(occurrences) >= 3,
                    "pattern": "recurring" if len(occurrences) >= 2 else "isolated",
                })

        # Also check follow_up_from_prior for items that go resolved → reappear
        follow_up_patterns = []
        for i, mvr in enumerate(mvrs):
            follow_ups = mvr.follow_up_from_prior or []
            for fu in follow_ups:
                if fu.get("status") == "Resolved":
                    # Check if a similar finding appears in later visits
                    action_text = fu.get("action", "").lower()
                    for later_mvr in mvrs[i+1:]:
                        later_findings = later_mvr.findings or []
                        for lf in later_findings:
                            if lf.get("action_required") and any(
                                word in (lf.get("action_required", "") + " " + lf.get("question", "")).lower()
                                for word in action_text.split()[:3]
                                if len(word) > 4
                            ):
                                follow_up_patterns.append({
                                    "resolved_visit_date": mvr.visit_date.isoformat(),
                                    "resolved_action": fu.get("action"),
                                    "reappeared_visit_date": later_mvr.visit_date.isoformat(),
                                    "reappeared_finding": lf.get("action_required"),
                                    "zombie_confirmed": True,
                                })
                                break

        data = {
            "site_id": site_id,
            "section_recurrences": recurrences,
            "follow_up_zombie_patterns": follow_up_patterns,
            "total_recurring_sections": len(recurrences),
            "total_zombie_patterns": len(follow_up_patterns),
        }
        return ToolResult(tool_name=self.name, success=True, data=[data], row_count=1)


class MVRTemporalPatternTool(BaseTool):
    name = "mvr_temporal_pattern"
    description = (
        "Time-series MVR metrics for a site: pi_engagement trajectory, action_required_count trend, "
        "word_count trend, finding severity over visits. Reveals temporal patterns like PI engagement "
        "decline, post-gap finding spikes, or CRA quality changes. "
        "Args: site_id (required)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        if not site_id:
            return ToolResult(tool_name=self.name, success=False, error="site_id is required")

        mvrs = db_session.query(MonitoringVisitReport).filter(
            MonitoringVisitReport.site_id == site_id
        ).order_by(MonitoringVisitReport.visit_date).all()

        if not mvrs:
            return ToolResult(tool_name=self.name, success=True, data=[], row_count=0)

        timeline = []
        for mvr in mvrs:
            pi = mvr.pi_engagement or {}
            timeline.append({
                "visit_date": mvr.visit_date.isoformat() if mvr.visit_date else "",
                "visit_number": mvr.visit_number,
                "cra_id": mvr.cra_id,
                "word_count": mvr.word_count,
                "action_required_count": mvr.action_required_count,
                "pi_present": pi.get("pi_present"),
                "pi_engagement_quality": pi.get("engagement_quality"),
                "pi_notes": pi.get("notes", ""),
                "urgent_issue_count": len(mvr.urgent_issues or []),
                "finding_count": len(mvr.findings or []),
                "sdv_finding_count": len(mvr.sdv_findings or []),
                "follow_up_open_count": sum(
                    1 for f in (mvr.follow_up_from_prior or [])
                    if f.get("status") in ("Open", "Partially Resolved")
                ),
            })

        # Compute trends
        word_counts = [t["word_count"] for t in timeline if t["word_count"]]
        action_counts = [t["action_required_count"] for t in timeline if t["action_required_count"] is not None]

        # Detect CRA changes
        cra_changes = []
        for i in range(1, len(timeline)):
            if timeline[i]["cra_id"] != timeline[i-1]["cra_id"]:
                cra_changes.append({
                    "change_date": timeline[i]["visit_date"],
                    "from_cra": timeline[i-1]["cra_id"],
                    "to_cra": timeline[i]["cra_id"],
                    "visit_number": timeline[i]["visit_number"],
                })

        data = {
            "site_id": site_id,
            "timeline": timeline,
            "total_visits": len(timeline),
            "avg_word_count": round(sum(word_counts) / len(word_counts), 0) if word_counts else 0,
            "avg_action_count": round(sum(action_counts) / len(action_counts), 1) if action_counts else 0,
            "cra_changes": cra_changes,
            "word_count_trend": "declining" if len(word_counts) >= 3 and word_counts[-1] < word_counts[0] * 0.7 else
                               "increasing" if len(word_counts) >= 3 and word_counts[-1] > word_counts[0] * 1.3 else "stable",
            "action_count_trend": "escalating" if len(action_counts) >= 3 and action_counts[-1] > action_counts[0] * 1.5 else
                                  "improving" if len(action_counts) >= 3 and action_counts[-1] < action_counts[0] * 0.5 else "stable",
        }
        return ToolResult(tool_name=self.name, success=True, data=[data], row_count=1)


class MVRCrossSiteComparisonTool(BaseTool):
    name = "mvr_cross_site_comparison"
    description = (
        "Comparative MVR metrics across sites: avg word_count, avg action_required_count, "
        "zero-finding visit %, pi_engagement quality distribution. "
        "Filters by CRA, country, or specific site list. "
        "Args: cra_id (optional), country (optional), site_ids (optional, comma-separated)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        cra_id = kwargs.get("cra_id")
        country = kwargs.get("country")
        site_ids_str = kwargs.get("site_ids", "")

        q = db_session.query(
            MonitoringVisitReport.site_id,
            func.count(MonitoringVisitReport.id).label("total_visits"),
            func.avg(MonitoringVisitReport.word_count).label("avg_word_count"),
            func.avg(MonitoringVisitReport.action_required_count).label("avg_action_count"),
            func.sum(case((MonitoringVisitReport.action_required_count == 0, 1), else_=0)).label("zero_finding_visits"),
        ).group_by(MonitoringVisitReport.site_id)

        if cra_id:
            q = q.filter(MonitoringVisitReport.cra_id == cra_id)
        if country:
            # Join with Site table to filter by country
            q = q.join(Site, Site.site_id == MonitoringVisitReport.site_id).filter(Site.country == country)
        if site_ids_str:
            site_ids = [s.strip() for s in site_ids_str.split(",")]
            q = q.filter(MonitoringVisitReport.site_id.in_(site_ids))

        rows = q.all()
        data = []
        for r in rows:
            total = r.total_visits or 1
            zero_pct = round((r.zero_finding_visits or 0) / total * 100, 1)
            data.append({
                "site_id": r.site_id,
                "total_visits": total,
                "avg_word_count": round(float(r.avg_word_count or 0), 0),
                "avg_action_required_count": round(float(r.avg_action_count or 0), 1),
                "zero_finding_visit_pct": zero_pct,
            })

        # Add PI engagement distribution per site
        for entry in data:
            pi_mvrs = db_session.query(MonitoringVisitReport).filter(
                MonitoringVisitReport.site_id == entry["site_id"]
            ).all()
            pi_qualities = []
            for mvr in pi_mvrs:
                pi = mvr.pi_engagement or {}
                quality = pi.get("engagement_quality", "unknown")
                pi_qualities.append(quality)
            entry["pi_engagement_distribution"] = {
                q: pi_qualities.count(q) for q in set(pi_qualities)
            } if pi_qualities else {}

        data.sort(key=lambda x: x["avg_word_count"])
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


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
    registry.register(MonitoringVisitReportTool())
    registry.register(SiteSummaryTool())
    registry.register(VisitComplianceAnalysisTool())
    registry.register(OverdueActionSummaryTool())
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
    # Fraud Detection tools (Advanced Data Integrity)
    registry.register(WeekdayEntryPatternTool())
    registry.register(CRAOversightGapTool())
    registry.register(CRAPortfolioAnalysisTool())
    registry.register(CorrectionProvenanceTool())
    registry.register(EntryDateClusteringTool())
    registry.register(ScreeningNarrativeDuplicationTool())
    registry.register(CrossDomainConsistencyTool())
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
    # Study-wide operational snapshot (shared data layer)
    registry.register(StudyOperationalSnapshotTool())
    # MVR Analysis tools (Monitoring Visit Report narratives)
    registry.register(MVRNarrativeSearchTool())
    registry.register(MVRCRAPortfolioTool())
    registry.register(MVRRecurrenceAnalysisTool())
    registry.register(MVRTemporalPatternTool())
    registry.register(MVRCrossSiteComparisonTool())
    # Competitive intelligence tools (BioMCP-powered) - optional
    try:
        from backend.tools.ctgov_tools import CompetingTrialSearchTool, TrialDetailTool, BIOMCP_AVAILABLE
        if BIOMCP_AVAILABLE:
            registry.register(CompetingTrialSearchTool())
            registry.register(TrialDetailTool())
    except ImportError:
        pass  # ClinicalTrials.gov tools not available
    return registry
