# Changelog

All notable changes to Sentinel DV will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `Redactor.from_config()`; indexer and server apply YAML redaction settings.
- `signature_id` populated at index time for failure clustering.
- `bound_response` / `detail_response` enforce `max_response_bytes`; `LIMIT_EXCEEDED` for oversized payloads and large VCD files.
- Indexer warnings when `adapters.assertions` or `adapters.coverage` are enabled but not implemented.
- Security tests (`tests/security/`) and expanded Verilator e2e integration test.

### Changed

- Artifact scan skips symlinks; `max_artifact_bytes` and `max_wave_signals` security limits.
- `config.example.yaml` defaults assertions/coverage to `false` with accurate comments.

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
