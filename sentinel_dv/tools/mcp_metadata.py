"""MCP tool descriptions, output schemas, and read-only annotations for LLM discoverability."""

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

_SCHEMA_VERSION = {"type": "string", "description": "Sentinel DV schema version (e.g. 1.0.0)"}

_ERROR_ENVELOPE = {
    "type": "object",
    "properties": {
        "schema_version": _SCHEMA_VERSION,
        "error": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "message": {"type": "string"},
                "details": {"type": "object"},
            },
            "required": ["code", "message"],
        },
    },
    "required": ["schema_version", "error"],
}

_PAGINATION = {
    "type": "object",
    "properties": {
        "page": {"type": "integer"},
        "page_size": {"type": "integer"},
        "total_items": {"type": "integer"},
        "total_pages": {"type": "integer"},
    },
    "required": ["page", "page_size", "total_items", "total_pages"],
}

_LIST_ENVELOPE = {
    "type": "object",
    "properties": {
        "schema_version": _SCHEMA_VERSION,
        "pagination": _PAGINATION,
    },
    "required": ["schema_version", "pagination"],
    "additionalProperties": True,
}

_ITEM_ENVELOPE = {
    "type": "object",
    "properties": {
        "schema_version": _SCHEMA_VERSION,
        "item": {"type": "object", "additionalProperties": True},
        "error": {"type": "object", "additionalProperties": True},
    },
    # Only schema_version is always required; "item" is present on success,
    # "error" is present on failure. Both shapes are valid.
    "required": ["schema_version"],
    "additionalProperties": True,
}

_DETAIL_ENVELOPE = {
    "type": "object",
    "properties": {"schema_version": _SCHEMA_VERSION},
    "required": ["schema_version"],
    "additionalProperties": True,
}

OUTPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "runs.list": {**_LIST_ENVELOPE, "description": "Paginated runs with total_tests counts."},
    "runs.get": {
        **_DETAIL_ENVELOPE,
        "properties": {
            **_DETAIL_ENVELOPE["properties"],
            "run": {"type": "object", "additionalProperties": True},
        },
    },
    "tests.list": _LIST_ENVELOPE,
    "tests.get": _ITEM_ENVELOPE,
    "tests.topology": _ITEM_ENVELOPE,
    "assertions.list": _LIST_ENVELOPE,
    "assertions.get": _ITEM_ENVELOPE,
    "assertions.failures": _LIST_ENVELOPE,
    "assertions.sva_status": {
        **_LIST_ENVELOPE,
        "description": "Per-assertion SVA runtime status with pass/fail/vacuous counts.",
    },
    "assertions.vacuity": {
        **_LIST_ENVELOPE,
        "description": "Assertions that fired vacuously (antecedent never held) with recommendations.",
    },
    "coverage.list": _LIST_ENVELOPE,
    "coverage.summary": {
        **_DETAIL_ENVELOPE,
        "description": "Bounded coverage summaries for one run (not paginated list).",
    },
    "coverage.gaps": {
        **_LIST_ENVELOPE,
        "description": "Prioritised coverage gaps with actionable recommendations.",
    },
    "failures.list": _LIST_ENVELOPE,
    "regressions.summary": _DETAIL_ENVELOPE,
    "runs.diff": _DETAIL_ENVELOPE,
    "runs.submit": _DETAIL_ENVELOPE,
    "tests.replay": _DETAIL_ENVELOPE,
    "sim.status": _DETAIL_ENVELOPE,
    "wave.signals": _DETAIL_ENVELOPE,
    "wave.summary": _DETAIL_ENVELOPE,
    # DV Intelligence tools — v2.1.0
    "coverage.trend": _DETAIL_ENVELOPE,
    "runs.cross_sim": _DETAIL_ENVELOPE,
    "tests.cluster": _DETAIL_ENVELOPE,
    "regression.health": _DETAIL_ENVELOPE,
    "coverage.advisor": _DETAIL_ENVELOPE,
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "runs.list": (
        "List indexed verification runs (read-only). "
        "Returns `{runs: [...], pagination}` where each run includes suite, status, "
        "created_at, and aggregated pass/fail test counts. "
        "Example: suite='verilator_counter', page=1 → nightly regression runs."
    ),
    "runs.get": (
        "Get one run by `run_id` (read-only). "
        "Returns `{run: {run_id, suite, status, ci_*, ...}}`. "
        "Use after `runs.list` when you need CI metadata for a specific run."
    ),
    "tests.list": (
        "Paginated test cases with filters (read-only). "
        "Returns `{tests: [...], pagination}`. "
        "Filter by `run_id`, `framework` (uvm|cocotb), `status`, or `name_pattern`. "
        "Example: run_id from `runs.list` → all tests in that run."
    ),
    "tests.get": (
        "Full record for one test (read-only). "
        "Returns `{item: {test_id, run_id, framework, name, status, seed, ...}}`."
    ),
    "tests.topology": (
        "UVM / testbench topology for a test (read-only). "
        "Returns `{item: {test_id, components, ...}}` when the UVM adapter indexed topology. "
        "Errors: NOT_FOUND if test_id unknown; TOPOLOGY_NOT_INDEXED if test exists but "
        "no topology was parsed from logs."
    ),
    "assertions.list": (
        "Paginated assertion *definitions* (read-only), not runtime failures. "
        "Returns `{assertions: [...], pagination}`. "
        "Filter by `protocol` (e.g. axi4), `tag`, `scope`, or `name_pattern`."
    ),
    "assertions.get": (
        "One assertion definition by `assertion_id` (read-only). "
        "Returns `{item: {name, scope, file, line, intent, signals, ...}}`."
    ),
    "assertions.failures": (
        "Paginated runtime assertion *failures* (read-only). "
        "Returns `{assertion_failures: [...], pagination}`. "
        "Distinct from `assertions.list` (definitions). "
        "Optional `start_time_ns`/`end_time_ns` window (both required together)."
    ),
    "failures.list": (
        "Paginated UVM/DUT failure events (read-only). "
        "Returns `{failures: [...], pagination}` with category, severity, signature_id. "
        "Set `include_evidence=true` for bounded log excerpts."
    ),
    "coverage.list": (
        "Paginated coverage summary rows across runs (read-only). "
        "Returns `{coverage: [{run_id, kind, metrics, ...}], pagination}`. "
        "Use to discover which runs have functional vs line coverage indexed."
    ),
    "coverage.summary": (
        "Bounded coverage rollup for a *single* `run_id` (read-only). "
        "Returns `{run_id, summaries: [...], total_summaries, truncated}` — not paginated. "
        "Distinct from `coverage.list` (multi-row catalog). "
        "Optional `kind` filter; `include_evidence` adds artifact refs."
    ),
    "regressions.summary": (
        "Suite-level pass rate and top failure signatures over a time window (read-only). "
        "Returns `{suite, window_days, as_of, pass_rate, runs, top_signatures}`. "
        "Use `as_of` (RFC3339 UTC) for deterministic replay."
    ),
    "runs.diff": (
        "Structured diff between two runs (read-only). "
        "Returns `{base_run_id, compare_run_id, test_changes, new_failures, resolved_failures}`."
    ),
    "wave.signals": (
        "Per-signal waveform data for a test (read-only). "
        "Returns `{signals: [{name, toggles, value_at_start, ...}], signal_count, truncated}`. "
        "Requires prior indexing of `*.vcd` or `*.wave.json`. "
        "Optional `start_time_ns`/`end_time_ns` (both required) re-slices VCD traces."
    ),
    "wave.summary": (
        "Waveform metadata and highlights for a test (read-only). "
        "Returns `{highlight_groups, highlights, signal_groups, metadata, signal_count}` "
        "without per-signal lists unless `include_signals=true` (combines wave.signals). "
        "Prefer this for overview; use `wave.signals` or `include_signals` for every signal."
    ),
    "runs.submit": (
        "Generate a regression job submission command (read-only dry-run). "
        "Returns `{command, scheduler_command, dry_run: true, ...}`. "
        "The server NEVER executes commands — all output is a shell command string for review. "
        "Requires `submit.enabled=true` and templates in config.yaml. "
        "Suite names are validated; extra_args are shell-quoted."
    ),
    "tests.replay": (
        "Generate a single-test replay command to reproduce a specific failure (read-only dry-run). "
        "Looks up the test seed and DUT topology, then generates a shell replay command. "
        "Returns `{command, seed, warning (if no seed recorded), dry_run: true, ...}`. "
        "The server NEVER executes commands."
    ),
    "sim.status": (
        "Read live simulation progress from a live_status.json file (read-only). "
        "Returns `{suite, phase, tests_total, tests_done, tests_passing, tests_failing, "
        "current_test, elapsed_seconds, stale, percent_done}`. "
        "The server reads a file written by the simulator harness — it never calls the simulator. "
        "Requires `adapters.live_sim=true` in config.yaml."
    ),
    "assertions.sva_status": (
        "Per-assertion SVA runtime status for a run or test (read-only). "
        "Returns `{sva_status: [{assertion_id, status, pass_count, fail_count, vacuous_count}], "
        "counts: {passing, failing, vacuous, ...}, pagination}`. "
        "Filter by `run_id`, `test_id`, or `status_filter` (passing|failing|vacuous|disabled|unknown)."
    ),
    "assertions.vacuity": (
        "List assertions that fired vacuously — antecedent never held (read-only). "
        "Returns `{vacuous_assertions: [{assertion_id, assertion_name, scope, vacuous_count, "
        "recommendation}], pagination}`. "
        "Vacuous assertions need testbench stimulus to exercise the antecedent."
    ),
    "coverage.gaps": (
        "Prioritised coverage gaps with actionable recommendations (read-only). "
        "Returns `{gaps: [{metric_name, scope, kind, covered_pct, bins_missed, priority, "
        "recommendation}], gaps_found, total_metrics, note}`. "
        "Filter by `suite` or `kind`; adjust `threshold_pct` (default 100%). "
        "Priorities: high (< 25% or error/boundary metrics), medium, low."
    ),
    # DV Intelligence tools — v2.1.0
    "coverage.trend": (
        "Show coverage trajectory across sequential runs — are you closing or regressing? (read-only). "
        "Returns `{trend: [{run_id, suite, created_at, kind, covered_pct, delta_pct}], "
        "summary: {runs_analysed, oldest_pct, latest_pct, total_delta_pct, direction}}`. "
        "Positive delta_pct means bins are being covered. "
        "Use to answer: 'Is our regression campaign making progress?'"
    ),
    "runs.cross_sim": (
        "Find tests whose pass/fail status diverges across simulators (read-only). "
        "Returns `{divergent_tests: [{test_name, sim_a, status_a, sim_b, status_b}], "
        "unique_divergent_names, simulator_pairs_analysed}`. "
        "Any divergence is a tape-out sign-off blocker — often indicates X-propagation, "
        "race conditions, or tool-specific bugs."
    ),
    "tests.cluster": (
        "Group test failures by error signature to surface root causes (read-only). "
        "Returns `{clusters: [{signature, count, representative_test_id, "
        "representative_message, test_ids}], total_failures_analysed, unique_clusters}`. "
        "Turns 500 individual failures into 5 actionable root causes. "
        "Fix the representative failure in each cluster first."
    ),
    "regression.health": (
        "Composite DV health score (0–100) with breakdown (read-only). "
        "Returns `{health_score, band, component_scores, recommendations}`. "
        "Score bands: 90–100 ✅ sign-off-ready, 75–89 🟡 minor issues, "
        "50–74 🟠 coverage gaps, 0–49 🔴 not ready. "
        "Components: pass_rate (30%), coverage (35%), assertion_health (15%), "
        "flakiness (10%), cross_sim_consistency (10%)."
    ),
    "coverage.advisor": (
        "Generate SystemVerilog constraints + UVM sequence hints to hit uncovered bins (read-only). "
        "Returns `{advisories: [{bin_name, covered_pct, protocol_hint, "
        "constraint_sv, sequence_hint}], total_gaps, high_priority_gaps}`. "
        "Protocol-aware: recognises AXI4, AHB, APB, CHI patterns. "
        "Each advisory includes ready-to-paste SV code. "
        "Use after `coverage.gaps` to turn gap analysis into directed tests."
    ),
}
