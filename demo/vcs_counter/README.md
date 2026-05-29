# VCS counter artifact example

This fixture contains simulator-exported artifacts only: JUnit XML, UVM log text, assertion JSON, coverage JSON, and a precomputed waveform summary. Sentinel DV indexes these read-only files; it does not invoke VCS from the MCP server.

To reproduce a similar artifact set in your environment, run your VCS job and export equivalent `results.xml`, `*.uvm.log`, assertion, coverage, and waveform-summary files into this directory layout before running `sentinel-dv-index`.
