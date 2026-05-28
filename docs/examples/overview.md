# Examples

Runnable examples ship in the repository. Use **`sentinel-dv>=1.2.0`** and enable **`adapters.waveform_summary: true`** for waveform tools.

| Example | Location | Docs |
|---------|----------|------|
| **Verilator — all 15 MCP tools** (recommended) | `demo/verilator_counter/` | [Full walkthrough](verilator-counter.md) |
| **Multi-project (all tools)** | `demo/` (UVM + cocotb + Verilator) | [demo/README](https://github.com/kiranreddi/sentinel-dv/blob/main/demo/README.md) |
| **cocotb + JSON waveforms** | `demo/cocotb_results/`, `demo/waveforms/` | [cocotb + waveforms](cocotb-waveforms.md) |

## Multi-project (rigorous)

Index **six suites** (two UVM, three cocotb, one Verilator) in one database:

```bash
cd demo/verilator_counter && make run && cd ../..
cp demo/config.example.yaml demo/config.yaml
sentinel-dv-index --config demo/config.yaml --index-all
python scripts/verify_all_mcp_tools.py --multi
pytest tests/integration/test_multi_project_all_mcp_tools.py -q
```

## Verilator — full MCP walkthrough

Build with Verilator, index assertions/coverage/UVM log + two JUnit runs + VCD, then verify:

```bash
cd demo/verilator_counter && make run && cp config.example.yaml config.yaml
sentinel-dv-index --config config.yaml --index-all
python ../../scripts/verify_all_mcp_tools.py --in-place
```

Covers **`runs.list`** through **`wave.summary`**. See [Verilator counter demo](verilator-counter.md).

## Verilator + VCD only

Build a counter testbench, write `waves/test_counter_sim.vcd` (~10 µs trace), index with the built-in **`VcdSummaryParser`**, and query **`wave.signals`** / **`wave.summary`**.

Optional **time window** (2–3 µs on the demo trace):

```json
{
  "test_id": "<from tests.list>",
  "start_time_ns": 2000,
  "end_time_ns": 3000
}
```

See [Verilator counter demo](verilator-counter.md).

## cocotb + precomputed waveforms

Index `demo/cocotb_results/*/results.xml` and `demo/waveforms/**/*.wave.json`. See [cocotb + waveforms](cocotb-waveforms.md).

## Combined demo tree

```bash
cp config.example.yaml config.yaml   # artifact_roots: ./demo
sentinel-dv-index --config config.yaml --index-all
sentinel-dv-server --config config.yaml
```

Details in the repository [`demo/README.md`](https://github.com/kiranreddi/sentinel-dv/blob/main/demo/README.md).
