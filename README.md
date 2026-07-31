# Sentinel DV

<!-- mcp-name: io.github.kiranreddi/sentinel-dv -->

[![PyPI](https://img.shields.io/pypi/v/sentinel-dv.svg)](https://pypi.org/project/sentinel-dv/)
[![MCP Registry](https://img.shields.io/badge/MCP-io.github.kiranreddi%2Fsentinel--dv-007f78)](https://registry.modelcontextprotocol.io/?search=io.github.kiranreddi/sentinel-dv)
[![CI](https://github.com/kiranreddi/sentinel-dv/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kiranreddi/sentinel-dv/actions/workflows/ci.yml)
[![Documentation](https://github.com/kiranreddi/sentinel-dv/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/kiranreddi/sentinel-dv/actions/workflows/docs.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-172126.svg)](LICENSE)

Sentinel DV v2.3.1 is a read-only Model Context Protocol server for design verification evidence. It indexes exported SystemVerilog, UVM, cocotb, assertion, coverage, regression, and waveform artifacts into DuckDB and exposes 28 bounded, schema-driven tools to AI agents.

[Documentation](https://kiranreddi.github.io/sentinel-dv/) | [Quick start](docs/getting-started/quick-start.md) | [Video walkthrough](docs/getting-started/video-walkthrough.md) | [All tools](docs/tools/mcp-tools-reference.md) | [Agent skills](docs/skills/overview.md)

## What it provides

- **Run and test intelligence:** discovery, summaries, history, topology, diffs, replay-command generation, and live-status snapshots.
- **Failure analysis:** normalized categories, stable signatures, bounded evidence, assertion failures, and failure clustering.
- **Coverage closure:** functional, code, toggle, and FSM metrics; trends; gaps; vacuity; SVA status; and protocol-aware constraint candidates.
- **Waveform context:** precomputed `*.wave.json` and bounded VCD summaries. Native FSDB/WLF streaming is intentionally out of scope.
- **Agent workflows:** regression triage, single-test failure debugging, and coverage closure skills for Codex, Claude Code, and GitHub Copilot.

Sentinel DV does not execute simulations, modify RTL or testbench files, or stream unrestricted raw artifacts. `runs.submit` and `tests.replay` return dry-run commands for engineer review.

## Quick start

Python 3.10 or newer is required. This example indexes the checked-in demo corpus:

For a persistent environment, install `sentinel-dv>=2.3.1`. The commands below use `uvx` to run the same release without a persistent install.

```bash
git clone https://github.com/kiranreddi/sentinel-dv.git
cd sentinel-dv
cp demo/config.example.yaml demo/config.yaml

uvx --from sentinel-dv@2.3.1 \
  sentinel-dv-index --config "$PWD/demo/config.yaml" --index-all
```

Connect one agent:

### Codex

```bash
codex mcp add sentinel-dv \
  --env SENTINEL_DV_CONFIG="$PWD/demo/config.yaml" \
  -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
```

### Claude Code

```bash
claude mcp add \
  --env SENTINEL_DV_CONFIG="$PWD/demo/config.yaml" \
  --transport stdio --scope local sentinel-dv \
  -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
```

### GitHub Copilot CLI

```bash
copilot mcp add sentinel-dv \
  --env SENTINEL_DV_CONFIG="$PWD/demo/config.yaml" \
  -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
```

Use an absolute `SENTINEL_DV_CONFIG` path. Verify the connection in the client's MCP status view, then call `runs.list`.

See [Agent setup](docs/getting-started/agent-setup.md) for configuration-file examples, project scope, skill discovery, and troubleshooting.

## Production configuration

Copy `config.example.yaml` and define allowed artifact roots:

```yaml
artifact_roots:
  - /absolute/path/to/regression/artifacts

index:
  type: duckdb
  path: ./sentinel_dv.db

adapters:
  uvm: true
  cocotb: true
  assertions: true
  coverage: true
  waveform_summary: true

security:
  max_response_bytes: 2097152
  max_page_size: 200
  max_evidence_refs: 10

redaction:
  enabled: true
  redact_emails: true
  redact_paths: true
```

Build the index before starting the server:

```bash
sentinel-dv-index --config /absolute/path/to/config.yaml --index-all
sentinel-dv-server --config /absolute/path/to/config.yaml
```

Relative paths inside the YAML are resolved from the config file's directory. Production startup never silently falls back to demo data.

## MCP tools

The 28 tools are grouped by engineering purpose:

| Area | Tools |
| --- | --- |
| Runs | `runs.list`, `runs.get`, `runs.summary`, `runs.diff`, `runs.cross_sim`, `runs.submit` |
| Tests | `tests.list`, `tests.get`, `tests.history`, `tests.topology`, `tests.cluster`, `tests.replay` |
| Failures and assertions | `failures.list`, `assertions.list`, `assertions.get`, `assertions.failures`, `assertions.sva_status`, `assertions.vacuity` |
| Coverage | `coverage.list`, `coverage.summary`, `coverage.gaps`, `coverage.trend`, `coverage.advisor` |
| Regression and simulation | `regressions.summary`, `regression.health`, `sim.status` |
| Waveforms | `wave.signals`, `wave.summary` |

Every registered tool carries read-only MCP annotations and a versioned output schema. The [MCP tools reference](docs/tools/mcp-tools-reference.md) documents exact inputs and outputs.

## Agent skills

The canonical skills live under `skills/`:

- [`sentinel-dv-regression-triage`](skills/sentinel-dv-regression-triage/SKILL.md)
- [`sentinel-dv-failure-debugging`](skills/sentinel-dv-failure-debugging/SKILL.md)
- [`sentinel-dv-coverage-closure`](skills/sentinel-dv-coverage-closure/SKILL.md)

Deterministic mirrors support project discovery:

| Host | Path |
| --- | --- |
| Codex | `.agents/skills/` |
| Claude Code | `.claude/skills/` |
| GitHub Copilot | `.github/skills/` |

The repository also contains Codex and Claude plugin manifests. `.mcp.json` defines the bundled stdio server command; provide `SENTINEL_DV_CONFIG` or a `config.yaml` in the server working directory.

After editing a canonical skill:

```bash
.venv/bin/python scripts/sync_agent_skills.py
.venv/bin/python scripts/sync_agent_skills.py --check
```

## Supported artifact sources

- UVM logs and topology hints
- cocotb and generic JUnit XML
- assertion definition and failure JSON
- SVA run-status JSON
- supported JSON, XML, text, and HTML coverage summaries
- `*.wave.json` and VCD
- live simulation status JSON
- exported VCS, Xcelium, Questa, and Verilator results

Adapter output is normalized into versioned schemas so clients do not need vendor-specific parsing logic.

## Security model

- Tools are read-only and operate on an index plus configured artifact roots.
- Path resolution is sandboxed to allowed roots.
- Evidence counts, excerpts, pages, wave signals, bins, and total response size are bounded.
- Configurable redaction protects common secrets, email addresses, IP addresses, and local paths.
- Tool output is deterministic; the MCP server does not generate causal conclusions.

Read [Security](docs/architecture/security.md) and [Production deployment](docs/deployment/production.md) before using production artifacts.

## Verification

Create a development environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,docs]"
```

Run endpoint and workflow checks:

```bash
.venv/bin/python scripts/verify_all_mcp_tools.py
.venv/bin/python scripts/verify_skill_workflows.py
```

Run the full quality suite:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/black --check .
.venv/bin/mypy sentinel_dv
.venv/bin/mkdocs build --strict
```

The all-tools verifier invokes every registered MCP endpoint. The skill verifier indexes 52 checked-in demo artifacts and executes the published regression triage, failure debugging, and coverage closure sequences.

## Project layout

```text
sentinel_dv/
  adapters/        artifact parsers
  indexing/        DuckDB indexing and queries
  normalization/   signatures, taxonomy, redaction, coverage guidance
  schemas/         versioned response contracts
  tools/core.py    tool implementations
  server.py        FastMCP registration and stdio entry point

skills/            canonical agent skills
demo/              license-free exported verification fixtures
docs/              MkDocs documentation
scripts/           verification, gallery, release, and skill-sync tooling
tests/             unit and integration coverage
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Sentinel DV is licensed under [Apache-2.0](LICENSE).
