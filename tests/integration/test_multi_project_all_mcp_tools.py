"""Rigorous MCP verification over multiple demo projects (UVM, cocotb, Verilator)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_dv.indexing.store import IndexStore
from tests.integration.multi_project_demo import (
    DEMO_ROOT,
    EXPECTED_SUITES,
    discover_fixtures,
    index_demo_tree,
    run_mcp_verification,
    verify_core_tools,
)


@pytest.fixture(scope="module")
def multi_index(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("multi_demo")
    db = tmp / "multi.duckdb"
    stats = index_demo_tree(DEMO_ROOT, db)
    cfg_path = tmp / "config.yaml"
    from tests.integration.multi_project_demo import build_multi_config

    build_multi_config(DEMO_ROOT, db).to_yaml(str(cfg_path))
    return db, cfg_path, stats


class TestMultiProjectIndex:
    def test_index_covers_all_projects(self, multi_index):
        _db, _cfg, stats = multi_index
        assert stats["runs"] >= 8, stats
        assert stats["tests"] >= 10, stats
        assert stats["failures"] >= 5, stats
        assert stats["waveforms"] >= 4, stats
        assert stats["assertions"] >= 2, stats
        assert stats["coverage"] >= 1, stats

    def test_expected_suites_present(self, multi_index):
        db, _cfg, _stats = multi_index
        with IndexStore(db) as store:
            runs, _ = store.query_runs(page_size=200)
            suites = {r["suite"] for r in runs}
        assert EXPECTED_SUITES <= suites


class TestMultiProjectCoreTools:
    def test_all_tools_across_projects(self, multi_index):
        db, _cfg, _stats = multi_index
        with IndexStore(db) as store:
            fix = discover_fixtures(store)
            verify_core_tools(store, fix)


class TestMultiProjectMcp:
    def test_fastmcp_all_fifteen_tools(self, multi_index):
        db, cfg_path, _stats = multi_index
        with IndexStore(db) as store:
            fix = discover_fixtures(store)
        run_mcp_verification(cfg_path, fix)


def test_per_suite_regression_summary(multi_index):
    db, _cfg, _stats = multi_index
    from sentinel_dv.tools import core

    with IndexStore(db) as store:
        for suite in ("axi_burst", "apb_register", "alu_core", "verilator_counter"):
            summary = core.get_regression_summary(
                store, suite=suite, window_days=30, as_of="2026-05-28T12:00:00Z"
            )
            assert summary["suite"] == suite
            assert summary["runs"], f"no runs for {suite}"


def test_waveforms_per_cocotb_project(multi_index):
    db, _cfg, _stats = multi_index
    from sentinel_dv.tools import core

    with IndexStore(db) as store:
        for pattern in ("test_alu_add", "test_fifo_push_pop", "test_increment", "test_counter_sim"):
            tests, total = store.query_tests(name_pattern=pattern, page_size=5)
            assert total >= 1, pattern
            wf = core.wave_signals(store, tests[0]["test_id"])
            assert wf["signals"], pattern
