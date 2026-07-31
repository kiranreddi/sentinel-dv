# Discovery Tools

Discovery tools list indexed records with bounded, consistent pagination. Filters
within one request use AND semantics.

## runs.list

List verification runs.

| Parameter | Type | Description |
|-----------|------|-------------|
| `suite` | string? | Exact suite name |
| `status` | string? | Run status |
| `ci_system` | string? | CI provider |
| `page`, `page_size` | int | Pagination |

```json
{
  "suite": "nightly",
  "status": "fail",
  "page": 1,
  "page_size": 100
}
```

The `runs` array includes run metadata and aggregate test counts. Use
`regressions.summary` for a bounded date window; `runs.list` does not accept
date, build-ID, or sort parameters.

## tests.list

List indexed tests.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Exact run identifier |
| `framework` | string? | Framework such as `uvm` or `cocotb` |
| `status` | string? | Test status |
| `name_pattern` | string? | Case-sensitive name substring |
| `page`, `page_size` | int | Pagination |

```json
{
  "run_id": "r_nightly",
  "status": "fail",
  "name_pattern": "axi",
  "page": 1
}
```

Use `failures.list` to determine whether a test has indexed failures; there is
no `has_failures` filter.

## assertions.list

List indexed assertion definitions.

| Parameter | Type | Description |
|-----------|------|-------------|
| `scope` | string? | Scope filter |
| `name_pattern` | string? | Assertion-name substring |
| `protocol` | string? | Exact `intent.protocol` value |
| `tag` | string? | Tag substring |
| `page`, `page_size` | int | Pagination |

```json
{
  "protocol": "axi4",
  "tag": "handshake",
  "page": 1
}
```

Definitions do not carry a severity filter. Use `assertions.failures` and
`assertions.sva_status` for runtime behavior.

## coverage.list

List indexed coverage-summary rows.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Exact run identifier |
| `kind` | string? | Coverage kind |
| `page`, `page_size` | int | Pagination |

```json
{
  "run_id": "r_nightly",
  "kind": "functional",
  "page": 1
}
```

Rows contain the indexed `metrics` payload. Use `coverage.gaps` for threshold,
priority, suite, or metric-level analysis.

## Pagination

List responses contain a named result array and a nested pagination object:

```json
{
  "schema_version": "1.0.0",
  "pagination": {
    "page": 1,
    "page_size": 100,
    "total_items": 150,
    "total_pages": 2
  },
  "tests": []
}
```

Read subsequent pages until the intended scope is complete. Do not infer
absence from the first page of a multi-page response.
