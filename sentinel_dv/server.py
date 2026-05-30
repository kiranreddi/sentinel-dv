"""
Sentinel DV MCP Server.

Exposes verification intelligence tools over the Model Context Protocol (stdio).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from fastmcp import FastMCP
from pydantic import Field

from sentinel_dv.config import get_config, resolve_config, set_config
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.normalization.redaction import Redactor, set_default_redactor
from sentinel_dv.tools import core
from sentinel_dv.tools.errors import ToolError
from sentinel_dv.tools.mcp_metadata import OUTPUT_SCHEMAS, READ_ONLY_ANNOTATIONS, TOOL_DESCRIPTIONS

F = TypeVar("F", bound=Callable[..., dict[str, Any]])

mcp = FastMCP("Sentinel DV")

_store: IndexStore | None = None


def get_store() -> IndexStore:
    """Return the connected index store."""
    global _store
    if _store is None:
        config = get_config()
        db_path = Path(config.index.path)
        _store = IndexStore(db_path)
        _store.connect()
    return _store


def init_server(config_path: Path | str | None = None) -> None:
    """Load configuration and reset the store connection."""
    global _store
    if _store is not None:
        _store.close()
        _store = None
    config = resolve_config(config_path)
    set_config(config)
    set_default_redactor(Redactor.from_config(config.redaction))


def _tool_wrapper(fn: F) -> F:
    """Map ToolError and validation failures to structured MCP responses."""

    @wraps(fn)
    def inner(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except ToolError as exc:
            return exc.to_dict()
        except ValueError as exc:
            return ToolError("INVALID_ARGUMENT", str(exc)).to_dict()
        except RuntimeError as exc:
            msg = str(exc)
            if "not initialized" in msg.lower() or "configuration" in msg.lower():
                return ToolError("INDEX_NOT_READY", msg).to_dict()
            return ToolError("INTERNAL", msg).to_dict()

    return inner  # type: ignore[return-value]


def _readonly_tool(name: str) -> Callable[[F], F]:
    """Register a read-only MCP tool with description, outputSchema, and annotations."""

    def decorator(fn: F) -> F:
        return mcp.tool(  # type: ignore[return-value]
            name=name,
            description=TOOL_DESCRIPTIONS[name],
            output_schema=OUTPUT_SCHEMAS[name],
            annotations=READ_ONLY_ANNOTATIONS,
        )(_tool_wrapper(fn))

    return decorator


# ============================================================================
# Discovery tools
# ============================================================================


@_readonly_tool("runs.list")
def runs_list(
    suite: str | None = Field(None, description="Filter by suite name"),
    status: str | None = Field(None, description="Filter by run status (pass|fail|error)"),
    ci_system: str | None = Field(None, description="Filter by CI system"),
    page: int = Field(1, description="Page number (1-based)"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    return core.list_runs(
        get_store(), suite=suite, status=status, ci_system=ci_system, page=page, page_size=page_size
    )


@_readonly_tool("runs.get")
def runs_get(
    run_id: str = Field(..., description="Run identifier"),
) -> dict[str, Any]:
    return core.get_run_details(get_store(), run_id)


@_readonly_tool("tests.list")
def tests_list(
    run_id: str | None = Field(None, description="Filter by run ID"),
    framework: str | None = Field(None, description="Filter by framework (uvm|cocotb)"),
    status: str | None = Field(None, description="Filter by status (pass|fail|error)"),
    name_pattern: str | None = Field(None, description="Filter by name substring"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    return core.list_tests(
        get_store(),
        run_id=run_id,
        framework=framework,
        status=status,
        name_pattern=name_pattern,
        page=page,
        page_size=page_size,
    )


@_readonly_tool("assertions.list")
def assertions_list(
    scope: str | None = Field(None, description="Filter by scope"),
    name_pattern: str | None = Field(None, description="Filter by assertion name"),
    protocol: str | None = Field(None, description="Filter by intent.protocol (e.g. axi4)"),
    tag: str | None = Field(None, description="Filter by tag substring in tags_flat"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    return core.list_assertions(
        get_store(),
        scope=scope,
        name_pattern=name_pattern,
        protocol=protocol,
        tag=tag,
        page=page,
        page_size=page_size,
    )


@_readonly_tool("coverage.list")
def coverage_list(
    run_id: str | None = Field(None, description="Filter by run ID"),
    kind: str | None = Field(None, description="Coverage kind (functional|line|code|toggle|fsm)"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    return core.list_coverage(get_store(), run_id=run_id, kind=kind, page=page, page_size=page_size)


# ============================================================================
# Detail tools
# ============================================================================


@_readonly_tool("tests.get")
def tests_get(
    test_id: str = Field(..., description="Test identifier"),
) -> dict[str, Any]:
    return core.get_test_details(get_store(), test_id)


@_readonly_tool("tests.topology")
def tests_topology(
    test_id: str = Field(..., description="Test identifier"),
) -> dict[str, Any]:
    return core.get_test_topology(get_store(), test_id)


@_readonly_tool("assertions.get")
def assertions_get(
    assertion_id: str = Field(..., description="Assertion identifier"),
) -> dict[str, Any]:
    return core.get_assertion_details(get_store(), assertion_id)


# ============================================================================
# Analysis tools
# ============================================================================


@_readonly_tool("failures.list")
def failures_list(
    test_id: str | None = Field(None, description="Filter by test ID"),
    run_id: str | None = Field(None, description="Filter by run ID"),
    category: str | None = Field(None, description="Failure category"),
    severity: str | None = Field(None, description="Severity"),
    tags_any: list[str] | None = Field(None, description="Match any of these tags"),
    include_evidence: bool = Field(False, description="Include bounded evidence refs"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    return core.list_failures(
        get_store(),
        test_id=test_id,
        run_id=run_id,
        category=category,
        severity=severity,
        tags_any=tags_any,
        include_evidence=include_evidence,
        page=page,
        page_size=page_size,
    )


@_readonly_tool("assertions.failures")
def assertions_failures(
    run_id: str | None = Field(None, description="Filter by run ID"),
    test_id: str | None = Field(None, description="Filter by test ID"),
    assertion_id: str | None = Field(None, description="Filter by assertion ID"),
    start_time_ns: int | None = Field(None, description="Window start (nanoseconds)"),
    end_time_ns: int | None = Field(None, description="Window end (nanoseconds)"),
    include_evidence: bool = Field(False, description="Include bounded evidence refs"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    return core.list_assertion_failures(
        get_store(),
        run_id=run_id,
        test_id=test_id,
        assertion_id=assertion_id,
        start_time_ns=start_time_ns,
        end_time_ns=end_time_ns,
        include_evidence=include_evidence,
        page=page,
        page_size=page_size,
    )


@_readonly_tool("coverage.summary")
def coverage_summary(
    run_id: str = Field(..., description="Run identifier"),
    kind: str | None = Field(None, description="Optional coverage kind filter"),
    include_evidence: bool = Field(
        False, description="Include evidence refs in coverage summaries"
    ),
) -> dict[str, Any]:
    return core.get_coverage_summary(
        get_store(), run_id, kind=kind, include_evidence=include_evidence
    )


# ============================================================================
# Regression tools
# ============================================================================


@_readonly_tool("regressions.summary")
def regressions_summary(
    suite: str = Field(..., description="Suite name"),
    window_days: int = Field(7, description="Time window in days"),
    as_of: str | None = Field(
        None,
        description="RFC3339 end timestamp for reproducible window (default: now UTC)",
    ),
) -> dict[str, Any]:
    return core.get_regression_summary(
        get_store(), suite=suite, window_days=window_days, as_of=as_of
    )


@_readonly_tool("runs.diff")
def runs_diff(
    base_run_id: str = Field(..., description="Base run ID"),
    compare_run_id: str = Field(..., description="Compare run ID"),
) -> dict[str, Any]:
    return core.compare_runs(get_store(), base_run_id=base_run_id, compare_run_id=compare_run_id)


# ============================================================================
# Waveform tools
# ============================================================================


@_readonly_tool("wave.signals")
def wave_signals(
    test_id: str = Field(..., description="Test identifier"),
    start_time_ns: int | None = Field(
        None,
        description="Optional window start in nanoseconds. VCD: re-parses source trace.",
    ),
    end_time_ns: int | None = Field(
        None,
        description="Optional window end in nanoseconds. Requires start_time_ns.",
    ),
) -> dict[str, Any]:
    return core.wave_signals(
        get_store(), test_id, start_time_ns=start_time_ns, end_time_ns=end_time_ns
    )


@_readonly_tool("wave.summary")
def wave_summary(
    test_id: str = Field(..., description="Test identifier"),
    start_time_ns: int | None = Field(
        None,
        description="Optional window start in nanoseconds. VCD: re-parses source trace.",
    ),
    end_time_ns: int | None = Field(
        None,
        description="Optional window end in nanoseconds. Requires start_time_ns.",
    ),
    include_signals: bool = Field(
        False,
        description="When true, include the same per-signal list as wave.signals in this response.",
    ),
) -> dict[str, Any]:
    return core.wave_summary(
        get_store(),
        test_id,
        start_time_ns=start_time_ns,
        end_time_ns=end_time_ns,
        include_signals=include_signals,
    )


# ============================================================================
# v2.0.0: Regression submission tools
# ============================================================================


@_readonly_tool("runs.submit")
def runs_submit(
    suite: str = Field(..., description="Suite name to generate submission command for"),
    simulator: str | None = Field(
        None,
        description="Simulator override (vcs|questa|xcelium|verilator). "
        "Defaults to submit.default_simulator in config.",
    ),
    seed: int | None = Field(None, description="Optional integer seed to embed in the command"),
    test_filter: str | None = Field(None, description="Optional test name glob/pattern"),
    extra_args: str | None = Field(None, description="Extra simulator arguments (shell-quoted)"),
) -> dict[str, Any]:
    return core.generate_submit_command(
        get_store(),
        suite=suite,
        simulator=simulator,
        seed=seed,
        test_filter=test_filter,
        extra_args=extra_args,
    )


@_readonly_tool("tests.replay")
def tests_replay(
    test_id: str = Field(..., description="Test identifier to reproduce"),
    simulator: str | None = Field(
        None,
        description="Simulator override. Defaults to sim_vendor from the test record.",
    ),
    extra_args: str | None = Field(None, description="Extra arguments appended to the command"),
) -> dict[str, Any]:
    return core.generate_replay_command(
        get_store(),
        test_id=test_id,
        simulator=simulator,
        extra_args=extra_args,
    )


# ============================================================================
# v2.0.0: Live simulation status
# ============================================================================


@_readonly_tool("sim.status")
def sim_status(
    suite: str | None = Field(
        None,
        description="Suite name to locate the live_status.json under artifact roots.",
    ),
    status_path: str | None = Field(
        None,
        description="Explicit path to live_status.json. Overrides automatic search.",
    ),
) -> dict[str, Any]:
    return core.get_sim_status(get_store(), suite=suite, status_path=status_path)


# ============================================================================
# v2.0.0: SVA / Formal property status
# ============================================================================


@_readonly_tool("assertions.sva_status")
def assertions_sva_status(
    run_id: str | None = Field(None, description="Filter by run ID"),
    test_id: str | None = Field(None, description="Filter by test ID"),
    status_filter: str | None = Field(
        None,
        description="Status filter: passing|failing|vacuous|disabled|unknown",
    ),
    page: int = Field(1, description="Page number (1-based)"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    return core.get_sva_status(
        get_store(),
        run_id=run_id,
        test_id=test_id,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@_readonly_tool("assertions.vacuity")
def assertions_vacuity(
    run_id: str | None = Field(None, description="Filter by run ID"),
    test_id: str | None = Field(None, description="Filter by test ID"),
    page: int = Field(1, description="Page number (1-based)"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    return core.get_vacuous_assertions(
        get_store(),
        run_id=run_id,
        test_id=test_id,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# v2.0.0: Coverage closure guidance
# ============================================================================


@_readonly_tool("coverage.gaps")
def coverage_gaps(
    suite: str | None = Field(None, description="Filter to a specific suite"),
    kind: str | None = Field(
        None,
        description="Coverage kind filter: functional|code|assertion|toggle|fsm|unknown",
    ),
    threshold_pct: float = Field(
        100.0,
        description="Report metrics with coverage below this percentage (default: 100.0 = all gaps)",
    ),
    page: int = Field(1, description="Page number (1-based)"),
    page_size: int = Field(50, description="Items per page"),
) -> dict[str, Any]:
    return core.get_coverage_gaps(
        get_store(),
        suite=suite,
        kind=kind,
        threshold_pct=threshold_pct,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# DV Intelligence tools — v2.1.0
# =============================================================================


@_readonly_tool("coverage.trend")
def coverage_trend(
    suite: str | None = Field(default=None, description="Filter by suite name."),
    kind: str | None = Field(default=None, description="Coverage kind (functional|code|toggle|...)."),
    limit: int = Field(default=20, description="Maximum number of runs to include (1–100)."),
) -> dict[str, Any]:
    """Show coverage trajectory across sequential runs — are you closing coverage?"""
    return core.get_coverage_trend(get_store(), suite=suite, kind=kind, limit=limit)


@_readonly_tool("runs.cross_sim")
def runs_cross_sim(
    suite_prefix: str | None = Field(default=None, description="Filter by suite name prefix."),
    limit: int = Field(default=100, description="Max divergent tests to return."),
) -> dict[str, Any]:
    """Find tests that pass on one simulator but fail on another — sign-off critical."""
    return core.get_cross_sim_comparison(get_store(), suite_prefix=suite_prefix, limit=limit)


@_readonly_tool("tests.cluster")
def tests_cluster(
    run_id: str | None = Field(default=None, description="Limit to one run; None = all runs."),
    max_clusters: int = Field(default=15, description="Maximum clusters to return (1–50)."),
) -> dict[str, Any]:
    """Group failing tests by root-cause signature — turns 500 failures into 5 root causes."""
    return core.cluster_test_failures(get_store(), run_id=run_id, max_clusters=max_clusters)


@_readonly_tool("regression.health")
def regression_health(
    run_id: str | None = Field(default=None, description="Score a specific run."),
    suite: str | None = Field(default=None, description="Filter to a specific suite."),
) -> dict[str, Any]:
    """Composite DV health score (0–100): pass rate + coverage + assertions + flakiness + cross-sim."""
    return core.get_regression_health(get_store(), run_id=run_id, suite=suite)


@_readonly_tool("coverage.advisor")
def coverage_advisor(
    suite: str | None = Field(default=None, description="Filter by suite name."),
    kind: str | None = Field(default=None, description="Coverage kind filter."),
    max_recommendations: int = Field(default=10, description="Max advisories to return (1–25)."),
) -> dict[str, Any]:
    """Generate SystemVerilog constraint + UVM sequence snippets to hit uncovered bins."""
    return core.get_coverage_advisor(
        get_store(), suite=suite, kind=kind, max_recommendations=max_recommendations
    )


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="Sentinel DV MCP server")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config.yaml (or set SENTINEL_DV_CONFIG)",
    )
    args = parser.parse_args(argv)

    try:
        init_server(args.config)
    except Exception as exc:
        print(f"Failed to initialize Sentinel DV: {exc}", file=sys.stderr)
        sys.exit(1)

    mcp.run()


if __name__ == "__main__":
    main()
