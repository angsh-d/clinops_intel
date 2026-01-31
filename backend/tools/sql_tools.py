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
)
from backend.tools.base import BaseTool, ToolResult


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

        rows = q.all()
        data = _serialize_rows(rows)
        return ToolResult(tool_name=self.name, success=True, data=data, row_count=len(data))


class QueryBurdenTool(BaseTool):
    name = "query_burden"
    description = (
        "Analyzes query counts, aging, types, and status by site. "
        "Returns open/answered/closed counts, aging distribution, query types. "
        "Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        q = db_session.query(
            Query.site_id,
            Query.status,
            Query.query_type,
            Query.priority,
            func.count(Query.id).label("query_count"),
            func.avg(Query.age_days).label("mean_age"),
            func.max(Query.age_days).label("max_age"),
            func.sum(case((Query.age_days > 14, 1), else_=0)).label("aging_over_14d"),
            func.sum(case((Query.age_days > 30, 1), else_=0)).label("aging_over_30d"),
        ).group_by(Query.site_id, Query.status, Query.query_type, Query.priority)

        if site_id:
            q = q.filter(Query.site_id == site_id)

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
        "target enrollment, anomaly type (if any). Args: site_id (optional), country (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        country = kwargs.get("country")
        q = db_session.query(
            Site.site_id, Site.country, Site.city, Site.site_type,
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
        "failure rate. Provides per-site funnel decomposition. Args: site_id (optional)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        q = db_session.query(
            ScreeningLog.site_id,
            func.count(ScreeningLog.id).label("total_screened"),
            func.sum(case((ScreeningLog.outcome == "Passed", 1), else_=0)).label("passed"),
            func.sum(case((ScreeningLog.outcome == "Failed", 1), else_=0)).label("failed"),
            func.sum(case((ScreeningLog.outcome == "Withdrawn", 1), else_=0)).label("withdrawn"),
        ).group_by(ScreeningLog.site_id)

        if site_id:
            q = q.filter(ScreeningLog.site_id == site_id)

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
        "Args: site_id (optional), include_narratives (bool, default false)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        site_id = kwargs.get("site_id")
        include_narratives = kwargs.get("include_narratives", False)

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
            narratives = nq.limit(200).all()
            result["narratives"] = _serialize_rows(narratives)

        return ToolResult(tool_name=self.name, success=True, data=result, row_count=len(data))


class RegionalComparisonTool(BaseTool):
    name = "regional_comparison"
    description = (
        "Compares enrollment and screening metrics across sites in the same country/region. "
        "Detects regional cluster patterns. Args: country (optional), site_ids (optional, comma-separated)."
    )

    async def execute(self, db_session: Session, **kwargs) -> ToolResult:
        country = kwargs.get("country")
        site_ids_str = kwargs.get("site_ids")

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
        screening = db_session.query(
            ScreeningLog.site_id,
            func.count(ScreeningLog.id).label("total_screened"),
            func.sum(case((ScreeningLog.outcome == "Failed", 1), else_=0)).label("failed"),
            func.sum(case((ScreeningLog.outcome == "Passed", 1), else_=0)).label("passed"),
        ).filter(ScreeningLog.site_id.in_(site_list)).group_by(ScreeningLog.site_id).all()

        # Randomization counts
        randomization = db_session.query(
            RandomizationLog.site_id,
            func.count(RandomizationLog.id).label("randomized"),
        ).filter(RandomizationLog.site_id.in_(site_list)).group_by(RandomizationLog.site_id).all()

        data = {
            "sites": _serialize_rows(sites),
            "screening": _serialize_rows(screening),
            "randomization": _serialize_rows(randomization),
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
    # Cross-domain tools
    registry.register(ContextSearchTool())
    registry.register(TrendProjectionTool())
    return registry
