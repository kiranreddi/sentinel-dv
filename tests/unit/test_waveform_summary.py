"""Tests for waveform summary adapter and MCP tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_dv.adapters.waveform_summary import WaveformSummaryParser
from sentinel_dv.config import AdaptersConfig, SentinelDVConfig, set_config
from sentinel_dv.ids import generate_run_id, generate_test_id
from sentinel_dv.indexing.indexer import ArtifactIndexer
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.tools import core
from sentinel_dv.tools.errors import ToolError


@pytest.fixture
def waveform_json(tmp_path: Path) -> Path:
    path = tmp_path / "test_increment.wave.json"
    path.write_text(
        """
{
  "test_name": "test_increment",
  "framework": "cocotb",
  "format": "precomputed",
  "end_time_ns": 1000,
  "signals": [
    {"name": "clk", "toggles": 10, "last_value": "1"}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    return path


def test_parser_normalizes_flat_signals(waveform_json: Path) -> None:
    parsed = WaveformSummaryParser().parse(waveform_json)
    assert parsed["test_name"] == "test_increment"
    assert parsed["signal_count"] == 1
    assert parsed["signals"][0]["name"] == "clk"


def test_indexer_links_waveform_to_test(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    demo = repo / "demo"
    if not (demo / "cocotb_results" / "results.xml").exists():
        pytest.skip("demo artifacts missing")

    db_path = tmp_path / "wave.duckdb"
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(demo)],
            index={"type": "duckdb", "path": str(db_path)},
            adapters=AdaptersConfig(waveform_summary=True),
        )
    )
    stats = ArtifactIndexer(
        [str(demo)],
        db_path,
        adapters=AdaptersConfig(waveform_summary=True),
    ).index_all()
    assert stats["waveforms"] >= 2

    with IndexStore(db_path) as store:
        tests = core.list_tests(store, name_pattern="test_counter.test_increment")
        test_id = tests["tests"][0]["test_id"]
        signals = core.wave_signals(store, test_id)
        assert signals["signals"][0]["name"] == "clk"
        summary = core.wave_summary(store, test_id)
        assert summary["end_time_ns"] == 50000


def test_wave_tools_not_found(tmp_path: Path) -> None:
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(tmp_path)],
            index={"type": "duckdb", "path": str(tmp_path / "empty.duckdb")},
        )
    )
    db_path = tmp_path / "empty.duckdb"
    with IndexStore(db_path) as store:
        run_id, run_full = generate_run_id(suite="s", ci_system="local", ci_build_id="1")
        store.insert_run(
            run_id=run_id,
            run_id_full=run_full,
            suite="s",
            created_at="2026-05-26T00:00:00Z",
            status="pass",
        )
        test_id, test_full = generate_test_id(
            run_id_full=run_full, framework="uvm", test_name="only_test"
        )
        store.insert_test(
            test_id=test_id,
            test_id_full=test_full,
            run_id=run_id,
            framework="uvm",
            name="only_test",
            status="pass",
            created_at="2026-05-26T00:00:00Z",
        )
        with pytest.raises(ToolError) as exc:
            core.wave_summary(store, test_id)
        assert exc.value.code == "NOT_FOUND"
