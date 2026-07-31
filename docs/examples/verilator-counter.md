# Verilator counter — full MCP tool walkthrough

This example indexes **all artifact types** needed to exercise **every Sentinel DV MCP tool** (26 read-only tools). Simulation uses **Verilator** for RTL + VCD; companion files model cocotb JUnit, UVM-style logs, assertions, and coverage (typical DV regression layout).

Source: [`demo/verilator_counter/`](https://github.com/kiranreddi/sentinel-dv/tree/main/demo/verilator_counter).

## Requirements

- [Verilator](https://verilator.org) on `PATH`
- `sentinel-dv>=2.3.1` (`pip install "sentinel-dv>=2.3.1"`)

## 1. Build and simulate (VCD)

```bash
cd demo/verilator_counter
make run
```

Creates `waves/test_counter_sim.vcd` (≈10 µs of activity; 100 ns per dump step).

## 2. Configure and index

```bash
cp config.example.yaml config.yaml
sentinel-dv-index --config config.yaml --index-all
```

Expected index stats (approximate):

| Stat | Count | Source |
|------|-------|--------|
| `runs` | 3 | `results.xml`, `results_regression_fail.xml`, `counter_tb.uvm.log` |
| `tests` | 3 | pass cocotb, fail cocotb overflow, UVM-style log |
| `failures` | 2 | UVM scoreboard + cocotb overflow |
| `assertions` | 3 | `assertions/*.assert.json` |
| `assertion_failures` | 1 | `counter_fail.assert.json` |
| `coverage` | 1 | `coverage/coverage.json` |
| `waveforms` | 1 | VCD via `VcdSummaryParser` |

All runs share suite name **`verilator_counter`** (artifact parent directory), which powers `regressions.summary` and `runs.diff`.

## 3. Verify all MCP tools (optional)

From the repository root:

```bash
python scripts/verify_all_mcp_tools.py --in-place
```

Runs FastMCP in-process against `sentinel-dv-server` handlers and prints `OK` for each of the 28 tools (`runs.submit`, `tests.replay`, and `sim.status` report `CONFIG_ERROR` unless enabled in `config.yaml`).

## 4. Start the MCP server

```bash
cd demo/verilator_counter
sentinel-dv-server --config config.yaml
```

## 5. Tool-by-tool examples

Use IDs from `tests.list` / `runs.list` in your client. Stable **names** below:

| Test name | Framework | Use for |
|-----------|-----------|---------|
| `counter_tb.test_counter_sim` | cocotb | waves, assertions, coverage |
| `counter_tb.test_counter_overflow` | cocotb | failing regression run |
| `test_counter_sim` | uvm | topology, scoreboard failure |

### Discovery

```json
{ "suite": "verilator_counter", "page": 1, "page_size": 20 }
```
→ **`runs.list`**

```json
{ "run_id": "<pass run_id>" }
```
→ **`runs.get`**

```json
{ "run_id": "<pass run_id>", "framework": "cocotb" }
```
→ **`tests.list`**

```json
{ "protocol": "axi4", "page": 1, "page_size": 50 }
```
→ **`assertions.list`** (demo assertion with `axi4` tag)

```json
{ "run_id": "<pass run_id>", "kind": "functional" }
```
→ **`coverage.list`**

### Detail

```json
{ "test_id": "<cocotb test_id>" }
```
→ **`tests.get`**

```json
{ "test_id": "<uvm test_id>" }
```
→ **`tests.topology`** (UVM hierarchy stub from log)

```json
{ "assertion_id": "<from assertions.list>" }
```
→ **`assertions.get`**

```json
{ "test_id": "<cocotb test_id>", "include_evidence": true }
```
→ **`assertions.failures`**

```json
{ "run_id": "<pass run_id>" }
```
→ **`coverage.summary`**

```json
{ "category": "scoreboard", "include_evidence": true }
```
→ **`failures.list`** (UVM scoreboard mismatch)

### Analysis

```json
{ "suite": "verilator_counter", "window_days": 30, "as_of": "2026-05-28T12:00:00Z" }
```
→ **`regressions.summary`**

```json
{ "base_run_id": "<fail run_id>", "compare_run_id": "<pass run_id>" }
```
→ **`runs.diff`**

### Waveforms

```json
{ "test_id": "<cocotb test_id for test_counter_sim>" }
```
→ **`wave.signals`** (`clk`, `rst`, `count` + toggles)

```json
{
  "test_id": "<cocotb test_id>",
  "start_time_ns": 2000,
  "end_time_ns": 3000
}
```
→ **`wave.summary`** (re-parses VCD for 2–3 µs window)

## Artifact layout

```
demo/verilator_counter/
├── counter.sv
├── sim_main.cpp
├── Makefile
├── results.xml                      # cocotb JUnit — pass
├── results_regression_fail.xml      # cocotb JUnit — fail (overflow)
├── counter_tb.uvm.log               # UVM-style log — topology + scoreboard
├── assertions/
│   ├── counter.assert.json
│   └── counter_fail.assert.json
├── coverage/coverage.json
├── waves/test_counter_sim.vcd       # after make run
└── config.example.yaml
```

## CI / automation

```bash
pytest tests/integration/test_verilator_all_mcp_tools.py -q
```

See also: [MCP tools reference](../tools/mcp-tools-reference.md), [MCP tool gallery](../tools/mcp-tool-gallery.md), [Waveform summaries](../guides/waveforms.md).
