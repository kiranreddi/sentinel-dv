# Cadence Xcelium counter artifact example

This fixture mirrors a Cadence Xcelium-style export using read-only artifacts: JUnit XML, UVM log text, assertion JSON, coverage JSON, and a waveform summary. Sentinel DV consumes these files after the simulation flow has produced them.

Use the same directory pattern for Xcelium regressions: keep simulator execution outside Sentinel DV, then point `artifact_roots` at the exported artifacts.
