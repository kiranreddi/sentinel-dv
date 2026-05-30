"""MCP tool implementations for Sentinel DV."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from sentinel_dv.adapters.vcd_summary import VcdSummaryParser
from sentinel_dv.config import get_config
from sentinel_dv.indexing import query as index_query
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.schemas.assertions import AssertionFailure, AssertionInfo
from sentinel_dv.schemas.common import EvidenceRef
from sentinel_dv.schemas.coverage import CoverageSummary
from sentinel_dv.tools.errors import ToolError
from sentinel_dv.tools.validate import (
    clamp_pagination,
    detail_response,
    item_response,
    list_response,
    validate_id,
)


def _validate_assertion_payload(assertion: dict[str, Any]) -> None:
    """Validate stored assertion rows against AssertionInfo schema."""
    try:
        AssertionInfo(
            id=assertion["assertion_id"],
            language=assertion["language"],
            name=assertion["name"],
            scope=assertion["scope"],
            file=assertion["file"],
            line=assertion["line"],
            intent=assertion.get("intent"),
            signals=assertion.get("signals", []),
            enabled_in_run=assertion.get("enabled_in_run"),
        )
    except ValidationError as exc:
        raise ToolError("INTERNAL", f"Invalid assertion payload in index: {exc}") from exc


def _validate_assertion_failure_payload(failure: dict[str, Any]) -> None:
    """Validate stored assertion failure rows against AssertionFailure schema."""
    try:
        AssertionFailure(
            assertion_id=failure["assertion_id"],
            test_id=failure["test_id"],
            time_ns=failure.get("time_ns"),
            message=failure.get("message", ""),
            evidence=[],
        )
    except ValidationError as exc:
        raise ToolError("INTERNAL", f"Invalid assertion failure payload in index: {exc}") from exc


def _validate_coverage_summary_payload(summary: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize coverage summary rows."""
    evidence = summary.get("evidence")
    if evidence is None:
        normalized_evidence: list[EvidenceRef] = []
    elif isinstance(evidence, dict):
        normalized_evidence = [EvidenceRef(**evidence)]
    else:
        normalized_evidence = [
            item if isinstance(item, EvidenceRef) else EvidenceRef(**item) for item in evidence
        ]
    try:
        CoverageSummary(
            run_id=summary["run_id"],
            test_id=summary.get("test_id"),
            kind=summary["kind"],
            metrics=summary.get("metrics", []),
            evidence=normalized_evidence,
        )
    except ValidationError as exc:
        raise ToolError("INTERNAL", f"Invalid coverage payload in index: {exc}") from exc
    normalized = dict(summary)
    normalized["evidence"] = [item.model_dump() for item in normalized_evidence]
    return normalized


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
    results, total = index_query.query_runs(
        store,
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
    results, total = index_query.query_tests(
        store,
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
    if not store.get_test(test_id):
        raise ToolError("NOT_FOUND", f"Test not found: {test_id}")
    topology = store.get_topology(test_id)
    if topology is None:
        raise ToolError(
            "TOPOLOGY_NOT_INDEXED",
            f"No UVM/topology indexed for test {test_id}. "
            "Re-index with adapters.uvm enabled and ensure the test log contains topology.",
            details={"test_id": test_id},
        )
    return item_response({"test_id": test_id, **topology})


def list_failures(
    store: IndexStore,
    test_id: str | None = None,
    run_id: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    tags_any: list[str] | None = None,
    include_evidence: bool = False,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List failure events."""
    if test_id:
        validate_id(test_id, "test_id")
    if run_id:
        validate_id(run_id, "run_id")
    page, page_size = clamp_pagination(page, page_size)
    results, total = index_query.query_failures(
        store,
        test_id=test_id,
        run_id=run_id,
        category=category,
        severity=severity,
        tags_any=tags_any,
        include_evidence=include_evidence,
        page=page,
        page_size=page_size,
    )
    return list_response("failures", results, page, page_size, total)


def list_assertions(
    store: IndexStore,
    scope: str | None = None,
    name_pattern: str | None = None,
    protocol: str | None = None,
    tag: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List assertion definitions."""
    page, page_size = clamp_pagination(page, page_size)
    results, total = index_query.query_assertions(
        store,
        scope=scope,
        name_pattern=name_pattern,
        protocol=protocol,
        tag=tag,
        page=page,
        page_size=page_size,
    )
    for row in results:
        _validate_assertion_payload(row)
    return list_response("assertions", results, page, page_size, total)


def get_assertion_details(store: IndexStore, assertion_id: str) -> dict[str, Any]:
    """Get assertion definition by ID."""
    validate_id(assertion_id, "assertion_id")
    assertion = store.get_assertion(assertion_id)
    if not assertion:
        raise ToolError("NOT_FOUND", f"Assertion not found: {assertion_id}")
    _validate_assertion_payload(assertion)
    return item_response(assertion)


def list_assertion_failures(
    store: IndexStore,
    run_id: str | None = None,
    test_id: str | None = None,
    assertion_id: str | None = None,
    start_time_ns: int | None = None,
    end_time_ns: int | None = None,
    include_evidence: bool = False,
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
    if start_time_ns is not None and end_time_ns is not None and start_time_ns > end_time_ns:
        raise ToolError("INVALID_ARGUMENT", "start_time_ns must be <= end_time_ns")
    if (start_time_ns is None) ^ (end_time_ns is None):
        raise ToolError(
            "INVALID_ARGUMENT",
            "Provide both start_time_ns and end_time_ns for a time window.",
        )
    page, page_size = clamp_pagination(page, page_size)
    results, total = index_query.query_assertion_failures(
        store,
        run_id=run_id,
        test_id=test_id,
        assertion_id=assertion_id,
        start_time_ns=start_time_ns,
        end_time_ns=end_time_ns,
        include_evidence=include_evidence,
        page=page,
        page_size=page_size,
    )
    for row in results:
        _validate_assertion_failure_payload(row)
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
    results, total = index_query.query_coverage_summaries(
        store,
        run_id=run_id,
        kind=kind,
        page=page,
        page_size=page_size,
    )
    normalized = [_validate_coverage_summary_payload(row) for row in results]
    return list_response("coverage", normalized, page, page_size, total)


def get_coverage_summary(
    store: IndexStore,
    run_id: str,
    kind: str | None = None,
    include_evidence: bool = False,
) -> dict[str, Any]:
    """Get bounded coverage summaries for a run."""
    validate_id(run_id, "run_id")
    max_rows = get_config().security.max_coverage_metrics
    results, total = index_query.query_coverage_summaries(
        store, run_id=run_id, kind=kind, page=1, page_size=max_rows
    )
    if total == 0:
        raise ToolError("NOT_FOUND", f"No coverage found for run: {run_id}")
    if total > max_rows:
        raise ToolError(
            "LIMIT_EXCEEDED",
            (
                f"coverage.summary matched {total} summaries, exceeding max_coverage_metrics "
                f"({max_rows}). Refine with kind or increase security.max_coverage_metrics."
            ),
        )
    normalized = [_validate_coverage_summary_payload(row) for row in results]
    if not include_evidence:
        for row in normalized:
            row.pop("evidence", None)
    return detail_response(
        {
            "run_id": run_id,
            "summaries": normalized,
            "total_summaries": total,
            "truncated": False,
        }
    )


def get_regression_summary(
    store: IndexStore,
    suite: str,
    window_days: int = 7,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Regression analytics for a suite."""
    if window_days < 1 or window_days > 365:
        raise ToolError("INVALID_ARGUMENT", "window_days must be between 1 and 365")
    summary = store.regression_summary(suite=suite, window_days=window_days, as_of=as_of)
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


def _infer_highlight_category(highlight: dict[str, Any]) -> str:
    """Classify a highlight for grouped waveform summaries."""
    explicit = highlight.get("category") or highlight.get("type")
    if explicit:
        return str(explicit)
    note = (highlight.get("note") or "").lower()
    if "toggle" in note:
        return "toggle_activity"
    if "reset" in note:
        return "reset_event"
    if "fsm" in note or "state" in note:
        return "fsm"
    return "event"


def _group_highlights(highlights: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group highlights by category for DV-oriented summaries."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in highlights:
        category = _infer_highlight_category(item)
        groups.setdefault(category, []).append(item)
    return groups


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


def _waveform_signals_payload(
    record: dict[str, Any],
    summary: dict[str, Any],
    *,
    test_id: str,
    start_time_ns: int | None,
    end_time_ns: int | None,
) -> dict[str, Any]:
    """Build bounded per-signal list from a loaded waveform summary."""
    signals = summary.get("signals", [])
    if not signals and summary.get("signal_groups"):
        for group in summary["signal_groups"]:
            signals.extend(group.get("signals", []))
    max_signals = get_config().security.max_wave_signals
    truncated = len(signals) > max_signals
    if truncated:
        signals = signals[:max_signals]
    return {
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
    return detail_response(
        _waveform_signals_payload(
            record, summary, test_id=test_id, start_time_ns=start_time_ns, end_time_ns=end_time_ns
        )
    )


def wave_summary(
    store: IndexStore,
    test_id: str,
    start_time_ns: int | None = None,
    end_time_ns: int | None = None,
    include_signals: bool = False,
) -> dict[str, Any]:
    """Get precomputed waveform summary for a test."""
    validate_id(test_id, "test_id")
    if not store.get_test(test_id):
        raise ToolError("NOT_FOUND", f"Test not found: {test_id}")

    record = _load_waveform_summary(store, test_id, start_time_ns, end_time_ns)
    summary = record["summary"]
    highlights = summary.get("highlights", [])
    payload: dict[str, Any] = {
        "test_id": test_id,
        "format": record["format"],
        "end_time_ns": record["end_time_ns"],
        "start_time_ns": start_time_ns,
        "end_time_ns_query": end_time_ns,
        "signal_count": summary.get("signal_count"),
        "highlights": highlights,
        "highlight_groups": _group_highlights(highlights),
        "signal_groups": summary.get("signal_groups"),
        "metadata": summary.get("metadata", {}),
        "evidence": summary.get("evidence"),
        "source_path": record["source_path"],
    }
    if include_signals:
        payload.update(
            _waveform_signals_payload(
                record,
                summary,
                test_id=test_id,
                start_time_ns=start_time_ns,
                end_time_ns=end_time_ns,
            )
        )
    return detail_response(payload)


# ==============================================================================
# v2.0.0: Feature 1 — Regression Job Submission
# ==============================================================================


def generate_submit_command(
    store: IndexStore,
    suite: str,
    simulator: str | None = None,
    seed: int | None = None,
    test_filter: str | None = None,
    extra_args: str | None = None,
) -> dict[str, Any]:
    """Generate a regression job submission command for a given suite.

    The server **never executes commands**. All output is a dry-run shell
    command string for the operator to review and run.

    Args:
        store: The index store (used to validate the suite exists).
        suite: Suite name (must match existing runs or be a known suite).
        simulator: Simulator override. Uses submit.default_simulator if not given.
        seed: Optional integer seed to embed in the command.
        test_filter: Optional test name filter (glob or regex).
        extra_args: Extra simulator arguments appended to the command.

    Returns:
        SubmitResponse-shaped dict.

    Raises:
        ToolError: INVALID_INPUT if suite/test_filter names contain unsafe characters.
        ToolError: CONFIG_ERROR if submit config is not enabled or no template found.
        ToolError: COMMAND_TOO_LONG if the generated command exceeds the limit.
    """
    import re
    import shlex

    cfg = get_config()
    submit_cfg = cfg.submit

    if not submit_cfg.enabled:
        raise ToolError(
            "CONFIG_ERROR",
            "Regression submission is not enabled. Set submit.enabled=true in config.yaml "
            "and configure at least one simulator template.",
        )

    # Validate suite name
    if not re.fullmatch(r"[a-zA-Z0-9_\-\.]+", suite):
        raise ToolError(
            "INVALID_INPUT",
            f"Invalid suite name '{suite}'. Only letters, digits, hyphens, underscores, "
            "and dots are allowed.",
        )

    # Validate test_filter name
    if test_filter and not re.fullmatch(r"[a-zA-Z0-9_\-\.\*\?]+", test_filter):
        raise ToolError(
            "INVALID_INPUT",
            f"Invalid test_filter '{test_filter}'. Only letters, digits, hyphens, "
            "underscores, dots, and glob wildcards (* ?) are allowed.",
        )

    # Resolve simulator
    sim_name = (simulator or submit_cfg.default_simulator).lower()
    template_obj = next(
        (t for t in submit_cfg.templates if t.simulator.lower() == sim_name), None
    )
    if template_obj is None:
        available = [t.simulator for t in submit_cfg.templates]
        raise ToolError(
            "CONFIG_ERROR",
            f"No template configured for simulator '{sim_name}'. "
            f"Available: {available or ['none']}. Add a template under submit.templates in config.yaml.",
        )

    # Build placeholder values
    artifact_root = str(cfg.artifact_roots[0]) if cfg.artifact_roots else ""
    seed_str = str(seed) if seed is not None else "0"
    filter_str = shlex.quote(test_filter) if test_filter else ""
    extra_str = shlex.quote(extra_args) if extra_args else shlex.quote(template_obj.default_args)

    cmd = template_obj.template.format(
        suite=shlex.quote(suite),
        seed=seed_str,
        test_filter=filter_str,
        extra_args=extra_str,
        artifact_root=shlex.quote(artifact_root),
    )

    # Enforce command length limit
    max_len = cfg.security.max_command_length
    if len(cmd) > max_len:
        raise ToolError(
            "COMMAND_TOO_LONG",
            f"Generated command ({len(cmd)} chars) exceeds max_command_length ({max_len}). "
            "Shorten suite name, test_filter, or extra_args.",
        )

    # Optionally wrap in scheduler command
    scheduler_cmd: str | None = None
    if submit_cfg.lsf_queue:
        scheduler_cmd = f"bsub -q {shlex.quote(submit_cfg.lsf_queue)} {cmd}"
    elif submit_cfg.slurm_partition:
        scheduler_cmd = f"sbatch -p {shlex.quote(submit_cfg.slurm_partition)} {cmd}"

    return {
        "suite": suite,
        "simulator": sim_name,
        "seed": seed,
        "command": cmd,
        "scheduler_command": scheduler_cmd,
        "dry_run": True,
        "note": (
            "This is a generated command. Sentinel DV never executes it. "
            "Review and run it in your shell or CI pipeline."
        ),
    }


# ==============================================================================
# v2.0.0: Feature 2 — Live Simulator Status
# ==============================================================================


def get_sim_status(
    store: IndexStore,
    suite: str | None = None,
    status_path: str | None = None,
) -> dict[str, Any]:
    """Read live simulation progress from a live_status.json file.

    The server reads a JSON file written by the simulator harness — it never
    calls the simulator directly.

    Args:
        store: The index store (not used for reads, kept for API symmetry).
        suite: Suite name to search under artifact roots.
        status_path: Explicit path to a live_status.json file.

    Returns:
        LiveSimProgress-shaped dict, or error if no file found.

    Raises:
        ToolError: NOT_FOUND if no live status file could be located.
        ToolError: CONFIG_ERROR if the live_sim adapter is not enabled.
    """
    cfg = get_config()
    if not cfg.adapters.live_sim:
        raise ToolError(
            "CONFIG_ERROR",
            "Live simulation adapter is not enabled. Set adapters.live_sim=true in config.yaml.",
        )

    from sentinel_dv.adapters.live_sim import LiveSimAdapter

    adapter = LiveSimAdapter(
        artifact_roots=cfg.artifact_roots,
        max_age_seconds=cfg.adapters.live_sim_max_age_seconds,
    )

    explicit_path = Path(status_path) if status_path else None
    progress = adapter.read(suite=suite, status_path=explicit_path)

    if progress is None:
        loc = status_path or f"artifact roots for suite '{suite}'"
        raise ToolError(
            "NOT_FOUND",
            f"No live_status.json found at {loc}. "
            "Ensure the simulator harness writes the file to <artifact_root>/<suite>/live_status.json.",
        )

    return detail_response(progress.model_dump())


# ==============================================================================
# v2.0.0: Feature 3 — SVA/Formal Property Status
# ==============================================================================


def get_sva_status(
    store: IndexStore,
    run_id: str | None = None,
    test_id: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """Return per-assertion SVA status for a run or test.

    Args:
        store: Index store.
        run_id: Filter to a specific run.
        test_id: Filter to a specific test.
        status_filter: One of: passing, failing, vacuous, disabled, unknown.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Paginated list of SVARunStatus-shaped dicts with category counts.

    Raises:
        ToolError: INVALID_INPUT if status_filter value is not valid.
        ToolError: INVALID_INPUT if run_id or test_id format is invalid.
    """
    valid_statuses = {"passing", "failing", "vacuous", "disabled", "unknown"}
    if status_filter and status_filter not in valid_statuses:
        raise ToolError(
            "INVALID_INPUT",
            f"Invalid status_filter '{status_filter}'. Must be one of: {sorted(valid_statuses)}.",
        )
    if run_id:
        validate_id(run_id, "run_id")
    if test_id:
        validate_id(test_id, "test_id")

    page, page_size = clamp_pagination(page, page_size)

    all_rows = store.query_sva_run_status(
        run_id=run_id,
        test_id=test_id,
        status_filter=status_filter,
        limit=page_size * page + page_size,  # Fetch enough for pagination
    )

    total = len(all_rows)
    offset = (page - 1) * page_size
    paginated = all_rows[offset : offset + page_size]

    # Counts per category for the whole filtered set
    counts: dict[str, int] = {}
    for row in all_rows:
        s = row.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1

    return list_response("sva_status", paginated, page, page_size, total, extra={"counts": counts})


def get_vacuous_assertions(
    store: IndexStore,
    run_id: str | None = None,
    test_id: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """List assertions that fired vacuously (antecedent never held).

    Vacuous firings indicate the assertion never actually checked anything —
    they need review to ensure the testbench exercises the antecedent.

    Args:
        store: Index store.
        run_id: Filter to a specific run.
        test_id: Filter to a specific test.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Paginated list of VacuousAssertion-shaped dicts with recommendations.
    """
    if run_id:
        validate_id(run_id, "run_id")
    if test_id:
        validate_id(test_id, "test_id")

    page, page_size = clamp_pagination(page, page_size)
    cfg = get_config()
    limit = min(cfg.security.max_coverage_gaps, page_size * page + page_size)

    rows = store.query_vacuous_assertions(run_id=run_id, test_id=test_id, limit=limit)

    # Build recommendation for each
    result = []
    for row in rows:
        name = row.get("assertion_name") or row.get("assertion_id", "unknown")
        scope = row.get("scope", "unknown")
        count = row.get("vacuous_count", 0)
        recommendation = (
            f"Assertion '{name}' in '{scope}' fired vacuously {count} time(s). "
            "The assertion antecedent (the premise condition) was never true. "
            "Add stimulus that drives the antecedent to ensure the property is "
            "actually exercised. Review if the assertion captures the intended behaviour."
        )
        result.append({**row, "recommendation": recommendation})

    total = len(result)
    offset = (page - 1) * page_size
    paginated = result[offset : offset + page_size]

    return list_response("vacuous_assertions", paginated, page, page_size, total)


# ==============================================================================
# v2.0.0: Feature 4 — Seed Replay
# ==============================================================================


def generate_replay_command(
    store: IndexStore,
    test_id: str,
    simulator: str | None = None,
    extra_args: str | None = None,
) -> dict[str, Any]:
    """Generate a single-test replay command to reproduce a specific test failure.

    Looks up the test in the index to extract seed, suite, DUT top, and
    simulator information, then generates a shell command using the configured
    replay_template (or falls back to the suite-level template).

    The server **never executes commands**. All output is a dry-run string.

    Args:
        store: Index store.
        test_id: Test identifier to reproduce.
        simulator: Simulator override.
        extra_args: Extra arguments to append.

    Returns:
        ReplayResponse-shaped dict.

    Raises:
        ToolError: NOT_FOUND if test does not exist in the index.
        ToolError: CONFIG_ERROR if submit is not enabled or no template found.
        ToolError: COMMAND_TOO_LONG if generated command is too long.
    """
    import re
    import shlex

    validate_id(test_id, "test_id")
    test = store.get_test(test_id)
    if not test:
        raise ToolError("NOT_FOUND", f"Test not found: {test_id}")

    cfg = get_config()
    submit_cfg = cfg.submit

    if not submit_cfg.enabled:
        raise ToolError(
            "CONFIG_ERROR",
            "Regression submission is not enabled. Set submit.enabled=true in config.yaml.",
        )

    # Extract test metadata
    test_name = str(test.get("name", test_id))
    seed = test.get("seed")
    dut_top = test.get("dut_top")

    # Resolve suite from run
    run_id = test.get("run_id", "")
    run = store.get_run(run_id) if run_id else None
    suite = str(run.get("suite", "")) if run else ""

    if not suite:
        raise ToolError(
            "NOT_FOUND",
            f"Could not determine suite for test {test_id} — run {run_id!r} not found.",
        )

    # Validate names
    if not re.fullmatch(r"[a-zA-Z0-9_\-\.]+", suite):
        raise ToolError("INVALID_INPUT", f"Suite name '{suite}' from index contains unsafe characters.")
    if not re.fullmatch(r"[a-zA-Z0-9_\-\.]+", test_name):
        raise ToolError("INVALID_INPUT", f"Test name '{test_name}' contains unsafe characters.")

    # Resolve simulator
    sim_name = (
        simulator
        or test.get("sim_vendor")
        or submit_cfg.default_simulator
    ).lower()
    template_obj = next(
        (t for t in submit_cfg.templates if t.simulator.lower() == sim_name), None
    )
    if template_obj is None:
        available = [t.simulator for t in submit_cfg.templates]
        raise ToolError(
            "CONFIG_ERROR",
            f"No template configured for simulator '{sim_name}'. Available: {available or ['none']}.",
        )

    artifact_root = str(cfg.artifact_roots[0]) if cfg.artifact_roots else ""
    seed_str = str(seed) if seed is not None else "0"
    extra_str = shlex.quote(extra_args) if extra_args else shlex.quote(template_obj.default_args)

    if template_obj.replay_template:
        cmd = template_obj.replay_template.format(
            test_name=shlex.quote(test_name),
            seed=seed_str,
            dut_top=shlex.quote(dut_top or ""),
            suite=shlex.quote(suite),
            extra_args=extra_str,
            artifact_root=shlex.quote(artifact_root),
        )
    else:
        # Fallback: use submit template with TESTFILTER and SEED overrides
        cmd = template_obj.template.format(
            suite=shlex.quote(suite),
            seed=seed_str,
            test_filter=shlex.quote(test_name),
            extra_args=extra_str,
            artifact_root=shlex.quote(artifact_root),
        )

    max_len = cfg.security.max_command_length
    if len(cmd) > max_len:
        raise ToolError(
            "COMMAND_TOO_LONG",
            f"Generated command ({len(cmd)} chars) exceeds max_command_length ({max_len}).",
        )

    scheduler_cmd: str | None = None
    if submit_cfg.lsf_queue:
        scheduler_cmd = f"bsub -q {shlex.quote(submit_cfg.lsf_queue)} {cmd}"
    elif submit_cfg.slurm_partition:
        scheduler_cmd = f"sbatch -p {shlex.quote(submit_cfg.slurm_partition)} {cmd}"

    warning: str | None = None
    if seed is None:
        warning = (
            f"Test '{test_id}' has no recorded seed. The replay command uses seed=0, "
            "which may not reproduce the exact failure."
        )

    return {
        "test_id": test_id,
        "test_name": test_name,
        "suite": suite,
        "simulator": sim_name,
        "seed": seed,
        "dut_top": dut_top,
        "command": cmd,
        "scheduler_command": scheduler_cmd,
        "dry_run": True,
        "note": (
            "This is a generated command. Sentinel DV never executes it. "
            "Review and run it in your shell or CI pipeline."
        ),
        "warning": warning,
    }


# ==============================================================================
# v2.0.0: Feature 5 — Coverage Closure Guidance
# ==============================================================================


def get_coverage_gaps(
    store: IndexStore,
    suite: str | None = None,
    kind: str | None = None,
    threshold_pct: float = 100.0,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Return prioritised coverage gaps with actionable recommendations.

    Queries all indexed coverage metrics, identifies items below the given
    threshold, and returns gap analysis with recommendations sorted by priority.

    Args:
        store: Index store.
        suite: Filter to a specific test suite.
        kind: Coverage kind filter (functional|code|assertion|toggle|fsm|unknown).
        threshold_pct: Report metrics below this coverage percentage (default: 100.0).
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        CoverageGapsResponse-shaped dict.

    Raises:
        ToolError: INVALID_INPUT if kind or threshold_pct are invalid.
    """
    from sentinel_dv.normalization.coverage_hints import generate_recommendations
    from sentinel_dv.schemas.coverage import CoverageGapsResponse

    valid_kinds = {"functional", "code", "assertion", "toggle", "fsm", "unknown"}
    if kind and kind not in valid_kinds:
        raise ToolError(
            "INVALID_INPUT",
            f"Invalid kind '{kind}'. Must be one of: {sorted(valid_kinds)}.",
        )
    if not 0.0 <= threshold_pct <= 100.0:
        raise ToolError(
            "INVALID_INPUT",
            f"threshold_pct must be between 0.0 and 100.0, got {threshold_pct}.",
        )

    page, page_size = clamp_pagination(page, page_size)
    cfg = get_config()
    max_gaps = cfg.security.max_coverage_gaps

    # Query all coverage metrics from indexed runs
    metrics = store.query_coverage_metrics(suite=suite, kind=kind)

    total_metrics = len(metrics)
    all_gaps = generate_recommendations(
        metrics=metrics,
        threshold_pct=threshold_pct,
        max_gaps=max_gaps,
    )

    gaps_found = len(all_gaps)
    offset = (page - 1) * page_size
    paginated_gaps = all_gaps[offset : offset + page_size]

    response = CoverageGapsResponse(
        suite=suite,
        kind=kind,  # type: ignore[arg-type]
        threshold_pct=threshold_pct,
        total_metrics=total_metrics,
        gaps_found=gaps_found,
        gaps=paginated_gaps,
        note=(
            "Gaps are sorted by priority (high→medium→low) then by coverage percentage. "
            "Use tests.replay to reproduce specific failures. "
            f"Showing page {page} of {max(1, (gaps_found + page_size - 1) // page_size)}."
        ),
    )
    return list_response(
        "gaps",
        [g.model_dump() for g in paginated_gaps],
        page,
        page_size,
        gaps_found,
        extra={
            "suite": suite,
            "kind": kind,
            "threshold_pct": threshold_pct,
            "total_metrics": total_metrics,
            "gaps_found": gaps_found,
            "note": response.note,
        },
    )

