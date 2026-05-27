"""MCP tool implementations for Sentinel DV."""

from __future__ import annotations

from typing import Any

from sentinel_dv.config import get_config
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.schemas.versioning import CURRENT_SCHEMA_VERSION
from sentinel_dv.tools.errors import ToolError
from sentinel_dv.tools.validate import (
    clamp_pagination,
    item_response,
    list_response,
    validate_id,
)


def list_runs(
    store: IndexStore,
    suite: str | None = None,
    status: str | None = None,
    ci_system: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List verification runs with pagination."""
    page, page_size = clamp_pagination(page, page_size)
    results, total = store.query_runs(
        suite=suite,
        status=status,
        ci_system=ci_system,
        page=page,
        page_size=page_size,
    )
    return list_response("runs", results, page, page_size, total)


def get_run_details(store: IndexStore, run_id: str) -> dict[str, Any]:
    """Get run metadata by ID."""
    validate_id(run_id, "run_id")
    run = store.get_run(run_id)
    if not run:
        raise ToolError("NOT_FOUND", f"Run not found: {run_id}")
    return {"schema_version": CURRENT_SCHEMA_VERSION, "run": run}


def list_tests(
    store: IndexStore,
    run_id: str | None = None,
    framework: str | None = None,
    status: str | None = None,
    name_pattern: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List tests with filters."""
    if run_id:
        validate_id(run_id, "run_id")
    page, page_size = clamp_pagination(page, page_size)
    results, total = store.query_tests(
        run_id=run_id,
        framework=framework,
        status=status,
        name_pattern=name_pattern,
        page=page,
        page_size=page_size,
    )
    return list_response("tests", results, page, page_size, total)


def get_test_details(store: IndexStore, test_id: str) -> dict[str, Any]:
    """Get a single test record."""
    validate_id(test_id, "test_id")
    test = store.get_test(test_id)
    if not test:
        raise ToolError("NOT_FOUND", f"Test not found: {test_id}")
    return item_response(test)


def get_test_topology(store: IndexStore, test_id: str) -> dict[str, Any]:
    """Get UVM/test topology for a test."""
    validate_id(test_id, "test_id")
    topology = store.get_topology(test_id)
    if topology is None:
        raise ToolError("NOT_FOUND", f"Topology not found for test: {test_id}")
    return item_response({"test_id": test_id, **topology})


def list_failures(
    store: IndexStore,
    test_id: str | None = None,
    run_id: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    tags_any: list[str] | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List failure events."""
    if test_id:
        validate_id(test_id, "test_id")
    if run_id:
        validate_id(run_id, "run_id")
    page, page_size = clamp_pagination(page, page_size)
    results, total = store.query_failures(
        test_id=test_id,
        run_id=run_id,
        category=category,
        severity=severity,
        tags_any=tags_any,
        page=page,
        page_size=page_size,
    )
    return list_response("failures", results, page, page_size, total)


def list_assertions(
    store: IndexStore,
    scope: str | None = None,
    name_pattern: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List assertion definitions."""
    page, page_size = clamp_pagination(page, page_size)
    results, total = store.query_assertions(
        scope=scope,
        name_pattern=name_pattern,
        page=page,
        page_size=page_size,
    )
    return list_response("assertions", results, page, page_size, total)


def get_assertion_details(store: IndexStore, assertion_id: str) -> dict[str, Any]:
    """Get assertion definition by ID."""
    validate_id(assertion_id, "assertion_id")
    assertion = store.get_assertion(assertion_id)
    if not assertion:
        raise ToolError("NOT_FOUND", f"Assertion not found: {assertion_id}")
    return item_response(assertion)


def list_assertion_failures(
    store: IndexStore,
    run_id: str | None = None,
    test_id: str | None = None,
    assertion_id: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List runtime assertion failures."""
    if run_id:
        validate_id(run_id, "run_id")
    if test_id:
        validate_id(test_id, "test_id")
    if assertion_id:
        validate_id(assertion_id, "assertion_id")
    page, page_size = clamp_pagination(page, page_size)
    results, total = store.query_assertion_failures(
        run_id=run_id,
        test_id=test_id,
        assertion_id=assertion_id,
        page=page,
        page_size=page_size,
    )
    return list_response("assertion_failures", results, page, page_size, total)


def list_coverage(
    store: IndexStore,
    run_id: str | None = None,
    kind: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List coverage summaries."""
    if run_id:
        validate_id(run_id, "run_id")
    page, page_size = clamp_pagination(page, page_size)
    results, total = store.query_coverage_summaries(
        run_id=run_id,
        kind=kind,
        page=page,
        page_size=page_size,
    )
    return list_response("coverage", results, page, page_size, total)


def get_coverage_summary(store: IndexStore, run_id: str, kind: str | None = None) -> dict[str, Any]:
    """Get aggregated coverage for a run (first matching summary)."""
    validate_id(run_id, "run_id")
    results, total = store.query_coverage_summaries(run_id=run_id, kind=kind, page=1, page_size=50)
    if total == 0:
        raise ToolError("NOT_FOUND", f"No coverage found for run: {run_id}")
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "run_id": run_id,
        "summaries": results,
    }


def get_regression_summary(
    store: IndexStore,
    suite: str,
    window_days: int = 7,
) -> dict[str, Any]:
    """Regression analytics for a suite."""
    if window_days < 1 or window_days > 365:
        raise ToolError("INVALID_ARGUMENT", "window_days must be between 1 and 365")
    summary = store.regression_summary(suite=suite, window_days=window_days)
    return {"schema_version": CURRENT_SCHEMA_VERSION, **summary}


def compare_runs(
    store: IndexStore,
    base_run_id: str,
    compare_run_id: str,
) -> dict[str, Any]:
    """Diff two runs."""
    validate_id(base_run_id, "base_run_id")
    validate_id(compare_run_id, "compare_run_id")
    try:
        diff = store.diff_runs(base_run_id, compare_run_id)
    except ValueError as exc:
        raise ToolError("NOT_FOUND", str(exc)) from exc
    return {"schema_version": CURRENT_SCHEMA_VERSION, **diff}


def wave_signals(
    store: IndexStore,
    test_id: str,
) -> dict[str, Any]:
    """List signals from a precomputed waveform summary indexed for the test."""
    validate_id(test_id, "test_id")
    if not store.get_test(test_id):
        raise ToolError("NOT_FOUND", f"Test not found: {test_id}")

    record = store.get_waveform_summary(test_id)
    if not record:
        raise ToolError(
            "NOT_FOUND",
            "No waveform summary indexed for this test. "
            "Enable adapters.waveform_summary and add a *.wave.json file with matching test_name.",
        )

    summary = record["summary"]
    signals = summary.get("signals", [])
    max_signals = get_config().security.max_coverage_metrics
    truncated = len(signals) > max_signals
    if truncated:
        signals = signals[:max_signals]

    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "test_id": test_id,
        "format": record["format"],
        "end_time_ns": record["end_time_ns"],
        "signals": signals,
        "signal_count": summary.get("signal_count", len(signals)),
        "truncated": truncated,
        "source_path": record["source_path"],
    }


def wave_summary(
    store: IndexStore,
    test_id: str,
) -> dict[str, Any]:
    """Get precomputed waveform summary for a test."""
    validate_id(test_id, "test_id")
    if not store.get_test(test_id):
        raise ToolError("NOT_FOUND", f"Test not found: {test_id}")

    record = store.get_waveform_summary(test_id)
    if not record:
        raise ToolError(
            "NOT_FOUND",
            "No waveform summary indexed for this test. "
            "Enable adapters.waveform_summary and add a *.wave.json file with matching test_name.",
        )

    summary = record["summary"]
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "test_id": test_id,
        "format": record["format"],
        "end_time_ns": record["end_time_ns"],
        "signal_count": summary.get("signal_count"),
        "highlights": summary.get("highlights", []),
        "metadata": summary.get("metadata", {}),
        "evidence": summary.get("evidence"),
        "source_path": record["source_path"],
    }
