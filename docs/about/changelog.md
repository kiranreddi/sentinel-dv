# Changelog

All notable changes to Sentinel DV are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Documentation alignment for assertion/coverage parameter usage and deterministic replay examples.

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

[1.1.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.1.0
[1.0.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.1
[1.0.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.0
