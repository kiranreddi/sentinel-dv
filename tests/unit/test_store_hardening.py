"""Store security and regression-window hardening tests."""

from __future__ import annotations

import pytest

from sentinel_dv.config import resolve_config
from sentinel_dv.ids import generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore, _iso_to_epoch_ms


def test_iso_to_epoch_ms_parses_z_suffix() -> None:
    assert _iso_to_epoch_ms("2026-05-20T10:00:00Z") == 1_779_271_200_000
    assert _iso_to_epoch_ms("not-a-date") is None


def test_query_tests_rejects_unknown_sort_column(tmp_path) -> None:
    store = IndexStore(tmp_path / "sort.db")
    store.connect()
    with pytest.raises(ValueError, match="Invalid sort_by"):
        store.query_tests(sort_by="'; DROP TABLE tests; --")
    store.close()


def test_regression_summary_uses_epoch_window(tmp_path) -> None:
    store = IndexStore(tmp_path / "reg.db")
    store.connect()

    run_id, run_full = generate_run_id(suite="nightly", ci_system="local", ci_build_id="1")
    store.insert_run(
        run_id=run_id,
        run_id_full=run_full,
        suite="nightly",
        created_at="2020-01-01T00:00:00Z",
        status="pass",
    )
    run2_id, run2_full = generate_run_id(suite="nightly", ci_system="local", ci_build_id="2")
    store.insert_run(
        run_id=run2_id,
        run_id_full=run2_full,
        suite="nightly",
        created_at="2026-05-20T10:00:00Z",
        status="pass",
    )

    summary = store.regression_summary(
        suite="nightly",
        window_days=30,
        as_of="2026-05-21T00:00:00Z",
    )
    assert summary["runs"]
    assert len(summary["runs"]) == 1
    assert summary["runs"][0]["run_id"] == run2_id
    store.close()


def test_assertion_failure_ids_are_monotonic(tmp_path) -> None:
    store = IndexStore(tmp_path / "ids.db")
    store.connect()
    run_id, run_full = generate_run_id(suite="s", ci_system="x", ci_build_id="1")
    test_id, test_full = generate_test_id(run_id_full=run_full, framework="uvm", test_name="t")
    store.insert_run(run_id, run_full, "s", "2026-05-20T10:00:00Z", "pass")
    store.insert_test(test_id, test_full, run_id, "uvm", "t", "pass", "2026-05-20T10:01:00Z")
    store.insert_assertion(
        assertion_id="a1",
        assertion_id_full="a1_full",
        language="sv",
        name="assert_one",
        scope="tb",
        file="tb.sv",
        line=1,
        signals=[],
        tags=[],
    )
    store.insert_assertion_failure("a1", test_id, run_id, "first")
    store.insert_assertion_failure("a1", test_id, run_id, "second")
    rows = store._conn.execute("SELECT id FROM assertion_failures ORDER BY id").fetchall()
    assert [r[0] for r in rows] == [1, 2]
    store.close()


def test_resolve_config_does_not_default_to_demo(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENTINEL_DV_CONFIG", raising=False)
    with pytest.raises(RuntimeError, match="does not silently default"):
        resolve_config(None)
