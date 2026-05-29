# Questa counter artifact example

This fixture mirrors a Questa/ModelSim-style export using read-only artifacts: JUnit XML, UVM log text, assertion JSON, coverage JSON, and a waveform summary. Sentinel DV consumes the exported files and never starts the simulator from MCP tools.

Use this layout as a template for Questa regressions that write logs and summaries into a stable artifact directory.
