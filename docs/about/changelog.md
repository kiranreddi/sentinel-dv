# Changelog

All notable changes to Sentinel DV are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-06-01

### Added

- **F1 — Regression job submission** (`runs.submit`): generate simulator-specific submit commands (VCS, Questa, Xcelium, Riviera) from config templates. Input is shell-quoted; suite names validated with strict allowlist regex.
- **F2 — Live simulator hook** (`sim.status`): read real-time `live_status.json` from artifact roots via `LiveSimAdapter`. Detects staleness, computes `percent_done`. Reference harness: `examples/live_sim_writer.py`.
- **F3 — SVA/Formal property status** (`assertions.sva_status`, `assertions.vacuity`): paginated query of the new `sva_run_status` DuckDB table; `vacuity` tool flags vacuously-passing assertions with remediation recommendations.
- **F4 — Seed replay** (`tests.replay`): look up failing test seed from the index and emit a ready-to-paste replay command.
- **F5 — Coverage closure guidance** (`coverage.gaps`): heuristic engine classifies under-covered bins as high/medium/low priority and emits actionable recommendations.
- **Bug Fix 1** — DuckDB ID sequences now seeded from existing max IDs at server start; no duplicate-key errors on re-open.
- **Bug Fix 2** — `resolve_config_with_demo_fallback()` emits `UserWarning` before falling back to demo data (silent fallback removed from `resolve_config`).
- New schemas: `submission.py` (`SubmitRequest`, `SubmitResponse`, `ReplayResponse`), `live_sim.py` (`LiveSimProgress`), extended `assertions.py` (`SVAStatus`, `SVARunStatus`, `VacuousAssertion`), extended `coverage.py` (`GapPriority`, `CoverageGap`, `CoverageGapsResponse`).
- Config additions: `SecurityLimits.max_command_length`, `SecurityLimits.max_coverage_gaps`, `AdaptersConfig.live_sim`, `AdaptersConfig.live_sim_max_age_seconds`, `SimulatorTemplate`, `SubmitConfig`.
- Example: `examples/live_sim_writer.py` — reference harness to write `live_status.json` while a simulator runs.
- Gallery assets regenerated for all 21 tools.

### Changed

- Tool count: **15 → 21** (6 new tools across 3 new MCP namespaces: `runs.submit`, `sim.status`, `assertions.sva_status`, `assertions.vacuity`, `tests.replay`, `coverage.gaps`).
- `validate.list_response()` accepts optional `extra: dict | None` kwarg for tool-specific top-level fields.
- Install **`sentinel-dv>=2.0.0`** for all v2 features.

## [Unreleased]

### Added

- (Nothing yet.)

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

- Assertion and coverage ingestion from exported JSON/text/XML summaries and simulator logs.
- Deterministic assertion-failure correlation with synthetic unknown-assertion placeholders.
- Protocol tagging for assertion intelligence (`AXI`, `AHB`, `APB`, `PCIe`, `USB`, `GPIO`, `JTAG`).
- Verilator counter demo assertion fixtures for real `assertions.*` outputs.

### Changed

- `assertions.list` adds `protocol` and `tag` filters.
- `assertions.failures` adds bounded time-window filtering (`start_time_ns`, `end_time_ns`).
- `coverage.summary` adds `include_evidence` and bounded/truncated summary behavior.
- `regressions.summary` adds deterministic `as_of` replay support.
- Release metadata updated to `1.2.0`.

## [1.1.0] - 2026-05-27

### Added

- Built-in **VCD indexing** (`VcdSummaryParser`) and **precomputed `*.wave.json`** summaries.
- **`wave.signals` / `wave.summary`** with optional **`start_time_ns` / `end_time_ns`** time windows (nanoseconds).
- Shipped examples: **`demo/`** (UVM, cocotb, JSON waveforms), **`demo/verilator_counter/`** (Verilator → VCD).
- Guides: [Waveform summaries](../guides/waveforms.md), [Examples overview](../examples/overview.md), [Verilator](../examples/verilator-counter.md), [cocotb waveforms](../examples/cocotb-waveforms.md).

### Changed

- Install **`sentinel-dv>=1.1.0`** for waveform and VCD support.

## [1.0.1] - 2026-05-26

### Fixed

- Fixed PyPI packaging to include all Python subpackages (`indexing`, `tools`, `schemas`, `adapters`).
- Added CI wheel smoke-check to catch packaging regressions before release.

### Changed

- Installation guidance requires `sentinel-dv>=1.0.1` (do not use 1.0.0).
- Current MCP surface documented as 15 tools.

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

[1.3.2]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.3.2
[1.3.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.3.1
[1.3.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.3.0
[1.2.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.2.0
[1.1.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.1.0
[1.0.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.1
[1.0.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.0
