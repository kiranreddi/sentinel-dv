# Changelog

All notable changes to Sentinel DV will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- (Nothing yet.)

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
