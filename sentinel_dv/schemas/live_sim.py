"""Schemas for live simulation progress reporting."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LiveSimPhase = Literal["compiling", "elaborating", "running", "done", "failed", "unknown"]


class LiveSimProgress(BaseModel):
    """Live simulation progress snapshot.

    Written by the simulator harness as live_status.json alongside build artefacts.
    The sentinel-dv server reads this file — it never calls the simulator directly.
    """

    suite: str = Field(..., description="Suite identifier")
    phase: LiveSimPhase = Field(..., description="Current simulator phase")
    tests_total: int = Field(default=0, ge=0, description="Total tests in the run")
    tests_done: int = Field(default=0, ge=0, description="Tests finished (pass + fail)")
    tests_passing: int = Field(default=0, ge=0, description="Tests passing so far")
    tests_failing: int = Field(default=0, ge=0, description="Tests failing so far")
    current_test: str | None = Field(None, description="Test currently executing, if known")
    elapsed_seconds: float | None = Field(None, ge=0.0, description="Wall-clock seconds elapsed")
    estimated_remaining_seconds: float | None = Field(
        None, ge=0.0, description="Estimated seconds remaining (optional)"
    )
    last_updated: str | None = Field(
        None, description="ISO-8601 timestamp when the status file was written"
    )
    stale: bool = Field(
        False,
        description=(
            "True when the status file is older than adapters.live_sim_max_age_seconds. "
            "Stale data is returned unchanged to allow the caller to decide."
        ),
    )
    percent_done: float | None = Field(
        None, ge=0.0, le=100.0, description="Completion percentage (tests_done / tests_total * 100)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "suite": "axi4_regression",
                "phase": "running",
                "tests_total": 120,
                "tests_done": 47,
                "tests_passing": 44,
                "tests_failing": 3,
                "current_test": "axi4_random_burst_test",
                "elapsed_seconds": 183.5,
                "estimated_remaining_seconds": 240.0,
                "last_updated": "2026-01-25T14:23:05Z",
                "stale": False,
                "percent_done": 39.17,
            }
        }
