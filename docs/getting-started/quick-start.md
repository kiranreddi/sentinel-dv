# Quick Start

Get up and running with Sentinel DV in minutes.

## Prerequisites

- Python 3.10 or higher
- Verification artifacts (UVM logs, cocotb results, coverage reports)
- 500MB+ disk space for indexing

## Installation

=== "PyPI (Recommended)"

    ```bash
    pip install "sentinel-dv>=2.3.0"
    ```

=== "From Source"

    ```bash
    git clone https://github.com/kiranreddi/sentinel-dv.git
    cd sentinel-dv
    pip install -e ".[dev]"
    ```

## Configuration

**Required:** Sentinel DV does not start without a config file (no silent `demo/` default).

From the repository root, copy the template and edit paths for your environment:

```bash
cp config.example.yaml config.yaml
```

Alternatively set `export SENTINEL_DV_CONFIG=/absolute/path/to/config.yaml`, or place `config.yaml` / `config.yml` in the directory where you start the server.

Example `config.yaml`:

```yaml
artifact_roots:
  - /path/to/verification/regressions
  
index:
  type: duckdb
  path: ./sentinel_dv.db

adapters:
  uvm: true
  cocotb: true
  assertions: true
  coverage: true

security:
  max_page_size: 200
  max_response_bytes: 2097152

redaction:
  enabled: true
  redact_emails: true
  redact_paths: true
```

!!! tip "Example Configuration"
    Copy `config.example.yaml` and customize for your environment.

## Index Your Artifacts

```bash
python -m sentinel_dv.indexing.indexer --config config.yaml --index-all
```

This will:

1. Scan configured artifact roots
2. Parse verification artifacts using enabled adapters
3. Build normalized index in DuckDB
4. Generate failure signatures and topology

**Expected output:**

```
[INFO] Scanning artifact roots...
[INFO] Found 150 test logs
[INFO] Parsing UVM logs...
[INFO] Parsing cocotb results...
[INFO] Building index...
[INFO] Indexed 150 tests, 45 failures, 1200 assertions, 80 coverage reports
[INFO] Index complete: sentinel_dv.db (125MB)
```

## Start the Server

```bash
python -m sentinel_dv.server --config config.yaml
```

**Server will start on stdio (MCP protocol):**

```
Sentinel DV v2.3.0 started
Schema version: 1.0.0
Tools registered: 15
Index ready: 150 tests indexed
```

## Use with Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "sentinel-dv": {
      "command": "python",
      "args": [
        "-m",
        "sentinel_dv.server",
        "--config",
        "/absolute/path/to/config.yaml"
      ]
    }
  }
}
```

Restart Claude Desktop.

## First Queries

Try these queries with Claude:

!!! example "Test Failure Analysis"
    ```
    "Why did test axi_burst_test fail in the latest run?"
    ```
    
    Claude will use:
    - `tests.list` to find the test
    - `failures.list` to get failure events
    - `tests.topology` to understand the testbench structure

!!! example "Coverage Comparison"
    ```
    "Compare functional coverage between runs R123 and R124"
    ```
    
    Claude will use:
    - `runs.diff` to compute differences
    - `coverage.summary` to get detailed metrics

!!! example "Assertion Tracking"
    ```
    "Show me all AXI assertion failures from this week"
    ```
    
    Claude will use:
    - `assertions.list` to find AXI assertions
    - `assertions.failures` to get runtime failures
    - `regressions.summary` for time windowing

!!! example "Regression Health"
    ```
    "What's the pass rate for the nightly regression?"
    ```
    
    Claude will use:
    - `regressions.summary` for suite-level stats
    - `runs.list` to enumerate runs

!!! example "Waveform window (1.2.0+)"
    ```
    "Show clk toggles for test_counter_sim between 2 and 3 microseconds"
    ```
    
    Claude will use:
    - `tests.list` to resolve `test_id`
    - `wave.signals` with `start_time_ns: 2000`, `end_time_ns: 3000`
    
    Requires `waveform_summary: true` and an indexed VCD or `*.wave.json`. See [MCP tools reference](../tools/mcp-tools-reference.md).

## Verify It Works

Check that tools are accessible:

```python
# test_connection.py
from sentinel_dv.config import load_config
from sentinel_dv.indexing.store import get_store

config = load_config("config.yaml")
store = get_store()

print(f"Tests indexed: {store.count_tests()}")
print(f"Runs indexed: {store.count_runs()}")
print(f"Failures indexed: {store.count_failures()}")
```

## Next Steps

- [MCP tool gallery](../tools/mcp-tool-gallery.md) — visual cards for all 28 tools (real JSON from `demo/`)
- [Multi-project demo](https://github.com/kiranreddi/sentinel-dv/blob/main/demo/README.md) — UVM, cocotb, Verilator, and commercial simulator fixtures
- [VCS, Questa, and Cadence](../examples/commercial-simulators.md) — license-free artifact validation (`python scripts/verify_all_mcp_tools.py --sim vcs`)
- [Verilator + VCD example](../examples/verilator-counter.md) — end-to-end waveform demo
- [Waveform summaries](../guides/waveforms.md) — `*.wave.json` and `*.vcd` indexing
- [Configure adapters](../configuration.md) for your specific simulator
- [Explore tools](../tools/overview.md) available for queries
- [Understand schemas](../architecture/schemas.md) for structured data
- [Deploy to production](../deployment/production.md) with systemd

## Troubleshooting

??? question "Index not building?"

    - Check artifact root paths are correct and readable
    - Ensure logs are in recognized format (UVM, cocotb)

??? question "Server not starting?"

    - Verify Python version (3.10+)
    - Check config.yaml is valid YAML
    - Ensure index database exists and is readable

??? question "No results from queries?"

    - Verify index was built successfully
    - Check that artifacts contain expected data
    - Try simpler queries first (e.g., `runs.list`)

[Full Troubleshooting Guide](../guides/troubleshooting.md){ .md-button }
