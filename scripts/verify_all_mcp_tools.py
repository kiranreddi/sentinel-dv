#!/usr/bin/env python3
"""
Verify all Sentinel DV MCP tools (see sentinel_dv.registry.TOOL_NAMES).

Usage (from repository root):
  python scripts/verify_all_mcp_tools.py --in-place
  python scripts/verify_all_mcp_tools.py --multi
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from fastmcp import Client  # noqa: E402

from sentinel_dv import server  # noqa: E402
from sentinel_dv.demo_fixtures import (  # noqa: E402  # noqa: E402
    DEMO_ROOT,
    build_demo_config,
    build_multi_config,
    discover_fixtures,
    expected_tool_names,
    index_demo,
    index_demo_tree,
    mcp_payload,
    prepare_work_dir,
    simulator_demo_dir,
    tool_call_matrix,
)
from sentinel_dv.indexing.store import IndexStore  # noqa: E402


def _print_ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _print_fail(msg: str) -> None:
    print(f"FAIL  {msg}", file=sys.stderr)


async def _run_single_project_mcp(config_path: Path, db_path: Path, suite: str) -> int:
    server.init_server(config_path)
    failures = 0

    with IndexStore(db_path) as store:
        fix = discover_fixtures(store, suite=suite)

    calls = tool_call_matrix(fix)

    async with Client(server.mcp) as client:
        for tool_name, arguments in calls:
            result = await client.call_tool(tool_name, arguments)
            payload = mcp_payload(result)
            if _tool_failure(payload, tool_name):
                _print_fail(f"{tool_name}: {payload['error']}")
                failures += 1
            else:
                _print_ok(tool_name)
    return failures


_FEATURE_GATED_TOOLS = frozenset({"runs.submit", "tests.replay", "sim.status"})
_ALLOWED_DEMO_ERRORS = frozenset({"CONFIG_ERROR", "NOT_FOUND"})


def _tool_failure(payload: dict, tool_name: str) -> bool:
    """True when the tool failed; feature-gated CONFIG/NOT_FOUND on demos is OK."""
    err = payload.get("error")
    if not err:
        return False
    code = err.get("code", "") if isinstance(err, dict) else str(err)
    return not (tool_name in _FEATURE_GATED_TOOLS and code in _ALLOWED_DEMO_ERRORS)


async def _run_multi_project_mcp(config_path: Path, db_path: Path) -> int:
    server.init_server(config_path)
    failures = 0

    with IndexStore(db_path) as store:
        fix = discover_fixtures(store)
        _print_ok(f"suites indexed: {len(fix.suites)} ({', '.join(sorted(fix.suites))})")

    async with Client(server.mcp) as client:
        for tool_name, arguments in tool_call_matrix(fix):
            result = await client.call_tool(tool_name, arguments)
            payload = mcp_payload(result)
            if _tool_failure(payload, tool_name):
                _print_fail(f"{tool_name}: {payload['error']}")
                failures += 1
            else:
                _print_ok(tool_name)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify all Sentinel DV MCP tools.")
    parser.add_argument(
        "--multi",
        action="store_true",
        help="Index entire demo/ tree (default; kept for compatibility)",
    )
    parser.add_argument(
        "--sim",
        choices=("all", "verilator", "vcs", "questa", "cadence"),
        default="all",
        help="Demo simulator fixture to verify, or all checked-in fixtures",
    )
    parser.add_argument(
        "--demo-dir",
        type=Path,
        default=None,
        help="Custom single-project demo directory",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Index demo-dir directly (single-project mode only)",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = tmp_path / "verify.duckdb"

        if args.multi or args.sim == "all":
            stats = index_demo_tree(DEMO_ROOT, db)
            print("Index stats:", stats)
            cfg = build_multi_config(DEMO_ROOT, db)
            config_path = tmp_path / "config.yaml"
            cfg.to_yaml(str(config_path))
            failures = asyncio.run(_run_multi_project_mcp(config_path, db))
        else:
            demo_dir = (args.demo_dir or simulator_demo_dir(args.sim)).resolve()
            if args.demo_dir is not None or args.in_place:
                work = demo_dir
            else:
                work = prepare_work_dir(tmp_path, simulator=args.sim)
            stats = index_demo(work, db)
            print("Index stats:", stats)
            cfg = build_demo_config(work, db)
            config_path = tmp_path / "config.yaml"
            cfg.to_yaml(str(config_path))
            failures = asyncio.run(_run_single_project_mcp(config_path, db, work.name))

    if failures:
        print(f"\n{failures} tool(s) failed.", file=sys.stderr)
        return 1
    print(f"\nAll {len(expected_tool_names())} MCP tools verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
