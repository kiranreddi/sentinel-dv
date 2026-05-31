# Changelog

All notable changes to Sentinel DV will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-01

### Added

- **F1 — Regression job submission** (`runs.submit`): generate simulator-specific submit commands (VCS, Questa, Xcelium, Riviera) from config templates. Input is shell-quoted; suite names validated with strict allowlist regex.
- **F2 — Live simulator hook** (`sim.status`): read real-time `live_status.json` from artifact roots via `LiveSimAdapter`. Detects staleness, computes `percent_done`. Reference harness: `examples/live_sim_writer.py`.
- **F3 — SVA/Formal property status** (`assertions.sva_status`, `assertions.vacuity`): paginated query of the new `sva_run_status` DuckDB table; `vacuity` tool flags vacuously-passing assertions with remediation recommendations.
- **F4 — Seed replay** (`tests.replay`): look up failing test seed from the index and emit a ready-to-paste replay command.
- **F5 — Coverage closure guidance** (`coverage.gaps`): heuristic engine classifies under-covered bins as high/medium/low priority and emits actionable recommendations.
- **Bug Fix 1** — DuckDB ID sequences now seeded from existing max IDs; no duplicate-key errors on re-open.
- **Bug Fix 2** — `resolve_config_with_demo_fallback()` emits `UserWarning` before using demo data (silent fallback removed from `resolve_config`).
- Config additions: `SecurityLimits.max_command_length`, `SecurityLimits.max_coverage_gaps`, `AdaptersConfig.live_sim`, `AdaptersConfig.live_sim_max_age_seconds`, `SimulatorTemplate`, `SubmitConfig`.
- Example: `examples/live_sim_writer.py` — reference harness to write `live_status.json` alongside a running simulator.

### Changed

- Tool count: **15 → 21** (6 new tools).
- Install **`sentinel-dv>=2.0.0`** for all v2 features.

## [Unreleased]

### Added

- (Nothing yet.)

## [2.1.0] - 2026-06-02

### Added

- **DV Intelligence tools** — `coverage.trend`, `runs.cross_sim`, `tests.cluster`, `regression.health`, `coverage.advisor` (protocol-aware SV constraint snippets for AXI4/AHB/APB/CHI).
- Coverage HTML parsers for VCS URG (`dashboard.html`) and Questa vcover (`overalldu.js`).
- **Xcelium IMC HTML coverage parser** (`cov_report.html`, `imc_summary.html`, `xcoverage_report.html`) — auto-detected and parsed; no proprietary DB access required.
- **4-simulator support** (VCS, Questa, Xcelium, Verilator) — all docs, demos, and examples updated from 3 to 4 simulators.
- Unit tests in `tests/unit/test_beyond_spec.py`; gallery assets for all 26 tools.
- Conference materials: DVCon/DAC 2026 paper, Beamer slides (19 pages), PPTX, and technical notes.

### Changed

- Tool count: **21 → 26** (5 new DV Intelligence tools).
- Documentation aligned to 26 tools across README, examples, MkDocs, and MCP reference.
- Demo: `demo/axi4_uvm/xcelium/coverage/cov_report.html` added as Xcelium coverage HTML fixture.

### Fixed

- UVM log parser: `Number of caught/demoted UVM_FATAL reports : N` count summary lines
  no longer parsed as real failure events (fixes false-positive `fail` status on passing tests).
- UVM log parser: `UVM_COUNT_SUMMARY_PATTERN` extended to cover both simple count lines
  (`UVM_ERROR :    0`) and report demote/catch lines.
- **UVM log parser: `aborted` status for incomplete simulations** — logs that end without a
  simulator completion marker (`VCS Simulation Report`, `$finish`, `UVM TEST DONE`, etc.) are
  now correctly reported as `status: "aborted"` rather than `"pass"`.  Catches OOM kills,
  license pre-emption, and run-script timeouts that terminate the process mid-simulation.
- MCP output schema validation for error responses (`item` optional in `_ITEM_ENVELOPE`).
- `runs.submit` and `tests.replay` responses include `schema_version` via `detail_response()`.

## [1.3.2] - 2026-05-29

### Added

- **Pre-release tooling** — `scripts/pre_release.sh`, `scripts/check_versions.py`, and [RELEASING.md](docs/release/RELEASING.md).
- **Release workflow preflight** — lint, tests, ≥70% coverage, and version/tag alignment before PyPI publish.
- **Unit tests** — MCP server handlers, indexing CLI, waveform helpers, and expanded store/utils coverage.

### Changed

- Documentation: explicit `cp config.example.yaml` in quick-start and troubleshooting.
- Version bumped to `1.3.2` across package metadata and docs.

## [1.3.1] - 2026-05-29

### Added

- **MCP metadata** — rich tool descriptions, `outputSchema` on all 15 tools, and `readOnlyHint` / `idempotentHint` annotations (`sentinel_dv/tools/mcp_metadata.py`).
- **`wave.summary`** — `include_signals` flag (combined metadata + per-signal list), `highlight_groups` by category, and `signal_groups` from JSON fixtures.
- **`TOPOLOGY_NOT_INDEXED`** error when a test exists but UVM topology was not indexed (distinct from `NOT_FOUND`).
- **`created_at_ms`** on runs/tests for epoch-based `regressions.summary` windows (legacy ISO strings backfilled on connect).
- **Unit tests** — `tests/unit/test_store_hardening.py` for sort safety, sequences, regression windows, and config resolution.

### Changed

- **SQL sort** — `ORDER BY` built only from fixed column maps (`_TESTS_ORDER_BY`, `_RUNS_ORDER_BY`).
- **ID allocation** — DuckDB sequences replace `MAX(id)+1` for assertion failures, evidence, and coverage rows.
- **Configuration** — `resolve_config()` no longer silently defaults to `demo/`; requires `--config`, `SENTINEL_DV_CONFIG`, or `config.yaml`/`config.yml` in cwd.
- **Documentation** — mandatory config guidance, `coverage.list` vs `coverage.summary`, waveform and topology error reference.

### Migration Notes

- **Breaking (config):** Deployments that relied on implicit `demo/` indexing must pass an explicit config path or place `config.yaml` in the server working directory.
- Re-index recommended after upgrade so `created_at_ms` is populated for all runs.

## [1.3.0] - 2026-05-29

### Added

- **Commercial simulator fixtures** — checked-in artifact trees for **VCS**, **Questa**, and **Cadence Xcelium** under `demo/vcs_counter/`, `demo/questa_counter/`, and `demo/cadence_counter/` (JUnit XML, UVM logs, assertion JSON, coverage JSON, `*.wave.json`).
- **Multi-project demo corpus** — additional UVM (`demo/uvm_logs/`) and cocotb (`demo/cocotb_results/`) sample projects for regression-style MCP validation.
- **`sentinel_dv/demo_fixtures.py`** — shared indexing helpers, MCP tool matrix, `discover_fixtures()`, and `scripts/verify_all_mcp_tools.py --sim` support.
- **`examples/simulator_matrix.py`** — run the 15-tool matrix across Verilator and commercial fixtures.
- **MCP tool gallery** — `scripts/generate_mcp_tool_gallery.py` and docs assets under `docs/assets/mcp-tools/`.
- **Integration tests** — `test_multi_project_all_mcp_tools.py`, `test_simulator_examples_all_mcp_tools.py` (parametrized VCS/Questa/Cadence).

### Changed

- **Config paths** — relative `artifact_roots` and `index.path` resolve from the config file directory.
- **Indexer** — broader cocotb JUnit/XML discovery; taxonomy enum coercion for DuckDB; evidence path traversal hardening.
- **Waveform indexing** — when both `*.wave.json` and `*.vcd` exist under a demo tree, both are indexed (documented for Verilator walkthrough).
- Version bumped to `1.3.0` in package metadata, docs, and MCP registry manifest (`server.json`).

### Migration Notes

- Re-index after upgrade: `sentinel-dv-index --config config.yaml --index-all`.
- For commercial simulators, point `artifact_roots` at exported artifacts only (Sentinel DV does not launch simulators). See [Commercial simulators](docs/examples/commercial-simulators.md).

## [1.2.0] - 2026-05-27

### Added

- **Assertion ingestion pipeline** via `AssertionReportParser` for JSON/text/exported reports and log-derived failures.
- **Coverage ingestion pipeline** via `CoverageReportParser` for JSON/text/XML summaries with deterministic normalization.
- **Protocol tagging** (`AXI`, `AHB`, `APB`, `PCIe`, `USB`, `GPIO`, `JTAG`) from assertion names/scopes/messages.
- **Assertion failure correlation** with deterministic synthetic fallbacks (`unknown_assertion_<stablehash>`) to avoid orphaned failures.
- **New adapters and extension points**:
  - `sentinel_dv/adapters/assertion_reports.py`
  - `sentinel_dv/adapters/coverage_reports.py`
  - `sentinel_dv/adapters/protocol_tags.py`
  - `sentinel_dv/indexing/query.py`
  - `sentinel_dv/registry.py`
- **Demo artifacts** for Verilator assertion and coverage outputs:
  - `demo/verilator_counter/assertions/counter.assert.json`
  - `demo/verilator_counter/assertions/counter_fail.assert.json`

### Changed

- `assertions.list` now supports protocol/tag filtering with deterministic pagination.
- `assertions.failures` now supports deterministic bounded time-window filtering (`start_time_ns`, `end_time_ns`).
- `coverage.summary` now supports bounded summaries with optional evidence (`include_evidence`) and truncation metadata.
- `regressions.summary` now supports deterministic replay windows via `as_of=<RFC3339>`.
- Indexer now ingests assertions and coverage when adapters are enabled (previous "not implemented" warnings removed).
- Version bumped to `1.2.0` in package metadata and MCP registry manifest.

### Migration Notes

- No schema-breaking wire-format changes for existing tool names.
- To consume new assertion/coverage behavior, re-run indexing:
  - `sentinel-dv-index --config config.yaml --index-all`
- For reproducible regression analytics, provide `as_of` explicitly in `regressions.summary`.

## [1.1.0] - 2026-05-27

### Added

- **Built-in VCD indexing** — `VcdSummaryParser` indexes `*.vcd` when `adapters.waveform_summary` is enabled (no EDA license; Verilator-friendly).
- **Precomputed waveform JSON** — `WaveformSummaryParser` indexes `*.wave.json` under artifact roots.
- **VCD time windows** — `wave.signals` and `wave.summary` accept `start_time_ns` and `end_time_ns` (nanoseconds, both required together). VCD sources are re-parsed for `value_at_start`, `value_at_end`, and toggles in range.
- **`$timescale` parsing** — VCD `#` timestamps converted to nanoseconds (fs, ps, ns, µs, ms, s).
- **Shipped examples**
  - `demo/` — UVM logs, cocotb JUnit XML, `demo/waveforms/*.wave.json`
  - `demo/verilator_counter/` — SystemVerilog counter, C++ TB, ~10 µs VCD trace, `config.example.yaml`
- **Documentation** — [Waveform summaries](docs/guides/waveforms.md), [Examples overview](docs/examples/overview.md), [Verilator + VCD](docs/examples/verilator-counter.md), [cocotb + JSON waveforms](docs/examples/cocotb-waveforms.md).
- **Tests** — Unit tests for VCD parsing and time windows; integration test builds Verilator, indexes VCD, queries a 2–3 µs window.

### Changed

- `wave.signals` / `wave.summary` return real indexed data (not placeholders) when waveform summaries exist.
- Install **`sentinel-dv>=1.1.0`** for waveform and VCD features.

## [1.0.1] - 2026-05-26

### Fixed

- PyPI wheel now includes all Python subpackages (`indexing`, `tools`, `schemas`, `adapters`, etc.). Version 1.0.0 was broken at install time (`ModuleNotFoundError: sentinel_dv.schemas`).
- CI builds the wheel and smoke-imports subpackages before release.

### Changed

- Install `sentinel-dv>=1.0.1`; yank PyPI 1.0.0 manually via [release management](https://pypi.org/manage/project/sentinel-dv/releases/).

## [1.0.0] - 2026-01-25

### Deprecated

- **Do not use** — broken PyPI wheel; yank on PyPI and use 1.0.1+.

### Added

- Initial release of Sentinel DV
- Core schema system with versioning (v1.0.0)
- MCP tools (14 total at launch; 15 with wave tools registered)
- Adapters, DuckDB indexing, normalization, security, documentation, CI/CD, GitHub Pages

### Known Limitations (1.0.0)

- Waveform summaries were experimental and required external preprocessing (addressed in 1.1.0 for JSON and VCD).

[1.1.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.1.0
[1.0.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.1
[1.0.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.0
