# Verilator counter + VCD demo

Minimal SystemVerilog counter with a C++ testbench that writes `waves/test_counter_sim.vcd`.

## Build and run (requires Verilator)

```bash
cd demo/verilator_counter
make run
```

## Index with Sentinel DV

Point `artifact_roots` at this directory and enable waveform summaries:

```yaml
artifact_roots:
  - /path/to/sentinel-dv/demo/verilator_counter
adapters:
  waveform_summary: true
```

```bash
sentinel-dv-index --config config.yaml --index-all
```

The indexer reads `results.xml` (JUnit) and parses `waves/test_counter_sim.vcd` into the DuckDB waveform table. Then query:

- `wave.signals` for `clk`, `rst`, `count`
- `wave.summary` for end time and highlights
