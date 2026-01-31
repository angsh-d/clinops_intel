"""SQLAlchemy ORM models for all 23 tables in clinops_intel."""

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── 1. study_config ──────────────────────────────────────────────────────────
class StudyConfig(Base):
    __tablename__ = "study_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(String(50), nullable=False)
    nct_number = Column(String(20))
    phase = Column(String(20))
    target_enrollment = Column(Integer)
    planned_sites = Column(Integer)
    cycle_length_days = Column(Integer)
    max_cycles = Column(Integer)
    screening_window_days = Column(Integer)
    countries = Column(JSONB)
    study_start_date = Column(Date)


# ── 2. study_arms ────────────────────────────────────────────────────────────
class StudyArm(Base):
    __tablename__ = "study_arms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    arm_code = Column(String(20), nullable=False, unique=True)
    arm_name = Column(String(200))
    arm_type = Column(String(50))
    allocation_ratio = Column(Float, default=0.5)


# ── 3. stratification_factors ────────────────────────────────────────────────
class StratificationFactor(Base):
    __tablename__ = "stratification_factors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_name = Column(String(100), nullable=False)
    factor_levels = Column(JSONB)


# ── 4. visit_schedule ────────────────────────────────────────────────────────
class VisitSchedule(Base):
    __tablename__ = "visit_schedule"
    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(String(20), nullable=False, unique=True)
    visit_name = Column(String(100))
    visit_type = Column(String(50))
    timing_value = Column(Integer)
    timing_unit = Column(String(20))
    timing_relative_to = Column(String(50))
    window_early_bound = Column(Integer)
    window_late_bound = Column(Integer)
    recurrence_pattern = Column(String(50))


# ── 5. visit_activities ──────────────────────────────────────────────────────
class VisitActivity(Base):
    __tablename__ = "visit_activities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(String(20), nullable=False)
    activity_id = Column(String(20), nullable=False)
    activity_name = Column(String(200))
    is_required = Column(Boolean, default=True)


# ── 6. eligibility_criteria ──────────────────────────────────────────────────
class EligibilityCriterion(Base):
    __tablename__ = "eligibility_criteria"
    id = Column(Integer, primary_key=True, autoincrement=True)
    criterion_id = Column(String(20), nullable=False, unique=True)
    type = Column(String(20))  # Inclusion / Exclusion
    original_text = Column(Text)
    short_label = Column(String(200))


# ── 7. screen_failure_reason_codes ───────────────────────────────────────────
class ScreenFailureReasonCode(Base):
    __tablename__ = "screen_failure_reason_codes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    reason_code = Column(String(30), nullable=False, unique=True)
    description = Column(String(300))
    criterion_id = Column(String(20))
    category = Column(String(50))


# ── 8. sites ─────────────────────────────────────────────────────────────────
class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False, unique=True)
    country = Column(String(3))
    city = Column(String(100))
    site_type = Column(String(30))
    experience_level = Column(String(20))
    activation_date = Column(Date)
    target_enrollment = Column(Integer)
    anomaly_type = Column(String(50))
    __table_args__ = (Index("ix_sites_country", "country"),)


# ── 9. cra_assignments ───────────────────────────────────────────────────────
class CRAAssignment(Base):
    __tablename__ = "cra_assignments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cra_id = Column(String(20), nullable=False)
    site_id = Column(String(20), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    is_current = Column(Boolean, default=True)
    __table_args__ = (Index("ix_cra_site", "site_id"),)


# ── 10a. drug_kit_types ──────────────────────────────────────────────────────
class DrugKitType(Base):
    __tablename__ = "drug_kit_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    kit_type_id = Column(String(20), nullable=False, unique=True)
    kit_name = Column(String(200))
    arm_code = Column(String(20))
    storage_conditions = Column(String(200))
    shelf_life_days = Column(Integer, default=365)


# ── 10b. depots ──────────────────────────────────────────────────────────────
class Depot(Base):
    __tablename__ = "depots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    depot_id = Column(String(20), nullable=False, unique=True)
    depot_name = Column(String(100))
    country = Column(String(3))
    city = Column(String(100))
    standard_shipping_days = Column(Integer)


# ── 11. screening_log ────────────────────────────────────────────────────────
class ScreeningLog(Base):
    __tablename__ = "screening_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False)
    subject_id = Column(String(30), nullable=False, unique=True)
    screening_date = Column(Date, nullable=False)
    outcome = Column(String(20))  # Passed / Failed / Withdrawn
    failure_reason_code = Column(String(30))
    failure_reason_narrative = Column(Text)
    __table_args__ = (
        Index("ix_screening_site", "site_id"),
        Index("ix_screening_date", "screening_date"),
    )


# ── 12. randomization_log ───────────────────────────────────────────────────
class RandomizationLog(Base):
    __tablename__ = "randomization_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(String(30), nullable=False, unique=True)
    site_id = Column(String(20), nullable=False)
    randomization_date = Column(Date, nullable=False)
    arm_code = Column(String(20))
    stratum_gender = Column(String(10))
    stratum_ecog = Column(String(5))
    __table_args__ = (Index("ix_rand_site", "site_id"),)


# ── 13. enrollment_velocity ──────────────────────────────────────────────────
class EnrollmentVelocity(Base):
    __tablename__ = "enrollment_velocity"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False)
    week_start = Column(Date, nullable=False)
    week_number = Column(Integer)
    screened_count = Column(Integer, default=0)
    screen_failed_count = Column(Integer, default=0)
    randomized_count = Column(Integer, default=0)
    cumulative_screened = Column(Integer, default=0)
    cumulative_randomized = Column(Integer, default=0)
    target_cumulative = Column(Integer, default=0)
    __table_args__ = (Index("ix_velocity_site_week", "site_id", "week_number"),)


# ── 14. subject_visits ───────────────────────────────────────────────────────
class SubjectVisit(Base):
    __tablename__ = "subject_visits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(String(30), nullable=False)
    visit_id = Column(String(20), nullable=False)
    cycle_number = Column(Integer)
    planned_date = Column(Date)
    actual_date = Column(Date)
    visit_status = Column(String(20))  # Completed / Missed / Pending
    __table_args__ = (
        Index("ix_sv_subject", "subject_id"),
        Index("ix_sv_visit", "visit_id"),
    )


# ── 15. ecrf_entries ─────────────────────────────────────────────────────────
class ECRFEntry(Base):
    __tablename__ = "ecrf_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_visit_id = Column(Integer, nullable=False)
    subject_id = Column(String(30), nullable=False)
    site_id = Column(String(20), nullable=False)
    crf_page_name = Column(String(50))
    visit_date = Column(Date)
    entry_date = Column(Date)
    entry_lag_days = Column(Integer)
    completeness_pct = Column(Float)
    has_missing_critical = Column(Boolean, default=False)
    missing_field_count = Column(Integer, default=0)
    __table_args__ = (
        Index("ix_ecrf_site", "site_id"),
        Index("ix_ecrf_subject", "subject_id"),
    )


# ── 16. queries ──────────────────────────────────────────────────────────────
class Query(Base):
    __tablename__ = "queries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False)
    subject_id = Column(String(30), nullable=False)
    crf_page_name = Column(String(50))
    query_type = Column(String(30))
    open_date = Column(Date)
    response_date = Column(Date)
    close_date = Column(Date)
    status = Column(String(20))  # Open / Answered / Closed
    age_days = Column(Integer)
    priority = Column(String(10))
    triggered_by = Column(String(50))
    __table_args__ = (
        Index("ix_queries_site", "site_id"),
        Index("ix_queries_subject", "subject_id"),
        Index("ix_queries_open", "open_date"),
    )


# ── 17. data_corrections ────────────────────────────────────────────────────
class DataCorrection(Base):
    __tablename__ = "data_corrections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False)
    subject_id = Column(String(30), nullable=False)
    crf_page_name = Column(String(50))
    field_name = Column(String(100))
    old_value = Column(String(200))
    new_value = Column(String(200))
    correction_date = Column(Date)
    triggered_by_query_id = Column(Integer)
    __table_args__ = (Index("ix_corrections_site", "site_id"),)


# ── 18. monitoring_visits ────────────────────────────────────────────────────
class MonitoringVisit(Base):
    __tablename__ = "monitoring_visits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False)
    cra_id = Column(String(20))
    planned_date = Column(Date)
    actual_date = Column(Date)
    visit_type = Column(String(20))  # On-Site / Remote
    findings_count = Column(Integer, default=0)
    critical_findings = Column(Integer, default=0)
    queries_generated = Column(Integer, default=0)
    days_overdue = Column(Integer, default=0)
    status = Column(String(20), default="Completed")
    __table_args__ = (Index("ix_monvisit_site", "site_id"),)


# ── 19. kri_snapshots ───────────────────────────────────────────────────────
class KRISnapshot(Base):
    __tablename__ = "kri_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    kri_name = Column(String(100))
    kri_value = Column(Float)
    amber_threshold = Column(Float)
    red_threshold = Column(Float)
    status = Column(String(10))  # Green / Amber / Red
    __table_args__ = (Index("ix_kri_site_date", "site_id", "snapshot_date"),)


# ── 20. overdue_actions ──────────────────────────────────────────────────────
class OverdueAction(Base):
    __tablename__ = "overdue_actions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False)
    monitoring_visit_id = Column(Integer)
    action_description = Column(Text)
    category = Column(String(50))
    due_date = Column(Date)
    completion_date = Column(Date)
    status = Column(String(20))  # Open / Completed / Overdue
    __table_args__ = (Index("ix_overdue_site", "site_id"),)


# ── 21. kit_inventory ────────────────────────────────────────────────────────
class KitInventory(Base):
    __tablename__ = "kit_inventory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(20), nullable=False)
    kit_type_id = Column(String(20), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    quantity_on_hand = Column(Integer)
    reorder_level = Column(Integer, default=3)
    is_below_reorder = Column(Boolean, default=False)
    __table_args__ = (Index("ix_kit_site_date", "site_id", "snapshot_date"),)


# ── 22. randomization_events ────────────────────────────────────────────────
class RandomizationEvent(Base):
    __tablename__ = "randomization_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(String(30), nullable=False)
    site_id = Column(String(20), nullable=False)
    event_date = Column(Date)
    event_type = Column(String(20))  # Success / Delay / Failure
    delay_reason = Column(String(100))
    delay_duration_hours = Column(Integer)
    __table_args__ = (Index("ix_randevt_site", "site_id"),)


# ── 23. depot_shipments ──────────────────────────────────────────────────────
class DepotShipment(Base):
    __tablename__ = "depot_shipments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    depot_id = Column(String(20), nullable=False)
    site_id = Column(String(20), nullable=False)
    kit_type_id = Column(String(20), nullable=False)
    shipment_date = Column(Date)
    expected_arrival = Column(Date)
    actual_arrival = Column(Date)
    kit_count = Column(Integer)
    status = Column(String(20))  # Delivered / In-Transit / Delayed
    delay_reason = Column(String(200))
    __table_args__ = (Index("ix_shipment_site", "site_id"),)
