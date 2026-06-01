# Verilator counter — full MCP walkthrough

SystemVerilog counter + C++ testbench (**Verilator**) that emits a VCD trace. The directory also ships **cocotb JUnit**, a **UVM-style log**, **assertion JSON**, and **coverage JSON** so a single `sentinel-dv-index` run exercises **all 28 MCP tools** (enable `submit` / `live_sim` in config for command-generation and live-status tools).

## Quick start

```bash
cd demo/verilator_counter
make run
cp config.example.yaml config.yaml
sentinel-dv-index --config config.yaml --index-all
```

Expected: `runs≥3`, `tests≥3`, `failures≥2`, `assertions≥2`, `assertion_failures≥1`, `coverage≥1`, `waveforms=1`.

Verify every MCP tool (from repo root):

```bash
python scripts/verify_all_mcp_tools.py --in-place
```

Start the server:

```bash
sentinel-dv-server --config config.yaml
```

## MCP tools covered

| Tool | Demo data |
|------|-----------|
| `runs.list` / `runs.get` | Pass + fail cocotb runs, UVM log run |
| `tests.list` / `tests.get` | `counter_tb.test_counter_sim`, overflow fail, UVM `test_counter_sim` |
| `tests.topology` | `counter_tb.uvm.log` |
| `assertions.list` / `assertions.get` / `assertions.failures` | `assertions/*.assert.json` |
| `coverage.list` / `coverage.summary` | `coverage/coverage.json` |
| `failures.list` | UVM scoreboard + cocotb overflow |
| `regressions.summary` | Suite `verilator_counter`, multiple runs |
| `runs.diff` | Fail run vs pass run |
| `wave.signals` / `wave.summary` | `waves/test_counter_sim.vcd` |

Full parameter examples: [docs/examples/verilator-counter.md](../../docs/examples/verilator-counter.md).

## Files

| File | Role |
|------|------|
| `counter.sv` | 4-bit counter RTL |
| `sim_main.cpp` | Clock/reset + VCD dump |
| `Makefile` | `verilator --trace` build |
| `results.xml` | JUnit pass (`test_counter_sim`) |
| `results_regression_fail.xml` | JUnit fail (`test_counter_overflow`) |
| `counter_tb.uvm.log` | Illustrative UVM log (topology + scoreboard error) |
| `assertions/` | SVA assertion reports |
| `coverage/coverage.json` | Functional coverage summary |
| `config.example.yaml` | All adapters enabled |

## Time window (wave tools)

VCD timescale is 1 ps; each step adds 100 ns. Query **2000–3000 ns** on `wave.signals` / `wave.summary` (both `start_time_ns` and `end_time_ns` required).
