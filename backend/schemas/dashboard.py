"""Pydantic schemas for dashboard endpoints (pure SQL, no LLM)."""

from pydantic import BaseModel
from typing import Any
from datetime import date, datetime


class SiteDataQualityMetrics(BaseModel):
    site_id: str
    mean_entry_lag: float | None
    total_queries: int
    open_queries: int
    aging_over_14d: int
    correction_count: int
    missing_critical_count: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "site_id": "SITE-001",
                    "mean_entry_lag": 3.2,
                    "total_queries": 45,
                    "open_queries": 12,
                    "aging_over_14d": 3,
                    "correction_count": 8,
                    "missing_critical_count": 2,
                }
            ]
        }
    }


class DataQualityDashboard(BaseModel):
    sites: list[SiteDataQualityMetrics]
    study_mean_entry_lag: float | None
    study_total_queries: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sites": [
                        {
                            "site_id": "SITE-001",
                            "mean_entry_lag": 3.2,
                            "total_queries": 45,
                            "open_queries": 12,
                            "aging_over_14d": 3,
                            "correction_count": 8,
                            "missing_critical_count": 2,
                        }
                    ],
                    "study_mean_entry_lag": 4.1,
                    "study_total_queries": 230,
                }
            ]
        }
    }


class SiteEnrollmentMetrics(BaseModel):
    site_id: str
    total_screened: int
    total_passed: int
    total_failed: int
    failure_rate_pct: float
    randomized: int
    target: int
    pct_of_target: float

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "site_id": "SITE-001",
                    "total_screened": 120,
                    "total_passed": 95,
                    "total_failed": 25,
                    "failure_rate_pct": 20.8,
                    "randomized": 80,
                    "target": 100,
                    "pct_of_target": 80.0,
                }
            ]
        }
    }


class EnrollmentDashboard(BaseModel):
    sites: list[SiteEnrollmentMetrics]
    study_total_screened: int
    study_total_randomized: int
    study_target: int
    study_pct_of_target: float

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sites": [
                        {
                            "site_id": "SITE-001",
                            "total_screened": 120,
                            "total_passed": 95,
                            "total_failed": 25,
                            "failure_rate_pct": 20.8,
                            "randomized": 80,
                            "target": 100,
                            "pct_of_target": 80.0,
                        }
                    ],
                    "study_total_screened": 600,
                    "study_total_randomized": 420,
                    "study_target": 595,
                    "study_pct_of_target": 70.6,
                }
            ]
        }
    }


# ── Site Metadata ────────────────────────────────────────────────────────────

class CRAAssignmentSchema(BaseModel):
    cra_id: str
    start_date: str | None
    end_date: str | None
    is_current: bool

    model_config = {"from_attributes": True}


class MonitoringVisitSchema(BaseModel):
    visit_date: str | None
    visit_type: str | None
    findings_count: int
    critical_findings: int
    days_overdue: int
    status: str | None

    model_config = {"from_attributes": True}


class SiteMetadata(BaseModel):
    site_id: str
    country: str | None
    city: str | None
    site_type: str | None
    experience_level: str | None
    activation_date: str | None
    target_enrollment: int
    anomaly_type: str | None
    cra_assignments: list[CRAAssignmentSchema]
    monitoring_visits: list[MonitoringVisitSchema]

    model_config = {"from_attributes": True}


class SiteMetadataResponse(BaseModel):
    sites: list[SiteMetadata]


# ── KRI Time Series ──────────────────────────────────────────────────────────

class KRIDataPoint(BaseModel):
    snapshot_date: str
    kri_name: str
    kri_value: float
    amber_threshold: float | None
    red_threshold: float | None
    status: str | None

    model_config = {"from_attributes": True}


class KRITimeSeriesResponse(BaseModel):
    site_id: str
    data: list[KRIDataPoint]


# ── Enrollment Velocity Time Series ──────────────────────────────────────────

class VelocityDataPoint(BaseModel):
    week_start: str
    week_number: int
    screened_count: int
    randomized_count: int
    cumulative_screened: int
    cumulative_randomized: int
    target_cumulative: int

    model_config = {"from_attributes": True}


class EnrollmentVelocityResponse(BaseModel):
    site_id: str
    data: list[VelocityDataPoint]


# ── Enhanced Alert Detail (with investigation trace) ─────────────────────────

class AlertDetailEnhanced(BaseModel):
    id: int
    finding_id: int | None
    agent_id: str
    severity: str
    site_id: str | None
    title: str
    description: str | None
    status: str
    suppressed: bool
    created_at: datetime | None
    # Investigation trace from referenced finding
    investigation_summary: str | None
    investigation_confidence: float | None
    investigation_reasoning: list[Any] | None
    investigation_findings: list[Any] | None
    recommended_actions: list[Any] | None

    model_config = {"from_attributes": True}


# ── Study Summary ────────────────────────────────────────────────────────────

class StudySummary(BaseModel):
    study_id: str
    study_name: str
    phase: str
    enrolled: int
    target: int
    pct_enrolled: float
    total_sites: int
    active_sites: int
    countries: list[str]
    last_updated: str


class AttentionSite(BaseModel):
    site_id: str
    site_name: str | None
    country: str | None
    city: str | None
    issue: str
    severity: str
    metric: str
    metric_value: float | None


class AttentionSitesResponse(BaseModel):
    sites: list[AttentionSite]
    critical_count: int
    warning_count: int
