"""Direct tests for MCP server tool handlers (server.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import sentinel_dv.server as server
from sentinel_dv.config import SentinelDVConfig
from sentinel_dv.ids import generate_failure_id, generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore


@pytest.fixture
def server_indexed(tmp_path: Path):
    """Populated DuckDB + config.yaml for init_server."""
    db_path = tmp_path / "handlers.db"
    artifact = tmp_path / "artifacts"
    artifact.mkdir()
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        f"artifact_roots: [{artifact!s}]\nindex:\n  type: duckdb\n  path: {db_path!s}\n",
        encoding="utf-8",
    )

    store = IndexStore(db_path)
    store.connect()
    run_id, run_full = generate_run_id(suite="nightly", ci_system="github", ci_build_id="99")
    store.insert_run(
        run_id, run_full, "nightly", "2026-05-20T10:00:00Z", "fail", ci_system="github"
    )
    pass_id, pass_full = generate_test_id(
        run_id_full=run_full, framework="cocotb", test_name="passing"
    )
    fail_id, fail_full = generate_test_id(
        run_id_full=run_full, framework="uvm", test_name="failing"
    )
    store.insert_test(
        pass_id, pass_full, run_id, "cocotb", "passing", "pass", "2026-05-20T10:01:00Z"
    )
    store.insert_test(
        fail_id, fail_full, run_id, "uvm", "failing", "fail", "2026-05-20T10:02:00Z"
    )
    store.insert_topology(fail_id, {"components": [{"name": "env", "type": "uvm_env"}]})
    failure_id, failure_full = generate_failure_id(
        test_id_full=fail_full,
        severity="error",
        category="scoreboard",
        summary="mismatch",
    )
    store.insert_failure(
        failure_id,
        failure_full,
        fail_id,
        run_id,
        "error",
        "scoreboard",
        "mismatch",
        "expected 1 got 0",
        tags=["scoreboard"],
        signature_id="sig_scoreboard",
    )
    store.insert_assertion(
        assertion_id="a_axi",
        assertion_id_full="full_axi",
        language="sva",
        name="axi_valid",
        scope="tb",
        file="tb.sv",
        line=1,
        signals=[],
        intent_protocol="axi4",
        tags=["axi4"],
    )
    store.insert_assertion_failure(
        "a_axi", pass_id, run_id, "assert fail", time_ns=100
    )
    store.insert_coverage_summary(
        run_id,
        "functional",
        [{"name": "line", "scope": "top", "covered": 0.9}],
        test_id=pass_id,
    )
    store.insert_waveform_summary(
        pass_id,
        {
            "format": "precomputed",
            "end_time_ns": 1000,
            "signals": [{"name": "clk", "toggles": 5}],
            "highlights": [{"time_ns": 500, "signal": "clk", "note": "toggle"}],
        },
        "waves/pass.wave.json",
    )
    store.close()

    server.init_server(cfg_path)
    yield {
        "run_id": run_id,
        "pass_id": pass_id,
        "fail_id": fail_id,
        "assertion_id": "a_axi",
        "cfg_path": cfg_path,
    }
    if server._store is not None:
        server._store.close()
        server._store = None


def test_server_handlers_smoke(server_indexed: dict) -> None:
    """Call handlers with explicit args (Field() defaults are for FastMCP only)."""
    run_id = server_indexed["run_id"]
    pass_id = server_indexed["pass_id"]
    fail_id = server_indexed["fail_id"]
    assertion_id = server_indexed["assertion_id"]

    runs = server.runs_list(
        suite="nightly", status=None, ci_system=None, page=1, page_size=10
    )
    assert "runs" in runs
    assert runs["runs"][0]["run_id"] == run_id

    assert "run" in server.runs_get(run_id=run_id)
    assert (
        server.tests_list(
            run_id=run_id,
            framework=None,
            status=None,
            name_pattern=None,
            page=1,
            page_size=10,
        )["pagination"]["total_items"]
        == 2
    )
    assert server.tests_get(test_id=pass_id)["item"]["name"] == "passing"
    assert server.tests_topology(test_id=fail_id)["item"]["components"]
    assert (
        server.assertions_list(
            scope=None,
            name_pattern=None,
            protocol="axi4",
            tag=None,
            page=1,
            page_size=50,
        )["assertions"]
    )
    assert server.assertions_get(assertion_id=assertion_id)["item"]["name"] == "axi_valid"
    assert server.assertions_failures(
        run_id=None,
        test_id=pass_id,
        assertion_id=None,
        start_time_ns=None,
        end_time_ns=None,
        include_evidence=False,
        page=1,
        page_size=50,
    )["assertion_failures"]
    assert server.failures_list(
        test_id=None,
        run_id=None,
        category="scoreboard",
        severity=None,
        tags_any=None,
        include_evidence=False,
        page=1,
        page_size=50,
    )["failures"]
    assert server.coverage_list(run_id=run_id, kind=None, page=1, page_size=50)["coverage"]
    assert server.coverage_summary(run_id=run_id, kind=None, include_evidence=False)["summaries"]
    assert (
        server.regressions_summary(suite="nightly", window_days=30, as_of=None)["pass_rate"]
        >= 0
    )
    assert server.runs_diff(base_run_id=run_id, compare_run_id=run_id)["test_changes"] is not None
    assert server.wave_signals(
        test_id=pass_id, start_time_ns=None, end_time_ns=None
    )["signals"]
    summary = server.wave_summary(
        test_id=pass_id,
        start_time_ns=None,
        end_time_ns=None,
        include_signals=True,
    )
    assert summary["highlight_groups"]
    assert summary["signals"]


def test_server_tool_wrapper_invalid_argument(server_indexed: dict) -> None:
    result = server.runs_list(
        suite=None, status=None, ci_system=None, page=1, page_size=5000
    )
    assert result["error"]["code"] == "INVALID_ARGUMENT"


def test_server_tool_wrapper_not_found(server_indexed: dict) -> None:
    result = server.runs_get(run_id="r_notindatabase")
    assert result["error"]["code"] == "NOT_FOUND"


def test_server_tool_wrapper_topology_not_indexed(server_indexed: dict) -> None:
    result = server.tests_topology(test_id=server_indexed["pass_id"])
    assert result["error"]["code"] == "TOPOLOGY_NOT_INDEXED"


def test_server_main_fails_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server.mcp, "run", MagicMock())
    with pytest.raises(SystemExit) as exc:
        server.main(["--config", "/nonexistent/config.yaml"])
    assert exc.value.code == 1
    server.mcp.run.assert_not_called()


def test_server_main_starts_with_config(server_indexed: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server.mcp, "run", MagicMock())
    server.main(["--config", str(server_indexed["cfg_path"])])
    server.mcp.run.assert_called_once()


def test_get_store_lazy_connects(server_indexed: dict) -> None:
    if server._store is not None:
        server._store.close()
        server._store = None
    store = server.get_store()
    assert store.count_runs() >= 1
    store.close()
    server._store = None
