"""Unit tests for waveform helpers in tools.core."""

from __future__ import annotations

import pytest

from sentinel_dv.config import SentinelDVConfig, set_config
from sentinel_dv.ids import generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.tools import core
from sentinel_dv.tools.core import _group_highlights, _infer_highlight_category
from sentinel_dv.tools.errors import ToolError


def test_infer_highlight_category_and_groups() -> None:
    assert _infer_highlight_category({"category": "custom"}) == "custom"
    assert _infer_highlight_category({"note": "many toggles in window"}) == "toggle_activity"
    assert _infer_highlight_category({"note": "reset released"}) == "reset_event"
    assert _infer_highlight_category({"note": "fsm entered IDLE"}) == "fsm"
    grouped = _group_highlights(
        [
            {"note": "toggle burst", "signal": "clk"},
            {"note": "reset released", "signal": "rst"},
        ]
    )
    assert "toggle_activity" in grouped
    assert "reset_event" in grouped


def test_wave_summary_include_signals_and_signal_groups(tmp_path) -> None:
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(tmp_path)],
            index={"type": "duckdb", "path": str(tmp_path / "wave.db")},
            security={"max_wave_signals": 2},
        )
    )
    store = IndexStore(tmp_path / "wave.db")
    store.connect()
    try:
        run_id, run_full = generate_run_id(suite="wave", ci_system="local", ci_build_id="1")
        test_id, test_full = generate_test_id(
            run_id_full=run_full, framework="cocotb", test_name="tb"
        )
        store.insert_run(run_id, run_full, "wave", "2026-05-20T10:00:00Z", "pass")
        store.insert_test(
            test_id, test_full, run_id, "cocotb", "tb", "pass", "2026-05-20T10:01:00Z"
        )
        summary = {
            "format": "precomputed",
            "end_time_ns": 5000,
            "highlights": [
                {"time_ns": 1000, "signal": "rst", "note": "reset released"},
                {"time_ns": 2000, "signal": "clk", "note": "toggle burst"},
            ],
            "signal_groups": [
                {
                    "name": "dut",
                    "signals": [
                        {"name": "clk", "toggles": 10},
                        {"name": "rst", "toggles": 1},
                        {"name": "count", "toggles": 4},
                    ],
                }
            ],
        }
        store.insert_waveform_summary(test_id, summary, "waves/tb.wave.json")

        result = core.wave_summary(store, test_id, include_signals=True)
        assert result["highlight_groups"]["reset_event"]
        assert result["signal_groups"][0]["name"] == "dut"
        assert len(result["signals"]) == 2
        assert result["truncated"] is True

        windowed = core.wave_summary(store, test_id, start_time_ns=1500, end_time_ns=2500)
        assert len(windowed["highlights"]) == 1
        assert windowed["metadata"]["window"]["start_time_ns"] == 1500
    finally:
        store.close()


def test_wave_invalid_time_window(tmp_path) -> None:
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(tmp_path)],
            index={"type": "duckdb", "path": str(tmp_path / "w2.db")},
        )
    )
    store = IndexStore(tmp_path / "w2.db")
    store.connect()
    try:
        run_id, run_full = generate_run_id(suite="w", ci_system="x", ci_build_id="1")
        test_id, test_full = generate_test_id(
            run_id_full=run_full, framework="cocotb", test_name="t"
        )
        store.insert_run(run_id, run_full, "w", "2026-05-20T10:00:00Z", "pass")
        store.insert_test(test_id, test_full, run_id, "cocotb", "t", "pass", "2026-05-20T10:01:00Z")
        store.insert_waveform_summary(
            test_id,
            {"format": "precomputed", "end_time_ns": 100, "signals": []},
            "x.wave.json",
        )
        with pytest.raises(ToolError) as exc:
            core.wave_signals(store, test_id, start_time_ns=500, end_time_ns=None)
        assert exc.value.code == "INVALID_ARGUMENT"
    finally:
        store.close()
