# Regression Triage

Use `sentinel-dv-regression-triage` when a run failed, pass rate changed, or a regression needs an evidence-backed priority order.

## Tool sequence

```text
runs.list
  -> runs.get + runs.summary
  -> regression.health
  -> regressions.summary (suite history, when needed)
  -> tests.cluster
  -> runs.diff (when a baseline exists)
  -> failures.list + assertions.failures
  -> tests.history / runs.cross_sim
  -> targeted tests.get / topology / wave tools
```

The skill does not call every tool mechanically. Compile and elaboration failures stop before waveform analysis; runtime failures can continue into topology and bounded waveform windows.

## Example request

```text
Use the Sentinel DV regression triage skill on run R124.
Compare it with R123, rank signature clusters, and disclose any unavailable
health components or truncated pages.
```

## Report contract

The result includes scope and counts, health data quality, baseline changes, prioritized clusters, heuristic limits, actions, and missing evidence. A cluster is a signature grouping, not proof of a shared root cause.

## Interpreting health

`regression.health` is a scoped indicator. Components without sufficient source data are `null` and removed from `effective_weights`:

- coverage needs indexed metrics;
- assertion health needs indexed SVA status;
- flakiness needs repeated test cohorts;
- cross-simulator consistency needs comparable cohorts from at least two simulators.

Do not use the score as a sign-off gate without reviewing `data_quality`.
