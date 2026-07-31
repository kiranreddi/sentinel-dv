# Failure Debugging

Use `sentinel-dv-failure-debugging` for one SystemVerilog, UVM, or cocotb failure.

## Tool sequence

```text
tests.list -> tests.get
  -> failures.list(include_evidence=true)
  -> assertions.failures -> assertions.get
  -> tests.topology
  -> tests.history
  -> wave.summary -> wave.signals(bounded window)
  -> tests.replay (only when requested)
```

## Example request

```text
Use the Sentinel DV failure debugging skill for test_counter_sim.
Build a chronological explanation, correlate only supported waveform evidence,
and separate the likely cause from alternatives.
```

## Causal standard

The skill prefers the earliest event that can explain later symptoms, but it does not promote an event to root cause without component, assertion-intent, or waveform support. Untimed events remain separate from a timestamped sequence.

For compile or elaboration failures, waveform calls are inappropriate. For aborted runs with sparse simulation evidence, the report inspects CI metadata and artifact completeness before using an infrastructure label.

## Reproduction

`tests.replay` returns a dry-run command. Review the simulator, seed, paths, and extra arguments before running it outside Sentinel DV.
