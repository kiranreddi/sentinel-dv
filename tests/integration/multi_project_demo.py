"""Helpers for multi-project demo indexing and MCP verification."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fastmcp import Client

from sentinel_dv import server
from sentinel_dv.config import AdaptersConfig, SentinelDVConfig, set_config
from sentinel_dv.indexing.indexer import ArtifactIndexer
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.registry import TOOL_NAMES
from sentinel_dv.tools import core
from tests.integration.verilator_mcp_demo import assert_tool_ok, ensure_vcd, mcp_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_ROOT = REPO_ROOT / "demo"
VERILATOR_DIR = DEMO_ROOT / "verilator_counter"

# Suite names match artifact parent directories (indexer convention).
EXPECTED_SUITES = frozenset(
    {
        "verilator_counter",
        "axi_burst",
        "apb_register",
        "alu_core",
        "fifo_sync",
        "counter_block",
    }
)


@dataclass(frozen=True)
class ProjectFixtures:
    """Indexed entity IDs discovered after indexing demo/."""

    suites: frozenset[str]
    pass_run_id: str
    fail_run_id: str
    cocotb_wave_test_id: str
    uvm_topology_test_id: str
    assertion_id: str
    axi_suite: str = "axi_burst"
    verilator_suite: str = "verilator_counter"


def build_multi_config(demo_root: Path, db_path: Path) -> SentinelDVConfig:
    return SentinelDVConfig(
        artifact_roots=[str(demo_root.resolve())],
        index={"type": "duckdb", "path": str(db_path)},
        adapters=AdaptersConfig(
            uvm=True,
            cocotb=True,
            assertions=True,
            coverage=True,
            waveform_summary=True,
        ),
    )


def index_demo_tree(demo_root: Path, db_path: Path) -> dict:
    ensure_vcd(VERILATOR_DIR)
    cfg = build_multi_config(demo_root, db_path)
    set_config(cfg)
    return ArtifactIndexer([str(demo_root.resolve())], db_path, config=cfg).index_all()


def discover_fixtures(store: IndexStore) -> ProjectFixtures:
    """Collect stable handles for cross-project MCP calls."""
    all_runs, _ = store.query_runs(page_size=500)
    suites = frozenset(r["suite"] for r in all_runs)
    missing = EXPECTED_SUITES - suites
    if missing:
        raise AssertionError(f"Missing expected suites after index: {sorted(missing)}")

    verilator_runs = [r for r in all_runs if r["suite"] == "verilator_counter"]
    pass_run = next(r for r in verilator_runs if r["status"] == "pass")
    fail_run = next(r for r in all_runs if r["status"] == "fail" and r["run_id"] != pass_run["run_id"])

    for pattern in ("test_alu_add", "test_fifo_push_pop", "test_increment", "test_counter_sim"):
        wave_tests, _ = store.query_tests(name_pattern=pattern, page_size=5)
        if wave_tests:
            cocotb_wave = wave_tests[0]
            break
    else:
        raise AssertionError("No cocotb test with indexed waveform found")

    uvm_tests, _ = store.query_tests(framework="uvm", page_size=50)
    uvm_with_topo = next(
        (t for t in uvm_tests if t["name"] in ("test_axi_burst", "test_counter_sim")),
        uvm_tests[0],
    )

    assertions, _ = store.query_assertions(page_size=10)
    if not assertions:
        raise AssertionError("No assertions indexed (expected verilator_counter bundle)")

    return ProjectFixtures(
        suites=suites,
        pass_run_id=pass_run["run_id"],
        fail_run_id=fail_run["run_id"],
        cocotb_wave_test_id=cocotb_wave["test_id"],
        uvm_topology_test_id=uvm_with_topo["test_id"],
        assertion_id=assertions[0]["assertion_id"],
    )


def tool_call_matrix(fix: ProjectFixtures) -> list[tuple[str, dict[str, Any]]]:
    """Exactly one MCP invocation per registered tool."""
    return [
        ("runs.list", {"page": 1, "page_size": 200}),
        ("runs.get", {"run_id": fix.pass_run_id}),
        ("tests.list", {"framework": "cocotb", "page": 1, "page_size": 100}),
        ("tests.get", {"test_id": fix.cocotb_wave_test_id}),
        ("tests.topology", {"test_id": fix.uvm_topology_test_id}),
        ("assertions.list", {"protocol": "axi4", "page": 1, "page_size": 50}),
        ("assertions.get", {"assertion_id": fix.assertion_id}),
        ("assertions.failures", {"include_evidence": True, "page": 1, "page_size": 50}),
        ("coverage.list", {"run_id": fix.pass_run_id, "page": 1, "page_size": 50}),
        ("coverage.summary", {"run_id": fix.pass_run_id}),
        ("failures.list", {"category": "scoreboard", "page": 1, "page_size": 50}),
        (
            "regressions.summary",
            {"suite": fix.axi_suite, "window_days": 30, "as_of": "2026-05-28T12:00:00Z"},
        ),
        ("runs.diff", {"base_run_id": fix.fail_run_id, "compare_run_id": fix.pass_run_id}),
        ("wave.signals", {"test_id": fix.cocotb_wave_test_id}),
        (
            "wave.summary",
            {
                "test_id": fix.cocotb_wave_test_id,
                "start_time_ns": 1000,
                "end_time_ns": 25000,
            },
        ),
    ]


def invoke_core_tool(store: IndexStore, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    dispatch: dict[str, Callable[..., dict[str, Any]]] = {
        "runs.list": lambda: core.list_runs(store, **args),
        "runs.get": lambda: core.get_run_details(store, args["run_id"]),
        "tests.list": lambda: core.list_tests(store, **args),
        "tests.get": lambda: core.get_test_details(store, args["test_id"]),
        "tests.topology": lambda: core.get_test_topology(store, args["test_id"]),
        "assertions.list": lambda: core.list_assertions(store, **args),
        "assertions.get": lambda: core.get_assertion_details(store, args["assertion_id"]),
        "assertions.failures": lambda: core.list_assertion_failures(store, **args),
        "coverage.list": lambda: core.list_coverage(store, **args),
        "coverage.summary": lambda: core.get_coverage_summary(store, args["run_id"]),
        "failures.list": lambda: core.list_failures(store, **args),
        "regressions.summary": lambda: core.get_regression_summary(store, **args),
        "runs.diff": lambda: core.compare_runs(
            store, args["base_run_id"], args["compare_run_id"]
        ),
        "wave.signals": lambda: core.wave_signals(store, args["test_id"]),
        "wave.summary": lambda: core.wave_summary(store, **args),
    }
    return dispatch[tool_name]()


def verify_core_tools(store: IndexStore, fix: ProjectFixtures) -> None:
    """Exercise core handlers with multi-project assertions."""
    all_runs = core.list_runs(store, page_size=200)
    assert all_runs["pagination"]["total_items"] >= 8, all_runs["pagination"]

    for suite in ("axi_burst", "apb_register", "alu_core", "fifo_sync", "counter_block"):
        filtered = core.list_runs(store, suite=suite)
        assert filtered["pagination"]["total_items"] >= 1, suite

    uvm_all = core.list_tests(store, framework="uvm", page_size=50)
    uvm_names = {t["name"] for t in uvm_all["tests"]}
    assert {"test_axi_burst", "test_apb_register", "test_counter_sim"} <= uvm_names

    cocotb_all = core.list_tests(store, framework="cocotb", page_size=100)
    assert cocotb_all["pagination"]["total_items"] >= 6

    assertion_fails = core.list_failures(store, category="assertion", page_size=50)
    assert assertion_fails["pagination"]["total_items"] >= 1

    for tool_name, args in tool_call_matrix(fix):
        result = invoke_core_tool(store, tool_name, args)
        if result.get("error"):
            raise AssertionError(f"{tool_name} failed: {result['error']}")

    verilator_reg = core.get_regression_summary(
        store, suite=fix.verilator_suite, window_days=30, as_of="2026-05-28T12:00:00Z"
    )
    assert len(verilator_reg["runs"]) >= 2


async def verify_mcp_tools(config_path: Path, fix: ProjectFixtures) -> None:
    server.init_server(config_path)
    async with Client(server.mcp) as client:
        listed = await client.list_tools()
        assert {t.name for t in listed} == set(TOOL_NAMES)

        matrix = tool_call_matrix(fix)
        assert len(matrix) == len(TOOL_NAMES)

        for tool_name, arguments in matrix:
            result = await client.call_tool(tool_name, arguments)
            assert_tool_ok(mcp_payload(result), tool_name)


def run_mcp_verification(config_path: Path, fix: ProjectFixtures) -> None:
    asyncio.run(verify_mcp_tools(config_path, fix))
