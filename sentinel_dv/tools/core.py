"""MCP tool implementations for Sentinel DV."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel_dv.adapters.vcd_summary import VcdSummaryParser
from sentinel_dv.config import get_config
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.schemas.versioning import CURRENT_SCHEMA_VERSION
from sentinel_dv.tools.errors import ToolError
from sentinel_dv.tools.validate import (
    clamp_pagination,
    detail_response,
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
    return detail_response({"run": run})


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
    return detail_response({"run_id": run_id, "summaries": results})


def get_regression_summary(
    store: IndexStore,
    suite: str,
    window_days: int = 7,
) -> dict[str, Any]:
    """Regression analytics for a suite."""
    if window_days < 1 or window_days > 365:
        raise ToolError("INVALID_ARGUMENT", "window_days must be between 1 and 365")
    summary = store.regression_summary(suite=suite, window_days=window_days)
    return detail_response(summary)


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
    return detail_response(diff)


def _resolve_artifact_path(relative_path: str) -> Path:
    """Resolve a relative artifact path under configured read-only roots."""
    for root in get_config().artifact_roots:
        root_path = Path(root).resolve()
        candidate = (root_path / relative_path).resolve()
        try:
            candidate.relative_to(root_path)
        except ValueError:
            continue
        if candidate.is_file() and not candidate.is_symlink():
            max_bytes = get_config().security.max_artifact_bytes
            if candidate.stat().st_size > max_bytes:
                raise ToolError(
                    "LIMIT_EXCEEDED",
                    f"Waveform artifact exceeds max_artifact_bytes ({max_bytes}): {relative_path}",
                )
            return candidate
    raise ToolError("NOT_FOUND", f"Waveform artifact not found: {relative_path}")


def _load_waveform_summary(
    store: IndexStore,
    test_id: str,
    start_time_ns: int | None = None,
    end_time_ns: int | None = None,
) -> dict[str, Any]:
    """Load indexed summary, optionally re-parsing VCD for a time window."""
    if start_time_ns is not None and end_time_ns is not None and start_time_ns > end_time_ns:
        raise ToolError("INVALID_ARGUMENT", "start_time_ns must be <= end_time_ns")
    if (start_time_ns is None) ^ (end_time_ns is None):
        raise ToolError(
            "INVALID_ARGUMENT",
            "Provide both start_time_ns and end_time_ns to query a time window.",
        )

    record = store.get_waveform_summary(test_id)
    if not record:
        raise ToolError(
            "NOT_FOUND",
            "No waveform summary indexed for this test. "
            "Enable adapters.waveform_summary and add a *.wave.json or *.vcd file.",
        )

    if start_time_ns is None and end_time_ns is None:
        return record

    if record["format"] == "vcd-summary":
        vcd_path = _resolve_artifact_path(record["source_path"])
        parsed = VcdSummaryParser().parse(
            vcd_path,
            start_time_ns=start_time_ns,
            end_time_ns=end_time_ns,
        )
        return {
            "test_id": test_id,
            "format": parsed["format"],
            "end_time_ns": parsed["end_time_ns"],
            "source_path": record["source_path"],
            "summary": parsed,
        }

    summary = dict(record["summary"])
    highlights = summary.get("highlights", [])
    if start_time_ns is not None or end_time_ns is not None:
        filtered = []
        for item in highlights:
            t = item.get("time_ns")
            if t is None:
                continue
            if start_time_ns is not None and t < start_time_ns:
                continue
            if end_time_ns is not None and t > end_time_ns:
                continue
            filtered.append(item)
        summary["highlights"] = filtered
        summary.setdefault("metadata", {})["window"] = {
            "start_time_ns": start_time_ns,
            "end_time_ns": end_time_ns,
            "note": "JSON summaries filter highlights only; use VCD for per-signal window values",
        }
    return {
        **record,
        "summary": summary,
        "end_time_ns": end_time_ns if end_time_ns is not None else record["end_time_ns"],
    }


def wave_signals(
    store: IndexStore,
    test_id: str,
    start_time_ns: int | None = None,
    end_time_ns: int | None = None,
) -> dict[str, Any]:
    """List signals from a precomputed waveform summary indexed for the test."""
    validate_id(test_id, "test_id")
    if not store.get_test(test_id):
        raise ToolError("NOT_FOUND", f"Test not found: {test_id}")

    record = _load_waveform_summary(store, test_id, start_time_ns, end_time_ns)
    summary = record["summary"]
    signals = summary.get("signals", [])
    max_signals = get_config().security.max_wave_signals
    truncated = len(signals) > max_signals
    if truncated:
        signals = signals[:max_signals]

    return detail_response(
        {
            "test_id": test_id,
            "format": record["format"],
            "end_time_ns": record["end_time_ns"],
            "start_time_ns": start_time_ns,
            "end_time_ns_query": end_time_ns,
            "signals": signals,
            "signal_count": summary.get("signal_count", len(signals)),
            "truncated": truncated,
            "source_path": record["source_path"],
        }
    )


def wave_summary(
    store: IndexStore,
    test_id: str,
    start_time_ns: int | None = None,
    end_time_ns: int | None = None,
) -> dict[str, Any]:
    """Get precomputed waveform summary for a test."""
    validate_id(test_id, "test_id")
    if not store.get_test(test_id):
        raise ToolError("NOT_FOUND", f"Test not found: {test_id}")

    record = _load_waveform_summary(store, test_id, start_time_ns, end_time_ns)
    summary = record["summary"]
    return detail_response(
        {
            "test_id": test_id,
            "format": record["format"],
            "end_time_ns": record["end_time_ns"],
            "start_time_ns": start_time_ns,
            "end_time_ns_query": end_time_ns,
            "signal_count": summary.get("signal_count"),
            "highlights": summary.get("highlights", []),
            "metadata": summary.get("metadata", {}),
            "evidence": summary.get("evidence"),
            "source_path": record["source_path"],
        }
    )
