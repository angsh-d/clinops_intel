"""Pydantic schemas for feed endpoints."""

from pydantic import BaseModel


class DataSourceHealth(BaseModel):
    row_count: int
    latest_date: str | None

    model_config = {
        "json_schema_extra": {
            "examples": [{"row_count": 1250, "latest_date": "2025-01-15"}]
        }
    }


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    data_sources: dict[str, DataSourceHealth]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "timestamp": "2025-01-15T10:30:00+00:00",
                    "data_sources": {
                        "ecrf_entries": {"row_count": 1250, "latest_date": "2025-01-15"},
                        "queries": {"row_count": 430, "latest_date": "2025-01-14"},
                    },
                }
            ]
        }
    }
