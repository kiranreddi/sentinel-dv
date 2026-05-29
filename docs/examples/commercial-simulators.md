# VCS, Questa, and Cadence artifact examples

Sentinel DV is simulator-agnostic: the MCP server indexes exported artifacts and never launches a simulator. The repository includes checked-in fixtures for VCS, Questa, and Cadence Xcelium so every MCP tool can be validated without proprietary databases or licenses.

| Simulator fixture | Location | Included artifacts |
|-------------------|----------|--------------------|
| VCS | `demo/vcs_counter/` | JUnit XML, UVM log, assertion JSON, coverage JSON, `*.wave.json` |
| Questa | `demo/questa_counter/` | JUnit XML, UVM log, assertion JSON, coverage JSON, `*.wave.json` |
| Cadence Xcelium | `demo/cadence_counter/` | JUnit XML, UVM log, assertion JSON, coverage JSON, `*.wave.json` |

## Verify all MCP tools

```bash
python examples/simulator_matrix.py --sim all
python scripts/verify_all_mcp_tools.py --sim vcs
python scripts/verify_all_mcp_tools.py --sim questa
python scripts/verify_all_mcp_tools.py --sim cadence
```

Each command indexes a temporary copy of the fixture, starts the in-process FastMCP client, and calls all 15 registered tools.

## Use your own simulator exports

1. Run simulation in your normal batch/CI system.
2. Export bounded text/JSON artifacts into the same layout: `results.xml`, `*.uvm.log`, `assertions/*.assert.json`, `coverage/coverage.json`, and `waveforms/*.wave.json`.
3. Point `artifact_roots` at the export directory and run:

```bash
sentinel-dv-index --config config.yaml --index-all
sentinel-dv-server --config config.yaml
```

For binary waveform databases, generate a bounded summary first. Sentinel DV intentionally does not stream raw FSDB, WLF, SHM, or VPD content through MCP.
