"""Coverage schemas for Sentinel DV."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sentinel_dv.schemas.common import EvidenceRef

# Coverage kinds
CoverageKind = Literal["functional", "code", "assertion", "toggle", "fsm", "unknown"]

GapPriority = Literal["high", "medium", "low"]


class CoverageMetric(BaseModel):
    """Individual coverage metric.

    Represents a single coverage item (coverpoint, bin, line, toggle, etc).
    """

    name: str = Field(..., description="Metric name (e.g., axi.awlen_bins)", min_length=1)
    scope: str = Field(..., description="Scope (e.g., tb.env.axi_agent)", min_length=1)
    covered: float = Field(..., ge=0.0, le=100.0, description="Coverage percentage (0-100)")
    hits: int | None = Field(None, ge=0, description="Number of hits")
    total: int | None = Field(None, ge=0, description="Total possible hits")
    bins_missed: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Names of uncovered bins (bounded)",
    )

    @field_validator("total")
    @classmethod
    def validate_total(cls, v: int | None, info) -> int | None:
        """Ensure total >= hits if both present."""
        if v is not None and info.data.get("hits") is not None and v < info.data["hits"]:
            raise ValueError("total must be >= hits")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "axi.awlen_bins",
                "scope": "tb.env.axi_master_agent",
                "covered": 87.5,
                "hits": 7,
                "total": 8,
                "bins_missed": ["awlen_15"],
            }
        }
    )


class CoverageSummary(BaseModel):
    """Coverage summary for a run or test.

    Contains multiple coverage metrics of a specific kind.
    """

    run_id: str = Field(..., description="Run identifier")
    test_id: str | None = Field(None, description="Test identifier (None for aggregated coverage)")
    kind: CoverageKind = Field(..., description="Coverage type")
    metrics: list[CoverageMetric] = Field(
        ..., max_length=200, description="Coverage metrics (bounded)"
    )
    evidence: list[EvidenceRef] = Field(
        default_factory=list, max_length=10, description="Evidence references"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "R20260125_142305",
                "test_id": "T20260125_142305_axi_burst_test",
                "kind": "functional",
                "metrics": [
                    {
                        "name": "axi.awlen_bins",
                        "scope": "tb.env.axi_master_agent",
                        "covered": 87.5,
                        "hits": 7,
                        "total": 8,
                        "bins_missed": ["awlen_15"],
                    },
                    {
                        "name": "axi.awburst_bins",
                        "scope": "tb.env.axi_master_agent",
                        "covered": 100.0,
                        "hits": 3,
                        "total": 3,
                        "bins_missed": [],
                    },
                ],
                "evidence": [
                    {
                        "kind": "coverage",
                        "path": "coverage/functional_coverage.txt",
                    }
                ],
            }
        }
    )


class CoverageGap(BaseModel):
    """A single coverage gap with a recommended fix.

    Produced by the coverage.gaps tool from existing coverage metrics and
    optional assertion status.
    """

    run_id: str | None = Field(None, description="Run that produced this coverage metric")
    suite: str | None = Field(None, description="Suite that produced this coverage metric")
    metric_name: str = Field(..., description="Coverage metric name with gap")
    scope: str = Field(..., description="Module or testbench scope")
    kind: CoverageKind = Field(..., description="Coverage type")
    covered_pct: float = Field(..., ge=0.0, le=100.0, description="Current coverage percentage")
    bins_missed: list[str] = Field(
        default_factory=list, max_length=50, description="Specific bins or items not yet hit"
    )
    priority: GapPriority = Field(
        ..., description="Gap priority based on coverage depth and signal importance"
    )
    recommendation: str = Field(..., description="Actionable recommendation to close this gap")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "R20260125_142305",
                "suite": "axi4_nightly",
                "metric_name": "axi.awlen_bins",
                "scope": "tb.env.axi_master_agent",
                "kind": "functional",
                "covered_pct": 87.5,
                "bins_missed": ["awlen_15"],
                "priority": "high",
                "recommendation": (
                    "Add a directed test with awlen=15 (max burst) to cover the awlen_15 bin. "
                    "Use the seed replay tool to reproduce and extend existing close tests."
                ),
            }
        }
    )


class CoverageGapsResponse(BaseModel):
    """Response from coverage.gaps listing uncovered areas with recommendations."""

    run_id: str | None = Field(None, description="Run filter applied, if any")
    suite: str | None = Field(None, description="Suite filter applied, if any")
    kind: CoverageKind | None = Field(None, description="Coverage kind filter applied, if any")
    threshold_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Coverage threshold used for gap detection"
    )
    total_metrics: int = Field(..., ge=0, description="Total coverage metrics evaluated")
    gaps_found: int = Field(..., ge=0, description="Number of gaps found")
    gaps: list[CoverageGap] = Field(
        ..., description="Gaps ordered by priority then coverage percentage"
    )
    note: str = Field(..., description="Guidance note on interpreting and acting on gaps")
