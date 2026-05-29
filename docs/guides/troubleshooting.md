# Troubleshooting

## Common startup issues

### “No configuration found…”

Sentinel DV requires a config file. Use either:
- Create config first: `cp config.example.yaml config.yaml` (required — no automatic `demo/` fallback)
- `python -m sentinel_dv.server --config /path/to/config.yaml`
- or `export SENTINEL_DV_CONFIG=/path/to/config.yaml` and then run `python -m sentinel_dv.server`

### “Index not ready…”

If a tool fails with `INDEX_NOT_READY`, run indexing first:

```bash
python -m sentinel_dv.indexing.indexer --config config.yaml --index-all
```

## Tool errors (structured)

Tool responses follow this error shape:

```json
{
  "schema_version": "1.0.0",
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "..."
  }
}
```

Common `code` values include:
- `INVALID_ARGUMENT`
- `INDEX_NOT_READY`
- `NOT_FOUND`
- `PERMISSION_DENIED`
- `INTERNAL`
- `LIMIT_EXCEEDED`

