"""Common schema types used across Sentinel DV.

This module defines base types and enums shared by all schema modules.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Evidence kinds
EvidenceKind = Literal["log", "report", "coverage", "waveform_summary", "artifact"]

# CI system types
CISystem = Literal["jenkins", "gitlab", "github-actions", "azure-devops", "unknown"]


class TimeSpan(BaseModel):
    """Time or line span for evidence references."""

    start_line: int | None = Field(None, ge=1, description="Starting line number (1-indexed)")
    end_line: int | None = Field(None, ge=1, description="Ending line number (1-indexed)")
    start_time_ns: int | None = Field(None, ge=0, description="Starting time in nanoseconds")
    end_time_ns: int | None = Field(None, ge=0, description="Ending time in nanoseconds")

    @field_validator("end_line")
    @classmethod
    def validate_line_range(cls, v: int | None, info) -> int | None:
        """Ensure end_line >= start_line if both present."""
        if v is not None and info.data.get("start_line") is not None:
            if v < info.data["start_line"]:
                raise ValueError("end_line must be >= start_line")
        return v

    @field_validator("end_time_ns")
    @classmethod
    def validate_time_range(cls, v: int | None, info) -> int | None:
        """Ensure end_time_ns >= start_time_ns if both present."""
        if v is not None and info.data.get("start_time_ns") is not None:
            if v < info.data["start_time_ns"]:
                raise ValueError("end_time_ns must be >= start_time_ns")
        return v


class EvidenceRef(BaseModel):
    """Reference to source evidence for a fact.

    All facts in Sentinel DV can optionally include evidence references
    that point to the exact artifact location where the fact was derived.
    """

    kind: EvidenceKind = Field(..., description="Type of evidence")
    path: str = Field(..., description="Relative path within artifact root", min_length=1)
    span: TimeSpan | None = Field(None, description="Line or time range within file")
    extract: str | None = Field(
        None, max_length=1024, description="Bounded excerpt (may be redacted)"
    )
    hash: str | None = Field(
        None, pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of referenced chunk"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Ensure path is normalized and doesn't escape."""
        if ".." in v.split("/"):
            raise ValueError("Path must not contain '..' components")
        if v.startswith("/"):
            raise ValueError("Path must be relative")
        return v


class CIInfo(BaseModel):
    """CI/CD system information for a run."""

    system: CISystem = Field(..., description="CI system type")
    job_url: str | None = Field(None, description="URL to CI job")
    build_id: str | None = Field(None, description="CI build identifier")


class RunRef(BaseModel):
    """Stable reference to a verification run."""

    run_id: str = Field(..., description="Stable run identifier", min_length=1)
    suite: str = Field(..., description="Test suite or regression name", min_length=1)
    created_at: datetime = Field(..., description="Run creation timestamp (RFC3339)")
    ci: CIInfo | None = Field(None, description="CI system information")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "R20260125_142305_abc123",
                "suite": "nightly_regression",
                "created_at": "2026-01-25T14:23:05Z",
                "ci": {
                    "system": "jenkins",
                    "job_url": "https://jenkins.example.com/job/verification/123",
                    "build_id": "123",
                },
            }
        }
    )


class PaginationInfo(BaseModel):
    """Pagination metadata for list responses."""

    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=200, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total items available")
    total_pages: int = Field(..., ge=0, description="Total pages available")


class ErrorResponse(BaseModel):
    """Standard error response."""

    code: Literal[
        "NOT_FOUND",
        "INVALID_ARGUMENT",
        "PERMISSION_DENIED",
        "INTERNAL",
        "INDEX_NOT_READY",
        "LIMIT_EXCEEDED",
    ] = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, str] | None = Field(None, description="Additional error details")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "INVALID_ARGUMENT",
                "message": "page_size must be between 1 and 200",
                "details": {"field": "page_size", "value": "500"},
            }
        }
    )
