"""Tests for MCP server registration and initialization."""

from __future__ import annotations

import asyncio

from sentinel_dv.server import init_server, mcp


def test_server_registers_all_documented_tools():
    init_server(None)

    async def _names() -> set[str]:
        tools = await mcp.list_tools()
        return {tool.name for tool in tools}

    names = asyncio.run(_names())
    expected = {
        "runs.list",
        "runs.get",
        "tests.list",
        "tests.get",
        "tests.topology",
        "assertions.list",
        "assertions.get",
        "assertions.failures",
        "failures.list",
        "coverage.list",
        "coverage.summary",
        "regressions.summary",
        "runs.diff",
        "wave.signals",
        "wave.summary",
    }
    assert expected == names
