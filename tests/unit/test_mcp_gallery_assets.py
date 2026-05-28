"""Ensure MCP tool gallery assets stay in sync with TOOL_NAMES."""

from __future__ import annotations

from pathlib import Path

from sentinel_dv.registry import TOOL_NAMES

REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "docs" / "assets" / "mcp-tools"


def test_gallery_svgs_exist_for_all_tools():
    missing = []
    for name in TOOL_NAMES:
        path = ASSETS / f"{name.replace('.', '-')}.svg"
        if not path.is_file():
            missing.append(path.name)
    assert not missing, f"Run: python scripts/generate_mcp_tool_gallery.py — missing {missing}"
