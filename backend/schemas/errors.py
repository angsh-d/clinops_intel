"""Shared error response models for OpenAPI documentation."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"detail": "Resource not found"}]
        }
    }


class ValidationErrorItem(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorDetail(BaseModel):
    detail: list[ValidationErrorItem]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": [
                        {
                            "loc": ["body", "question"],
                            "msg": "String should have at least 1 character",
                            "type": "string_too_short",
                        }
                    ]
                }
            ]
        }
    }
