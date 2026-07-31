"""Failure and diagnostic schemas for Sentinel DV."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel_dv.schemas.common import EvidenceRef

# Severity levels
Severity = Literal["info", "warning", "error", "fatal"]

# Failure categories
FailureCategory = Literal[
    "assertion",
    "scoreboard",
    "protocol",
    "timeout",
    "xprop",
    "compile",
    "elab",
    "runtime",
    "unknown",
]


class FailureEvent(BaseModel):
    """Normalized failure or diagnostic event.

    Represents things that went wrong during verification:
    - UVM errors/fatals
    - cocotb exceptions
    - Assertion failures
    - Scoreboard mismatches
    - Protocol violations
    - Timeouts
    - Compilation/elaboration errors
    """

    id: str | None = Field(None, description="Stable event identifier", min_length=1)
    test_id: str | None = Field(None, description="Test this failure occurred in")
    severity: Severity = Field(..., description="Event severity level")
    category: FailureCategory = Field(..., description="Failure category")
    summary: str = Field(
        ...,
        max_length=256,
        description="Normalized summary (stable across runs)",
    )
    message: str = Field(
        ...,
        max_length=4096,
        description="Full message (bounded and redacted)",
    )
    time_ns: int | None = Field(None, ge=0, description="Simulation time in nanoseconds")
    phase: str | None = Field(None, description="UVM phase (if applicable)")
    component: str | None = Field(
        None, description="Component path or module name where failure occurred"
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Categorization tags (e.g., ['AXI', 'BRESP', 'DECERR'])",
    )
    evidence: list[EvidenceRef] = Field(
        default_factory=list, max_length=10, description="Evidence references"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "F20260125_142305_001",
                "test_id": "T20260125_142305_axi_burst_test",
                "severity": "error",
                "category": "assertion",
                "summary": "AXI BRESP received DECERR for write transaction",
                "message": "UVM_ERROR @ 1250ns: Assertion axi_protocol_check.bresp_valid failed: Expected OKAY but got DECERR",
                "time_ns": 1250,
                "phase": "main_phase",
                "component": "uvm_test_top.env.axi_master_agent.monitor",
                "tags": ["AXI", "BRESP", "DECERR", "protocol"],
                "evidence": [
                    {
                        "kind": "log",
                        "path": "regression/axi_burst_test.log",
                        "span": {"start_line": 142, "end_line": 148},
                        "extract": "UVM_ERROR @ 1250ns: Assertion failed...",
                    }
                ],
            }
        }
    )


class FailureSignature(BaseModel):
    """Stable signature for grouping similar failures across runs.

    Computed from normalized category + summary (and optionally protocol tag).
    Used for regression analytics and failure trending.
    """

    signature_id: str = Field(
        ..., description="Stable hash identifying this failure pattern", min_length=1
    )
    category: FailureCategory = Field(..., description="Failure category")
    summary: str = Field(..., max_length=256, description="Normalized summary")
    count: int = Field(..., ge=1, description="Number of occurrences")
    example_test_ids: list[str] = Field(
        ..., max_length=10, description="Example test IDs (bounded)"
    )
    first_seen: datetime = Field(..., description="First occurrence timestamp")
    last_seen: datetime = Field(..., description="Last occurrence timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "signature_id": "sig_axi_bresp_decerr_abc123",
                "category": "assertion",
                "summary": "AXI BRESP received DECERR for write transaction",
                "count": 15,
                "example_test_ids": [
                    "T20260125_142305_axi_burst_test",
                    "T20260125_143510_axi_wrap_test",
                ],
                "first_seen": "2026-01-20T08:15:00Z",
                "last_seen": "2026-01-25T14:23:05Z",
            }
        }
    )
