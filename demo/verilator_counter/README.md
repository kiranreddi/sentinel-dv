# Verilator counter + VCD demo

Minimal SystemVerilog counter with a C++ testbench that writes `waves/test_counter_sim.vcd`. Sentinel DV indexes the VCD with the built-in **`VcdSummaryParser`** and exposes **`wave.signals`** / **`wave.summary`** via MCP.

## Requirements

- [Verilator](https://verilator.org) on your `PATH`
- `sentinel-dv>=1.1.0` (`pip install "sentinel-dv>=1.1.0"`)

## 1. Build and simulate

```bash
cd demo/verilator_counter
make run
```

Output: `waves/test_counter_sim.vcd`

## 2. Configure Sentinel DV

```bash
cp config.example.yaml config.yaml
```

`config.example.yaml` sets `artifact_roots` to the current directory (`.`) and enables `waveform_summary`.

## 3. Index

```bash
sentinel-dv-index --config config.yaml --index-all
```

Expected: `tests=1`, `waveforms=1` (JUnit `results.xml` plus VCD).

## 4. Query (MCP)

Start the server:

```bash
sentinel-dv-server --config config.yaml
```

Or add to an MCP client config with `--config` pointing at this `config.yaml`.

Use tools on the indexed test (`counter_tb.test_counter_sim`):

- **`wave.signals`** — `clk`, `rst`, `count` with toggle counts from the VCD
- **`wave.summary`** — `format: vcd-summary`, end time (~10 µs), highlights

**Time window example** (2–3 µs): pass `start_time_ns: 2000` and `end_time_ns: 3000` to `wave.signals` or `wave.summary`.

## Files

| File | Role |
|------|------|
| `counter.sv` | 4-bit counter RTL |
| `sim_main.cpp` | Clock/reset stimulus + VCD dump |
| `Makefile` | `verilator --trace` build |
| `results.xml` | JUnit listing `test_counter_sim` |
| `config.example.yaml` | Indexer/server config for this demo |

See also: [Waveform summaries guide](https://kiranreddi.github.io/sentinel-dv/guides/waveforms/).
