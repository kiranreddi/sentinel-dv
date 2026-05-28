# MCP tools reference (all 15)

Sentinel DV exposes **15 read-only MCP tools**. Every tool returns JSON with `schema_version` (currently `1.0.0`) or a structured `error` object.

**Prerequisites:** `sentinel-dv-index --config config.yaml --index-all` before querying.

List tools in your client or see [Tool overview](overview.md) for category descriptions. Deep dives: [Discovery](discovery.md), [Detail](detail.md), [Analysis](analysis.md), [Regression](regression.md), [Waveforms](waveforms.md).

---

## Discovery

### runs.list

List indexed verification runs.

| Parameter | Type | Description |
|-----------|------|-------------|
| `suite` | string? | Filter by suite |
| `status` | string? | `pass`, `fail`, `error` |
| `ci_system` | string? | CI identifier |
| `page` | int | Default `1` |
| `page_size` | int | Default `100` |

```json
{ "suite": "nightly", "status": "fail", "page": 1, "page_size": 20 }
```

### tests.list

List tests with filters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Scope to one run |
| `framework` | string? | `uvm`, `cocotb`, `verilator`, … |
| `status` | string? | `pass`, `fail`, `error` |
| `name_pattern` | string? | Substring match on test name |
| `page`, `page_size` | int | Pagination |

```json
{ "run_id": "r_xyz", "status": "fail", "name_pattern": "axi" }
```

### assertions.list

List assertion definitions in the index.

| Parameter | Type | Description |
|-----------|------|-------------|
| `scope` | string? | Hierarchy scope |
| `name_pattern` | string? | Name substring |
| `page`, `page_size` | int | Pagination |

```json
{ "scope": "axi_agent", "page": 1, "page_size": 50 }
```

### coverage.list

List coverage summary records.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Filter by run |
| `kind` | string? | e.g. `functional`, `line` |
| `page`, `page_size` | int | Pagination |

```json
{ "run_id": "r_xyz", "kind": "functional" }
```

---

## Detail

### runs.get

Get one run by ID.

```json
{ "run_id": "r_xyz" }
```

### tests.get

Full test record (status, duration, evidence refs).

```json
{ "test_id": "t_abc" }
```

### tests.topology

UVM / testbench topology and interface bindings for a test.

```json
{ "test_id": "t_abc" }
```

### assertions.get

Assertion definition and intent metadata.

```json
{ "assertion_id": "a_xyz" }
```

---

## Analysis

### failures.list

Failure events with taxonomy and evidence.

| Parameter | Type | Description |
|-----------|------|-------------|
| `test_id`, `run_id` | string? | Scope |
| `category` | string? | e.g. `assertion`, `scoreboard` |
| `severity` | string? | Severity filter |
| `tags_any` | string[]? | Match any tag |
| `page`, `page_size` | int | Pagination |

```json
{
  "test_id": "t_abc",
  "category": "scoreboard",
  "page": 1,
  "page_size": 25
}
```

### assertions.failures

Runtime assertion failures linked to definitions.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id`, `test_id`, `assertion_id` | string? | Filters |
| `page`, `page_size` | int | Pagination |

```json
{ "test_id": "t_abc", "page": 1, "page_size": 50 }
```

### coverage.summary

Aggregated coverage metrics for a run.

```json
{ "run_id": "r_xyz", "kind": "functional" }
```

---

## Regression

### regressions.summary

Pass rate and top failure signatures for a suite over a time window.

```json
{ "suite": "nightly", "window_days": 7 }
```

### runs.diff

Structured diff between two runs (tests, coverage deltas).

```json
{ "base_run_id": "r_old", "compare_run_id": "r_new" }
```

---

## Waveforms

Requires `adapters.waveform_summary: true` and indexed `*.wave.json` or `*.vcd`. See [Waveform tools](waveforms.md).

### wave.signals

```json
{ "test_id": "t_abc" }
```

With time window (nanoseconds; both required together):

```json
{
  "test_id": "t_abc",
  "start_time_ns": 2000,
  "end_time_ns": 3000
}
```

### wave.summary

Same parameters as `wave.signals`.

```json
{
  "test_id": "t_abc",
  "start_time_ns": 2000,
  "end_time_ns": 3000
}
```

---

## Suggested tool chains

| Goal | Tools |
|------|--------|
| Why did a test fail? | `tests.list` → `tests.get` → `failures.list` → `tests.topology` |
| Assertion debug | `assertions.list` → `assertions.failures` → `assertions.get` |
| Nightly health | `regressions.summary` → `runs.list` → `failures.list` |
| Run comparison | `runs.diff` → `coverage.summary` |
| Waveform slice | `tests.list` → `wave.summary` → `wave.signals` (+ optional window) |

---

## Errors

| Code | Meaning |
|------|---------|
| `INDEX_NOT_READY` | Index missing or config not loaded |
| `INVALID_ARGUMENT` | Bad IDs, pagination, or time window (`start` > `end`, only one of start/end set) |
| `NOT_FOUND` | Unknown `test_id`, `run_id`, etc. |
