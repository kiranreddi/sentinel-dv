# Examples

Runnable examples ship in the repository. Use **`sentinel-dv>=1.1.0`** and enable **`adapters.waveform_summary: true`** for waveform tools.

| Example | Location | Docs |
|---------|----------|------|
| **Verilator + VCD** (recommended first) | `demo/verilator_counter/` | [Walkthrough](verilator-counter.md) |
| **cocotb + JSON waveforms** | `demo/`, `demo/waveforms/` | [cocotb + waveforms](cocotb-waveforms.md) |
| **UVM logs + failures** | `demo/uvm_logs/` | [demo/README](https://github.com/kiranreddi/sentinel-dv/blob/main/demo/README.md) |

## Verilator + VCD

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

Index `demo/cocotb_results/results.xml` and `demo/waveforms/*.wave.json` in one pass. See [cocotb + waveforms](cocotb-waveforms.md).

## Combined demo tree

```bash
cp config.example.yaml config.yaml   # artifact_roots: ./demo
sentinel-dv-index --config config.yaml --index-all
sentinel-dv-server --config config.yaml
```

Details in the repository [`demo/README.md`](https://github.com/kiranreddi/sentinel-dv/blob/main/demo/README.md).
