"""Pydantic schemas for query endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000, description="The user's natural language question")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "Which sites are behind on enrollment targets?",
                    "session_id": "sess-abc123",
                }
            ]
        }
    }


class QueryResponse(BaseModel):
    query_id: str
    status: str = "accepted"
    message: str = "Query submitted for processing"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "status": "accepted",
                    "message": "Query submitted for processing",
                }
            ]
        }
    }


class QueryStatus(BaseModel):
    query_id: str
    status: str  # pending / processing / completed / failed
    routing: dict | None = None
    agent_outputs: dict[str, Any] | None = None
    synthesis: dict | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "status": "completed",
                    "routing": {"selected_agents": ["data_quality"]},
                    "agent_outputs": {"data_quality": {"summary": "3 sites flagged"}},
                    "synthesis": {"executive_summary": "Data quality issues at 3 sites."},
                    "created_at": "2025-01-15T10:30:00Z",
                    "completed_at": "2025-01-15T10:31:15Z",
                }
            ]
        }
    }


class FollowUpRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"question": "Can you break that down by region?"}
            ]
        }
    }
