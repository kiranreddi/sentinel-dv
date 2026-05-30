# Examples

Runnable examples shipped with Sentinel DV (**v2.1.0+**, 26 MCP tools):

| Path | Description | Documentation |
|------|-------------|---------------|
| [axi4_sentinel_demo.py](axi4_sentinel_demo.py) | **All 26 MCP tools** against AXI4 UVM (VCS + Questa + Xcelium) | [AXI4 demo](../demo/axi4_uvm/README.md) |
| [live_sim_writer.py](live_sim_writer.py) | Write `live_status.json` while a simulator runs (sim.status tool) | [Live sim status](../docs/tools/mcp-tools-reference.md) |
| [simulator_matrix.py](simulator_matrix.py) | Verifies all MCP tools against VCS, Questa, and Cadence examples | [Examples overview](https://kiranreddi.github.io/sentinel-dv/examples/overview/) |
| [demo.py](demo.py) | Minimal cocotb JUnit + waveform demo | [cocotb + waveforms](https://kiranreddi.github.io/sentinel-dv/examples/cocotb-waveforms/) |
| [demo/axi4_uvm/](../demo/axi4_uvm/) | AXI4-Lite slave RTL + UVM TB + 3-simulator artifacts | [AXI4 README](../demo/axi4_uvm/README.md) |
| [demo/verilator_counter/](../demo/verilator_counter/) | Verilator RTL + C++ TB → VCD → time-window queries | [Verilator + VCD](https://kiranreddi.github.io/sentinel-dv/examples/verilator-counter/) |
| [demo/vcs_counter/](../demo/vcs_counter/) | VCS-style exported logs, JUnit, coverage, assertions, waveform summary | [Simulator support](https://kiranreddi.github.io/sentinel-dv/guides/simulator-support/) |
| [demo/questa_counter/](../demo/questa_counter/) | Questa-style exported logs, JUnit, coverage, assertions, waveform summary | [Simulator support](https://kiranreddi.github.io/sentinel-dv/guides/simulator-support/) |
| [demo/cadence_counter/](../demo/cadence_counter/) | Cadence Xcelium-style exported logs, JUnit, coverage, assertions, waveform summary | [Simulator support](https://kiranreddi.github.io/sentinel-dv/guides/simulator-support/) |

## Quick start — AXI4 three-simulator demo

```bash
pip install "sentinel-dv>=2.1.0"

cd demo/axi4_uvm
sentinel-dv-index --config config.yaml --index-all

python ../../examples/axi4_sentinel_demo.py
```

Install: `pip install "sentinel-dv>=2.1.0"`
