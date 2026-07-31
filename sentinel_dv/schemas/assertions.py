"""Assertion schemas for Sentinel DV."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel_dv.schemas.common import EvidenceRef

# Assertion languages
AssertionLanguage = Literal["sva", "immediate", "psl", "unknown"]

# SVA run status per assertion
SVAStatus = Literal["passing", "failing", "vacuous", "disabled", "unknown"]


class AssertionIntent(BaseModel):
    """Assertion intent/purpose metadata."""

    protocol: str | None = Field(None, description="Protocol this assertion checks")
    requirement: str | None = Field(None, description="Requirement or spec reference")


class AssertionInfo(BaseModel):
    """Assertion definition information.

    Represents a static assertion (SVA, immediate, PSL) indexed from
    source code or assertion compile maps.
    """

    id: str = Field(..., description="Stable assertion identifier", min_length=1)
    language: AssertionLanguage = Field(..., description="Assertion language")
    name: str = Field(..., description="Assertion name/label", min_length=1)
    scope: str = Field(..., description="Scope (module/interface/class)", min_length=1)
    file: str = Field(..., description="Source file path", min_length=1)
    line: int = Field(..., ge=1, description="Line number in source file")
    intent: AssertionIntent | None = Field(None, description="Assertion intent metadata")
    signals: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Signals referenced in assertion (best-effort)",
    )
    enabled_in_run: bool | None = Field(
        None, description="Whether assertion was enabled in a specific run"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "A_axi_protocol_check_bresp_valid",
                "language": "sva",
                "name": "axi_protocol_check_bresp_valid",
                "scope": "axi_master_agent",
                "file": "rtl/axi_protocol_checker.sv",
                "line": 145,
                "intent": {
                    "protocol": "AXI4",
                    "requirement": "IHI0022E Section A3.4.1",
                },
                "signals": ["bvalid", "bready", "bresp"],
                "enabled_in_run": True,
            }
        }
    )


class AssertionFailure(BaseModel):
    """Runtime assertion failure instance.

    Represents a specific assertion firing during simulation.
    Links to AssertionInfo via assertion_id.
    """

    assertion_id: str = Field(..., description="Reference to AssertionInfo.id")
    test_id: str = Field(..., description="Test where assertion failed")
    time_ns: int | None = Field(None, ge=0, description="Simulation time in nanoseconds")
    message: str = Field(
        ...,
        max_length=2048,
        description="Failure message (bounded and redacted)",
    )
    evidence: list[EvidenceRef] = Field(
        default_factory=list, max_length=10, description="Evidence references"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "assertion_id": "A_axi_protocol_check_bresp_valid",
                "test_id": "T20260125_142305_axi_burst_test",
                "time_ns": 1250,
                "message": "Expected OKAY but got DECERR on write response channel",
                "evidence": [
                    {
                        "kind": "log",
                        "path": "regression/axi_burst_test.log",
                        "span": {"start_line": 142, "end_line": 148, "start_time_ns": 1250},
                        "extract": "Assertion axi_protocol_check_bresp_valid failed...",
                    }
                ],
            }
        }
    )


class SVARunStatus(BaseModel):
    """Per-assertion runtime status from a simulation run.

    Produced by assertion_reports adapter parsing simulator VCS/Questa/Xcelium
    assertion summary sections. Stored in the sva_run_status DuckDB table.
    """

    assertion_id: str = Field(..., description="Reference to AssertionInfo.id")
    test_id: str = Field(..., description="Test run that produced this status")
    status: SVAStatus = Field(..., description="Assertion status in this run")
    pass_count: int = Field(default=0, ge=0, description="Number of times assertion passed")
    fail_count: int = Field(default=0, ge=0, description="Number of times assertion failed")
    vacuous_count: int = Field(
        default=0, ge=0, description="Number of vacuous firings (antecedent never held)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "assertion_id": "A_axi_protocol_check_bresp_valid",
                "test_id": "T20260125_142305_axi_burst_test",
                "status": "passing",
                "pass_count": 48,
                "fail_count": 0,
                "vacuous_count": 0,
            }
        }
    )


class VacuousAssertion(BaseModel):
    """Summary of a vacuously-passing assertion.

    An assertion is vacuous if its antecedent (the ``if`` or ``|->`` premise)
    was never true during the run — so the implication passed trivially.
    These need review to ensure the assertion is actually exercising anything.
    """

    assertion_id: str = Field(..., description="Reference to AssertionInfo.id")
    assertion_name: str = Field(..., description="Human-readable assertion name")
    scope: str = Field(..., description="Module scope of the assertion")
    test_id: str = Field(..., description="Test run that produced this status")
    vacuous_count: int = Field(..., ge=0, description="Total vacuous firings in the run")
    recommendation: str = Field(
        ..., description="Actionable recommendation to exercise the antecedent"
    )
