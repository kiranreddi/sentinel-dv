# Coverage Closure

Use `sentinel-dv-coverage-closure` to turn functional, assertion, code, toggle, or FSM coverage into a risk-based closure plan.

## Tool sequence

```text
coverage.list -> coverage.summary
  -> coverage.trend
  -> coverage.gaps(run_id=...)
  -> assertions.vacuity + assertions.sva_status
  -> runs.diff (when a baseline exists)
  -> coverage.advisor(exact run_id + metric_name)
  -> tests.topology / tests.history (after ownership is identified)
```

## Example request

```text
Use the Sentinel DV coverage closure skill for the latest xcelium AXI4 run.
Prioritize reachable functional gaps, check vacuous assertions, and generate
one candidate constraint for the highest-risk bin.
```

## Advisor boundary

`coverage.advisor` returns a candidate `constraint_sv` and `sequence_hint`. The generated snippet can encode protocol knowledge, but it cannot know local transaction class names, address maps, legal exclusions, or testbench ownership. Review and adapt it before use.

Closure is demonstrated only by a later indexed run that records the intended improvement without unacceptable regression elsewhere.

## Acceptance criteria

A useful closure item names:

- the exact run, scope, kind, metric or bin;
- reachability and risk evidence;
- the proposed test, constraint, assertion, exclusion, or instrumentation change;
- the next run and measurable expected delta;
- protection against regression in other metrics or configurations.
