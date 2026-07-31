# Tool Overview

Sentinel DV provides **28 MCP tools** organized into categories for verification intelligence.

## Tool Categories

### 🔍 Discovery Tools

Find and list verification artifacts with filtering and pagination.

| Tool | Purpose | Key Filters |
|------|---------|-------------|
| [`runs.list`](discovery.md#runslist) | List indexed runs | suite, status, CI system |
| [`tests.list`](discovery.md#testslist) | List tests | run_id, framework, status, name pattern |
| [`assertions.list`](discovery.md#assertionslist) | List assertions | scope, protocol, tags |
| [`coverage.list`](discovery.md#coveragelist) | List coverage summaries | run_id, kind |

### 📊 Detail Tools

Get comprehensive information about specific items.

| Tool | Purpose | Returns |
|------|---------|---------|
| [`tests.get`](detail.md#testsget) | Get test details | Indexed execution metadata |
| [`tests.history`](mcp-tools-reference.md#testshistory) | Test outcomes over time | Status timeline + flaky hint |
| [`tests.topology`](detail.md#teststopology) | Get test topology | UVM hierarchy + interface bindings |
| `runs.get` | Get run details | Run identifier |
| [`runs.summary`](mcp-tools-reference.md#runssummary) | Per-run rollup | Test counts, pass rate, slowest tests |
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
| [`wave.signals`](waveforms.md#wavesignals) | List signals; optional `start_time_ns` / `end_time_ns` window | Stable |
| [`wave.summary`](waveforms.md#wavesummary) | Highlights and metadata; same time window | Stable |

Full parameter reference: [MCP tools reference](mcp-tools-reference.md).

### MCP tool gallery (visual)

Auto-generated **SVG cards** show real request/response JSON for every tool (from the multi-project `demo/` index):

- **[Browse all 28 tools in the gallery](mcp-tool-gallery.md)** — embedded screenshots + full JSON
- [Interactive HTML preview](../assets/mcp-tools/gallery.html) — open in a new tab

Regenerate after demo or API changes:

```bash
python scripts/generate_mcp_tool_gallery.py
```

### 🚀 v2.0.0 Tools

New in v2.0.0: job submission, live simulation monitoring, SVA formal status, seed replay, and coverage closure.

| Tool | Purpose | Requires config |
|------|---------|-----------------|
| [`runs.submit`](mcp-tools-reference.md#runssubmit) | Generate simulator submit command | `submit.enabled: true` |
| [`sim.status`](mcp-tools-reference.md#simstatus) | Live simulation progress | `adapters.live_sim: true` |
| [`assertions.sva_status`](mcp-tools-reference.md#assertionssva_status) | SVA/formal property status | — |
| [`assertions.vacuity`](mcp-tools-reference.md#assertionsvacuity) | Vacuously-passing assertions | — |
| [`tests.replay`](mcp-tools-reference.md#testsreplay) | Seed-replay command for failing test | `submit.enabled: true` |
| [`coverage.gaps`](mcp-tools-reference.md#coveragegaps) | Prioritized coverage closure guidance | — |

### 🧠 v2.1.0 DV Intelligence Tools

New in v2.1.0: bounded analysis tools that turn indexed evidence into reviewable DV investigation signals.

| Tool | Purpose | Key Insight |
|------|---------|-------------|
| [`coverage.trend`](mcp-tools-reference.md#coveragetrend) | Coverage trajectory over time | Identifies stalled or regressing coverage |
| [`runs.cross_sim`](mcp-tools-reference.md#runscross_sim) | Cross-simulator divergence detector | Finds tests that pass on one sim but fail on another |
| [`tests.cluster`](mcp-tools-reference.md#testscluster) | Failure signature clustering | Heuristically groups failures for faster triage |
| [`regression.health`](mcp-tools-reference.md#regressionhealth) | Composite DV health indicator | Scoped 0–100 score with data-quality disclosure |
| [`coverage.advisor`](mcp-tools-reference.md#coverageadvisor) | SV constraint candidate generator | Reviewable protocol-aware snippets (AXI4, AHB, APB, CHI) |

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
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 150,
    "total_pages": 3
  },
  "runs": [...]
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

### "How do I close coverage?"

```
1. coverage.summary (identify low coverage runs)
2. coverage.gaps    (get prioritized gap list with recommendations)
3. coverage.advisor (get a reviewable SV constraint candidate)
4. runs.submit      (generate a dry-run command for engineer review)
```

### "What sign-off evidence is available?"

```
1. regression.health (get scoped indicator, effective weights, and missing-data warnings)
2. coverage.trend    (check if coverage is trending upward)
3. runs.cross_sim    (inspect comparable simulator cohorts and divergence)
```

### "Why are so many tests failing?"

```
1. tests.cluster     (group failures by normalized signature)
2. failures.list     (drill into each cluster)
3. assertions.failures (check correlated assertion failures)
```

### "Is my simulation still running?"

```
1. sim.status (check phase, percent_done, staleness)
```

### "Replay a failing test with the same seed"

```
1. tests.list   (find the failing test ID)
2. tests.replay (get a dry-run replay command for engineer review)
```

---

## Next Steps

- [Discovery Tools Reference](discovery.md)
- [Detail Tools Reference](detail.md)
- [Analysis Tools Reference](analysis.md)
- [Regression Tools Reference](regression.md)
