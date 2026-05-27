# Tool Overview

Sentinel DV provides **15 MCP tools** organized into categories for verification intelligence.

## Tool Categories

### 🔍 Discovery Tools

Find and list verification artifacts with filtering and pagination.

| Tool | Purpose | Key Filters |
|------|---------|-------------|
| [`runs.list`](discovery.md#runslist) | List indexed runs | suite, status, time range, CI info |
| [`tests.list`](discovery.md#testslist) | List tests | run_id, framework, status, name pattern |
| [`assertions.list`](discovery.md#assertionslist) | List assertions | scope, protocol, tags |
| [`coverage.list`](discovery.md#coveragelist) | List coverage summaries | run_id, kind, scope |

### 📊 Detail Tools

Get comprehensive information about specific items.

| Tool | Purpose | Returns |
|------|---------|---------|
| [`tests.get`](detail.md#testsget) | Get test details | Full TestCase with evidence |
| [`tests.topology`](detail.md#teststopology) | Get test topology | UVM hierarchy + interface bindings |
| `runs.get` | Get run details | Run identifier |
| [`assertions.get`](detail.md#assertionsget) | Get assertion definition | AssertionInfo with intent |

### 🔬 Analysis Tools

Analyze failures, assertions, and coverage.

| Tool | Purpose | Key Features |
|------|---------|--------------|
| [`failures.list`](analysis.md#failureslist) | List failure events | Categorized, with evidence |
| [`assertions.failures`](analysis.md#assertionsfailures) | List assertion failures | Runtime failures linked to definitions |
| [`coverage.summary`](analysis.md#coveragesummary) | Get coverage metrics | Bounded metrics with missed bins |

### 📈 Regression Tools

Regression analytics and comparisons.

| Tool | Purpose | Returns |
|------|---------|---------|
| [`regressions.summary`](regression.md#regressionssummary) | Regression summary | Pass rate + top failure signatures |
| [`runs.diff`](regression.md#runsdiff) | Compare two runs | Structured diff with coverage deltas |

### 🌊 Waveform Tools

Pre-computed summaries from **`*.wave.json`** and **`*.vcd`** (built-in `VcdSummaryParser`). No raw FSDB/WLF streaming to clients.

| Tool | Purpose | Status |
|------|---------|--------|
| `wave.signals` | List indexed signals for a test | Stable |
| `wave.summary` | Get highlights and metadata for a test | Stable |

---

## Common Request Patterns

### Pagination

All list tools support pagination:

```json
{
  "page": 1,
  "page_size": 50,
  "sort_by": "created_at",
  "sort_order": "desc"
}
```

**Response includes:**

```json
{
  "schema_version": "1.0.0",
  "page": 1,
  "page_size": 50,
  "total_items": 150,
  "total_pages": 3,
  "items": [...]
}
```

### Filtering

Most tools support multiple filters (AND semantics):

```json
{
  "status": "fail",
  "framework": "uvm",
  "name_contains": "axi"
}
```

### Evidence Inclusion

Control evidence attachment:

```json
{
  "include_evidence": true
}
```

**Default:** `false` (for performance)

---

## Tool Selection Guide

### "Why did this test fail?"

```
1. tests.list (find test by name/status)
2. failures.list (get failure events for test)
3. tests.topology (understand testbench structure)
4. assertions.failures (check assertion failures)
```

### "What changed between runs?"

```
1. runs.diff (structured comparison)
2. coverage.summary (for both runs, if needed)
```

### "Which tests cover this interface?"

```
1. tests.list (filter by name pattern)
2. tests.topology (check interface bindings)
3. coverage.summary (verify coverage)
```

### "Show me top failures this week"

```
1. regressions.summary (time window + top signatures)
2. failures.list (detailed events for signature)
```

---

## Error Handling

All tools return structured errors:

```json
{
  "schema_version": "1.0.0",
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "page_size must be between 1 and 200",
    "details": {"field": "page_size", "value": "500"}
  }
}
```

**Error codes:**

- `NOT_FOUND` - Resource doesn't exist
- `INVALID_ARGUMENT` - Bad request parameters
- `PERMISSION_DENIED` - Path sandboxing violation
- `INTERNAL` - Server error
- `INDEX_NOT_READY` - Index not built or stale
- `LIMIT_EXCEEDED` - Response would exceed limits

---

## Next Steps

- [Discovery Tools Reference](discovery.md)
- [Detail Tools Reference](detail.md)
- [Analysis Tools Reference](analysis.md)
- [Regression Tools Reference](regression.md)
