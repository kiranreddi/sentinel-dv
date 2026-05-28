# cocotb + precomputed waveform JSON

Index the bundled **`demo/`** tree to exercise UVM logs, cocotb JUnit results, and precomputed **`*.wave.json`** summaries alongside MCP **`wave.signals`** / **`wave.summary`**.

## Requirements

- `sentinel-dv>=1.1.0`
- Repository clone (examples live under `demo/`)

## 1. Configure

From the repository root:

```bash
cp config.example.yaml config.yaml
```

Ensure `artifact_roots` includes `./demo` and `adapters.waveform_summary: true` (see `config.example.yaml`).

## 2. Index

```bash
sentinel-dv-index --config config.yaml --index-all
```

Expected: cocotb tests from `demo/cocotb_results/results.xml`, plus waveform rows for `demo/waveforms/test_increment.wave.json` and `test_overflow.wave.json`.

## 3. Query (MCP)

Start the server:

```bash
sentinel-dv-server --config config.yaml
```

Use **`tests.list`** to find test IDs, then:

- **`wave.signals`** — per-signal toggles and last values from JSON summaries
- **`wave.summary`** — highlights and trace bounds

Precomputed JSON must include a `test_name` matching an indexed test (see `demo/waveforms/test_increment.wave.json`).

## Files

| Path | Role |
|------|------|
| `demo/cocotb_results/results.xml` | JUnit listing `test_increment`, `test_overflow` |
| `demo/waveforms/*.wave.json` | Bounded summaries linked by `test_name` |
| `demo/uvm_logs/` | Sample UVM log for failure/triage tools |

See also: [Examples overview](overview.md), [Waveform summaries guide](../guides/waveforms.md).
