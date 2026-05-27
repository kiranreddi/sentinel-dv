# Changelog

All notable changes to Sentinel DV are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Built-in **VCD indexing** via `VcdSummaryParser` (`*.vcd` under `waveform_summary`).
- **`wave.signals`** / **`wave.summary`** backed by DuckDB (no longer placeholder responses).
- Shipped **Verilator counter** example: `demo/verilator_counter/`.

## [1.0.1] - 2026-05-26

### Fixed

- Fixed PyPI packaging to include all Python subpackages (`indexing`, `tools`, `schemas`, `adapters`).
- Added CI wheel smoke-check to catch packaging regressions before release.

### Changed

- Installation guidance now requires `sentinel-dv>=1.0.1` (do not use 1.0.0).
- Current MCP surface documented as 15 tools.

## [1.0.0] - 2026-01-25

### Added

#### Core Features
- ✅ Complete schema system with versioning (v1.0.0)
- ✅ 14 MCP tools across 6 categories
- ✅ 5 adapters for verification artifact parsing
- ✅ DuckDB-based indexing with efficient querying
- ✅ Comprehensive normalization and redaction
- ✅ Security-first design with bounded outputs

#### Schemas
- Common types: `EvidenceRef`, `RunRef`, `TimeSpan`, `PaginationInfo`
- Test models: `TestCase`, `TestTopology`, `UvmTopology`, `InterfaceBinding`  
- Failure models: `FailureEvent`, `FailureSignature`
- Assertion models: `AssertionInfo`, `AssertionFailure`
- Coverage models: `CoverageSummary`, `CoverageMetric`
- Regression models: `RegressionSummary`, `RunDiff`, `DiffItem`

#### Tools
- **Discovery**: `runs.list`, `tests.list`, `assertions.list`, `coverage.list`
- **Detail**: `tests.get`, `tests.topology`, `assertions.get`
- **Analysis**: `failures.list`, `assertions.failures`, `coverage.summary`
- **Regression**: `regressions.summary`, `runs.diff`
- **Waveform**: `wave.summary`, `wave.signals` (precomputed JSON; VCD added in unreleased)

#### Adapters
- UVM log parser (UVM_INFO/WARNING/ERROR/FATAL)
- cocotb results parser (JUnit XML)
- Assertion map and failure parser
- Coverage export parser
- Waveform summary parser (experimental)

#### Infrastructure
- YAML-based configuration with validation
- Automatic redaction (12+ patterns)
- Path sandboxing
- Response size limits
- Evidence bounding

#### Testing
- 70%+ code coverage
- Unit tests for all components
- Integration test framework
- Fixtures for common scenarios

#### Documentation
- Professional MkDocs Material site
- Comprehensive guides and API reference
- Getting started tutorials
- Architecture documentation
- Security guidelines

#### CI/CD
- GitHub Actions workflows
- Automated testing across Python 3.10-3.12
- Coverage reporting
- Security scanning
- Documentation deployment

### Known Limitations
- Waveform summaries require external preprocessing
- Coverage parsing supports limited vendor formats
- Assertion intent extraction is heuristic-based

[1.0.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.1
[1.0.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.0
