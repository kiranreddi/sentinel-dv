# Simulator support

Sentinel DV is **simulator-agnostic**. It indexes exported verification artifacts and exposes them through read-only MCP tools; it does not start simulator jobs, open proprietary databases, or stream raw waveform files.

## Supported artifact types

| Artifact | Files indexed today | Notes |
|----------|---------------------|-------|
| UVM logs | `*.log` | Parses common UVM report lines from VCS, Questa, Xcelium, Verilator, and generic logs. |
| cocotb/JUnit | `results.xml`, `results_*.xml`, `junit.xml`, `*junit*.xml` | Produces tests and failure events. |
| Assertions | `*.assert.json`, `*.assertions.txt`, `assertions*.rpt`, `vcs_assert*.log`, `vsim_assertions*.log`, `questa_assertions*.txt` | Produces assertion definitions and runtime failures. |
| Coverage summaries | `coverage.json`, `coverage_summary.json`, `coverage.xml`, `*.cov.json`, `*.cov.txt`, `coverage.dat.summary` | Use exported summaries, not proprietary coverage databases directly. |
| Waveform summaries | `*.wave.json`, `*_waveform.json`, `waveform_summary.json`, `*.vcd` | VCD can be parsed directly; FSDB/WLF/SHM/VPD should be converted to bounded JSON summaries first. |

## Checked-in simulator examples

| Simulator | Fixture | Verify all MCP tools |
|-----------|---------|----------------------|
| VCS | `demo/vcs_counter/` | `python scripts/verify_all_mcp_tools.py --sim vcs` |
| Questa | `demo/questa_counter/` | `python scripts/verify_all_mcp_tools.py --sim questa` |
| Cadence Xcelium | `demo/cadence_counter/` | `python scripts/verify_all_mcp_tools.py --sim cadence` |
| Verilator | `demo/verilator_counter/` | `python scripts/verify_all_mcp_tools.py --sim verilator` |

Run all simulator fixtures:

```bash
python examples/simulator_matrix.py --sim all
```

## Configuration

Point `artifact_roots` at directories that contain exported artifacts:

```yaml
artifact_roots:
  - ./demo/vcs_counter

index:
  type: duckdb
  path: ./sentinel_dv.db

adapters:
  uvm: true
  cocotb: true
  assertions: true
  coverage: true
  waveform_summary: true
```

Then build the index:

```bash
sentinel-dv-index --config config.yaml --index-all
```

Relative paths in `config.yaml` are resolved relative to the config file location.

## Export guidance

### VCS

Export text reports and summaries next to your regression artifacts:

```bash
vcs -sverilog -full64 -debug_access+all -l simv.log ...
./simv +UVM_TESTNAME=my_test -l run.log
```

Recommended files for Sentinel DV:

- `results.xml` from your regression runner or CI harness
- `run.log` or `simv.log`
- `assertions/*.assert.json` or bounded assertion report text
- `coverage/coverage.json` or exported XML/text summaries
- `waveforms/*.wave.json` generated from VPD/FSDB/VCD as a bounded summary

### Questa

Use Questa logs and exported summaries:

```bash
vlog counter.sv tb.sv
vsim -c work.tb -do "run -all; quit" -l vsim.log
vcover report -html -output coverage_html coverage.ucdb
```

For MCP use, export coverage/assertion/waveform data to bounded JSON/XML/text files before indexing. Raw WLF/UCDB files are not parsed directly.

### Cadence Xcelium

Use Xcelium logs and exported summaries:

```bash
xrun -sv counter.sv tb.sv -l xrun.log
```

For MCP use, export IMC coverage, assertion summaries, and SHM waveform information into bounded JSON/XML/text files before indexing. Raw SHM/coverage databases are not parsed directly.

## UVM log parsing details

Sentinel DV ships patterns for the four common UVM log formats:

| Format | Example line |
|--------|-------------|
| VCS native | `UVM_ERROR /path/file.svh(10) @ 887915000000: uvm_test_top.comp [TAG] message` |
| VCS Jenkins | `UVM_ERROR /path/file.svh @ 887915000000: uvm_test_top.comp message` |
| Questa | `# UVM_ERROR @ 100 ns: uvm_test_top.comp message` |
| Generic fallback | `UVM_ERROR @ 100 ns: message` |

Patterns are tried in the order shown; the first match wins.

**Count-summary lines are always skipped**: VCS appends `UVM_ERROR :    0`
and Questa appends `# UVM_ERROR :    0` at end-of-simulation to report
per-severity counts.  These lines are **not** failures and are filtered
before any pattern is attempted.

## Security model

Sentinel DV keeps simulator support artifact-based by design:

- MCP tools are read-only.
- Evidence paths are normalized and cannot escape configured artifact roots.
- Output size, evidence count, and excerpts are bounded by `security` settings.
- Redaction is applied to parsed log messages and failure details.
