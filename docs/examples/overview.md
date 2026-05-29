# Examples

Runnable examples ship in the repository. Use **`sentinel-dv>=1.3.1`** and enable **`adapters.waveform_summary: true`** for waveform tools.

| Example | Location | Docs |
|---------|----------|------|
| **VCS, Questa, and Cadence artifacts** | `demo/{vcs,questa,cadence}_counter/` | [Simulator artifact examples](commercial-simulators.md) |
| **Multi-project (all tools)** | `demo/` (UVM + cocotb + Verilator + VCS + Questa + Cadence) | [demo/README](https://github.com/kiranreddi/sentinel-dv/blob/main/demo/README.md) |
| **Verilator — all 15 MCP tools** | `demo/verilator_counter/` | [Full walkthrough](verilator-counter.md) |
| **cocotb + JSON waveforms** | `demo/cocotb_results/`, `demo/waveforms/` | [cocotb + waveforms](cocotb-waveforms.md) |

## Multi-project (rigorous)

Index the complete checked-in demo corpus in one database:

```bash
cp demo/config.example.yaml demo/config.yaml
sentinel-dv-index --config demo/config.yaml --index-all
python scripts/verify_all_mcp_tools.py
pytest tests/integration/test_multi_project_all_mcp_tools.py -q
```

## VCS, Questa, and Cadence

Verify simulator-specific artifact fixtures:

```bash
python examples/simulator_matrix.py --sim all
python scripts/verify_all_mcp_tools.py --sim vcs
python scripts/verify_all_mcp_tools.py --sim questa
python scripts/verify_all_mcp_tools.py --sim cadence
```

See [VCS, Questa, and Cadence artifact examples](commercial-simulators.md).

## Verilator — full MCP walkthrough

Index assertions/coverage/UVM log + two JUnit runs + waveform summary, then verify:

```bash
cd demo/verilator_counter && cp config.example.yaml config.yaml
sentinel-dv-index --config config.yaml --index-all
python ../../scripts/verify_all_mcp_tools.py --in-place
```

Covers **`runs.list`** through **`wave.summary`**. If Verilator is installed, `make run` also regenerates the VCD used by the VCD-only walkthrough. See [Verilator counter demo](verilator-counter.md).

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
