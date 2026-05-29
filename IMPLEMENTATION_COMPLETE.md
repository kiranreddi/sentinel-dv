# Sentinel DV implementation status

**Version:** 1.2.0
**Status:** Complete for the documented 15-tool, read-only artifact-indexing scope.

## What is complete

- Deterministic ID generation for runs, tests, failures, assertions, and signatures.
- Rule-based taxonomy and redaction for parsed failure content.
- DuckDB index store with runs, tests, failures, assertions, assertion failures, coverage summaries, topologies, waveform summaries, evidence, and metadata.
- Artifact indexer for UVM logs, cocotb/JUnit XML, assertion reports, coverage summaries, precomputed waveform JSON, and VCD summaries.
- FastMCP server exposing all 15 registered tools.
- Security hardening for artifact roots, path traversal rejection, bounded evidence, bounded responses, and configurable redaction.
- Checked-in demo corpus covering UVM, cocotb, Verilator, VCS, Questa, and Cadence Xcelium exported artifacts.
- SVG MCP tool gallery generated from real demo-indexed request/response payloads.
- Unit, security, and integration tests for the implemented surfaces.

## Explicit non-goals

- Sentinel DV does not submit simulation jobs.
- Sentinel DV does not modify RTL, testbench, simulator databases, or artifacts.
- Sentinel DV does not stream raw FSDB, WLF, SHM, VPD, or other proprietary waveform databases through MCP.
- Proprietary simulator outputs should be exported to bounded text, XML, JSON, VCD, or `*.wave.json` summaries before indexing.

## Verification entry points

```bash
python scripts/verify_all_mcp_tools.py
python scripts/verify_all_mcp_tools.py --sim vcs
python scripts/verify_all_mcp_tools.py --sim questa
python scripts/verify_all_mcp_tools.py --sim cadence
python examples/simulator_matrix.py --sim all
```

## Documentation entry points

- `README.md`
- `demo/README.md`
- `docs/examples/overview.md`
- `docs/examples/commercial-simulators.md`
- `docs/guides/simulator-support.md`
- `docs/tools/mcp-tools-reference.md`
- `docs/tools/mcp-tool-gallery.md`
