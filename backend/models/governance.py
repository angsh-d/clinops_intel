"""Governance tables added to the existing clinops_intel schema.

Uses the same Base from data_generators.models so all tables share
one metadata and one create_all() call.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, LargeBinary, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from data_generators.models import Base


# ── audit_trail ──────────────────────────────────────────────────────────────
class AuditTrail(Base):
    __tablename__ = "audit_trail"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = Column(String(100))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(String(100))
    detail = Column(JSONB)


# ── agent_findings ───────────────────────────────────────────────────────────
class AgentFinding(Base):
    __tablename__ = "agent_findings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(30), nullable=False)
    finding_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    site_id = Column(String(20))
    summary = Column(Text, nullable=False)
    detail = Column(JSONB)
    data_signals = Column(JSONB)
    reasoning_trace = Column(JSONB)
    confidence = Column(Float)
    dedup_hash = Column(String(64), unique=True)
    scan_id = Column(String(50))
    directive_id = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        Index("ix_findings_agent", "agent_id"),
        Index("ix_findings_site", "site_id"),
        Index("ix_findings_scan", "scan_id"),
    )


# ── alert_log ────────────────────────────────────────────────────────────────
class AlertLog(Base):
    __tablename__ = "alert_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    finding_id = Column(Integer, ForeignKey("agent_findings.id", ondelete="CASCADE"))
    agent_id = Column(String(30), nullable=False)
    severity = Column(String(20), nullable=False)
    site_id = Column(String(20))
    title = Column(String(300), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="open")  # open / acknowledged / suppressed / resolved
    suppressed = Column(Boolean, default=False)
    suppression_rule_id = Column(Integer, ForeignKey("suppression_rules.id", ondelete="SET NULL"))
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        Index("ix_alert_status", "status"),
        Index("ix_alert_site", "site_id"),
    )


# ── conversational_interactions ──────────────────────────────────────────────
class ConversationalInteraction(Base):
    __tablename__ = "conversational_interactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(50), nullable=False, unique=True)
    session_id = Column(String(50), nullable=False)
    parent_query_id = Column(String(50))
    user_query = Column(Text, nullable=False)
    routed_agents = Column(JSONB)
    agent_responses = Column(JSONB)
    synthesized_response = Column(Text)
    synthesis_data = Column(JSONB)  # Full synthesis dict (hypotheses, actions, findings)
    status = Column(String(20), default="pending")  # pending / processing / completed / failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)
    __table_args__ = (
        Index("ix_interaction_session", "session_id"),
        Index("ix_interaction_status", "status"),
    )


# ── alert_thresholds ────────────────────────────────────────────────────────
class AlertThreshold(Base):
    __tablename__ = "alert_thresholds"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(30), nullable=False)
    metric_name = Column(String(100), nullable=False)
    warning_threshold = Column(Float)
    critical_threshold = Column(Float)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── suppression_rules ────────────────────────────────────────────────────────
class SuppressionRule(Base):
    __tablename__ = "suppression_rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(30))
    site_id = Column(String(20))
    finding_type = Column(String(50))
    reason = Column(Text, nullable=False)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)


# ── agent_parameters ─────────────────────────────────────────────────────────
class AgentParameter(Base):
    __tablename__ = "agent_parameters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(30), nullable=False)
    parameter_name = Column(String(100), nullable=False)
    parameter_value = Column(JSONB)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── cache_entries ───────────────────────────────────────────────────────────
class CacheEntry(Base):
    __tablename__ = "cache_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    namespace = Column(String(50), nullable=False)
    cache_key = Column(String(64), nullable=False)
    value = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        UniqueConstraint("namespace", "cache_key", name="uq_cache_ns_key"),
        Index("ix_cache_namespace", "namespace"),
    )


# ── proactive_scans ─────────────────────────────────────────────────────────
class ProactiveScan(Base):
    __tablename__ = "proactive_scans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(50), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pending")  # pending/running/completed/failed
    trigger_type = Column(String(30), nullable=False, default="api")  # api/schedule/data_refresh
    directives_executed = Column(JSONB)
    agent_results = Column(JSONB)
    findings_count = Column(Integer, default=0)
    alerts_count = Column(Integer, default=0)
    brief_ids = Column(JSONB)
    study_synthesis = Column(JSONB)  # study-wide cross-domain synthesis
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    error_detail = Column(Text)
    __table_args__ = (
        Index("ix_scan_status", "status"),
    )


# ── site_intelligence_briefs ────────────────────────────────────────────────
class SiteIntelligenceBrief(Base):
    __tablename__ = "site_intelligence_briefs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(String(50), nullable=False)
    site_id = Column(String(20), nullable=False)
    risk_summary = Column(JSONB)
    vendor_accountability = Column(JSONB)
    cross_domain_correlations = Column(JSONB)
    recommended_actions = Column(JSONB)
    trend_indicator = Column(String(20))  # improving/stable/deteriorating
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        Index("ix_brief_scan", "scan_id"),
        Index("ix_brief_site", "site_id"),
    )
