# Verilator counter + VCD demo

Minimal SystemVerilog counter with a C++ testbench that writes `waves/test_counter_sim.vcd`. Sentinel DV indexes the VCD with the built-in **`VcdSummaryParser`** and exposes **`wave.signals`** / **`wave.summary`** via MCP.

Source files live in the repository at `demo/verilator_counter/`.

## Requirements

- [Verilator](https://verilator.org) on your `PATH`
- `sentinel-dv>=1.0.1` (`pip install "sentinel-dv>=1.0.1"`)

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
- **`wave.summary`** — `format: vcd-summary`, end time (~10 µs for this demo), highlights

### Time window (2–3 µs)

The testbench advances the VCD timestamp by **100 ns** per step (`$timescale 1ps`, `+100_000` per dump). Query a slice in **nanoseconds**:

```json
{
  "test_id": "<from tests.list>",
  "start_time_ns": 2000,
  "end_time_ns": 3000
}
```

Use with **`wave.signals`** or **`wave.summary`** — both parameters are required together.

## Files in `demo/verilator_counter/`

| File | Role |
|------|------|
| `counter.sv` | 4-bit counter RTL |
| `sim_main.cpp` | Clock/reset stimulus + VCD dump |
| `Makefile` | `verilator --trace` build |
| `results.xml` | JUnit listing `test_counter_sim` |
| `config.example.yaml` | Indexer/server config for this demo |

See also: [Waveform summaries](../guides/waveforms.md).
