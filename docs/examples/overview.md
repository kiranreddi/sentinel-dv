# Examples

Runnable examples ship in the repository:

| Location | Description |
|----------|-------------|
| `demo/` | UVM logs, cocotb JUnit XML, precomputed `*.wave.json` |
| `demo/verilator_counter/` | Verilator RTL + C++ TB → VCD → built-in `VcdSummaryParser` |

## Verilator + VCD (recommended first)

See [Verilator counter demo](verilator-counter.md) for a full walkthrough: build, index, and query `wave.signals` / `wave.summary`.

## cocotb + JSON waveforms

Index the whole `demo/` tree with `waveform_summary: true` to load `demo/waveforms/*.wave.json` alongside `demo/cocotb_results/results.xml`. Details in the repository `demo/README.md`.
