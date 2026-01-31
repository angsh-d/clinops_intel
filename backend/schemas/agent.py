"""Pydantic schemas for agent endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field


class AgentInvokeResponse(BaseModel):
    finding_id: int
    agent_id: str
    finding_type: str
    severity: str
    summary: str
    detail: dict | None = None
    confidence: float | None = None
    reasoning_trace: dict | None = None
    findings: list[dict] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "finding_id": 1,
                    "agent_id": "data_quality",
                    "finding_type": "high_entry_lag",
                    "severity": "warning",
                    "summary": "Site SITE-003 has mean entry lag of 12.4 days",
                    "detail": {"mean_entry_lag": 12.4, "threshold": 7.0},
                    "confidence": 0.92,
                    "reasoning_trace": {"steps": ["queried ecrf_entries", "computed lag"]},
                    "findings": [{"site_id": "SITE-003", "metric": "entry_lag", "value": 12.4}],
                }
            ]
        }
    }


class AgentInvokeRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question for the agent to investigate")
    session_id: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "Which sites have the worst data quality issues?",
                    "session_id": "sess-abc123",
                }
            ]
        }
    }


class AgentFindingSchema(BaseModel):
    id: int
    agent_id: str
    finding_type: str
    severity: str
    site_id: str | None
    summary: str
    detail: dict | None
    confidence: float | None
    created_at: datetime | None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "agent_id": "data_quality",
                    "finding_type": "high_entry_lag",
                    "severity": "warning",
                    "site_id": "SITE-003",
                    "summary": "Site SITE-003 has mean entry lag of 12.4 days",
                    "detail": {"mean_entry_lag": 12.4, "threshold": 7.0},
                    "confidence": 0.92,
                    "created_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    }


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    description: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_id": "data_quality",
                    "name": "Data Quality Agent",
                    "description": "Analyses eCRF entry lags, query volumes, and data correction patterns.",
                }
            ]
        }
    }
