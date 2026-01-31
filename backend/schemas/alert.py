"""Pydantic schemas for alert endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field
class AlertActionResponse(BaseModel):
    status: str
    alert_id: int

    model_config = {
        "json_schema_extra": {
            "examples": [{"status": "suppressed", "alert_id": 42}]
        }
    }


class AlertDetail(BaseModel):
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

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 42,
                    "finding_id": 7,
                    "agent_id": "data_quality",
                    "severity": "critical",
                    "site_id": "SITE-003",
                    "title": "Critical entry lag at SITE-003",
                    "description": "Mean eCRF entry lag exceeds 14-day threshold.",
                    "status": "open",
                    "suppressed": False,
                    "created_at": "2025-01-15T10:30:00Z",
                }
            ]
        },
    }


class AlertResponse(BaseModel):
    alerts: list[AlertDetail]
    total: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "alerts": [
                        {
                            "id": 42,
                            "finding_id": 7,
                            "agent_id": "data_quality",
                            "severity": "critical",
                            "site_id": "SITE-003",
                            "title": "Critical entry lag at SITE-003",
                            "description": "Mean eCRF entry lag exceeds 14-day threshold.",
                            "status": "open",
                            "suppressed": False,
                            "created_at": "2025-01-15T10:30:00Z",
                        }
                    ],
                    "total": 1,
                }
            ]
        }
    }


class SuppressRequest(BaseModel):
    reason: str = Field(..., min_length=1)
    created_by: str | None = None
    expires_in_days: int | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"reason": "Known issue, site remediation in progress", "created_by": "admin@clinops.com", "expires_in_days": 30}
            ]
        }
    }


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(..., min_length=1)

    model_config = {
        "json_schema_extra": {
            "examples": [{"acknowledged_by": "monitor@clinops.com"}]
        }
    }
