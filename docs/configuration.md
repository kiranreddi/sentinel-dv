# Configuration

`config.yaml` (or `config.yml`) controls what Sentinel DV indexes and the safety limits it enforces on tool responses.

## Configuration is required

The MCP server and indexer **do not start without a config file**. Sentinel DV will **not** silently point at the bundled `demo/` tree if you omit configuration.

Provide config in **one** of these ways:

1. **`--config /absolute/path/to/config.yaml`** on `sentinel-dv-server` and `sentinel-dv-index`
2. **`SENTINEL_DV_CONFIG`** environment variable (same path)
3. **`config.yaml` or `config.yml`** in the process **current working directory**

Copy the template from the repository root:

```bash
cp config.example.yaml config.yaml
# edit artifact_roots and index.path, then index and start the server
```

For trying examples only, use the demo-specific templates (e.g. `cp demo/config.example.yaml demo/config.yaml`).

## Minimal example

```yaml
artifact_roots:
  - /path/to/verification/regressions

index:
  type: duckdb
  path: ./sentinel_dv.db

adapters:
  uvm: true
  cocotb: true
  assertions: true
  coverage: true
  waveform_summary: false  # index *.wave.json and *.vcd (see guides/waveforms.md)

security:
  max_response_bytes: 2097152
  max_page_size: 200
  max_evidence_refs: 10
  max_excerpt_length: 1024
  max_message_length: 4096
  max_tags_per_event: 20
  max_coverage_metrics: 200
  max_bins_missed: 50

redaction:
  enabled: true
  patterns: []
  redact_emails: true
  redact_ips: false
  redact_paths: true
```

## Where to set the config path

You can either pass `--config /path/to/config.yaml` to the server/indexer, or set:

```bash
export SENTINEL_DV_CONFIG=/absolute/path/to/config.yaml
```

## Waveform summaries

When `adapters.waveform_summary` is `true`, the indexer uses:

- **`WaveformSummaryParser`** — `*.wave.json` precomputed summaries
- **`VcdSummaryParser`** — Verilator-style `*.vcd` files (toggle counts, last values)

See [Waveform summaries](guides/waveforms.md) and the [Verilator example](examples/verilator-counter.md).

