# Installation

**Current release: v1.3.0** ([changelog](../about/changelog.md))

This guide shows how to configure and run Sentinel DV locally, then connect it to an MCP client (e.g. Claude Desktop).

## 1. Install

### From MCP Registry (recommended)

Use server name `io.github.kiranreddi/sentinel-dv` in an MCP registry–aware client, or run with `uvx`:

```bash
uvx --from sentinel-dv sentinel-dv-server --config /absolute/path/to/config.yaml
```

### From PyPI

```bash
pip install "sentinel-dv>=1.3.0"
```

> **Note:** Do not install PyPI **1.0.0** (broken wheel). Use **`sentinel-dv>=1.3.0`** for VCS/Questa/Cadence fixtures, assertion/coverage intelligence, VCD/JSON waveforms, and all 15 MCP tools. Verified flow: install → `sentinel-dv-index --index-all` → `sentinel-dv-server` → MCP tools.

For development:

```bash
pip install -e ".[dev]"
```

## 2. Create `config.yaml`

Copy the provided template and update:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to set:

- `artifact_roots`: directories that contain your verification artifacts (UVM `*.log`, cocotb JUnit XML like `results.xml` / `junit.xml`)
- `index.path`: where the DuckDB database should be written
- `adapters`: enable/disable parsers (booleans under `uvm`, `cocotb`, `assertions`, `coverage`, `waveform_summary`)
- For waveforms: set `waveform_summary: true` and add `*.wave.json` and/or `*.vcd` files whose `test_name` matches indexed tests (see [Waveform summaries](../guides/waveforms.md) and `demo/verilator_counter/`)

## 3. Index artifacts (required)

```bash
python -m sentinel_dv.indexing.indexer --config config.yaml --index-all
```

This scans the configured `artifact_roots` and rebuilds the index.

## 4. Start the MCP server (stdio)

```bash
python -m sentinel_dv.server --config config.yaml
```

Alternative: set the config path once:

```bash
export SENTINEL_DV_CONFIG=/absolute/path/to/config.yaml
python -m sentinel_dv.server
```

## 5. Connect via Claude Desktop

Add Sentinel DV to your Claude Desktop MCP config:

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

## 6. Connect via Cline (VS Code)

Update `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "sentinel-dv": {
      "command": "python",
      "args": [
        "-m",
        "sentinel_dv.server",
        "--config",
        "${workspaceFolder}/config.yaml"
      ]
    }
  }
}
```

## Notes

- Sentinel DV exposes MCP tools over **stdio** (there are currently no documented HTTP endpoints).
- If the server reports `INDEX_NOT_READY`, run the indexing step again.
