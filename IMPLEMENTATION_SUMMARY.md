# Sentinel DV implementation summary

**Version:** 1.2.0
**Status:** Implemented MCP server with artifact indexing, schema validation, demo fixtures, and documentation.

## Implemented surfaces

| Area | Status |
|------|--------|
| MCP server | 26 read-only FastMCP tools in `sentinel_dv/server.py` |
| Indexing | DuckDB-backed store and artifact scanner in `sentinel_dv/indexing/` |
| Adapters | UVM logs, cocotb/JUnit XML, assertion reports, coverage summaries, waveform JSON, and VCD summaries |
| Security | Configured artifact roots, path containment checks, bounded responses, bounded evidence, and redaction |
| Tests | Unit, security, and integration tests for tools, indexing, waveforms, gallery assets, and simulator fixtures |
| Examples | UVM, cocotb, Verilator, VCS, Questa, and Cadence Xcelium artifact fixtures under `demo/` |
| Documentation | MkDocs site with architecture, configuration, tools, examples, simulator support, troubleshooting, and release notes |

## Tool coverage

Sentinel DV currently registers:

1. `runs.list`
2. `runs.get`
3. `tests.list`
4. `tests.get`
5. `tests.topology`
6. `assertions.list`
7. `assertions.get`
8. `assertions.failures`
9. `coverage.list`
10. `coverage.summary`
11. `failures.list`
12. `regressions.summary`
13. `runs.diff`
14. `wave.signals`
15. `wave.summary`

Use `python scripts/verify_all_mcp_tools.py` to index the checked-in demo corpus and call every tool through FastMCP.

## Simulator examples

The repository includes artifact-based examples for:

- `demo/verilator_counter/`
- `demo/vcs_counter/`
- `demo/questa_counter/`
- `demo/cadence_counter/`

These fixtures contain exported logs, JUnit XML, coverage JSON, assertion JSON, and waveform summaries. The MCP server remains read-only and does not launch simulators.

## Current validation commands

```bash
python scripts/verify_all_mcp_tools.py
python examples/simulator_matrix.py --sim all
pytest tests/unit tests/security tests/integration/test_multi_project_all_mcp_tools.py tests/integration/test_simulator_examples_all_mcp_tools.py -q
```
