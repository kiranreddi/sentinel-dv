"""Regression and diff schemas for Sentinel DV."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel_dv.schemas.common import EvidenceRef, RunRef
from sentinel_dv.schemas.failures import FailureSignature

# Diff item kinds
DiffKind = Literal[
    "new_failure_signature",
    "resolved_failure_signature",
    "coverage_delta",
    "test_status_change",
    "config_change",
]


class RegressionSummary(BaseModel):
    """High-level regression summary over a time window."""

    suite: str = Field(..., description="Suite name")
    window: dict[str, datetime] = Field(..., description="Time window (start, end)")
    runs: list[RunRef] = Field(..., description="Runs in this regression")
    pass_rate: float = Field(..., ge=0.0, le=100.0, description="Overall pass rate (0-100)")
    top_fail_signatures: list[FailureSignature] = Field(
        ..., max_length=100, description="Top failure signatures by count"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suite": "nightly_regression",
                "window": {
                    "start": "2026-01-18T00:00:00Z",
                    "end": "2026-01-25T23:59:59Z",
                },
                "runs": [
                    {
                        "run_id": "R20260125_142305",
                        "suite": "nightly_regression",
                        "created_at": "2026-01-25T14:23:05Z",
                    }
                ],
                "pass_rate": 92.3,
                "top_fail_signatures": [
                    {
                        "signature_id": "sig_axi_bresp_decerr_abc123",
                        "category": "assertion",
                        "summary": "AXI BRESP received DECERR for write transaction",
                        "count": 15,
                        "example_test_ids": ["T20260125_142305_axi_burst_test"],
                        "first_seen": "2026-01-20T08:15:00Z",
                        "last_seen": "2026-01-25T14:23:05Z",
                    }
                ],
            }
        }
    )


class DiffItem(BaseModel):
    """Individual difference between two runs."""

    kind: DiffKind = Field(..., description="Type of difference")
    description: str = Field(..., max_length=512, description="Human-readable description")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured details (bounded, progressively typed)",
    )
    evidence: list[EvidenceRef] = Field(
        default_factory=list, max_length=5, description="Evidence references"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kind": "new_failure_signature",
                "description": "New assertion failure: AXI BRESP DECERR",
                "details": {
                    "signature_id": "sig_axi_bresp_decerr_abc123",
                    "category": "assertion",
                    "count": 3,
                },
                "evidence": [],
            }
        }
    )


class RunDiff(BaseModel):
    """Structured diff between two verification runs."""

    base_run_id: str = Field(..., description="Base run identifier")
    compare_run_id: str = Field(..., description="Comparison run identifier")
    changes: list[DiffItem] = Field(..., description="List of differences")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "base_run_id": "R20260124_142305",
                "compare_run_id": "R20260125_142305",
                "changes": [
                    {
                        "kind": "new_failure_signature",
                        "description": "New assertion failure: AXI BRESP DECERR",
                        "details": {
                            "signature_id": "sig_axi_bresp_decerr_abc123",
                            "count": 3,
                        },
                        "evidence": [],
                    },
                    {
                        "kind": "coverage_delta",
                        "description": "Functional coverage decreased by 5.2%",
                        "details": {
                            "kind": "functional",
                            "base_coverage": 92.5,
                            "compare_coverage": 87.3,
                            "delta": -5.2,
                        },
                        "evidence": [],
                    },
                ],
            }
        }
    )
