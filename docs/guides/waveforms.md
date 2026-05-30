# Waveform summaries

Sentinel DV does **not** stream raw FSDB, VCD, or WLF files to MCP clients. Instead, it indexes **bounded waveform summaries** so agents can answer questions like “which signals toggled?” without loading multi-gigabyte dumps.

Two input formats are supported:

| Format | Adapter | When to use |
|--------|---------|-------------|
| **Precomputed JSON** (`*.wave.json`, `waveform_summary.json`) | `WaveformSummaryParser` | Pipelines that already emit JSON summaries |
| **VCD** (`*.vcd`) | `VcdSummaryParser` | Verilator and other simulators that write Value Change Dump files |

Both are built into the `sentinel-dv` package (no separate install).

## Enable indexing

```yaml
adapters:
  waveform_summary: true
```

Then rebuild the index:

```bash
sentinel-dv-index --config config.yaml --index-all
```

The indexer scans artifact roots for:

- `*.wave.json`, `*_waveform.json`, `waveform_summary.json`
- `*.vcd`

Summaries are stored in DuckDB and linked to tests by **`test_name`**.

## Linking waveforms to tests

Each waveform file must resolve to an **already indexed** test:

1. **Exact or suffix match** on `tests.name` (e.g. `test_counter_sim` matches `counter_tb.test_counter_sim`).
2. Optional **`framework`** in JSON (for `*.wave.json` only); VCD lookup falls back without framework if needed.
3. **VCD file naming**: use `{test_name}.vcd` (e.g. `test_counter_sim.vcd` for JUnit testcase `test_counter_sim`).

If no test matches, the file is skipped silently during indexing.

## Precomputed JSON format

Example (`demo/waveforms/test_increment.wave.json`):

```json
{
  "test_name": "test_counter.test_increment",
  "framework": "cocotb",
  "format": "precomputed-vcd",
  "end_time_ns": 50000,
  "signal_groups": [
    {
      "name": "dut",
      "signals": [
        {"name": "clk", "width": 1, "toggles": 100, "last_value": "1"},
        {"name": "count", "width": 8, "toggles": 8, "last_value": "0x05"}
      ]
    }
  ],
  "highlights": [
    {"time_ns": 10000, "signal": "count", "value": "0x01", "note": "first increment"}
  ]
}
```

Required fields:

- `test_name` (string)
- `signals` (array) **or** `signal_groups` (array of `{name, signals}`)

Optional: `framework`, `format`, `end_time_ns`, `highlights`, `metadata`.

## VCD format (built-in parser)

`VcdSummaryParser` (`sentinel_dv/adapters/vcd_summary.py`) reads standard VCD files and computes per-signal:

- Toggle counts (full trace at index time, or within a window at query time)
- `value_at_start` / `value_at_end` when a window is requested
- `$timescale` conversion so `#` timestamps map to **nanoseconds**

Hierarchical duplicate signal names in the dump are merged by name.

### Time windows (20–30 µs example)

MCP tools accept optional **`start_time_ns`** and **`end_time_ns`** (always **nanoseconds**):

| Human unit | Nanoseconds for API |
|------------|---------------------|
| 20 µs | `20000` |
| 30 µs | `30000` |

Example MCP call (after indexing a VCD):

```json
{
  "test_id": "t_…",
  "start_time_ns": 20000,
  "end_time_ns": 30000
}
```

For indexed **VCD** files, Sentinel DV **re-opens** the source `.vcd` under `artifact_roots` and parses only that window (values + toggles inside the range). Both parameters are required together.

For **JSON** summaries, the window filters `highlights` only; use VCD for per-signal window values.

!!! note "Summary only"
    This is not a waveform viewer. Very large VCDs are read sequentially; only aggregated stats are stored.

## MCP tools

After indexing, query by `test_id`:

| Tool | Returns |
|------|---------|
| `wave.signals` | Signal list (`value_at_start`, `value_at_end`, toggles, …); optional `start_time_ns` / `end_time_ns` |
| `wave.summary` | Format, highlights, metadata; optional time window |

If no summary exists for a test, tools return `NOT_FOUND` with guidance to enable `waveform_summary` and re-index.

## Shipped example: Verilator counter

The repository includes a complete minimal flow under **`demo/verilator_counter/`**:

```
demo/verilator_counter/
├── counter.sv          # 4-bit counter RTL
├── sim_main.cpp        # C++ TB with VCD trace
├── Makefile            # verilator --trace build + run
├── results.xml         # JUnit (test_counter_sim)
├── config.example.yaml # ready-to-copy config
└── README.md           # step-by-step
```

### Quick run

```bash
cd demo/verilator_counter
make run
cp config.example.yaml config.yaml
sentinel-dv-index --config config.yaml --index-all
```

Expected indexer output includes `waveforms=1`. Then start the MCP server and call `wave.signals` / `wave.summary` for the indexed test.

Requirements: [Verilator](https://verilator.org) on `PATH`, `sentinel-dv>=2.1.0` installed.

## Combined demo (cocotb + JSON waveforms)

Under **`demo/`**, cocotb JUnit results and precomputed `demo/waveforms/*.wave.json` illustrate linking without Verilator. Point `artifact_roots` at `./demo` and enable `waveform_summary` (see `demo/README.md`).
