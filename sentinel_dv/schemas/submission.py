"""Schemas for regression job submission and test replay command generation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SubmitRequest(BaseModel):
    """Request model for runs.submit command generation."""

    suite: str = Field(..., description="Suite name from existing runs")
    simulator: str | None = Field(
        None, description="Simulator override. Defaults to submit.default_simulator."
    )
    seed: int | None = Field(None, ge=0, description="Integer seed to reproduce a specific test")
    test_filter: str | None = Field(None, description="Glob or regex test name filter")
    extra_args: str | None = Field(None, description="Extra simulator arguments appended verbatim")


class SubmitResponse(BaseModel):
    """Generated regression submission command."""

    suite: str = Field(..., description="Suite name the command targets")
    simulator: str = Field(..., description="Simulator used in the command")
    seed: int | None = Field(None, description="Seed embedded in the command, or None for random")
    command: str = Field(..., description="Generated shell command (bounded by max_command_length)")
    scheduler_command: str | None = Field(
        None, description="LSF bsub or SLURM sbatch wrapped form, if scheduler configured"
    )
    dry_run: bool = Field(True, description="Always True — this server never executes commands")
    note: str = Field(..., description="Reminder that this is a generated command, not executed")


class ReplayResponse(BaseModel):
    """Generated single-test replay command."""

    test_id: str = Field(..., description="Test identifier the command reproduces")
    test_name: str = Field(..., description="Test name")
    suite: str = Field(..., description="Suite the test belongs to")
    simulator: str = Field(..., description="Simulator used in the replay command")
    seed: int | None = Field(None, description="Seed embedded in the command")
    dut_top: str | None = Field(None, description="DUT top module, if indexed")
    command: str = Field(
        ..., description="Generated replay command (bounded by max_command_length)"
    )
    scheduler_command: str | None = Field(
        None, description="LSF or SLURM wrapped form, if scheduler configured"
    )
    dry_run: bool = Field(True, description="Always True — this server never executes commands")
    note: str = Field(..., description="Reminder that this is a generated command, not executed")
    warning: str | None = Field(
        None,
        description="Set if seed is None — replay may not reproduce the exact failure deterministically",
    )
