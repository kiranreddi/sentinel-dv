# Agent Setup

Sentinel DV has two complementary layers:

1. The **MCP server** exposes 28 read-only tools backed by indexed artifacts.
2. The **agent skills** define repeatable regression triage, failure debugging, and coverage closure procedures.

Install or configure both. A skill without the MCP server has no live verification data; the MCP server without a skill still works, but the agent must plan each investigation from scratch.

## Build the index first

Create `config.yaml`, then build the DuckDB index:

```bash
uvx --from sentinel-dv@2.3.1 \
  sentinel-dv-index --config /absolute/path/to/config.yaml --index-all
```

Use the same config path for the server. Relative `artifact_roots` and `index.path` entries are resolved from the config file's directory.

## MCP configuration

### Codex

Codex CLI, the IDE extension, and the desktop app share MCP configuration:

```bash
codex mcp add sentinel-dv \
  --env SENTINEL_DV_CONFIG=/absolute/path/to/config.yaml \
  -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
```

Equivalent `~/.codex/config.toml`:

```toml
[mcp_servers.sentinel-dv]
command = "uvx"
args = ["--from", "sentinel-dv@2.3.1", "sentinel-dv-server"]

[mcp_servers.sentinel-dv.env]
SENTINEL_DV_CONFIG = "/absolute/path/to/config.yaml"
```

Verify with `/mcp`, then call `runs.list`.

### Claude Code

Add a local server:

```bash
claude mcp add \
  --env SENTINEL_DV_CONFIG=/absolute/path/to/config.yaml \
  --transport stdio --scope local sentinel-dv \
  -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
```

For team-shared project configuration, add `.mcp.json` at the repository root and keep the machine-specific path in an environment variable:

```json
{
  "mcpServers": {
    "sentinel-dv": {
      "command": "uvx",
      "args": ["--from", "sentinel-dv@2.3.1", "sentinel-dv-server"],
      "env": {
        "SENTINEL_DV_CONFIG": "${SENTINEL_DV_CONFIG}"
      }
    }
  }
}
```

Run `/mcp` or `claude mcp list`. Project MCP servers require workspace approval.

### GitHub Copilot CLI

```bash
copilot mcp add sentinel-dv \
  --env SENTINEL_DV_CONFIG=/absolute/path/to/config.yaml \
  -- uvx --from sentinel-dv@2.3.1 sentinel-dv-server
```

Equivalent `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "sentinel-dv": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "sentinel-dv@2.3.1", "sentinel-dv-server"],
      "env": {
        "SENTINEL_DV_CONFIG": "/absolute/path/to/config.yaml"
      },
      "tools": ["*"]
    }
  }
}
```

Verify with `/mcp list` or `copilot mcp list`.

### Other MCP clients

Use a stdio entry with `uvx`:

```json
{
  "mcpServers": {
    "sentinel-dv": {
      "command": "uvx",
      "args": [
        "--from",
        "sentinel-dv@2.3.1",
        "sentinel-dv-server",
        "--config",
        "/absolute/path/to/config.yaml"
      ]
    }
  }
}
```

## Skill discovery

The canonical source is `skills/`. Mirrors are committed for each host:

| Host | Project skill path | Explicit invocation |
| --- | --- | --- |
| Codex | `.agents/skills/<name>/SKILL.md` | Mention with `$<skill-name>` |
| Claude Code | `.claude/skills/<name>/SKILL.md` | Run `/<skill-name>` |
| GitHub Copilot | `.github/skills/<name>/SKILL.md` | Ask for the skill by name; Copilot also selects relevant skills automatically |

Available names:

- `sentinel-dv-regression-triage`
- `sentinel-dv-failure-debugging`
- `sentinel-dv-coverage-closure`

Codex and Claude Code can also load the repository as a plugin. The plugin packages the canonical `skills/` directory; the Codex manifest also points at the bundled `.mcp.json`.

## Verify skill loading

| Host | Check |
| --- | --- |
| Codex | Open the skill selector or mention `$sentinel-dv-regression-triage` |
| Claude Code | Run `/skills` and `/mcp` |
| GitHub Copilot CLI | Run `/skills list` and `/mcp list` |

Test with a direct prompt:

```text
Use the sentinel-dv-regression-triage skill on the latest failing run.
Report data-quality warnings and keep every run_id, test_id, and signature_id.
```

## Security boundary

- All 28 MCP tools are annotated read-only.
- `runs.submit` and `tests.replay` generate commands; they do not execute simulations.
- The server reads only configured artifact roots and its index.
- Evidence excerpts are bounded and redacted according to `config.yaml`.
- An agent's permission system is separate from Sentinel DV. Keep normal host approvals enabled.

## Troubleshooting

`Server failed to start`
: Confirm `uvx` is on the host application's `PATH` and use an absolute config path.

`INDEX_NOT_READY`
: Run `sentinel-dv-index --index-all` with the same config used by the server.

`Skill is visible but tools are not`
: The skill loaded correctly, but the MCP server did not. Check the host's MCP status view and server stderr.

`Tools work but the skill is not selected`
: Invoke the skill explicitly once and confirm the client started inside the repository containing the host-specific skill directory.

`Health score looks incomplete`
: Inspect `component_scores`, `effective_weights`, and `data_quality`. Missing coverage, assertion, repeated-history, or multi-simulator cohorts are reported as unavailable rather than scored as perfect.
