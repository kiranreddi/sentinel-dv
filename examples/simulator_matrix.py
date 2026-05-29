#!/usr/bin/env python3
"""Verify Sentinel DV MCP tools against checked-in simulator artifact examples."""

from __future__ import annotations

import argparse
import asyncio
import tempfile
from pathlib import Path

from fastmcp import Client

from sentinel_dv import server
from sentinel_dv.demo_fixtures import (
    build_demo_config,
    discover_fixtures,
    index_demo,
    mcp_payload,
    prepare_work_dir,
    tool_call_matrix,
)
from sentinel_dv.indexing.store import IndexStore


async def verify_simulator(simulator: str, tmp_path: Path) -> int:
    tmp_path.mkdir(parents=True, exist_ok=True)
    work = prepare_work_dir(tmp_path, simulator=simulator)
    db_path = tmp_path / f"{simulator}.duckdb"
    stats = index_demo(work, db_path)
    print(f"{simulator}: indexed {stats}")

    cfg = build_demo_config(work, db_path)
    cfg_path = tmp_path / f"{simulator}.yaml"
    cfg.to_yaml(str(cfg_path))
    server.init_server(cfg_path)

    with IndexStore(db_path) as store:
        fix = discover_fixtures(store, suite=work.name)

    failures = 0
    async with Client(server.mcp) as client:
        for tool_name, args in tool_call_matrix(fix):
            result = await client.call_tool(tool_name, args)
            payload = mcp_payload(result)
            if payload.get("error"):
                failures += 1
                print(f"FAIL {simulator} {tool_name}: {payload['error']}")
            else:
                print(f" OK  {simulator} {tool_name}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sim",
        choices=("vcs", "questa", "cadence", "all"),
        default="all",
        help="Simulator artifact fixture to verify",
    )
    args = parser.parse_args()

    simulators = ("vcs", "questa", "cadence") if args.sim == "all" else (args.sim,)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        failures = sum(asyncio.run(verify_simulator(sim, root / sim)) for sim in simulators)

    if failures:
        print(f"{failures} MCP tool call(s) failed")
        return 1
    print("All simulator example MCP tool calls passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
