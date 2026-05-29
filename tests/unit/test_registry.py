"""Tests for MCP tool registry metadata."""

from __future__ import annotations

from sentinel_dv import registry
from sentinel_dv.demo_fixtures import expected_tool_names


def test_tool_names_match_demo_fixture() -> None:
    assert registry.TOOL_COUNT == 15
    assert set(registry.TOOL_NAMES) == set(expected_tool_names())
