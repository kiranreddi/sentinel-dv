"""Unit tests for MCP tool implementations."""

from __future__ import annotations

import pytest

from sentinel_dv.config import SentinelDVConfig, set_config
from sentinel_dv.ids import generate_failure_id, generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.tools import core
from sentinel_dv.tools.errors import ToolError


@pytest.fixture
def indexed_store(tmp_path):
    """Store with one run, two tests, and a failure."""
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(tmp_path)],
            index={"type": "duckdb", "path": str(tmp_path / "mcp_test.db")},
        )
    )
    db_path = tmp_path / "mcp_test.db"
    store = IndexStore(db_path)
    store.connect()

    run_id, run_id_full = generate_run_id(suite="nightly", ci_system="github", ci_build_id="42")
    store.insert_run(
        run_id=run_id,
        run_id_full=run_id_full,
        suite="nightly",
        created_at="2026-05-20T10:00:00Z",
        status="fail",
        ci_system="github",
    )

    pass_id, pass_full = generate_test_id(
        run_id_full=run_id_full, framework="uvm", test_name="passing"
    )
    fail_id, fail_full = generate_test_id(
        run_id_full=run_id_full, framework="uvm", test_name="failing"
    )

    store.insert_test(
        test_id=pass_id,
        test_id_full=pass_full,
        run_id=run_id,
        framework="uvm",
        name="passing",
        status="pass",
        created_at="2026-05-20T10:01:00Z",
    )
    store.insert_test(
        test_id=fail_id,
        test_id_full=fail_full,
        run_id=run_id,
        framework="uvm",
        name="failing",
        status="fail",
        created_at="2026-05-20T10:02:00Z",
    )

    failure_id, failure_id_full = generate_failure_id(
        test_id_full=fail_full,
        severity="error",
        category="scoreboard",
        summary="data mismatch",
    )
    store.insert_failure(
        failure_id=failure_id,
        failure_id_full=failure_id_full,
        test_id=fail_id,
        run_id=run_id,
        severity="error",
        category="scoreboard",
        summary="data mismatch",
        message="expected 1 got 0",
        tags=["scoreboard"],
        signature_id="sig_scoreboard",
        evidence_refs=[
            {
                "kind": "log",
                "path": "demo/failing.log",
                "span": {"start_line": 10, "end_line": 12},
                "extract": "expected 1 got 0",
            }
        ],
    )

    store.insert_topology(fail_id, {"components": [{"name": "env", "type": "uvm_env"}]})

    yield store
    store.close()


class TestMcpTools:
    def test_list_runs_returns_indexed_run(self, indexed_store):
        result = core.list_runs(indexed_store, suite="nightly")
        assert result["schema_version"] == "1.0.0"
        assert result["pagination"]["total_items"] == 1
        assert result["runs"][0]["suite"] == "nightly"
        assert result["runs"][0]["failed_tests"] == 1

    def test_get_run_not_found(self, indexed_store):
        with pytest.raises(ToolError) as exc:
            core.get_run_details(indexed_store, "r_notindatabase")
        assert exc.value.code == "NOT_FOUND"

    def test_list_tests_filter_by_status(self, indexed_store):
        result = core.list_tests(indexed_store, status="fail")
        assert result["pagination"]["total_items"] == 1
        assert result["tests"][0]["name"] == "failing"

    def test_find_test_by_name_matches_substrings(self, indexed_store):
        result = indexed_store.find_test_by_name("ail")
        assert result is not None
        assert result["name"] in {"failing", "passing"}

    def test_list_failures_include_evidence(self, indexed_store):
        result = core.list_failures(indexed_store, include_evidence=True)
        assert result["pagination"]["total_items"] == 1
        assert result["failures"][0]["evidence"][0]["path"] == "demo/failing.log"

    def test_get_test_topology(self, indexed_store):
        test_id = core.list_tests(indexed_store, status="fail")["tests"][0]["test_id"]
        topo = core.get_test_topology(indexed_store, test_id)
        assert topo["item"]["components"][0]["name"] == "env"

    def test_regression_summary(self, indexed_store):
        summary = core.get_regression_summary(indexed_store, suite="nightly", window_days=30)
        assert summary["pass_rate"] == 50.0
        assert summary["top_signatures"][0]["signature_id"] == "sig_scoreboard"

    def test_compare_runs_detects_new_failure_signature(self, indexed_store):
        run_id = core.list_runs(indexed_store)["runs"][0]["run_id"]
        run2_id, run2_full = generate_run_id(suite="nightly", ci_system="github", ci_build_id="43")
        indexed_store.insert_run(
            run_id=run2_id,
            run_id_full=run2_full,
            suite="nightly",
            created_at="2026-05-21T10:00:00Z",
            status="pass",
        )
        diff = core.compare_runs(indexed_store, run_id, run2_id)
        assert diff["resolved_failures"][0]["signature_id"] == "sig_scoreboard"

    def test_invalid_page_size(self, indexed_store):
        with pytest.raises(ValueError, match="page_size"):
            core.list_runs(indexed_store, page_size=5000)


def test_coverage_summary_limit_exceeded(tmp_path):
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(tmp_path)],
            index={"type": "duckdb", "path": str(tmp_path / "limit_test.db")},
            security={"max_coverage_metrics": 1},
        )
    )
    db_path = tmp_path / "limit_test.db"
    store = IndexStore(db_path)
    store.connect()
    try:
        run_id, run_id_full = generate_run_id(
            suite="nightly", ci_system="github", ci_build_id="coverage-limit"
        )
        store.insert_run(
            run_id=run_id,
            run_id_full=run_id_full,
            suite="nightly",
            created_at="2026-05-20T10:00:00Z",
            status="pass",
        )
        store.insert_coverage_summary(
            run_id=run_id,
            kind="functional",
            metrics=[{"name": "line", "scope": "top", "covered": 0.8}],
        )
        store.insert_coverage_summary(
            run_id=run_id,
            kind="assertion",
            metrics=[{"name": "assert", "scope": "top", "covered": 0.9}],
        )

        with pytest.raises(ToolError) as exc:
            core.get_coverage_summary(store, run_id)
        assert exc.value.code == "LIMIT_EXCEEDED"
    finally:
        store.close()


def test_assertion_failures_include_evidence(tmp_path):
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(tmp_path)],
            index={"type": "duckdb", "path": str(tmp_path / "assert_fail.db")},
        )
    )
    db_path = tmp_path / "assert_fail.db"
    store = IndexStore(db_path)
    store.connect()
    try:
        run_id, run_id_full = generate_run_id(
            suite="nightly", ci_system="github", ci_build_id="assert-fail"
        )
        store.insert_run(
            run_id=run_id,
            run_id_full=run_id_full,
            suite="nightly",
            created_at="2026-05-20T10:00:00Z",
            status="fail",
        )
        test_id, test_id_full = generate_test_id(
            run_id_full=run_id_full, framework="uvm", test_name="assert_test"
        )
        store.insert_test(
            test_id=test_id,
            test_id_full=test_id_full,
            run_id=run_id,
            framework="uvm",
            name="assert_test",
            status="fail",
            created_at="2026-05-20T10:01:00Z",
        )
        store.insert_assertion(
            assertion_id="a_assert",
            assertion_id_full="full_assert",
            language="sva",
            name="assert_name",
            scope="tb",
            file="tb/assert.sv",
            line=12,
            signals=[],
        )
        store.insert_assertion_failure(
            assertion_id="a_assert",
            test_id=test_id,
            run_id=run_id,
            message="assertion failed",
            time_ns=100,
            evidence_refs=[
                {
                    "kind": "log",
                    "path": "logs/sim.log",
                    "span": {"start_line": 99, "end_line": 101},
                    "extract": "assertion failed",
                }
            ],
        )
        result = core.list_assertion_failures(store, include_evidence=True)
        assert result["pagination"]["total_items"] == 1
        assert result["assertion_failures"][0]["evidence"][0]["path"] == "logs/sim.log"
    finally:
        store.close()
