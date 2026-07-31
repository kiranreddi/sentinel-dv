---
name: sentinel-dv-coverage-closure
description: Plan and assess SystemVerilog functional, assertion, code, toggle, and FSM coverage closure with Sentinel DV MCP tools. Use when asked to find important gaps, explain stalled or regressing coverage, prioritize bins, evaluate vacuous assertions, generate protocol-aware constraint candidates, or define evidence-backed closure acceptance criteria.
---

# Sentinel DV Coverage Closure

Convert indexed coverage into a risk-based closure plan. Generated constraints are candidates for review; only a later indexed run can demonstrate closure.

## Inputs

Accept a run, suite, coverage kind, protocol, target percentage, baseline, and known exclusions. Resolve omitted run IDs from indexed coverage, but do not invent goals or exclusions.

## Preflight

1. Confirm the Sentinel DV tools are available with `coverage.list` using `page=1`.
2. If unavailable, report that the Sentinel DV MCP server must be configured and coverage artifacts indexed.
3. Treat absent coverage kinds or empty summaries as missing data, not 0% coverage.

## Workflow

1. Establish the target run or suite, coverage kind, protocol, baseline run, goal, and known exclusions.
2. If the run is unknown, page through `coverage.list` to discover indexed records. Call `coverage.summary` for the selected `run_id` and optional `kind`.
3. Call `coverage.trend` with the exact supported inputs: `suite`, `kind`, and `limit`. It reports per-run averages, not per-bin age or an arbitrary time window.
4. Call `coverage.gaps` with `run_id` whenever closing a specific run. Narrow with `suite`, `kind`, `priority`, and `threshold_pct` as needed. Page through all intended results.
5. For assertion goals, page through `assertions.vacuity` and `assertions.sva_status` in the same run scope. Separate unexercised antecedents, failing properties, disabled properties, and missing status data.
6. If a baseline exists, call `runs.diff` and use `coverage_deltas` to distinguish improved, regressed, added, and removed metrics.
7. Select a valid, reachable functional gap. Call `coverage.advisor` with its exact `run_id`, `metric_name`, optional `kind`, and protocol context. Treat `constraint_sv` and `sequence_hint` as templates requiring source and testbench review.
8. Use `tests.topology` and `tests.history` only after identifying a candidate owner or existing test. Do not infer ownership from coverage scope alone.
9. Call `runs.submit` only when a dry-run follow-up command is requested.

## Prioritization

Rank by verification risk, feature criticality, valid reachability, regression direction, cross-configuration impact, assertion quality, and effort. Do not optimize for aggregate percentage alone.

Flag exclusions, unreachable bins, contradictory metrics, stale indexes, missing kinds, and instrumentation defects as explicit review decisions. Never silently remove them.

## Deliverable

Return:

1. Scoped current state, trend, and data completeness.
2. Prioritized gaps with `run_id`, scope, metric or bin, risk, and reachability evidence.
3. Recommended test, constraint, assertion, exclusion, or instrumentation change.
4. Advisor output labeled as candidate code.
5. Follow-up run and measurable acceptance criteria, including no unacceptable regression elsewhere.
6. Assumptions, pagination or truncation limits, and missing evidence.

Do not claim closure until a later indexed run records the intended improvement.

## Invocation Examples

- "Build a closure plan for AXI4 functional coverage in the latest xcelium run."
- "Explain why toggle coverage stalled and identify the next three reviewable actions."
- "Check functional gaps and vacuous assertions, then generate one candidate constraint for the highest-risk reachable bin."
