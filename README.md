# 🛡️ Sentinel DV v1.0.0 - Verification Intelligence for AI Agents

<div align="center">

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.0.0-purple.svg)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![CI](https://github.com/kiranreddi/sentinel-dv/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kiranreddi/sentinel-dv/actions/workflows/ci.yml)
[![Documentation](https://github.com/kiranreddi/sentinel-dv/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/kiranreddi/sentinel-dv/actions/workflows/docs.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Coverage](https://img.shields.io/badge/coverage-70%25+-brightgreen.svg)](tests/)

**A security-first MCP server for verification intelligence (SystemVerilog/UVM/cocotb)**

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [Documentation](#-documentation)

</div>

---

## 🌟 What is Sentinel DV?

Sentinel DV is an **open-source Model Context Protocol (MCP) server** that provides large language models and AI agents with **safe, structured, read-only access** to verification artifacts—enabling deterministic triage, root-cause analysis, and verification insight without exposing raw logs or granting control of simulators.

### Verification Ecosystems Supported

- 🔧 **UVM (Universal Verification Methodology)** - Enterprise verification framework
- 🐍 **cocotb** - Python-based verification with coroutines  
- 📊 **SystemVerilog** - Assertions, coverage, and native testbenches
- 🌊 **Waveform summaries** - Pre-computed signal analysis (no raw FSDB/VCD streaming)

All through a **unified, schema-driven interface** with built-in security, redaction, and deterministic outputs.

---

## 🏗️ Architecture

Sentinel DV follows a **strict separation of concerns** with security-first principles:

```
sentinel_dv/
├── server.py              # MCP server entrypoint
├── config.py              # Security limits, feature flags, governance
├── registry.py            # Tool registration and versioning
├── schemas/               # Typed contracts for all data
│   ├── common.py         # EvidenceRef, RunRef, base types
│   ├── tests.py          # TestCase, TestTopology, UvmTopology
│   ├── failures.py       # FailureEvent, FailureSignature
│   ├── assertions.py     # AssertionInfo, AssertionFailure
│   ├── coverage.py       # CoverageSummary, CoverageMetric
│   ├── regressions.py    # RegressionSummary, RunDiff
│   └── versioning.py     # Schema version management
├── tools/                 # MCP tools (discovery + detail)
│   ├── runs.py           # runs.list, runs.diff
│   ├── tests.py          # tests.list, tests.get, tests.topology
│   ├── failures.py       # failures.list
│   ├── assertions.py     # assertions.list/get/failures
│   ├── coverage.py       # coverage.list/summary
│   ├── regressions.py    # regressions.summary
│   └── wave.py           # wave.summary, wave.signals
├── indexing/              # Artifact indexing and querying
│   ├── indexer.py        # Build normalized index from artifacts
│   ├── store.py          # DuckDB storage interface
│   └── query.py          # Filter/sort/pagination
├── adapters/              # Parse verification artifacts
│   ├── uvm_log.py        # UVM log parsing
│   ├── cocotb.py         # cocotb result parsing
│   ├── assertions.py     # Assertion map/failure parsing
│   ├── coverage.py       # Coverage export parsing
│   └── waveform_summary.py  # Waveform summary parsing
├── normalization/         # Security and determinism
│   ├── signatures.py     # Stable failure signature hashing
│   ├── taxonomy.py       # Failure categorization
│   └── redaction.py      # Automatic secret/PII redaction
└── utils/                 # Common utilities
    ├── hashing.py
    ├── time.py
    └── bounded_text.py
```

**Design Principles:**
- **Read-only by default** - No simulator control, no artifact modification
- **Schema-first** - Every response conforms to typed contracts
- **Deterministic** - Same input → same output (no LLM-generated fields)
- **Evidence-based** - All facts traceable to source artifacts
- **Bounded and safe** - Automatic redaction, size limits, path sandboxing

---

## ✨ Features

### 🔒 Security First
- **Read-only by design** - No simulation triggers or artifact writes
- **Automatic redaction** - Credentials, tokens, emails, IP addresses, paths
- **Path sandboxing** - Only configured artifact roots accessible
- **Bounded outputs** - Max response sizes, max evidence excerpts
- **Provenance tracking** - Every fact includes optional source references

### 📊 Rich Verification Data
- **Test results** - Status, duration, seed, simulator info, DUT config
- **UVM topology** - Env/agent/driver/monitor/scoreboard hierarchy
- **Failure analysis** - Categorized events (assertion/scoreboard/protocol/timeout)
- **Assertion intelligence** - SVA definitions, runtime failures, intent mapping
- **Coverage metrics** - Functional/code/assertion/toggle/FSM coverage
- **Regression analytics** - Pass rates, failure signatures, run diffs
- **Interface bindings** - Protocol mapping (AXI/AHB/APB/PCIe/USB)

### ⚡ Performance & Scale
- **Efficient indexing** - DuckDB for fast filtering and aggregation
- **Smart pagination** - Bounded result sets with stable sorting
- **Normalized storage** - Deduplicated, hashed artifacts
- **Selective projection** - Request only needed fields

### 🔌 Simulator Agnostic
- Works with **any simulator** (Synopsys VCS, Cadence Xcelium, Mentor Questa, Verilator)
- **Adapter pattern** - Ingest tool-specific formats, output unified schemas
- **Pre-computed summaries** - No runtime dependency on EDA tools

### 📋 Schema-Driven Contracts
- **Versioned schemas** - SemVer with compatibility guarantees
- **JSON Schema validation** - Deterministic, testable
- **Stable tool APIs** - Backwards-compatible evolution
- **Self-documenting** - Schemas define the interface

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/sentinel-dv.git
cd sentinel-dv

# Install with development dependencies
pip install -e ".[dev]"

# Or production install
pip install sentinel-dv
```

### Configuration

Create a `config.yaml`:

```yaml
# Artifact roots (read-only)
artifact_roots:
  - /path/to/verification/regressions
  - /path/to/uvm/logs

# Index storage
index:
  type: duckdb  # or sqlite, json
  path: ./sentinel_dv.db

# Adapters (enable/disable)
adapters:
  uvm: true
  cocotb: true
  assertions: true
  coverage: true
  waveform_summary: false

# Security & limits
security:
  max_response_bytes: 2097152  # 2MB
  max_page_size: 200
  max_evidence_refs: 10
  max_excerpt_length: 1024

# Redaction
redaction:
  enabled: true
  patterns:
    - AKIA.*           # AWS keys
    - ghp_.*           # GitHub tokens
    - Bearer\s+\S+     # Bearer tokens
  redact_emails: true
  redact_paths: true
```

### Running the Server

```bash
# Start the MCP server
python -m sentinel_dv.server --config config.yaml

# Index artifacts (one-time or scheduled)
python -m sentinel_dv.indexing.indexer --config config.yaml --index-all

# Run with Claude Desktop
# Add to Claude config:
{
  "mcpServers": {
    "sentinel-dv": {
      "command": "python",
      "args": ["-m", "sentinel_dv.server", "--config", "/path/to/config.yaml"]
    }
  }
}
```

### Example Queries

With Claude or any MCP client:

```
"Why did test axi_burst_test fail in the latest regression?"
→ Uses: tests.list, failures.list, tests.topology

"What assertions failed in the AXI agent?"
→ Uses: assertions.failures, assertions.get

"Compare coverage between runs R123 and R124"
→ Uses: runs.diff, coverage.summary

"Show me the failure signatures from the past week"
→ Uses: regressions.summary
```

---

## 📖 Documentation

### Core Concepts
- [Architecture Overview](docs/architecture.md) - Design principles and structure
- [Schema Reference](docs/schemas.md) - Complete type definitions
- [Tool Contracts](docs/tools.md) - Request/response specifications
- [Security Model](docs/security.md) - Redaction, bounding, sandboxing

### Guides
- [Getting Started](docs/getting-started/quick-start.md) - Setup and first queries
- [Adapter Development](docs/adapters.md) - Parse new artifact formats
- [Simulator Support](docs/simulator_support.md) - Vendor-specific notes
- [Deployment Guide](docs/deployment.md) - Production best practices

### Reference
- [API Documentation](https://yourusername.github.io/sentinel-dv/api/)
- [Configuration Reference](docs/configuration.md)
- [Examples](examples/) - Demo artifacts and clients

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of Conduct
- Development setup
- Testing guidelines
- Pull request process

### Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=sentinel_dv --cov-report=html

# Lint and format
ruff check .
black .
mypy sentinel_dv/
```

---

## 📊 Project Status

- ✅ **Core schemas** - Stable v1.0
- ✅ **MCP tools** - 14 tools across 6 categories
- ✅ **Adapters** - UVM, cocotb, assertions, coverage
- ✅ **Indexing** - DuckDB with efficient querying
- ✅ **Security** - Redaction, sandboxing, bounding
- ✅ **Test coverage** - 70%+ with unit and integration tests
- ✅ **Documentation** - Full guides and API reference
- 🚧 **Waveform summaries** - Experimental
- 🚧 **Plugin ecosystem** - Coming soon

---

## 🎯 Positioning

### What Sentinel DV **is**
- A **read-only MCP server** for verification ecosystems
- A **schema-first context provider** for agents and LLMs
- A **deterministic translation layer** from noisy artifacts to typed data
- A **composable infrastructure component** for debug workflows

### What Sentinel DV **is not**
- ❌ It does **not** start simulations or submit jobs
- ❌ It does **not** modify RTL/testbench code
- ❌ It does **not** require any specific simulator
- ❌ It is **not** an "AI that guesses"; it returns grounded, typed facts

---

## 🙏 Acknowledgments

Inspired by:
- [Sentinel CI](https://github.com/kiranreddi/sentinel-ci) - Universal CI/CD intelligence
- [Model Context Protocol](https://modelcontextprotocol.io) - Anthropic's agent-context standard
- The verification community using UVM, cocotb, and SystemVerilog

---

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- 🌐 [Documentation](https://yourusername.github.io/sentinel-dv/)
- 💬 [Discussions](https://github.com/yourusername/sentinel-dv/discussions)
- 🐛 [Issue Tracker](https://github.com/yourusername/sentinel-dv/issues)
- 📣 [Changelog](CHANGELOG.md)

---

<div align="center">

**Built with ❤️ for the verification community**

[⬆ back to top](#️-sentinel-dv-v100---verification-intelligence-for-ai-agents)

</div>
