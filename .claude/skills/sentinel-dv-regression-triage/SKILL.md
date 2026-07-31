---
name: sentinel-dv-regression-triage
description: Triage SystemVerilog, UVM, and cocotb regressions with Sentinel DV MCP tools. Use when asked to assess a run, explain a pass-rate drop, prioritize failure clusters, compare a baseline, identify flaky or simulator-specific signals, or produce an evidence-backed regression report.
---

# Sentinel DV Regression Triage

Turn an indexed regression into a traceable, prioritized report. Preserve every returned identifier and distinguish observed facts from heuristics.

## Inputs

Accept a `run_id`, suite, CI build reference, or a request to find the latest failing run. Ask for a baseline only when the requested comparison cannot be resolved from indexed runs.

## Preflight

1. Confirm the Sentinel DV tools are available by calling `runs.list` with `page=1`.
2. If the tool is unavailable, stop and report that the Sentinel DV MCP server must be configured and its artifact store indexed.
3. Treat empty results as an indexing or scope condition, not as a passing regression.

## Workflow

1. Resolve the target with `runs.list` using the narrowest supported filters. Do not invent time filters. Use `runs.get` for CI metadata and `runs.summary` for counts.
2. Call `regression.health` with `run_id` or `suite`. Treat the score as a scoped indicator whose unavailable components are `null`, omitted from `effective_weights`, and explained in `data_quality`; it is not independent sign-off proof.
3. For suite history, call `regressions.summary` with `suite`, `window_days`, and an explicit `as_of` when reproducibility matters.
4. Call `tests.cluster` for the run. Rank using `distinct_test_count`, `failure_count`, severity, category, and recurrence. Clusters are signature heuristics, not established root causes. Disclose `clusters_truncated`.
5. If a baseline exists, call `runs.diff`. Separate `new_failures`, `persistent_failures`, `resolved_failures`, test changes, and `coverage_deltas`.
6. For leading clusters, page through `failures.list` with `run_id` or representative `test_id` and `include_evidence=true`. Continue until all pages in the intended scope are read or state the exact bounded subset.
7. Page through `assertions.failures` when assertions are implicated. Resolve relevant definitions with `assertions.get`.
8. Use `tests.history` for the logical test cohort. Its `is_flaky` field means mixed pass/fail outcomes in a bounded indexed history; report it as a flakiness signal, not proof.
9. Use `runs.cross_sim` only when multiple simulators are relevant. Its comparisons are latest-result cohorts matched by suite, framework, DUT top, and test name.
10. Deepen only the highest-impact unresolved cases with `tests.get`, `tests.topology`, `wave.summary`, or `wave.signals`.

## Failure Classes

- Route `compile` and `elab` categories to build source, options, generated files, and tool-version investigation. Do not request waveform evidence for a simulation that never ran.
- For `aborted` tests or runs with no simulation-time evidence, inspect CI metadata and missing artifacts. Label infrastructure failure only when evidence supports it.
- For runtime assertion, protocol, scoreboard, timeout, or x-propagation failures, build a chronological event chain and separate initiating events from cascades.

## Deliverable

Return:

1. Scope, counts, and health data quality.
2. Baseline changes, including persistent and resolved issues and coverage deltas.
3. Prioritized clusters with affected tests, severity, category, IDs, and concise evidence.
4. Flakiness, cross-simulator, build, or infrastructure signals with their heuristic limits.
5. Recommended actions tied to findings.
6. Confidence, pagination or truncation limits, and missing evidence.

Never imply that `runs.submit` or `tests.replay` executed anything. Both return dry-run commands.

## Invocation Examples

- "Triage the latest failing nightly regression and compare it with the previous passing run."
- "Why did the pass rate fall in run R124? Group the failures and identify the highest-impact investigation."
- "Assess whether this regression has enough coverage, assertion, flakiness, and cross-simulator evidence for review."
