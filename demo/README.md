# Sentinel DV Demo

This directory contains example verification artifacts for testing and demonstration.

## Structure

```
demo/
├── uvm_logs/          # Example UVM simulation logs
├── cocotb_results/    # Example cocotb JUnit XML results  
└── README.md          # This file
```

## Usage

### 1. Index the Demo Artifacts

```bash
# From repository root
python -m sentinel_dv.indexing.indexer \
    --config config.example.yaml \
    --index-all
```

### 2. Start the MCP Server

```bash
python -m sentinel_dv.server --config config.example.yaml
```

### 3. Query with MCP Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to server
server_params = StdioServerParameters(
    command="python",
    args=["-m", "sentinel_dv.server", "--config", "config.example.yaml"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize
        await session.initialize()
        
        # List tests
        result = await session.call_tool("tests.list", {"page": 1, "page_size": 10})
        print(result)
```

## Example Artifacts

### UVM Log (test_axi_basic.log)

Contains:
- UVM_INFO messages showing transaction flow
- UVM_ERROR for data mismatch in scoreboard
- Test failure summary

### cocotb Results (results.xml)

Contains:
- JUnit XML format test results
- Passing test (test_increment)
- Failing test (test_overflow) with assertion error

## Creating Your Own Artifacts

### UVM Logs

Place UVM simulator logs in `uvm_logs/`:
- Questa: `*.log`
- VCS: `*.log` 
- Xcelium: `*.log`

### cocotb Results

Place JUnit XML results in `cocotb_results/`:
- `results.xml` (standard cocotb output)

### Coverage Reports

Place coverage reports in `coverage/`:
- Functional coverage summaries
- Code coverage reports

## Indexing Configuration

Update `config.example.yaml` to point to demo artifacts:

```yaml
artifact_roots:
  - "./demo"

adapters:
  uvm: true
  cocotb: true
  assertions: true
  coverage: true
  waveform_summary: false
```

## Expected Results

After indexing, you should see:
- 1-2 runs indexed
- 2-3 tests found
- 1-2 failures catalogued
- Failure taxonomy applied (scoreboard, assertion categories)
- Evidence links to original artifacts
