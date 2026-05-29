# Sentinel DV Demo

Multi-project verification artifacts for indexing, MCP queries, and CI.

## Layout

```
demo/
├── config.example.yaml          # Index entire demo/ tree
├── uvm_logs/
│   ├── axi_burst/               # AXI scoreboard failure
│   └── apb_register/           # APB assertion timeout
├── cocotb_results/
│   ├── alu_core/                # ALU pass + multiply fail
│   ├── fifo_sync/               # FIFO pass + underflow fail
│   └── counter_block/           # Counter pass + overflow fail
├── waveforms/                   # Precomputed summaries (JSON)
├── verilator_counter/           # Verilator artifacts + waveform summary
├── vcs_counter/                  # VCS-style exported artifacts
├── questa_counter/               # Questa-style exported artifacts
├── cadence_counter/              # Cadence Xcelium-style exported artifacts
└── README.md
```

**Suite names** equal the artifact parent directory (for example `alu_core`, `axi_burst`).

## Multi-project quick start

```bash
cp demo/config.example.yaml demo/config.yaml
sentinel-dv-index --config demo/config.yaml --index-all
python scripts/verify_all_mcp_tools.py
```

Expected index scale: **≥17 runs**, **≥19 tests**, **≥11 failures**, **≥8 waveforms**, with assertion and coverage artifacts across Verilator, VCS, Questa, and Cadence examples.

## Single-project simulator fixtures

```bash
python scripts/verify_all_mcp_tools.py --sim vcs
python scripts/verify_all_mcp_tools.py --sim questa
python scripts/verify_all_mcp_tools.py --sim cadence
```

The checked-in fixtures are exported artifacts. The MCP server remains read-only and does not invoke simulators. If you regenerate artifacts from a simulator, preserve this layout and rerun the indexer.

## Projects at a glance

| Suite | Framework | Tests | Failure flavor |
|-------|-----------|-------|----------------|
| `axi_burst` | UVM log | `test_axi_burst` | scoreboard |
| `apb_register` | UVM log | `test_apb_register` | assertion |
| `alu_core` | cocotb JUnit | `test_alu_add`, `test_alu_mul` | assertion |
| `fifo_sync` | cocotb JUnit | `test_fifo_push_pop`, `test_fifo_underflow` | assertion |
| `counter_block` | cocotb JUnit | `test_increment`, `test_overflow` | assertion |
| `verilator_counter` | cocotb + UVM + VCD | `test_counter_sim`, overflow run, … | mixed |
| `vcs_counter` | VCS-style artifacts | `test_vcs_counter`, overflow run, … | mixed |
| `questa_counter` | Questa-style artifacts | `test_questa_counter`, overflow run, … | mixed |
| `cadence_counter` | Xcelium-style artifacts | `test_cadence_counter`, overflow run, … | mixed |

## Tests

```bash
pytest tests/integration/test_multi_project_all_mcp_tools.py -q
pytest tests/integration/test_verilator_all_mcp_tools.py -q
pytest tests/integration/test_simulator_examples_all_mcp_tools.py -q
```

## Documentation screenshots

Generate SVG “screenshots” (real MCP request/response cards) for the docs site:

```bash
python scripts/generate_mcp_tool_gallery.py
python scripts/generate_mcp_tool_gallery.py --open   # preview HTML in browser
```

Outputs: `docs/tools/mcp-tool-gallery.md` and `docs/assets/mcp-tools/*.svg`.
