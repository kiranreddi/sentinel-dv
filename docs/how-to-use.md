# How to Use Sentinel DV - Complete Guide

Welcome to Sentinel DV! This guide will help you effectively use the MCP server for verification intelligence.

---

## 📚 Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding the Architecture](#understanding-the-architecture)
3. [Setting Up Your Environment](#setting-up-your-environment)
4. [Indexing Verification Artifacts](#indexing-verification-artifacts)
5. [Using MCP Tools](#using-mcp-tools)
6. [Integration with AI Agents](#integration-with-ai-agents)
7. [Common Workflows](#common-workflows)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Quick Start

### Installation (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/kiranreddi/sentinel-dv.git
cd sentinel-dv

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Verify installation
python -m sentinel_dv.server --help
```

### First Index (10 minutes)

```bash
# 1. Create configuration
cp config.example.yaml config.yaml

# 2. Edit config.yaml to point to your artifacts
nano config.yaml
# Set artifact_roots to your verification directories

# 3. Index demo artifacts (test the system)
python -m sentinel_dv.indexing.indexer \
    --config config.yaml \
    --index-all

# 4. Check index was created
ls -lh sentinel_dv.db
```

### Start Server (2 minutes)

```bash
# Start the MCP server
python -m sentinel_dv.server --config config.yaml

# Server is now ready for MCP clients!
```

---

## Understanding the Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│                   MCP Client                        │
│            (Claude, Custom Agent, etc.)             │
└────────────────┬────────────────────────────────────┘
                 │ MCP Protocol
┌────────────────▼────────────────────────────────────┐
│              Sentinel DV Server                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  MCP Tools (runs, tests, failures, etc.)     │  │
│  └──────────────┬───────────────────────────────┘  │
│                 │                                   │
│  ┌──────────────▼───────────────────────────────┐  │
│  │      DuckDB Index Store                      │  │
│  │  - runs, tests, failures, coverage           │  │
│  └──────────────┬───────────────────────────────┘  │
│                 │                                   │
│  ┌──────────────▼───────────────────────────────┐  │
│  │  Adapters (UVM, cocotb, coverage)            │  │
│  └──────────────┬───────────────────────────────┘  │
└─────────────────┼────────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────────┐
│         Verification Artifacts                       │
│  - UVM logs                                          │
│  - cocotb JUnit XML                                  │
│  - Coverage reports                                  │
│  - Assertion definitions                             │
└──────────────────────────────────────────────────────┘
```

### Data Flow

1. **Indexing Phase** (offline)
   - Adapters parse raw artifacts
   - Data is normalized and classified
   - IDs are generated deterministically
   - Everything stored in DuckDB

2. **Query Phase** (runtime)
   - MCP client sends tool request
   - Server queries DuckDB index
   - Results are paginated and returned
   - All responses are typed and validated

---

## Setting Up Your Environment

### Configuration File Explained

```yaml
# config.yaml - Current configuration reference (matches `config.example.yaml`)

# 1. ARTIFACT ROOTS (Required)
artifact_roots:
  - /path/to/nightly/regressions
  - /path/to/uvm/logs

# 2. INDEX CONFIGURATION
index:
  type: duckdb
  path: ./sentinel_dv.db

# 3. ADAPTER CONFIGURATION
adapters:
  uvm: true
  cocotb: true
  assertions: true
  coverage: true
  waveform_summary: false

# 4. SECURITY SETTINGS
security:
  max_response_bytes: 2097152
  max_page_size: 200
  max_evidence_refs: 10
  max_excerpt_length: 1024
  max_message_length: 4096
  max_tags_per_event: 20
  max_coverage_metrics: 200
  max_bins_missed: 50

# 5. REDACTION
redaction:
  enabled: true
  patterns: []
  redact_emails: true
  redact_ips: false
  redact_paths: true
```

### Directory Structure

Organize your artifacts like this:

```
verification/
├── nightly_runs/
│   ├── 2026-01-20/
│   │   ├── run_123/
│   │   │   ├── test_axi_burst.log
│   │   │   ├── coverage.xml
│   │   │   └── assertions.rpt
│   │   └── run_124/
│   └── 2026-01-21/
├── continuous_integration/
│   └── pr_456/
│       ├── cocotb_results.xml
│       └── uvm_test.log
└── regression_database/
    └── historical_data.db
```

---

## Indexing Verification Artifacts

### Full Indexing

```bash
# Index all configured artifact roots
python -m sentinel_dv.indexing.indexer \
    --config config.yaml \
    --index-all

# Expected output:
# Scanning artifacts...
# Found 1,234 files
# Parsing UVM logs: 500 files
# Parsing cocotb results: 234 files
# Parsing coverage: 500 files
# Generating IDs...
# Writing to DuckDB...
# Indexed 1,234 files in 45.3s
# Runs: 50
# Tests: 2,500
# Failures: 156
# Coverage summaries: 50
```

### Incremental / Selective Indexing

Sentinel DV currently supports **full indexing only**:
- Update `artifact_roots` in `config.yaml`
- Re-run: `python -m sentinel_dv.indexing.indexer --config config.yaml --index-all`

---

## Using MCP Tools

Sentinel DV provides **15** read-only MCP tools. The canonical reference—with parameters, JSON examples, and suggested tool chains—is **[MCP tools reference](tools/mcp-tools-reference.md)**.

| Category | Tools |
|----------|--------|
| Discovery | `runs.list`, `tests.list`, `assertions.list`, `coverage.list` |
| Detail | `runs.get`, `tests.get`, `tests.topology`, `assertions.get` |
| Analysis | `failures.list`, `assertions.failures`, `coverage.summary` |
| Regression | `regressions.summary`, `runs.diff` |
| Waveforms | `wave.signals`, `wave.summary` |

Category guides: [Discovery](tools/discovery.md) · [Detail](tools/detail.md) · [Analysis](tools/analysis.md) · [Regression](tools/regression.md) · [Waveforms](tools/waveforms.md)

**Waveform tools:** enable `adapters.waveform_summary: true`, index `*.wave.json` and/or `*.vcd`, then call `wave.signals` / `wave.summary` with optional `start_time_ns` / `end_time_ns` (nanoseconds). See [Waveform summaries](guides/waveforms.md) and [Verilator + VCD](examples/verilator-counter.md).

---

## Integration with AI Agents

### Claude Desktop Integration

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sentinel-dv": {
      "command": "python",
      "args": [
        "-m",
        "sentinel_dv.server",
        "--config",
        "/full/path/to/config.yaml"
      ],
      "env": {
        "PYTHONPATH": "/full/path/to/sentinel-dv"
      }
    }
  }
}
```

Restart Claude Desktop, and Sentinel DV tools will be available!

### Custom MCP Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def query_sentinel_dv():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "sentinel_dv.server", "--config", "config.yaml"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # List failing tests
            result = await session.call_tool("tests.list", {
                "status": "fail",
                "page": 1,
                "page_size": 10
            })
            
            print(result)
```

### API Client (HTTP/REST)

Sentinel DV currently exposes tools over **stdio MCP** (no HTTP endpoints are documented).

---

## Common Workflows

### Workflow 1: Daily Regression Triage

```bash
# 1. Index latest nightly run
python -m sentinel_dv.indexing.indexer \
    --config config.yaml \
    --index-all

# 2. Start server
python -m sentinel_dv.server --config config.yaml
```

Then in Claude:

```
"Show me the regression summary for the nightly suite from the past 7 days"
→ Uses: regressions.summary

"List all assertion failures from last night's run"
→ Uses: failures.list with category=assertion

"Compare coverage between yesterday and today"
→ Uses: runs.diff
```

For deterministic replay across reruns, pass `as_of` (RFC3339):

```json
{ "suite": "nightly", "window_days": 7, "as_of": "2026-05-27T23:00:00Z" }
```

### Workflow 2: PR Validation

```bash
# Index PR artifacts
python -m sentinel_dv.indexing.indexer \
    --config config.yaml \
    --index-all
```

In Claude:

```
"Did PR #123 introduce any new failures?"
→ Uses: runs.diff comparing main vs PR

"What's the coverage impact of this PR?"
→ Uses: coverage.summary
```

### Workflow 3: Top Failure Signatures

```bash
# Index (update `artifact_roots` in config.yaml to include the historical runs)
python -m sentinel_dv.indexing.indexer \
    --config config.yaml \
    --index-all
```

In Claude:

```
"Show me the top failure signatures for the nightly suite"
→ Uses: regressions.summary
```

### Workflow 4: Root Cause Analysis

In Claude:

```
"Why did test axi_burst_wr fail?"
→ Uses: tests.get, failures.list

"Show me the scoreboard mismatches in the AXI agent"
→ Uses: failures.list with component=axi_agent, category=scoreboard

"What assertions failed during this test?"
→ Uses: assertions.failures
```

### Workflow 5: Assertion and coverage intelligence

In Claude:

```
"List APB assertions and show failures in this run between 2us and 3us"
→ Uses: assertions.list with protocol/tag filters, then assertions.failures with start_time_ns/end_time_ns

"Show bounded functional coverage with evidence for latest run"
→ Uses: coverage.list, then coverage.summary with include_evidence=true
```

Tips:
- `assertions.list` supports deterministic filtering by `scope`, `name_pattern`, `protocol`, and `tag`.
- `coverage.summary` is bounded by `security.max_coverage_metrics` and `security.max_bins_missed`.
- `assertions.failures` time windows require both `start_time_ns` and `end_time_ns`.

### Workflow 6: Waveform time window

Index with waveforms enabled, then in your MCP client:

```
"List signals for test_counter_sim between 2 and 3 microseconds"
→ Uses: tests.list → wave.signals with start_time_ns: 2000, end_time_ns: 3000
```

See [MCP tools reference — Waveforms](tools/mcp-tools-reference.md#waveforms) and [Verilator example](examples/verilator-counter.md).

---

## Troubleshooting

### Issue: Indexing is slow

**Solution:**
```yaml
# In config.yaml, increase parallelism
index:
  workers: 8  # Use more CPU cores

performance:
  duckdb_threads: 8
```

### Issue: Server won't start

**Check:**
```bash
# 1. Verify Python version
python --version  # Must be 3.10+

# 2. Check dependencies
pip list | grep fastmcp
pip list | grep duckdb

# 3. Verify config
python -c "from sentinel_dv.config import load_config; load_config('config.yaml')"

# 4. Check database
ls -lh sentinel_dv.db
```

### Issue: No results from queries

**Debug:**
```bash
# 1. Check index contents
python -c "
from sentinel_dv.indexing.store import IndexStore
with IndexStore('sentinel_dv.db') as store:
    print(f'Runs: {store.count_runs()}')
    print(f'Tests: {store.count_tests()}')
    print(f'Failures: {store.count_failures()}')
"

# 2. Re-index with verbose logging
python -m sentinel_dv.indexing.indexer \
    --config config.yaml \
    --index-all
```

### Issue: Redaction too aggressive

**Solution:**
```yaml
# In config.yaml, tune redaction
redaction:
  enabled: true
  redact_emails: false  # Keep emails if needed
  redact_paths: false   # Keep paths if needed
  
  # Remove aggressive patterns
  patterns: []
```

### Issue: MCP client can't connect

**Check:**
```bash
# 1. Test server manually
python -m sentinel_dv.server --config config.yaml

# 2. Check server logs
python -m sentinel_dv.server --config config.yaml

# 3. Verify MCP protocol version
python -c "import fastmcp; print(fastmcp.__version__)"
```

---

## Best Practices

### 1. Regular Indexing

Schedule daily indexing:

```bash
# crontab -e
0 2 * * * cd /path/to/sentinel-dv && python -m sentinel_dv.indexing.indexer --config config.yaml --index-all
```

### 2. Organize Artifacts

Keep artifacts organized by suite/date:

```
/verification/
├── nightly/YYYY-MM-DD/
├── pr/PR_NUMBER/
└── release/VERSION/
```

### 3. Incremental Indexing

Incremental indexing flags are not currently exposed. For updates, re-run full indexing:
`python -m sentinel_dv.indexing.indexer --config config.yaml --index-all`

### 4. Monitor Index Size

```bash
# Check database size
du -h sentinel_dv.db

# Vacuum if needed (reclaim space)
python -c "
from sentinel_dv.indexing.store import IndexStore
with IndexStore('sentinel_dv.db') as store:
    store._conn.execute('VACUUM')
"
```

### 5. Version Control Config

```bash
# Track config changes
git add config.yaml
git commit -m "Update artifact roots"
git push
```

### 6. Security Checklist

- ✅ Enable redaction for production
- ✅ Restrict artifact_roots to necessary paths
- ✅ Set appropriate max_response_bytes
- ✅ Review `redaction.patterns` for your environment
- ✅ Never commit credentials in config.yaml

### 7. Performance Tuning

```yaml
# For large scale (100K+ tests)
index:
  workers: 16
  
performance:
  cache_size_mb: 500
  duckdb_threads: 16
  max_connections: 20

# For small scale (<10K tests)
index:
  workers: 4
  
performance:
  cache_size_mb: 50
  duckdb_threads: 4
  max_connections: 5
```

---

## Advanced Usage

### Custom Taxonomy

```yaml
# In config.yaml
taxonomy:
  custom_categories:
    - custom_axi_protocol_violation
    - custom_ahb_timeout
  
  custom_tags:
    - my_dut_version_1_0
    - my_protocol_xyz
```

### Programmatic Access

```python
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.adapters import UVMLogParser

# Direct adapter usage
parser = UVMLogParser()
result = parser.parse_log("test.log")

# Direct store access
with IndexStore("sentinel_dv.db") as store:
    tests, total = store.query_tests(
        status="fail",
        framework="uvm"
    )
    
    for test in tests:
        print(f"{test['name']}: {test['status']}")
```

### Custom Adapters

```python
# Create custom adapter for your tool
from sentinel_dv.adapters.base import BaseAdapter

class MyToolAdapter(BaseAdapter):
    def parse(self, file_path):
        # Your parsing logic
        return {
            "tests": [...],
            "failures": [...]
        }

# Register adapter
# In config.yaml:
adapters:
  enabled:
    - my_tool
  
  my_tool:
    patterns:
      - "**/*.mytool"
```

---

## Getting Help

### Resources

- 📖 [Full Documentation](https://kiranreddi.github.io/sentinel-dv/)
- 💬 [GitHub Discussions](https://github.com/kiranreddi/sentinel-dv/discussions)
- 🐛 [Issue Tracker](https://github.com/kiranreddi/sentinel-dv/issues)
- 📧 Email: support@sentinel-dv.io

### Community

- Join our Discord: [discord.gg/sentinel-dv](#)
- Follow updates: [@SentinelDV](#)
- Weekly office hours: Wednesdays 2pm PST

---

## Next Steps

1. ✅ Complete quick start
2. ✅ Index your first artifacts
3. ✅ Try example queries in Claude
4. 📖 Read [Architecture Overview](architecture/overview.md)
5. 🔧 Explore [Tool Reference](tools/overview.md)
6. 🚀 Set up production deployment

**Happy debugging! 🛡️**
