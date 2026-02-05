"""Pydantic schemas for proactive intelligence endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    trigger_type: Literal["api", "schedule", "data_refresh"] = "api"
    agent_filter: list[str] | None = Field(None, description="Optional list of agent IDs to include")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"trigger_type": "api", "agent_filter": ["data_quality", "enrollment_funnel"]}
            ]
        }
    }


class ScanStatusResponse(BaseModel):
    scan_id: str
    status: str  # pending/running/completed/failed
    trigger_type: str | None = None
    directives_executed: list[dict] | None = None
    agent_results: list[dict] | None = None
    findings_count: int = 0
    alerts_count: int = 0
    briefs_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_detail: str | None = None
    created_at: datetime | None = None


class ScanListItem(BaseModel):
    scan_id: str
    status: str
    trigger_type: str | None = None
    findings_count: int = 0
    alerts_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class SiteBriefResponse(BaseModel):
    id: int
    scan_id: str
    site_id: str
    risk_summary: dict | None = None
    vendor_accountability: dict | None = None
    cross_domain_correlations: list[dict] | None = None
    recommended_actions: list[dict] | None = None
    trend_indicator: str | None = None
    agent: str | None = None
    contributing_agents: list[dict] | None = None
    investigation_steps: list[dict] | None = None
    created_at: datetime | None = None


class DirectiveResponse(BaseModel):
    directive_id: str
    agent_id: str
    name: str
    description: str
    enabled: bool = True
    priority: str = "medium"


class DirectiveToggleRequest(BaseModel):
    enabled: bool


class DirectiveCreateRequest(BaseModel):
    directive_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")
    agent_id: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    prompt_text: str = Field(..., min_length=1, description="The directive prompt text")
    priority: Literal["low", "medium", "high"] = "medium"
