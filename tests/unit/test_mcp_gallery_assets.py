"""Ensure MCP tool gallery assets stay in sync with TOOL_NAMES."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_dv.registry import TOOL_NAMES

REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "docs" / "assets" / "mcp-tools"
DATA = ASSETS / "data"


def test_gallery_svgs_exist_for_all_tools():
    missing = []
    for name in TOOL_NAMES:
        path = ASSETS / f"{name.replace('.', '-')}.svg"
        if not path.is_file():
            missing.append(path.name)
    assert not missing, f"Run: python scripts/generate_mcp_tool_gallery.py — missing {missing}"


def test_gallery_data_exists_for_all_tools():
    missing = []
    wrong_tool = []
    for name in TOOL_NAMES:
        path = DATA / f"{name.replace('.', '-')}.json"
        if not path.is_file():
            missing.append(path.name)
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("tool") != name:
            wrong_tool.append(path.name)
        assert isinstance(payload.get("arguments"), dict), path
        assert isinstance(payload.get("response"), dict), path
    assert not missing, f"Run: python scripts/generate_mcp_tool_gallery.py — missing {missing}"
    assert not wrong_tool, f"Gallery data tool names are stale: {wrong_tool}"


def test_gallery_html_links_all_tools():
    html = (ASSETS / "gallery.html").read_text(encoding="utf-8")
    missing = [name for name in TOOL_NAMES if name not in html]
    assert not missing, f"gallery.html missing tool cards for {missing}"
