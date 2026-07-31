# MCP tools reference (all 28)

Sentinel DV exposes **28 read-only MCP tools** (v1.x discovery/analysis/regression/waveform, v2.0 submission/live-sim/SVA/replay/gaps, v2.1 DV intelligence). Every tool returns JSON with `schema_version` (currently `1.0.0`) or a structured `error` object.

See [Tool overview](overview.md) for categories and [MCP tool gallery](mcp-tool-gallery.md) for visual examples.

**Prerequisites:** `sentinel-dv-index --config config.yaml --index-all` before querying.

**End-to-end examples (all 28 tools):**

- **Multi-project:** index `demo/` (UVM, cocotb, Verilator, VCS, Questa, Cadence) — `python scripts/verify_all_mcp_tools.py` — see [demo/README](https://github.com/kiranreddi/sentinel-dv/blob/main/demo/README.md)
- **Simulator fixtures:** [VCS, Questa, and Cadence examples](../examples/commercial-simulators.md) — `python examples/simulator_matrix.py --sim all`
- **Verilator:** [Verilator counter walkthrough](../examples/verilator-counter.md) — `python scripts/verify_all_mcp_tools.py --sim verilator`
- **Visual gallery:** [MCP Tool Gallery](mcp-tool-gallery.md) — SVG “screenshots” from `python scripts/generate_mcp_tool_gallery.py`

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
| `framework` | string? | `uvm`, `cocotb`, `unknown`, … |
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
| `protocol` | string? | Filter by `intent.protocol` (for example `axi4`, `apb`) |
| `tag` | string? | Substring filter over assertion tags |
| `page`, `page_size` | int | Pagination |

```json
{ "scope": "axi_agent", "protocol": "axi4", "tag": "handshake", "page": 1, "page_size": 50 }
```

### coverage.list

**Paginated catalog** of coverage rows (possibly across many runs). Use to discover which `run_id` / `kind` combinations exist.

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

### runs.summary

Per-run rollup: test status counts, pass rate, failure/assertion event totals, and slowest tests (no full `tests.list` pagination).

```json
{ "run_id": "r_xyz" }
```

### tests.get

Full test record (status, duration, evidence refs).

```json
{ "test_id": "t_abc" }
```

### tests.history

Time-ordered outcomes for a logical `test_name` across runs (flaky detection via `is_flaky` / `distinct_statuses`).

```json
{
  "test_name": "counter_tb.test_counter_sim",
  "suite": "verilator_counter",
  "window_days": 30,
  "limit": 50
}
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
| `include_evidence` | bool | Include bounded evidence refs |
| `page`, `page_size` | int | Pagination |

```json
{
  "test_id": "t_abc",
  "category": "scoreboard",
  "include_evidence": true,
  "page": 1,
  "page_size": 25
}
```

### assertions.failures

Runtime assertion failures linked to definitions.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id`, `test_id`, `assertion_id` | string? | Filters |
| `start_time_ns`, `end_time_ns` | int? | Optional bounded time window (both required together) |
| `include_evidence` | bool | Include bounded evidence refs |
| `page`, `page_size` | int | Pagination |

```json
{
  "test_id": "t_abc",
  "start_time_ns": 2000,
  "end_time_ns": 3000,
  "include_evidence": true,
  "page": 1,
  "page_size": 50
}
```

### coverage.summary

**Single-run rollup** (not paginated): all coverage summaries for one `run_id`, bounded by `security.max_coverage_metrics`. Distinct from `coverage.list`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string | Run identifier |
| `kind` | string? | Optional coverage kind filter |
| `include_evidence` | bool | Include bounded evidence refs in each summary |

```json
{ "run_id": "r_xyz", "kind": "functional", "include_evidence": true }
```

---

## Regression

### regressions.summary

Pass rate and top failure signatures for a suite over a time window.

| Parameter | Type | Description |
|-----------|------|-------------|
| `suite` | string | Regression suite name |
| `window_days` | int | Window size in days (`1..365`) |
| `as_of` | string? | RFC3339 end timestamp for deterministic replay |

```json
{ "suite": "nightly", "window_days": 7, "as_of": "2026-05-27T23:00:00Z" }
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

Metadata, **`highlight_groups`** (by category), and optional time window. Set **`include_signals": true`** to also return the per-signal list (same data as `wave.signals` in one call).

```json
{
  "test_id": "t_abc",
  "start_time_ns": 2000,
  "end_time_ns": 3000,
  "include_signals": false
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
| Waveform slice | `tests.list` → `wave.summary` (optionally `include_signals: true`) (+ optional window) |

---

## Errors

| Code | Meaning |
|------|---------|
| `INDEX_NOT_READY` | Index missing or config not loaded |
| `INVALID_ARGUMENT` | Bad IDs, pagination, or time window (`start` > `end`, only one of start/end set) |
| `NOT_FOUND` | Unknown `test_id`, `run_id`, etc. |
| `TOPOLOGY_NOT_INDEXED` | Test exists but no UVM/topology was indexed (re-index with `adapters.uvm: true`) |
| `CONFIG_ERROR` | Feature not enabled in config (e.g. `submit.enabled: false`) |
| `INVALID_INPUT` | Input fails validation (name pattern, enum value, etc.) |

---

## v2.0.0 Tools

### runs.submit

Generate a ready-to-run simulator submit command from config templates. Requires `submit.enabled: true` in config.

| Parameter | Type | Description |
|-----------|------|-------------|
| `suite` | string | Suite name (alphanumeric, `_`, `-`, `.` only) |
| `simulator` | string | `vcs`, `questa`, `xcelium`, or `riviera` |
| `extra_args` | string? | Additional simulator flags (shell-quoted automatically) |

```json
{ "suite": "nightly_axi4", "simulator": "vcs", "extra_args": "+seed=42" }
```

Config template (in `config.yaml`):

```yaml
submit:
  enabled: true
  simulators:
    vcs:
      compile: "vcs -sv -f {suite}.f -o simv"
      simulate: "simv +plusarg={extra_args}"
    questa:
      compile: "vlog -sv -f {suite}.f"
      simulate: "vsim -batch -do 'run -all' tb_top {extra_args}"
```

---

### sim.status

Read real-time simulation progress from `live_status.json` in an artifact root. Requires `adapters.live_sim: true`.

```json
{}
```

Response includes `phase` (`compiling` | `running` | `done` | `failed`), `percent_done`, `tests_done`, `tests_total`, `stale` (true if file not updated within `live_sim_max_age_seconds`).

Write `live_status.json` from your simulator wrapper using `examples/live_sim_writer.py`:

```bash
python examples/live_sim_writer.py --artifact-root /path/to/run --total 500 -- vcs -R simv
```

---

### assertions.sva_status

Paginated list of SVA/formal property pass/fail status rows. Populated after indexing runs that include `sva_run_status` JSON evidence.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Scope to a specific run |
| `status_filter` | string? | `pass`, `fail`, `vacuous`, `disabled` |
| `page`, `page_size` | int | Pagination |

```json
{ "run_id": "r_xyz", "status_filter": "fail", "page": 1, "page_size": 50 }
```

---

### assertions.vacuity

List assertions that passed vacuously (triggered zero times). Includes a `recommendation` string explaining why this is a concern and how to fix it.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Scope to a run |
| `page`, `page_size` | int | Pagination |

```json
{ "run_id": "r_xyz" }
```

---

### tests.replay

Generate a dry-run seed-replay command for a failing test. The seed is looked up
from the indexed test record. Review the command before execution outside Sentinel
DV. Requires `submit.enabled: true`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `test_id` | string | Test identifier (from `tests.list`) |
| `simulator` | string? | Override simulator (default: inferred from run metadata) |

```json
{ "test_id": "t_abc" }
```

---

### coverage.gaps

Prioritized list of under-covered bins with actionable recommendations. The heuristic engine classifies gaps as `high`, `medium`, or `low` priority based on coverage percentage and bin name patterns.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Scope to a specific run |
| `suite` | string? | Scope to a specific suite |
| `kind` | string? | `functional`, `code`, `assertion`, `toggle`, `fsm`, or `unknown` |
| `priority` | string? | Filter: `high`, `medium`, `low` |
| `threshold_pct` | float | Return metrics below this percentage |
| `page`, `page_size` | int | Pagination |

```json
{ "run_id": "r_xyz", "kind": "functional", "priority": "high" }
```

---

## Suggested tool chains (v2.0.0)

| Goal | Tools |
|------|--------|
| Why did a test fail? | `runs.summary` → `tests.get` → `failures.list` → `tests.topology` |
| Flaky / regressing test? | `tests.history` → `tests.cluster` |
| Assertion debug | `assertions.list` → `assertions.failures` → `assertions.get` |
| SVA formal coverage | `assertions.sva_status` → `assertions.vacuity` |
| Nightly health | `regressions.summary` → `runs.list` → `failures.list` |
| Run comparison | `runs.diff` → `coverage.summary` |
| Coverage closure | `coverage.summary` → `coverage.gaps` → `runs.submit` |
| Waveform slice | `tests.list` → `wave.summary` (optionally `include_signals: true`) |
| Replay failing test | `tests.list` → `tests.replay` |
| Monitor live sim | `sim.status` (requires `live_sim_writer.py` harness) |

## DV Intelligence tool chains (v2.1.0)

| Goal | Tools |
|------|--------|
| Sign-off evidence review | `regression.health` → `coverage.trend` → `runs.cross_sim` |
| Coverage acceleration | `coverage.gaps` → `coverage.advisor` → `runs.submit` |
| Failure triage at scale | `tests.cluster` → `failures.list` (per cluster) |
| Cross-simulator confidence | `runs.cross_sim` → `assertions.failures` (for divergent tests) |
| Coverage trending | `coverage.trend` → `coverage.summary` (for stalled runs) |

---

## v2.1.0 DV Intelligence Tools

### coverage.trend

Computes average coverage over sequential indexed runs, grouped by coverage kind.

| Parameter | Type | Description |
|-----------|------|-------------|
| `suite` | string? | Suite name (defaults to all) |
| `kind` | string? | Coverage kind filter |
| `limit` | int | Maximum runs to include (1-100, default 20) |

```json
{ "suite": "axi_burst", "kind": "functional", "limit": 14 }
```

Response includes `trend` rows with `run_id`, `created_at`, `covered_pct`, and
`delta_pct`, plus a summary direction. It does not accept an arbitrary date window.

---

### runs.cross_sim

Detects latest pass/fail results that diverge across simulators. Comparisons stay
within the same suite, framework, DUT top, and test name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `suite_prefix` | string? | Filter by suite-name prefix |
| `limit` | int | Maximum divergent rows |

```json
{ "suite_prefix": "axi_burst", "limit": 100 }
```

Response includes suite and cohort identity, simulator versions, statuses, run IDs,
and run timestamps. It does not assign a severity or establish a cause.

---

### tests.cluster

Heuristically groups failures by indexed signature or normalized message.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Scope to one run |
| `max_clusters` | int | Maximum clusters returned (1-50) |

```json
{ "run_id": "r_axi_burst", "max_clusters": 20 }
```

Each cluster includes failure and distinct-test counts, severity and category counts,
representative evidence, bounded IDs, and truncation flags. A cluster is a triage
candidate, not a proven root cause.

---

### regression.health

Returns a scoped composite 0-100 health indicator broken down into pass rate,
coverage, assertion health, historical status variation, and cross-simulator consistency.

| Parameter | Type | Description |
|-----------|------|-------------|
| `suite` | string? | Scope to a suite |
| `run_id` | string? | Scope test, coverage, and assertion data to one run |

```json
{ "run_id": "r_axi_burst" }
```

Response includes `health_score`, `band`, `component_scores`, effective weights,
heuristic definitions, and `data_quality`. Coverage, assertion, flakiness, and
cross-simulator components without sufficient indexed evidence are `null`, excluded
from the weighted score, and disclosed. The score is not independent sign-off proof.

---

### coverage.advisor

Generates reviewable SystemVerilog constraint and UVM sequence candidates for
uncovered bins. Protocol-aware rules cover AXI4, AHB, APB, and CHI patterns.

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | string? | Scope to one run |
| `suite` | string? | Scope to a suite |
| `kind` | string? | Coverage kind filter |
| `metric_name` | string? | Exact metric to target |
| `protocol` | string? | `axi4`, `ahb`, `apb`, `chi`, or `generic` |
| `max_recommendations` | int | Max snippets (1–25, default 10) |

```json
{
  "run_id": "r_axi_burst",
  "kind": "functional",
  "metric_name": "cp_awburst.wrap",
  "protocol": "axi4",
  "max_recommendations": 5
}
```

Each advisory includes `run_id`, `suite`, `bin_name`, `scope`, `covered_pct`,
`priority`, `protocol_hint`, `constraint_sv`, and `sequence_hint`. Generated code
requires source and testbench review.
