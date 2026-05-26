# Configuration

`config.yaml` controls what Sentinel DV indexes and the safety limits it enforces on tool responses.

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
  waveform_summary: false

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

