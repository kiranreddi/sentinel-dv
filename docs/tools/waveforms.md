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

Bounded highlights and metadata for the same indexed test. Accepts the same time-window parameters as `wave.signals`, plus:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `include_signals` | `false` | When `true`, includes the full per-signal list (same as calling `wave.signals`) |

```json
{
  "test_id": "t_abc123",
  "start_time_ns": 2000,
  "end_time_ns": 3000,
  "include_signals": false
}
```

**Response fields (typical):** `format`, `highlight_groups` (highlights grouped by category), `highlights`, `signal_groups` (from JSON fixtures), `metadata`, optional `signals` when `include_signals` is true.

## Typical workflow

1. `tests.list` — find `test_id` for the simulation under debug.
2. `wave.summary` — trace length, `highlight_groups`, and busiest intervals.
3. `wave.signals` or `wave.summary` with `include_signals: true` — per-signal toggles; add a time window to narrow to a failure interval.
