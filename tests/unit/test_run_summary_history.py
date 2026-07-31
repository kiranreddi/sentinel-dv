"""Unit tests for runs.summary and tests.history."""

from __future__ import annotations

import pytest

from sentinel_dv.config import SentinelDVConfig, set_config
from sentinel_dv.ids import generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.tools import core
from sentinel_dv.tools.errors import ToolError


@pytest.fixture
def indexed_store(tmp_path):
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(tmp_path)],
            index={"type": "duckdb", "path": str(tmp_path / "summary_history.db")},
        )
    )
    db_path = tmp_path / "summary_history.db"
    store = IndexStore(db_path)
    store.connect()

    run_a, run_a_full = generate_run_id(suite="demo_suite", ci_system="local", ci_build_id="1")
    run_b, run_b_full = generate_run_id(suite="demo_suite", ci_system="local", ci_build_id="2")
    store.insert_run(
        run_id=run_a,
        run_id_full=run_a_full,
        suite="demo_suite",
        created_at="2026-05-28T00:00:00Z",
        status="pass",
    )
    store.insert_run(
        run_id=run_b,
        run_id_full=run_b_full,
        suite="demo_suite",
        created_at="2026-05-29T00:00:00Z",
        status="fail",
    )

    t1, t1_full = generate_test_id(
        run_id_full=run_a_full, framework="cocotb", test_name="tb.test_one"
    )
    t2, t2_full = generate_test_id(
        run_id_full=run_a_full, framework="cocotb", test_name="tb.test_two"
    )
    t3, t3_full = generate_test_id(
        run_id_full=run_b_full, framework="cocotb", test_name="tb.test_one"
    )

    store.insert_test(
        test_id=t1,
        test_id_full=t1_full,
        run_id=run_a,
        framework="cocotb",
        name="tb.test_one",
        status="pass",
        created_at="2026-05-28T00:00:00Z",
        duration_ms=100,
    )
    store.insert_test(
        test_id=t2,
        test_id_full=t2_full,
        run_id=run_a,
        framework="cocotb",
        name="tb.test_two",
        status="fail",
        created_at="2026-05-28T00:01:00Z",
        duration_ms=500,
    )
    store.insert_test(
        test_id=t3,
        test_id_full=t3_full,
        run_id=run_b,
        framework="cocotb",
        name="tb.test_one",
        status="fail",
        created_at="2026-05-29T00:00:00Z",
        duration_ms=200,
    )
    store.insert_failure(
        failure_id="f_demo_001",
        failure_id_full="f_demo_001_full",
        test_id=t2,
        run_id=run_a,
        severity="error",
        category="scoreboard",
        summary="mismatch",
        message="expected 1 got 0",
        tags=["scoreboard"],
        signature_id="sig_demo_001",
    )
    yield {"store": store, "pass_run_id": run_a}
    store.close()


def test_run_summary_counts(indexed_store) -> None:
    store = indexed_store["store"]
    run_id = indexed_store["pass_run_id"]

    payload = core.get_run_summary(store, run_id)
    assert payload["total_tests"] == 2
    assert payload["test_counts"]["pass"] == 1
    assert payload["test_counts"]["fail"] == 1
    assert payload["pass_rate"] == 50.0
    assert payload["failure_events"] == 1
    assert payload["slowest_tests"][0]["name"] == "tb.test_two"


def test_run_summary_not_found(indexed_store) -> None:
    with pytest.raises(ToolError) as exc:
        core.get_run_summary(indexed_store["store"], "r_not_indexed_xyz")
    assert exc.value.code == "NOT_FOUND"


def test_test_history_across_runs(indexed_store) -> None:
    payload = core.get_test_history(
        indexed_store["store"],
        test_name="tb.test_one",
        suite="demo_suite",
        window_days=30,
        as_of="2026-05-30T00:00:00Z",
    )
    assert payload["entries_returned"] == 2
    assert payload["is_flaky"] is True
    assert set(payload["distinct_statuses"]) == {"fail", "pass"}


def test_test_history_requires_name(indexed_store) -> None:
    with pytest.raises(ToolError) as exc:
        core.get_test_history(indexed_store["store"], test_name="  ")
    assert exc.value.code == "INVALID_ARGUMENT"
