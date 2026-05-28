# Waveform tools

`wave.signals` and `wave.summary` read **precomputed** waveform data indexed from `*.wave.json` or `*.vcd`. Enable `adapters.waveform_summary: true` and re-index before calling these tools.

See [Waveform summaries guide](../guides/waveforms.md) for indexing rules and [Verilator example](../examples/verilator-counter.md) for an end-to-end walkthrough.

## wave.signals

List signals for an indexed test.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `test_id` | Yes | From `tests.list` |
| `start_time_ns` | No* | Window start in **nanoseconds** |
| `end_time_ns` | No* | Window end in **nanoseconds** |

\* If either time parameter is set, **both** are required.

**VCD:** When a window is set, Sentinel DV re-reads the source `.vcd` from `artifact_roots` and returns `value_at_start`, `value_at_end`, and `toggles` in range.

**Example (full trace):**

```json
{
  "test_id": "t_abc123"
}
```

**Example (2–3 µs on Verilator demo, trace uses 1ps timescale with 100 ns steps):**

```json
{
  "test_id": "t_abc123",
  "start_time_ns": 2000,
  "end_time_ns": 3000
}
```

**Example (20–30 µs with `$timescale 1 us` in VCD):**

```json
{
  "test_id": "t_abc123",
  "start_time_ns": 20000,
  "end_time_ns": 30000
}
```

## wave.summary

Bounded highlights and metadata for the same indexed test. Accepts the same parameters as `wave.signals`.

```json
{
  "test_id": "t_abc123",
  "start_time_ns": 2000,
  "end_time_ns": 3000
}
```

**Response fields (typical):** `format` (`vcd-summary` or `wave-json`), `start_time_ns`, `end_time_ns`, `highlights`, signal metadata.

## Typical workflow

1. `tests.list` — find `test_id` for the simulation under debug.
2. `wave.summary` — see trace length and busiest signals.
3. `wave.signals` — per-signal toggles; add a time window to narrow to a failure interval.
