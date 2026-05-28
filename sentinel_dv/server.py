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


# ============================================================================
# Discovery tools
# ============================================================================


@mcp.tool(name="runs.list")
@_tool_wrapper
def runs_list(
    suite: str | None = Field(None, description="Filter by suite name"),
    status: str | None = Field(None, description="Filter by run status (pass|fail|error)"),
    ci_system: str | None = Field(None, description="Filter by CI system"),
    page: int = Field(1, description="Page number (1-based)"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    """List indexed verification runs."""
    return core.list_runs(
        get_store(), suite=suite, status=status, ci_system=ci_system, page=page, page_size=page_size
    )


@mcp.tool(name="runs.get")
@_tool_wrapper
def runs_get(
    run_id: str = Field(..., description="Run identifier"),
) -> dict[str, Any]:
    """Get detailed information about a run."""
    return core.get_run_details(get_store(), run_id)


@mcp.tool(name="tests.list")
@_tool_wrapper
def tests_list(
    run_id: str | None = Field(None, description="Filter by run ID"),
    framework: str | None = Field(None, description="Filter by framework (uvm|cocotb)"),
    status: str | None = Field(None, description="Filter by status (pass|fail|error)"),
    name_pattern: str | None = Field(None, description="Filter by name substring"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    """List tests with filtering and pagination."""
    return core.list_tests(
        get_store(),
        run_id=run_id,
        framework=framework,
        status=status,
        name_pattern=name_pattern,
        page=page,
        page_size=page_size,
    )


@mcp.tool(name="assertions.list")
@_tool_wrapper
def assertions_list(
    scope: str | None = Field(None, description="Filter by scope"),
    name_pattern: str | None = Field(None, description="Filter by assertion name"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    """List assertion definitions."""
    return core.list_assertions(
        get_store(), scope=scope, name_pattern=name_pattern, page=page, page_size=page_size
    )


@mcp.tool(name="coverage.list")
@_tool_wrapper
def coverage_list(
    run_id: str | None = Field(None, description="Filter by run ID"),
    kind: str | None = Field(None, description="Coverage kind (functional|line|...)"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    """List coverage summaries."""
    return core.list_coverage(get_store(), run_id=run_id, kind=kind, page=page, page_size=page_size)


# ============================================================================
# Detail tools
# ============================================================================


@mcp.tool(name="tests.get")
@_tool_wrapper
def tests_get(
    test_id: str = Field(..., description="Test identifier"),
) -> dict[str, Any]:
    """Get full test details."""
    return core.get_test_details(get_store(), test_id)


@mcp.tool(name="tests.topology")
@_tool_wrapper
def tests_topology(
    test_id: str = Field(..., description="Test identifier"),
) -> dict[str, Any]:
    """Get test/UVM topology."""
    return core.get_test_topology(get_store(), test_id)


@mcp.tool(name="assertions.get")
@_tool_wrapper
def assertions_get(
    assertion_id: str = Field(..., description="Assertion identifier"),
) -> dict[str, Any]:
    """Get assertion definition."""
    return core.get_assertion_details(get_store(), assertion_id)


# ============================================================================
# Analysis tools
# ============================================================================


@mcp.tool(name="failures.list")
@_tool_wrapper
def failures_list(
    test_id: str | None = Field(None, description="Filter by test ID"),
    run_id: str | None = Field(None, description="Filter by run ID"),
    category: str | None = Field(None, description="Failure category"),
    severity: str | None = Field(None, description="Severity"),
    tags_any: list[str] | None = Field(None, description="Match any of these tags"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    """List failure events."""
    return core.list_failures(
        get_store(),
        test_id=test_id,
        run_id=run_id,
        category=category,
        severity=severity,
        tags_any=tags_any,
        page=page,
        page_size=page_size,
    )


@mcp.tool(name="assertions.failures")
@_tool_wrapper
def assertions_failures(
    run_id: str | None = Field(None, description="Filter by run ID"),
    test_id: str | None = Field(None, description="Filter by test ID"),
    assertion_id: str | None = Field(None, description="Filter by assertion ID"),
    page: int = Field(1, description="Page number"),
    page_size: int = Field(100, description="Items per page"),
) -> dict[str, Any]:
    """List runtime assertion failures."""
    return core.list_assertion_failures(
        get_store(),
        run_id=run_id,
        test_id=test_id,
        assertion_id=assertion_id,
        page=page,
        page_size=page_size,
    )


@mcp.tool(name="coverage.summary")
@_tool_wrapper
def coverage_summary(
    run_id: str = Field(..., description="Run identifier"),
    kind: str | None = Field(None, description="Optional coverage kind filter"),
) -> dict[str, Any]:
    """Get coverage summaries for a run."""
    return core.get_coverage_summary(get_store(), run_id, kind=kind)


# ============================================================================
# Regression tools
# ============================================================================


@mcp.tool(name="regressions.summary")
@_tool_wrapper
def regressions_summary(
    suite: str = Field(..., description="Suite name"),
    window_days: int = Field(7, description="Time window in days"),
) -> dict[str, Any]:
    """Regression pass rate and top failure signatures."""
    return core.get_regression_summary(get_store(), suite=suite, window_days=window_days)


@mcp.tool(name="runs.diff")
@_tool_wrapper
def runs_diff(
    base_run_id: str = Field(..., description="Base run ID"),
    compare_run_id: str = Field(..., description="Compare run ID"),
) -> dict[str, Any]:
    """Compare two runs."""
    return core.compare_runs(get_store(), base_run_id=base_run_id, compare_run_id=compare_run_id)


# ============================================================================
# Waveform tools (experimental)
# ============================================================================


@mcp.tool(name="wave.signals")
@_tool_wrapper
def wave_signals(
    test_id: str = Field(..., description="Test identifier"),
    start_time_ns: int | None = Field(
        None,
        description="Optional window start in nanoseconds (e.g. 20000 for 20 µs). VCD: re-parses source trace.",
    ),
    end_time_ns: int | None = Field(
        None,
        description="Optional window end in nanoseconds (e.g. 30000 for 30 µs). Requires start_time_ns.",
    ),
) -> dict[str, Any]:
    """List signals from a precomputed waveform summary."""
    return core.wave_signals(
        get_store(), test_id, start_time_ns=start_time_ns, end_time_ns=end_time_ns
    )


@mcp.tool(name="wave.summary")
@_tool_wrapper
def wave_summary(
    test_id: str = Field(..., description="Test identifier"),
    start_time_ns: int | None = Field(
        None,
        description="Optional window start in nanoseconds (e.g. 20000 for 20 µs). VCD: re-parses source trace.",
    ),
    end_time_ns: int | None = Field(
        None,
        description="Optional window end in nanoseconds (e.g. 30000 for 30 µs). Requires start_time_ns.",
    ),
) -> dict[str, Any]:
    """Get precomputed waveform summary for a test."""
    return core.wave_summary(
        get_store(), test_id, start_time_ns=start_time_ns, end_time_ns=end_time_ns
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
