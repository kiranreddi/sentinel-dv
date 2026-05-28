#!/usr/bin/env python3
"""
Verify all 15 Sentinel DV MCP tools.

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
from sentinel_dv.indexing.store import IndexStore  # noqa: E402
from sentinel_dv.tools import core  # noqa: E402
from tests.integration.multi_project_demo import (  # noqa: E402
    DEMO_ROOT,
    build_multi_config,
    discover_fixtures,
    index_demo_tree,
    tool_call_matrix,
)
from tests.integration.verilator_mcp_demo import (  # noqa: E402
    DEMO_DIR,
    assert_tool_ok,
    build_demo_config,
    expected_tool_names,
    index_demo,
    mcp_payload,
    prepare_work_dir,
    verilator_available,
)


def _print_ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _print_fail(msg: str) -> None:
    print(f"FAIL  {msg}", file=sys.stderr)


async def _run_single_project_mcp(config_path: Path, db_path: Path, suite: str) -> int:
    server.init_server(config_path)
    failures = 0

    with IndexStore(db_path) as store:
        runs = core.list_runs(store, suite=suite)
        if runs["pagination"]["total_items"] < 3:
            _print_fail(f"expected >=3 runs for suite={suite!r}, got {runs['pagination']}")
            return 1

        pass_run = next(r for r in runs["runs"] if r["status"] == "pass")
        fail_run = next(r for r in runs["runs"] if r["status"] == "fail")
        wave_test = core.list_tests(store, run_id=pass_run["run_id"])["tests"][0]
        uvm_test = core.list_tests(store, framework="uvm")["tests"][0]
        assertion_id = core.list_assertions(store, protocol="axi4")["assertions"][0]["assertion_id"]

    calls: list[tuple[str, dict]] = [
        ("runs.list", {"suite": suite, "page": 1, "page_size": 50}),
        ("runs.get", {"run_id": pass_run["run_id"]}),
        ("tests.list", {"run_id": pass_run["run_id"]}),
        ("tests.get", {"test_id": wave_test["test_id"]}),
        ("tests.topology", {"test_id": uvm_test["test_id"]}),
        ("assertions.list", {"protocol": "axi4"}),
        ("assertions.get", {"assertion_id": assertion_id}),
        ("assertions.failures", {"test_id": wave_test["test_id"], "include_evidence": True}),
        ("coverage.list", {"run_id": pass_run["run_id"]}),
        ("coverage.summary", {"run_id": pass_run["run_id"]}),
        ("failures.list", {"category": "scoreboard"}),
        (
            "regressions.summary",
            {"suite": suite, "window_days": 30, "as_of": "2026-05-28T12:00:00Z"},
        ),
        ("runs.diff", {"base_run_id": fail_run["run_id"], "compare_run_id": pass_run["run_id"]}),
        ("wave.signals", {"test_id": wave_test["test_id"]}),
        (
            "wave.summary",
            {"test_id": wave_test["test_id"], "start_time_ns": 2000, "end_time_ns": 3000},
        ),
    ]

    async with Client(server.mcp) as client:
        for tool_name, arguments in calls:
            result = await client.call_tool(tool_name, arguments)
            payload = mcp_payload(result)
            if payload.get("error"):
                _print_fail(f"{tool_name}: {payload['error']}")
                failures += 1
            else:
                _print_ok(tool_name)
    return failures


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
            if payload.get("error"):
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
        help="Index entire demo/ tree (UVM + cocotb + Verilator projects)",
    )
    parser.add_argument(
        "--demo-dir",
        type=Path,
        default=DEMO_DIR,
        help="Single-project Verilator demo directory",
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

        if args.multi:
            stats = index_demo_tree(DEMO_ROOT, db)
            print("Index stats:", stats)
            cfg = build_multi_config(DEMO_ROOT, db)
            config_path = tmp_path / "config.yaml"
            cfg.to_yaml(str(config_path))
            failures = asyncio.run(_run_multi_project_mcp(config_path, db))
        else:
            demo_dir = args.demo_dir.resolve()
            if not verilator_available():
                vcd = demo_dir / "waves" / "test_counter_sim.vcd"
                if not vcd.is_file():
                    _print_fail("Verilator not on PATH and no prebuilt VCD")
                    return 1
            if args.in_place:
                from tests.integration.verilator_mcp_demo import ensure_vcd

                ensure_vcd(demo_dir)
                work = demo_dir
            else:
                work = prepare_work_dir(tmp_path)
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
