# Index Store

## Overview

Sentinel DV uses an index store to serve MCP tools efficiently and deterministically from potentially massive artifact trees.

## Storage Backend Recommendation (v1)

**DuckDB** is the recommended default:

- Simple to ship and operate
- Strong filtering and pagination
- Deterministic queries
- Excellent for analytical workloads (100k–100M rows)
- Built-in support for complex aggregations

`v1.x` supports DuckDB only.

---

## DuckDB Schema (v1)

### Table: runs

**Columns**:

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,              -- short form, e.g., r_...
    run_id_full TEXT UNIQUE NOT NULL,     -- full sha256 hex
    suite TEXT NOT NULL,
    created_at TEXT NOT NULL,             -- RFC3339
    status TEXT NOT NULL,                 -- pass|fail|mixed|unknown
    ci_system TEXT,
    ci_build_id TEXT,
    ci_job_url TEXT,
    artifact_manifest_hash TEXT,
    index_built_at TEXT NOT NULL
);
```

**Indexes**:

```sql
CREATE INDEX idx_runs_suite_created_at ON runs(suite, created_at);
CREATE INDEX idx_runs_ci_build ON runs(ci_system, ci_build_id);
```

### Table: tests

**Columns**:

```sql
CREATE TABLE tests (
    test_id TEXT PRIMARY KEY,             -- t_...
    test_id_full TEXT UNIQUE NOT NULL,
    run_id TEXT NOT NULL,                 -- REFERENCES runs(run_id)
    framework TEXT NOT NULL,
    name TEXT NOT NULL,
    seed INTEGER,
    status TEXT NOT NULL,                 -- pass|fail|error|skipped|unknown
    duration_ms INTEGER,
    sim_vendor TEXT,
    sim_version TEXT,
    dut_top TEXT,
    created_at TEXT NOT NULL              -- copied from run for easier filtering
);
```

**Indexes**:

```sql
CREATE INDEX idx_tests_run_status ON tests(run_id, status);
CREATE INDEX idx_tests_name ON tests(name);
CREATE INDEX idx_tests_framework ON tests(framework);
CREATE INDEX idx_tests_created_at ON tests(created_at);
```

### Table: failures

**Columns**:

```sql
CREATE TABLE failures (
    failure_id TEXT PRIMARY KEY,          -- f_...
    failure_id_full TEXT UNIQUE NOT NULL,
    test_id TEXT NOT NULL,                -- REFERENCES tests(test_id)
    run_id TEXT NOT NULL,                 -- REFERENCES runs(run_id)
    severity TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    message TEXT NOT NULL,                -- bounded+redacted
    time_ns BIGINT,
    phase TEXT,
    component TEXT,
    tags_json TEXT NOT NULL,              -- JSON array string, bounded
    tags_flat TEXT NOT NULL,              -- space-delimited for LIKE queries
    signature_id TEXT                     -- s_... precomputed clustering id
);
```

**Indexes**:

```sql
CREATE INDEX idx_failures_run_category ON failures(run_id, category);
CREATE INDEX idx_failures_test ON failures(test_id);
CREATE INDEX idx_failures_signature ON failures(signature_id);
CREATE INDEX idx_failures_time ON failures(time_ns);
```

### Table: assertions

**Columns**:

```sql
CREATE TABLE assertions (
    assertion_id TEXT PRIMARY KEY,
    assertion_id_full TEXT UNIQUE NOT NULL,
    language TEXT NOT NULL,
    name TEXT NOT NULL,
    scope TEXT NOT NULL,
    file TEXT NOT NULL,                   -- relative
    line INTEGER NOT NULL,
    intent_protocol TEXT,
    intent_requirement TEXT,
    signals_json TEXT NOT NULL            -- JSON array string, bounded
);
```

**Indexes**:

```sql
CREATE INDEX idx_assertions_name ON assertions(name);
CREATE INDEX idx_assertions_scope ON assertions(scope);
CREATE INDEX idx_assertions_file ON assertions(file);
```

### Table: assertion_failures

**Columns**:

```sql
CREATE TABLE assertion_failures (
    id INTEGER PRIMARY KEY,
    assertion_id TEXT NOT NULL,           -- REFERENCES assertions(assertion_id)
    test_id TEXT NOT NULL,                -- REFERENCES tests(test_id)
    run_id TEXT NOT NULL,                 -- REFERENCES runs(run_id)
    time_ns BIGINT,
    message TEXT NOT NULL                 -- bounded+redacted
);
```

**Indexes**:

```sql
CREATE INDEX idx_asfail_run ON assertion_failures(run_id);
CREATE INDEX idx_asfail_test ON assertion_failures(test_id);
CREATE INDEX idx_asfail_assertion ON assertion_failures(assertion_id);
```

### Table: coverage_summaries

**Columns**:

```sql
CREATE TABLE coverage_summaries (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,                 -- REFERENCES runs(run_id)
    test_id TEXT,                         -- REFERENCES tests(test_id), nullable
    kind TEXT NOT NULL,
    metrics_json TEXT NOT NULL,           -- bounded array of CoverageMetric
    evidence_json TEXT
);
```

**Indexes**:

```sql
CREATE INDEX idx_cov_run_kind ON coverage_summaries(run_id, kind);
CREATE INDEX idx_cov_test_kind ON coverage_summaries(test_id, kind);
```

### Table: topologies

**Columns**:

```sql
CREATE TABLE topologies (
    test_id TEXT PRIMARY KEY,             -- REFERENCES tests(test_id)
    topology_json TEXT NOT NULL           -- TestTopology, bounded
);
```

### Table: evidence

**Columns** (if normalized evidence desired):

```sql
CREATE TABLE evidence (
    id INTEGER PRIMARY KEY,
    owner_kind TEXT NOT NULL,             -- test|failure|assertion_failure|coverage|diff
    owner_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    start_time_ns BIGINT,
    end_time_ns BIGINT,
    extract TEXT,                         -- bounded+redacted
    hash TEXT
);
```

**Indexes**:

```sql
CREATE INDEX idx_evidence_owner ON evidence(owner_kind, owner_id);
```

**Note**: Sentinel DV now writes normalized evidence rows for failures, assertion failures, and coverage summaries. Tool-level `include_evidence` flags read from this table with bounded payloads.

---

## Query Semantics (How Tools Map to SQL)

### Common Constraints

- **Always apply page/page_size as**:
  ```sql
  LIMIT page_size OFFSET (page-1)*page_size
  ```
- **Always return `total_items`** computed via a separate `COUNT(*)` query with the same filters
- **Sorting must be stable**: if sort field ties, add secondary sort on primary key (`test_id`, `failure_id`) to keep deterministic ordering

### tests.list

Filters map to WHERE clauses:

- `run_id = ?`
- `framework = ?`
- `status = ?`
- `name LIKE %?%` (escape wildcards)
- `seed = ?`

### failures.list

Filters map to WHERE clauses:

- `test_id = ?` or `run_id = ?`
- `category = ?`
- `severity = ?`
- `component LIKE %?%`
- **Tags**:
  - For v1, tags stored as JSON string; simplest deterministic approach:
    - precompute a `tags_flat TEXT` column (space-delimited normalized tags) and query with `LIKE`
    - or use DuckDB's JSON functions: `json_extract`

**Recommended**: Store both:
- `tags_json`
- `tags_flat` (lowercase, space delimited, bounded)

Then `tags_any` → OR of `tags_flat LIKE %tag%`.

### regressions.summary

Compute:

- **pass rate**: count tests by status across runs in window
- **top signatures**: group failures by `signature_id` and count distinct tests (or failures)

**Recommended**: define clearly:
- `count` = number of occurrences (failures)
- optionally `affected_tests` = count distinct `test_id`

Use deterministic top-N ordering:
- order by `affected_tests desc`, then `count desc`, then `signature_id asc`

### runs.diff

Deterministic diff components:

1. **Test status changes**:
   - join tests by `(framework, name, seed)` (or by stable test GUID if available)

2. **Signature changes**:
   - signatures in `compare` not in `base` → "new"
   - in `base` not in `compare` → "resolved"

3. **Coverage deltas**:
   - compare coverage metrics by `(kind, name, scope)` for shared keys

4. **Config deltas**:
   - only if config snapshot is indexed (optional v1.1)

---

## Index Build Semantics

### Indexing Phases

1. **Discover runs** and their artifact roots
2. **Parse adapters** producing normalized records
3. **Compute IDs and signatures**
4. **Apply redaction and bounding**
5. **Write to DuckDB** in a transaction
6. **Record** `index_built_at` and schema version

### Incremental Indexing (optional)

- Use `artifact_manifest_hash` changes to detect whether a run needs reindex
- For CI-backed runs, prefer `ci_build_id` + `suite` as key

---

## Integrity and Reproducibility Fields (recommended)

Include in index metadata table:

### Table: meta

```sql
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**Suggested keys**:

- `schema_version`
- `indexer_version`
- `built_at`
- `config_hash` (sha256 of normalized config affecting indexing)

This supports "same inputs → same outputs" audits.

---

## Tight Coupling Decisions (explicit)

- IDs depend only on normalized semantic fields, not on indexing time
- Signature IDs depend only on category + signature-normalized summary (+ optional tags)
- Taxonomy rules are ordered and versioned; changes should increment MINOR or MAJOR depending on whether it changes enum behavior significantly

---

## Implementation Reference

See `sentinel_dv/indexing/store.py` for the canonical DuckDB implementation.
