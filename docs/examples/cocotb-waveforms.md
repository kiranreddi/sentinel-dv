# cocotb + precomputed waveform JSON

Index the bundled **`demo/`** tree to exercise multiple cocotb projects, UVM logs, and precomputed **`*.wave.json`** summaries.

## Requirements

- `sentinel-dv>=1.2.0`
- Repository clone (examples live under `demo/`)

## 1. Configure

```bash
cp demo/config.example.yaml demo/config.yaml
```

This enables all adapters and sets `artifact_roots: [.] ` relative to `demo/`.

## 2. Index

From `demo/` or pass `--config demo/config.yaml` from the repo root:

```bash
sentinel-dv-index --config demo/config.yaml --index-all
```

Expected cocotb suites:

| Suite | JUnit | Waveform JSON |
|-------|-------|----------------|
| `counter_block` | `cocotb_results/counter_block/results.xml` | `waveforms/test_increment.wave.json`, `test_overflow.wave.json` |
| `alu_core` | `cocotb_results/alu_core/results.xml` | `waveforms/alu_core/test_alu_add.wave.json` |
| `fifo_sync` | `cocotb_results/fifo_sync/results.xml` | `waveforms/fifo_sync/test_fifo_push_pop.wave.json` |

## 3. Query (MCP)

```bash
sentinel-dv-server --config demo/config.yaml
```

Use **`tests.list`** with `name_pattern` (for example `alu_tb`) to find test IDs, then **`wave.signals`** / **`wave.summary`**.

## Verify

```bash
python scripts/verify_all_mcp_tools.py --multi
pytest tests/integration/test_multi_project_all_mcp_tools.py -q
```

See also: [Examples overview](overview.md), [Multi-project demo README](https://github.com/kiranreddi/sentinel-dv/blob/main/demo/README.md).
