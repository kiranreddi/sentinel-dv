# Changelog

All notable changes to Sentinel DV are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [2.3.1] - 2026-07-31

### Added

- Three evidence-driven agent skills for Codex, Claude Code, and GitHub Copilot.
- Real workflow verifier covering regression triage, failure debugging, and coverage closure.
- Agent setup guide, redesigned documentation, complete 28-tool gallery, and an embedded 45-second walkthrough.

### Changed

- Product positioning consistently uses **design verification**.
- Signature clusters and generated SystemVerilog are explicitly described as heuristic investigation groups and reviewable candidates.
- Health reports disclose unavailable components and effective reweighting.

### Fixed

- Exact run scoping for coverage, health, diffs, and cross-simulator comparisons.
- Missing cohort data no longer receives a perfect health score.
- Coverage advisor brace generation, stable-trend notes, assertion windows, pagination, and output-schema accuracy.

---

## [2.3.0] - 2026-06-05

### Added

- **`runs.summary`** — per-run test status rollup (counts, pass rate, slowest tests, failure totals).
- **`tests.history`** — cross-run timeline for a logical test name with flaky detection.
- **Jenkins artifact indexing** — suite and CI metadata from common Jenkins paths; canonical JUnit XML per directory.
- **Cocotb JUnit evidence** — `test_artifacts` properties linked as per-test evidence.

### Changed

- Tool count **26 → 28**; gallery, MCP registry manifest (logo/tags), and verify script aligned.
- Install **`sentinel-dv>=2.3.0`** for the new tools and Jenkins-aware indexing.

## [2.2.0] - 2026-05-29

Minor release: reliability and coverage-ingestion improvements since v2.1.0, plus deployment and demo documentation.

### Added

- **Coverage HTML parsing** — VCS URG (`dashboard.html`), Questa vcover (`overalldu.js`), and Xcelium IMC HTML reports; parsers use content-sniffing so unrelated `dashboard.html` / `overalldu.js` files are not matched.
- **Production deployment** — stdio MCP + systemd guide; documents that Sentinel DV is not deployed to Vercel or similar HTTP hosts.
- **Verilator demo** — `config.example.yaml` with `live_sim` and `submit` for full 26-tool walkthrough.
### Changed

- Install **`sentinel-dv>=2.2.0`** for parser fixes and HTML coverage ingestion shipped after v2.1.0.
- `.gitignore` for local `demo/verilator_counter/live_status.json` harness output.
- `scripts/verify_all_mcp_tools.py` aligned to **26 tools** with sensible handling of feature-gated tools.

### Fixed

- **UVM log parser** — count-summary and demoted/caught lines no longer indexed as failures; `aborted` status when simulation ends without a completion marker; `TEST_FAILED_PATTERN` no longer matches `UVM_FATAL : 0` on passing tests.
- **MCP output schema** — optional `item` on error envelopes for FastMCP validation.
- **Coverage text parser** — scope/kind regex delimiter fix.
- **`runs.submit` / `tests.replay`** — `schema_version` on all success responses.

### Removed

- Vercel `api/index.py` entrypoint (stdio MCP only).

---

## [2.1.0] - 2026-06-02

### Added

- **DV Intelligence Tool 1 — Coverage Trend** (`coverage.trend`): time-series coverage trajectory across runs. Computes per-run coverage percentages with deltas and characterizes trend direction as `improving`, `stalling`, or `declining`.
- **DV Intelligence Tool 2 — Cross-Simulator Divergence** (`runs.cross_sim`): detects comparable tests that pass on one simulator vendor but fail on another and surfaces those cohorts for engineer review.
- **DV Intelligence Tool 3 — Failure Clustering** (`tests.cluster`): groups failures by normalized message and category similarity, reducing repeated symptoms to bounded investigation candidates.
- **DV Intelligence Tool 4 — Regression Health Score** (`regression.health`): composite 0–100 DV readiness score with weighted sub-scores for pass rate (30%), coverage (35%), assertion health (15%), flakiness (10%), and cross-simulator consistency (10%). Outputs `band`: `sign-off-ready` | `minor-issues` | `coverage-gaps` | `not-ready`.
- **DV Intelligence Tool 5 — Coverage Advisor** (`coverage.advisor`): generates reviewable SystemVerilog constraint candidates and UVM sequence hints for uncovered bins. Protocol-aware for AXI4, AHB, APB, and CHI naming patterns.
- `sentinel_dv/normalization/coverage_advisor.py`: new module — `_PROTOCOL_RULES` knowledge base + `build_advisories()` entry point.
- New store methods: `coverage_trend()`, `cross_sim_divergence()`, `cluster_failures()`, `regression_health_data()`.
- Gallery assets regenerated for all 26 tools (5 new SVG cards).
- 25 new unit tests in `tests/unit/test_beyond_spec.py`.

### Changed

- Tool count: **21 → 26** (5 new DV Intelligence tools).
- `sentinel_dv/registry.py`: 5 new tool names added to `TOOL_NAMES`.
- `sentinel_dv/demo_fixtures.py`: `tool_call_matrix()` and `invoke_core_tool()` updated with the 5 new tools.
- `docs/tools/overview.md`: updated tool count, added v2.1.0 section and decision guide entries.
- `docs/tools/mcp-tools-reference.md`: updated tool count, added v2.1.0 tool chain table and full reference for all 5 new tools.
- Install **`sentinel-dv>=2.1.0`** for DV Intelligence tools.

## [2.0.0] - 2026-06-01

### Added

- **F1 — Regression job submission** (`runs.submit`): generate simulator-specific submit commands (VCS, Questa, Xcelium, Riviera) from config templates. Input is shell-quoted; suite names validated with strict allowlist regex.
- **F2 — Live simulator hook** (`sim.status`): read real-time `live_status.json` from artifact roots via `LiveSimAdapter`. Detects staleness, computes `percent_done`. Reference harness: `examples/live_sim_writer.py`.
- **F3 — SVA/Formal property status** (`assertions.sva_status`, `assertions.vacuity`): paginated query of the new `sva_run_status` DuckDB table; `vacuity` tool flags vacuously-passing assertions with remediation recommendations.
- **F4 — Seed replay** (`tests.replay`): look up a failing test seed from the index and emit a dry-run replay command for engineer review.
- **F5 — Coverage closure guidance** (`coverage.gaps`): heuristic engine classifies under-covered bins as high/medium/low priority and emits actionable recommendations.
- **Bug Fix 1** — DuckDB ID sequences now seeded from existing max IDs at server start; no duplicate-key errors on re-open.
- **Bug Fix 2** — `resolve_config_with_demo_fallback()` emits `UserWarning` before falling back to demo data (silent fallback removed from `resolve_config`).
- New schemas: `submission.py` (`SubmitRequest`, `SubmitResponse`, `ReplayResponse`), `live_sim.py` (`LiveSimProgress`), extended `assertions.py` (`SVAStatus`, `SVARunStatus`, `VacuousAssertion`), extended `coverage.py` (`GapPriority`, `CoverageGap`, `CoverageGapsResponse`).
- Config additions: `SecurityLimits.max_command_length`, `SecurityLimits.max_coverage_gaps`, `AdaptersConfig.live_sim`, `AdaptersConfig.live_sim_max_age_seconds`, `SimulatorTemplate`, `SubmitConfig`.
- Example: `examples/live_sim_writer.py` — reference harness to write `live_status.json` while a simulator runs.

### Changed

- Tool count: **15 → 21** (6 new tools).
- Install **`sentinel-dv>=2.0.0`** for v2 submission, live-sim, SVA, replay, and coverage gaps.

## [1.3.2] - 2026-05-29

### Added

- Pre-release scripts and release workflow gates (`pre_release.sh`, `check_versions.py`).
- Additional unit tests for server handlers, CLI, and coverage.

### Changed

- Install **`sentinel-dv>=1.3.2`** for pre-release tooling and doc fixes since 1.3.1.

## [1.3.1] - 2026-05-29

### Added

- MCP tool `outputSchema`, read-only annotations, and expanded descriptions for LLM discoverability.
- `wave.summary` `include_signals`, `highlight_groups`, and `TOPOLOGY_NOT_INDEXED` error code.

### Changed

- Config file is required (no silent `demo/` fallback); regression windows use epoch milliseconds.
- Install **`sentinel-dv>=1.3.1`** for these fixes.

## [1.3.0] - 2026-05-29

### Added

- VCS, Questa, and Cadence Xcelium checked-in fixtures plus multi-project UVM/cocotb demos.
- Shared `demo_fixtures` harness, `verify_all_mcp_tools.py --sim`, and MCP tool gallery assets.
- Integration tests for the full demo corpus and commercial simulator matrix.

### Changed

- Relative config paths resolve from the config file directory; indexer and evidence handling hardened.
- Install **`sentinel-dv>=1.3.0`** for commercial simulator examples and multi-project validation.

## [1.2.0] - 2026-05-27

### Added

- Waveform summary adapter (VCD + JSON), `wave.summary` tool, and waveform documentation.
- Expanded demo fixtures and indexing for cocotb/JUnit artifacts.

## [1.1.0] - 2026-05-26

### Added

- Assertion adapter improvements and additional MCP tool metadata.

## [1.0.1] - 2026-05-25

### Fixed

- Packaging and import path fixes for PyPI wheel.

## [1.0.0] - 2026-01-25

### Added

#### Core Features

- Complete schema system with versioning (v1.0.0)
- 14 MCP tools across 6 categories (15 with wave tools)
- 5 adapters for verification artifact parsing
- DuckDB-based indexing with efficient querying
- Comprehensive normalization and redaction
- Security-first design with bounded outputs

See the repository [CHANGELOG.md](https://github.com/kiranreddi/sentinel-dv/blob/main/CHANGELOG.md) for the full 1.0.0 entry.

[2.3.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v2.3.1
[2.3.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v2.3.0
[2.2.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v2.2.0
[2.1.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v2.1.0
[2.0.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v2.0.0
[1.3.2]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.3.2
[1.3.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.3.1
[1.3.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.3.0
[1.2.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.2.0
[1.1.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.1.0
[1.0.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.1
[1.0.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.0
