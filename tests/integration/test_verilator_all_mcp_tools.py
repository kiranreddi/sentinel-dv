"""Exercise all 26 MCP tools against the Verilator counter walkthrough index."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastmcp import Client

from sentinel_dv import server
from sentinel_dv.demo_fixtures import DEMO_AS_OF
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.tools import core
from tests.integration.verilator_mcp_demo import (
    DEMO_DIR,
    assert_tool_ok,
    build_demo_config,
    expected_tool_names,
    index_demo,
    mcp_payload,
    prepare_work_dir,
    verilator_available,
)


@pytest.fixture
def indexed_demo(tmp_path):
    work = prepare_work_dir(tmp_path)
    db = tmp_path / "walkthrough.duckdb"
    stats = index_demo(work, db)
    assert stats["runs"] >= 3, stats
    assert stats["tests"] >= 3, stats
    assert stats["failures"] >= 2, stats
    assert stats["assertions"] >= 2, stats
    assert stats["assertion_failures"] >= 1, stats
    assert stats["coverage"] >= 1, stats
    # Repo demo may index both precomputed *.wave.json and waves/*.vcd
    assert stats["waveforms"] >= 1, stats
    cfg = build_demo_config(work, db)
    suite = work.name if work != DEMO_DIR else "verilator_counter"
    return work, db, cfg, suite, stats


class TestVerilatorAllMcpToolsCore:
    """Call sentinel_dv.tools.core directly (same handlers as MCP server)."""

    def test_all_mcp_tools_core(self, indexed_demo):
        work, db, _cfg, suite, _stats = indexed_demo
        with IndexStore(db) as store:
            runs = core.list_runs(store, suite=suite)
            assert runs["pagination"]["total_items"] >= 3

            pass_run = next(r for r in runs["runs"] if r["status"] == "pass")
            fail_run = next(r for r in runs["runs"] if r["status"] == "fail")

            run_detail = core.get_run_details(store, pass_run["run_id"])
            assert run_detail["run"]["suite"] == suite

            tests = core.list_tests(store, run_id=pass_run["run_id"])
            wave_test = next(
                t for t in tests["tests"] if t["name"] == "counter_tb.test_counter_sim"
            )

            uvm_tests = core.list_tests(store, framework="uvm")
            uvm_test = uvm_tests["tests"][0]
            topo = core.get_test_topology(store, uvm_test["test_id"])
            assert topo["item"].get("uvm") is not None

            test_detail = core.get_test_details(store, wave_test["test_id"])
            assert test_detail["item"]["framework"] == "cocotb"

            axi = core.list_assertions(store, protocol="axi4")
            assert axi["pagination"]["total_items"] >= 1
            assertion_id = axi["assertions"][0]["assertion_id"]
            assertion_detail = core.get_assertion_details(store, assertion_id)
            assert assertion_detail["item"]["name"]

            af = core.list_assertion_failures(
                store, test_id=wave_test["test_id"], include_evidence=True
            )
            assert af["pagination"]["total_items"] >= 1

            cov_list = core.list_coverage(store, run_id=pass_run["run_id"])
            assert cov_list["pagination"]["total_items"] >= 1

            cov_sum = core.get_coverage_summary(store, pass_run["run_id"])
            assert cov_sum["summaries"][0]["metrics"]

            scoreboard = core.list_failures(store, category="scoreboard")
            assert scoreboard["pagination"]["total_items"] >= 1

            cocotb_fail = core.list_failures(
                store, run_id=fail_run["run_id"], include_evidence=True
            )
            assert cocotb_fail["pagination"]["total_items"] >= 1

            reg = core.get_regression_summary(store, suite=suite, window_days=30, as_of=DEMO_AS_OF)
            assert reg["suite"] == suite
            assert len(reg["runs"]) >= 3

            diff = core.compare_runs(store, fail_run["run_id"], pass_run["run_id"])
            assert "new_failures" in diff or "resolved_failures" in diff

            signals = core.wave_signals(store, wave_test["test_id"])
            assert signals["signals"]

            window = core.wave_signals(
                store, wave_test["test_id"], start_time_ns=2000, end_time_ns=3000
            )
            assert window["start_time_ns"] == 2000

            summary = core.wave_summary(store, wave_test["test_id"])
            assert summary["highlights"] is not None


@pytest.mark.skipif(not verilator_available(), reason="Verilator not installed")
def test_index_in_repo_demo_dir(tmp_path):
    """Index demo/verilator_counter in place (paths match published docs)."""
    work = prepare_work_dir(tmp_path, use_repo_demo=True)
    db = tmp_path / "inplace.duckdb"
    stats = index_demo(work, db)
    assert stats["waveforms"] >= 1
    assert stats["runs"] >= 3


@pytest.mark.skipif(not verilator_available(), reason="verilator not available")
def test_all_mcp_tools_via_fastmcp(indexed_demo, tmp_path):
    """Invoke every registered MCP tool through FastMCP (stdio-equivalent in-process)."""

    async def _run():
        work, db, cfg, suite, _stats = indexed_demo
        config_path = tmp_path / "config.yaml"
        cfg.to_yaml(str(config_path))
        server.init_server(config_path)

        async with Client(server.mcp) as client:
            listed = await client.list_tools()
            names = {t.name for t in listed}
            assert names == set(expected_tool_names())

            with IndexStore(db) as store:
                runs = core.list_runs(store, suite=suite)
                pass_run = next(r for r in runs["runs"] if r["status"] == "pass")
                fail_run = next(r for r in runs["runs"] if r["status"] == "fail")
                wave_test = core.list_tests(store, run_id=pass_run["run_id"])["tests"][0]
                uvm_test = core.list_tests(store, framework="uvm")["tests"][0]
                assertion_id = core.list_assertions(store, protocol="axi4")["assertions"][0][
                    "assertion_id"
                ]

            calls: list[tuple[str, dict]] = [
                ("runs.list", {"suite": suite, "page": 1, "page_size": 50}),
                ("runs.get", {"run_id": pass_run["run_id"]}),
                ("runs.submit", {"suite": suite}),
                ("tests.list", {"run_id": pass_run["run_id"], "page": 1, "page_size": 50}),
                ("tests.get", {"test_id": wave_test["test_id"]}),
                ("tests.topology", {"test_id": uvm_test["test_id"]}),
                ("tests.replay", {"test_id": wave_test["test_id"]}),
                ("assertions.list", {"protocol": "axi4", "page": 1, "page_size": 50}),
                ("assertions.get", {"assertion_id": assertion_id}),
                (
                    "assertions.failures",
                    {"test_id": wave_test["test_id"], "include_evidence": True, "page": 1},
                ),
                (
                    "assertions.sva_status",
                    {"run_id": pass_run["run_id"], "page": 1, "page_size": 50},
                ),
                ("assertions.vacuity", {"run_id": pass_run["run_id"], "page": 1, "page_size": 50}),
                ("coverage.list", {"run_id": pass_run["run_id"], "page": 1, "page_size": 50}),
                ("coverage.summary", {"run_id": pass_run["run_id"]}),
                ("coverage.gaps", {"suite": suite, "threshold_pct": 100.0}),
                ("failures.list", {"category": "scoreboard", "include_evidence": True}),
                (
                    "regressions.summary",
                    {"suite": suite, "window_days": 30, "as_of": DEMO_AS_OF},
                ),
                (
                    "runs.diff",
                    {"base_run_id": fail_run["run_id"], "compare_run_id": pass_run["run_id"]},
                ),
                ("sim.status", {"suite": suite}),
                ("wave.signals", {"test_id": wave_test["test_id"]}),
                (
                    "wave.summary",
                    {
                        "test_id": wave_test["test_id"],
                        "start_time_ns": 2000,
                        "end_time_ns": 3000,
                    },
                ),
                # DV Intelligence tools — v2.1.0
                ("coverage.trend", {"suite": suite}),
                ("runs.cross_sim", {}),
                ("tests.cluster", {}),
                ("regression.health", {"suite": suite}),
                ("coverage.advisor", {"suite": suite}),
            ]
            assert len(calls) == len(expected_tool_names())

            for tool_name, arguments in calls:
                result = await client.call_tool(tool_name, arguments)
                payload = mcp_payload(result)
                assert_tool_ok(payload, tool_name)

    asyncio.run(_run())
