#!/usr/bin/env python3
"""
Generate MCP tool "screenshots" (SVG cards + gallery markdown) from live index data.

Usage (repository root):
  python scripts/generate_mcp_tool_gallery.py
  python scripts/generate_mcp_tool_gallery.py --open   # open HTML gallery in browser (macOS)

Outputs:
  docs/assets/mcp-tools/*.svg       — per-tool cards (MkDocs-embeddable)
  docs/assets/mcp-tools/gallery.html — full-page preview
  docs/assets/mcp-tools/data/*.json  — captured request/response payloads
  docs/tools/mcp-tool-gallery.md     — gallery page (auto-generated banner)
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sentinel_dv.demo_fixtures import (  # noqa: E402
    DEMO_ROOT,
    discover_fixtures,
    index_demo_tree,
    invoke_core_tool,
    tool_call_matrix,
)
from sentinel_dv.indexing.store import IndexStore  # noqa: E402

ASSETS_DIR = REPO_ROOT / "docs" / "assets" / "mcp-tools"
DATA_DIR = ASSETS_DIR / "data"
GALLERY_MD = REPO_ROOT / "docs" / "tools" / "mcp-tool-gallery.md"
GALLERY_HTML = ASSETS_DIR / "gallery.html"

# Visual theme (matches docs teal/slate aesthetic)
BG = "#0f1419"
PANEL = "#1a2332"
BORDER = "#2d3a4f"
ACCENT = "#14b8a6"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
ERROR = "#f87171"
FONT = "ui-monospace, 'Fira Code', 'SF Mono', Menlo, monospace"
LINE_H = 15
PAD = 16
WIDTH = 920


def _slug(tool_name: str) -> str:
    return tool_name.replace(".", "-")


def _truncate_json(payload: dict[str, Any], max_lines: int = 28, width: int = 96) -> str:
    raw = json.dumps(payload, indent=2, sort_keys=False)
    lines = raw.splitlines()
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + ["  …"]
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= width:
            wrapped.append(line)
        else:
            wrapped.extend(textwrap.wrap(line, width=width) or [line[:width]])
    return "\n".join(wrapped)


def _svg_text_block(
    lines: list[str],
    x: int,
    y0: int,
    fill: str,
    font_size: int = 12,
) -> str:
    parts = []
    y = y0
    for line in lines:
        safe = html.escape(line) or " "
        parts.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-family="{FONT}" '
            f'font-size="{font_size}">{safe}</text>'
        )
        y += LINE_H
    return "\n".join(parts)


def render_tool_svg(tool_name: str, arguments: dict[str, Any], response: dict[str, Any]) -> str:
    has_error = bool(response.get("error"))
    status = "error" if has_error else "ok"
    status_color = ERROR if has_error else ACCENT

    arg_lines = ["Request"] + _truncate_json(arguments, max_lines=8, width=88).splitlines()
    resp_label = "Response (error)" if has_error else "Response"
    resp_lines = [resp_label] + _truncate_json(response, max_lines=26, width=88).splitlines()

    header_h = 52
    arg_h = PAD + len(arg_lines) * LINE_H + PAD
    resp_h = PAD + len(resp_lines) * LINE_H + PAD
    total_h = header_h + arg_h + resp_h + 24

    arg_svg = _svg_text_block(arg_lines, PAD + 4, header_h + PAD + 14, MUTED)
    resp_svg = _svg_text_block(resp_lines, PAD + 4, header_h + arg_h + PAD + 14, TEXT)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{total_h}" viewBox="0 0 {WIDTH} {total_h}">
  <rect width="100%" height="100%" fill="{BG}" rx="8"/>
  <rect x="1" y="1" width="{WIDTH - 2}" height="{header_h - 2}" fill="{PANEL}" rx="8"/>
  <circle cx="{PAD + 8}" cy="26" r="6" fill="#ef4444"/>
  <circle cx="{PAD + 28}" cy="26" r="6" fill="#eab308"/>
  <circle cx="{PAD + 48}" cy="26" r="6" fill="#22c55e"/>
  <text x="{PAD + 72}" y="30" fill="{TEXT}" font-family="Inter, system-ui, sans-serif" font-size="15" font-weight="600">Sentinel DV — {html.escape(tool_name)}</text>
  <text x="{WIDTH - PAD}" y="30" fill="{status_color}" font-family="Inter, system-ui, sans-serif" font-size="12" text-anchor="end">{status}</text>
  <rect x="{PAD}" y="{header_h}" width="{WIDTH - 2 * PAD}" height="{arg_h}" fill="{PANEL}" stroke="{BORDER}" rx="6"/>
  {arg_svg}
  <rect x="{PAD}" y="{header_h + arg_h + 8}" width="{WIDTH - 2 * PAD}" height="{resp_h}" fill="{PANEL}" stroke="{BORDER}" rx="6"/>
  {resp_svg}
</svg>
"""


def _capture_tools(db_path: Path) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    captured: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    with IndexStore(db_path) as store:
        fix = discover_fixtures(store)
        for tool_name, args in tool_call_matrix(fix):
            result = invoke_core_tool(store, tool_name, args)
            captured.append((tool_name, args, result))
    return captured


def _md_json_block(payload: dict[str, Any], admonition: str) -> list[str]:
    """Format JSON inside a pymdownx admonition (4-space indented body)."""
    body = (
        ["    ```json"]
        + ["    " + line for line in json.dumps(payload, indent=2).splitlines()]
        + ["    ```"]
    )
    return [f"??? {admonition}"] + body + [""]


def _write_gallery_md(captured: list[tuple[str, dict, dict]]) -> None:
    lines = [
        "# MCP tool gallery",
        "",
        '!!! note "Auto-generated"',
        "    Regenerate after demo or tool changes:",
        "    ```bash",
        "    python scripts/generate_mcp_tool_gallery.py",
        "    ```",
        "",
        "Visual cards below are produced from a real `demo/` index (multi-project).",
        "Each image shows the **request arguments** and a **truncated JSON response**",
        "exactly as MCP clients receive it (`schema_version` + payload or `error`).",
        "",
        "[Open interactive HTML gallery](../assets/mcp-tools/gallery.html){ .md-button }",
        "",
        "---",
        "",
    ]
    for tool_name, args, response in captured:
        slug = _slug(tool_name)
        lines.extend(
            [
                f"## `{tool_name}`",
                "",
                f"![MCP tool {tool_name}](../assets/mcp-tools/{slug}.svg)",
                "",
                *_md_json_block(args, 'example "Request"'),
                *_md_json_block(response, 'success "Response"'),
            ]
        )
    GALLERY_MD.write_text("\n".join(lines), encoding="utf-8")


def _write_gallery_html(captured: list[tuple[str, dict, dict]]) -> None:
    cards = []
    for tool_name, _args, _resp in captured:
        slug = _slug(tool_name)
        cards.append(
            f'<section class="card"><h2>{html.escape(tool_name)}</h2>'
            f'<img src="{slug}.svg" alt="{html.escape(tool_name)}" loading="lazy"/></section>'
        )
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Sentinel DV — MCP Tool Gallery</title>
  <style>
    body {{ margin: 0; font-family: Inter, system-ui, sans-serif; background: #0b0f14; color: #e2e8f0; }}
    header {{ padding: 24px 32px; border-bottom: 1px solid #2d3a4f; background: #111827; }}
    header h1 {{ margin: 0 0 8px; font-size: 1.5rem; }}
    header p {{ margin: 0; color: #94a3b8; max-width: 720px; }}
    main {{ padding: 24px 32px 48px; display: grid; gap: 32px; max-width: 1000px; margin: 0 auto; }}
    .card h2 {{ font-size: 1.1rem; color: #14b8a6; margin: 0 0 12px; font-family: ui-monospace, monospace; }}
    .card img {{ width: 100%; height: auto; border-radius: 8px; border: 1px solid #2d3a4f; }}
  </style>
</head>
<body>
  <header>
    <h1>Sentinel DV — MCP Tool Gallery</h1>
    <p>Auto-generated from <code>scripts/generate_mcp_tool_gallery.py</code> using the multi-project <code>demo/</code> index.</p>
  </header>
  <main>
    {"".join(cards)}
  </main>
</body>
</html>
"""
    GALLERY_HTML.write_text(doc, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MCP tool screenshot gallery.")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open gallery.html in the default browser (macOS open)",
    )
    args = parser.parse_args()

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "gallery.duckdb"
        print("Indexing demo/ …")
        stats = index_demo_tree(DEMO_ROOT, db)
        print("Index stats:", stats)

        captured = _capture_tools(db)
        from sentinel_dv.registry import TOOL_COUNT

        if len(captured) != TOOL_COUNT:
            print(
                f"warning: expected {TOOL_COUNT} tools, captured {len(captured)}",
                file=sys.stderr,
            )

        for tool_name, arguments, response in captured:
            slug = _slug(tool_name)
            svg_path = ASSETS_DIR / f"{slug}.svg"
            svg_path.write_text(render_tool_svg(tool_name, arguments, response), encoding="utf-8")
            data_path = DATA_DIR / f"{slug}.json"
            data_path.write_text(
                json.dumps(
                    {"tool": tool_name, "arguments": arguments, "response": response},
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"  wrote {svg_path.relative_to(REPO_ROOT)}")

        _write_gallery_md(captured)
        _write_gallery_html(captured)
        print(f"Wrote {GALLERY_MD.relative_to(REPO_ROOT)}")
        print(f"Wrote {GALLERY_HTML.relative_to(REPO_ROOT)}")

    if args.open and sys.platform == "darwin":
        subprocess.run(["open", str(GALLERY_HTML)], check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
