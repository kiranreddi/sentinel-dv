# Regression Tools

Compare verification runs and track quality trends over time.

## regressions.summary

Regression analytics for a *suite* over a rolling time window.

### Input

```json
{
  "suite": "nightly",
  "window_days": 7
}
```

### Output

```json
{
  "schema_version": "1.0.0",
  "suite": "nightly",
  "window_days": 7,
  "pass_rate": 50.0,
  "runs": [
    {
      "run_id": "r_...",
      "suite": "nightly",
      "status": "pass",
      "created_at": "2026-05-20T10:00:00Z"
    }
  ],
  "top_signatures": [
    {
      "signature_id": "sig_...",
      "category": "scoreboard",
      "summary": "data mismatch",
      "count": 12
    }
  ]
}
```

### Notes

- `window_days` is validated to be between `1` and `365`.

## runs.diff

Structured diff between two runs.

### Input

```json
{
  "base_run_id": "r_abc123",
  "compare_run_id": "r_def456"
}
```

### Output

```json
{
  "schema_version": "1.0.0",
  "base_run_id": "r_abc123",
  "compare_run_id": "r_def456",
  "test_changes": [
    {
      "kind": "test_status_change",
      "name": "axi_burst_test",
      "base_status": "pass",
      "compare_status": "fail"
    },
    {
      "kind": "test_removed",
      "name": "axi_old_test",
      "base_status": "fail"
    },
    {
      "kind": "test_added",
      "name": "axi_new_test",
      "compare_status": "pass"
    }
  ],
  "new_failures": [
    { "signature_id": "sig_...", "count": 3 }
  ],
  "resolved_failures": [
    { "signature_id": "sig_...", "count": 5 }
  ]
}
```

