"""Tests for MCP server registration and initialization."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sentinel_dv.config import SentinelDVConfig
from sentinel_dv.server import init_server, mcp


def test_server_registers_all_documented_tools(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"artifact_roots: [{tmp_path!s}]\nindex:\n  type: duckdb\n  path: {tmp_path / 't.db'}\n",
        encoding="utf-8",
    )
    init_server(cfg)

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


def test_mcp_tools_expose_read_only_annotations(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"artifact_roots: [{tmp_path!s}]\nindex:\n  type: duckdb\n  path: {tmp_path / 't.db'}\n",
        encoding="utf-8",
    )
    init_server(cfg)

    async def _check() -> None:
        tools = await mcp.list_tools()
        for tool in tools:
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is True
            assert tool.description
            assert tool.output_schema is not None

    asyncio.run(_check())
