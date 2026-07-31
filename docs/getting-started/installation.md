# Installation

Sentinel DV v2.3.1 is distributed through PyPI and the MCP Registry as `io.github.kiranreddi/sentinel-dv`.

## Choose an install

=== "uvx"

    `uvx` runs an isolated package without modifying the active Python environment:

    ```bash
    uvx --from sentinel-dv@2.3.1 sentinel-dv-server --config /absolute/path/to/config.yaml
    ```

=== "PyPI"

    ```bash
    python3 -m pip install "sentinel-dv>=2.3.1"
    sentinel-dv-server --config /absolute/path/to/config.yaml
    ```

=== "Source"

    ```bash
    git clone https://github.com/kiranreddi/sentinel-dv.git
    cd sentinel-dv
    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev,docs]"
    ```

Python 3.10 or newer is required.

## Configure

Copy the production template:

```bash
cp config.example.yaml config.yaml
```

At minimum, set:

```yaml
artifact_roots:
  - /absolute/path/to/regression/artifacts

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

Relative paths are resolved from the directory containing the config file. See [Configuration](../configuration.md) for security limits, redaction, submit templates, and adapter settings.

## Build the index

```bash
sentinel-dv-index --config /absolute/path/to/config.yaml --index-all
```

Run indexing after artifacts change. The server queries the index and does not watch artifact roots.

## Start the stdio server

```bash
sentinel-dv-server --config /absolute/path/to/config.yaml
```

A stdio MCP server normally appears silent when started directly because stdout is reserved for JSON-RPC. Use your MCP client's status view to test the handshake.

You may set the config once instead:

```bash
export SENTINEL_DV_CONFIG=/absolute/path/to/config.yaml
sentinel-dv-server
```

If neither `--config` nor `SENTINEL_DV_CONFIG` is set, Sentinel DV checks for `config.yaml` or `config.yml` in the server's working directory. It never falls back to demo artifacts in production.

## Connect an agent

Continue to [Agent setup](agent-setup.md) for Codex, Claude Code, GitHub Copilot CLI, and generic MCP JSON examples.

## Verify a development checkout

```bash
.venv/bin/python scripts/verify_all_mcp_tools.py
.venv/bin/python scripts/verify_skill_workflows.py
```

Expected final lines:

```text
All 28 MCP tools verified.
All 3 Sentinel DV skill workflows verified.
```

These checks index the checked-in demo corpus; they do not require commercial simulator licenses.

## Upgrade

Pin the package version in MCP configuration so every host runs the same server:

```text
sentinel-dv@2.3.1
```

After changing versions, rebuild the index and re-run the connection check. Review the [changelog](../about/changelog.md) before adopting schema or tool changes.
