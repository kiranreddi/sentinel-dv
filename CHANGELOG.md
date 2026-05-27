# Changelog

All notable changes to Sentinel DV will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - Common types: EvidenceRef, RunRef
  - Test models: TestCase, TestTopology, UvmTopology, InterfaceBinding
  - Failure models: FailureEvent, FailureSignature
  - Assertion models: AssertionInfo, AssertionFailure
  - Coverage models: CoverageSummary, CoverageMetric
  - Regression models: RegressionSummary, RunDiff
- MCP tools (14 total)
  - Discovery: runs.list, tests.list, assertions.list, coverage.list
  - Detail: tests.get, tests.topology, assertions.get
  - Analysis: failures.list, assertions.failures, coverage.summary
  - Intelligence: regressions.summary, runs.diff
  - Optional: wave.summary, wave.signals
- Adapters for artifact ingestion
  - UVM log parser
  - cocotb results parser
  - Assertion map and failure parser
  - Coverage export parser
  - Waveform summary parser (experimental)
- Indexing system with DuckDB backend
  - Efficient filtering and aggregation
  - Smart pagination with stable sorting
  - Normalized storage with deduplication
- Normalization layer
  - Failure signature hashing
  - Taxonomy-based categorization
  - Deterministic text normalization
- Security features
  - Automatic redaction (credentials, tokens, emails, paths, IPs)
  - Path sandboxing
  - Response size limits
  - Evidence excerpt bounding
- Configuration system
  - YAML-based configuration
  - Feature flags for adapters
  - Security limits and redaction rules
- Comprehensive test suite
  - Unit tests for all components
  - Integration tests for tool workflows
  - 70%+ code coverage
- Documentation
  - Architecture guide
  - Schema reference
  - Tool contracts
  - Security model
  - Adapter development guide
  - Getting started guide
- CI/CD pipeline
  - GitHub Actions workflows
  - Automated testing and coverage
  - Linting and type checking
  - Documentation deployment
- GitHub Pages site
  - MkDocs Material theme
  - Professional design
  - Comprehensive API reference

### Known Limitations
- Waveform summaries are experimental and require external preprocessing
- Coverage parsing currently supports limited vendor formats
- Assertion intent extraction is heuristic-based

[1.0.1]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.1
[1.0.0]: https://github.com/kiranreddi/sentinel-dv/releases/tag/v1.0.0
