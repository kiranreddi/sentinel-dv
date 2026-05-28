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
├── verilator_counter/           # Verilator VCD + assertions + coverage
└── README.md
```

**Suite names** equal the artifact parent directory (for example `alu_core`, `axi_burst`).

## Multi-project quick start

```bash
cd demo/verilator_counter && make run && cd ../..
cp demo/config.example.yaml demo/config.yaml
sentinel-dv-index --config demo/config.yaml --index-all
python scripts/verify_all_mcp_tools.py --multi
```

Expected index scale: **≥8 runs**, **≥10 tests**, **≥5 failures**, **≥4 waveforms**, assertions/coverage from Verilator project.

## Single-project (Verilator only)

```bash
cd demo/verilator_counter
make run && cp config.example.yaml config.yaml
sentinel-dv-index --config config.yaml --index-all
python ../../scripts/verify_all_mcp_tools.py --in-place
```

See [verilator_counter/README.md](verilator_counter/README.md).

## Projects at a glance

| Suite | Framework | Tests | Failure flavor |
|-------|-----------|-------|----------------|
| `axi_burst` | UVM log | `test_axi_burst` | scoreboard |
| `apb_register` | UVM log | `test_apb_register` | assertion |
| `alu_core` | cocotb JUnit | `test_alu_add`, `test_alu_mul` | assertion |
| `fifo_sync` | cocotb JUnit | `test_fifo_push_pop`, `test_fifo_underflow` | assertion |
| `counter_block` | cocotb JUnit | `test_increment`, `test_overflow` | assertion |
| `verilator_counter` | cocotb + UVM + VCD | `test_counter_sim`, overflow run, … | mixed |

## Tests

```bash
pytest tests/integration/test_multi_project_all_mcp_tools.py -q
pytest tests/integration/test_verilator_all_mcp_tools.py -q
```

## Documentation screenshots

Generate SVG “screenshots” (real MCP request/response cards) for the docs site:

```bash
python scripts/generate_mcp_tool_gallery.py
python scripts/generate_mcp_tool_gallery.py --open   # preview HTML in browser
```

Outputs: `docs/tools/mcp-tool-gallery.md` and `docs/assets/mcp-tools/*.svg`.
