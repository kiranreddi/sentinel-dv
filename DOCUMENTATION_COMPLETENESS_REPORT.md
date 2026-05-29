# Documentation completeness report

**Status:** Current for Sentinel DV v1.2.0.

## Included documentation

| Area | Pages |
|------|-------|
| Getting started | `docs/getting-started/quick-start.md`, `docs/getting-started/installation.md`, `docs/configuration.md`, `docs/how-to-use.md` |
| Examples | `docs/examples/overview.md`, `docs/examples/verilator-counter.md`, `docs/examples/cocotb-waveforms.md`, `docs/examples/commercial-simulators.md` |
| Architecture | `docs/architecture/overview.md`, `docs/architecture/security.md`, `docs/architecture/schemas.md`, `docs/ids.md`, `docs/taxonomy.md`, `docs/index-store.md` |
| Tools | `docs/tools/overview.md`, `docs/tools/mcp-tools-reference.md`, `docs/tools/mcp-tool-gallery.md`, discovery/detail/analysis/regression/waveform pages |
| Guides | `docs/guides/simulator-support.md`, `docs/guides/waveforms.md`, `docs/guides/performance.md`, `docs/guides/troubleshooting.md` |
| Adapters and operations | `docs/adapters/custom.md`, `docs/deployment/production.md`, `docs/release/v1.2.0-checklist.md` |
| About | changelog, license, security policy |

## Current example coverage

- UVM log fixtures
- cocotb/JUnit fixtures
- Verilator counter artifacts
- VCS-style exported artifacts
- Questa-style exported artifacts
- Cadence Xcelium-style exported artifacts
- MCP gallery assets generated from real indexed demo payloads

## Navigation status

All documentation pages above are linked from `mkdocs.yml`.

## Regeneration commands

```bash
python scripts/generate_mcp_tool_gallery.py
mkdocs build --strict
```
