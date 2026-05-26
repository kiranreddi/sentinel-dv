# Performance Optimization

Sentinel DV indexes verification artifacts into DuckDB using a single, supported mode: full indexing via `--index-all`.

## Indexing performance (what you can tune)

1. Narrow your `artifact_roots`
   - Point `artifact_roots` only at the directories you actually want indexed.
   - This directly reduces the number of `*.log`, `results.xml`, and `junit.xml` files scanned.

2. Use recognized artifact formats
   - UVM logs: `*.log`
   - cocotb results: `results.xml` / `junit.xml`

## Query performance (what you can tune)

1. Pagination
   - List tools accept `page` and `page_size` and are clamped to `security.max_page_size`.

2. Response sizing
   - `security.max_response_bytes` limits how much data can be returned per tool call.

## Practical workflow

1. Start with a small subset of artifacts (few runs / a single directory).
2. Run: `python -m sentinel_dv.indexing.indexer --config config.yaml --index-all`
3. Validate your queries using list tools (`runs.list`, `tests.list`, `failures.list`, etc.).
4. Increase scope once you confirm schemas and redaction behave as expected.

