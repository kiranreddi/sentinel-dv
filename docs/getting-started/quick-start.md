# Quick Start

This path installs Sentinel DV, indexes the checked-in demo artifacts, connects an MCP client, and verifies the server with real tool calls.

## Prerequisites

- Python 3.10 or newer
- [`uv`](https://docs.astral.sh/uv/) for the shortest install path
- An MCP client such as Codex, Claude Code, or GitHub Copilot CLI

The commands below run v2.3.1 through `uvx`. For a persistent environment, use
`python3 -m pip install "sentinel-dv>=2.3.1"`.

## 1. Create a demo configuration

Clone the repository so the example artifacts and verification scripts are available:

```bash
git clone https://github.com/kiranreddi/sentinel-dv.git
cd sentinel-dv
cp demo/config.example.yaml demo/config.yaml
```

`config.yaml` is resolved relative to its own directory. Review `artifact_roots` and `index.path` before using the same pattern with production artifacts.

## 2. Index artifacts

```bash
uvx --from sentinel-dv@2.3.1 \
  sentinel-dv-index --config "$PWD/demo/config.yaml" --index-all
```

Indexing is a required, separate step. The MCP server reads the DuckDB index; it does not scan raw artifacts on each tool call.

## 3. Connect an MCP client

=== "Codex"

    ```bash
    codex mcp add sentinel-dv \
      --env SENTINEL_DV_CONFIG="$PWD/demo/config.yaml" \
      -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
    ```

=== "Claude Code"

    ```bash
    claude mcp add \
      --env SENTINEL_DV_CONFIG="$PWD/demo/config.yaml" \
      --transport stdio --scope local sentinel-dv \
      -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
    ```

=== "GitHub Copilot CLI"

    ```bash
    copilot mcp add sentinel-dv \
      --env SENTINEL_DV_CONFIG="$PWD/demo/config.yaml" \
      -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
    ```

Use an absolute path for `SENTINEL_DV_CONFIG`. See [Agent setup](agent-setup.md) for configuration files, project scope, skills, and host-specific verification.

## 4. Verify the connection

In the client, confirm that the `sentinel-dv` server is connected and that `runs.list` is available:

| Client | Check |
| --- | --- |
| Codex | `/mcp` |
| Claude Code | `/mcp` or `claude mcp list` |
| GitHub Copilot CLI | `/mcp list` or `copilot mcp list` |

Then ask:

```text
List the indexed runs with runs.list. Do not summarize beyond the returned data.
```

An empty result is not a passing regression. It means the selected index has no matching records or needs to be rebuilt.

## 5. Use a workflow skill

The repository includes three skills under `.agents/skills`, `.claude/skills`, and `.github/skills`.

=== "Regression triage"

    ```text
    Use the Sentinel DV regression triage skill to assess the latest failing run.
    Preserve IDs, disclose missing health components, and prioritize failure clusters.
    ```

=== "Failure debugging"

    ```text
    Use the Sentinel DV failure debugging skill to explain why test_counter_sim failed.
    Separate observations, inference, and missing evidence.
    ```

=== "Coverage closure"

    ```text
    Use the Sentinel DV coverage closure skill for the latest xcelium run.
    Prioritize AXI4 functional gaps and check assertion vacuity.
    ```

The skills guide the tool sequence and reporting rules. The MCP server remains the source of live, typed verification data.

## Repository verification

From a development checkout:

```bash
.venv/bin/python scripts/verify_all_mcp_tools.py
.venv/bin/python scripts/verify_skill_workflows.py
```

The first command invokes all 28 MCP tools. The second executes the three published skill workflows against 52 checked-in demo artifacts.

## Next

- [Agent setup](agent-setup.md)
- [Skill workflows](../skills/overview.md)
- [All 28 MCP tools](../tools/mcp-tools-reference.md)
- [Artifact and simulator support](../guides/simulator-support.md)
- [Production deployment](../deployment/production.md)
