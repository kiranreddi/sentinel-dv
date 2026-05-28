# Architecture Overview

Sentinel DV is designed with **security-first principles** and strict **separation of concerns**.

## Design Principles

### 1. Read-Only by Design

**No mutations, no control:**

- All tools are strictly read-only
- No simulator triggers or job submissions
- No artifact modification
- No configuration changes via API

**Enforcement:**

```python
# All file operations use read-only modes
with open(artifact_path, 'r') as f:  # Never 'w' or 'a'
    data = f.read()
```

### 2. Schema-First Contracts

**Every response conforms to versioned schemas:**

```python
from sentinel_dv.schemas import TestCase

# Response structure is deterministic
test: TestCase = {
    "id": "T123",
    "framework": "uvm",
    "status": "fail",
    ...
}
```

**Benefits:**

- LLMs can reason reliably
- Backward compatibility guarantees
- Self-documenting APIs
- Testable contracts

### 3. Deterministic Outputs

**Same input → same output:**

- No LLM-generated fields in responses
- All facts derived from artifacts
- Stable signature hashing
- Reproducible indexing

### 4. Evidence-Based Facts

**Every fact traceable to source:**

```python
failure: FailureEvent = {
    "message": "AXI BRESP error",
    "evidence": [
        {
            "kind": "log",
            "path": "test.log",
            "span": {"start_line": 142, "end_line": 148},
            "extract": "...",
            "hash": "sha256..."
        }
    ]
}
```

### 5. Security Boundaries

**Defense in depth:**

1. **Path sandboxing** - Only configured roots accessible
2. **Automatic redaction** - Secrets/PII removed
3. **Size limits** - Prevent DoS and prompt injection
4. **Input validation** - Pydantic schemas
5. **Fail-safe defaults** - Conservative limits

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Server                           │
│  (server.py + registry.py)                             │
│  - Tool registration                                    │
│  - Request routing                                      │
│  - Response serialization                               │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                    Tools Layer                          │
│  runs.py │ tests.py │ failures.py │ assertions.py │...  │
│  - Business logic                                       │
│  - Query construction                                   │
│  - Pagination & filtering                               │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                  Indexing Layer                         │
│  indexer.py │ store.py │ query.py                       │
│  - Artifact scanning                                    │
│  - DuckDB queries                                       │
│  - Caching & optimization                               │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                  Adapters Layer                         │
│  uvm_log.py │ cocotb.py │ assertions.py │ coverage.py   │
│  - Parse raw artifacts                                  │
│  - Normalize to schemas                                 │
│  - Extract metadata                                     │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│               Normalization Layer                       │
│  signatures.py │ taxonomy.py │ redaction.py             │
│  - Failure signature hashing                            │
│  - Category mapping                                     │
│  - Automatic redaction                                  │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                   Schemas Layer                         │
│  common.py │ tests.py │ failures.py │ assertions.py │...│
│  - Pydantic models                                      │
│  - Validation rules                                     │
│  - Type definitions                                     │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Indexing Flow

```
Artifact Roots → Adapters → Normalization → Index Store
                    ↓           ↓              ↓
                Raw Parse   Redact &      DuckDB
                            Categorize
```

**Steps:**

1. **Scan** configured artifact roots
2. **Parse** files using enabled adapters
3. **Normalize** extracted data (redaction, signatures)
4. **Store** in indexed database
5. **Build** lookup indexes for fast queries

### Query Flow

```
MCP Request → Tool → Query Builder → Index Store → Normalization → Response
                ↓          ↓              ↓             ↓              ↓
           Validate   SQL/Filter     DuckDB       Redact        Schema
           Input      Construction    Query        Evidence      Serialize
```

**Steps:**

1. **Receive** MCP tool call
2. **Validate** input parameters
3. **Build** database query with filters/pagination
4. **Execute** query against index
5. **Normalize** results (redaction, bounding)
6. **Serialize** to schema-compliant JSON

---

## Storage Architecture

### DuckDB Schema

```sql
-- Runs table
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    suite TEXT,
    created_at TIMESTAMP,
    ci_system TEXT,
    ci_job_url TEXT,
    ci_build_id TEXT
);

-- Tests table
CREATE TABLE tests (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    framework TEXT,
    name TEXT,
    status TEXT,
    duration_ms INTEGER,
    seed INTEGER,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Failures table
CREATE TABLE failures (
    id TEXT PRIMARY KEY,
    test_id TEXT,
    category TEXT,
    severity TEXT,
    summary TEXT,
    message TEXT,
    time_ns INTEGER,
    signature_id TEXT,
    FOREIGN KEY (test_id) REFERENCES tests(id)
);

-- ... additional tables for assertions, coverage, topology
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_tests_run_id ON tests(run_id);
CREATE INDEX idx_tests_status ON tests(status);
CREATE INDEX idx_failures_test_id ON failures(test_id);
CREATE INDEX idx_failures_signature ON failures(signature_id);
CREATE INDEX idx_failures_category ON failures(category);
```

---

## Security Architecture

### Defense Layers

1. **Configuration Validation**
   - Schema-based validation
   - Path existence checks
   - Permission verification

2. **Path Sandboxing**
   - Normalized paths only
   - No `..` traversal
   - Artifact root allowlist

3. **Automatic Redaction**
   - Credential patterns
   - Email addresses
   - Absolute paths
   - IP addresses

4. **Response Bounding**
   - Max response size (2MB default)
   - Max items per page (200 default)
   - Max evidence refs (10 default)
   - Max excerpt length (1KB default)

5. **Input Validation**
   - Pydantic models
   - Enum validation
   - Range checks

### Redaction Pipeline

```
Raw Text → Pattern Matching → Replacement → Truncation → Output
              ↓                   ↓             ↓
          Regex Scan        <REDACTED>    Max Length
```

---

## Extensibility

### Adding a New Adapter

1. Create `adapters/new_tool.py`
2. Implement parser functions returning schema objects
3. Add enable flag to `AdaptersConfig`
4. Write tests with fixtures
5. Update documentation

### Adding a New Tool

1. Create `tools/new_tool.py`
2. Define request/response schemas
3. Implement query logic
4. Register in `registry.py`
5. Document in tool reference

---

## Performance Considerations

### Indexing

- **Incremental indexing** for large artifact sets
- **Parallel parsing** of independent files
- **Deduplication** of identical artifacts

### Querying

- **Selective projection** - fetch only needed fields
- **Smart pagination** - stable ordering
- **Query optimization** - DuckDB query planner
- **Connection pooling** - reuse database connections

---

## See Also

- [Schema Reference](schemas.md)
- [Security Model](security.md)
- [Tool Reference](../tools/overview.md)
- [Adapter Development](../adapters/custom.md)
