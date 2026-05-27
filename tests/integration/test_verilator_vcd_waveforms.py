"""End-to-end: Verilator sim -> VCD -> index -> wave.* MCP tools."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from sentinel_dv.config import AdaptersConfig, SentinelDVConfig, set_config
from sentinel_dv.indexing.indexer import ArtifactIndexer
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.tools import core


@pytest.mark.skipif(not shutil.which("verilator"), reason="Verilator not installed")
def test_verilator_vcd_indexed_waveform_tools(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    demo = repo / "demo" / "verilator_counter"
    if not (demo / "counter.sv").exists():
        pytest.skip("verilator_counter demo missing")

    build_dir = tmp_path / "obj_dir"
    wave_dir = tmp_path / "sim_waves"
    wave_dir.mkdir()

    subprocess.run(
        [
            "verilator",
            "--cc",
            "--exe",
            "--build",
            "--trace",
            "-Wno-UNOPTFLAT",
            "-Mdir",
            str(build_dir),
            str(demo / "counter.sv"),
            str(demo / "sim_main.cpp"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    sim_bin = build_dir / "Vcounter"
    assert sim_bin.exists()
    subprocess.run([str(sim_bin)], check=True, cwd=wave_dir, capture_output=True, text=True)

    vcd_path = wave_dir / "waves" / "test_counter_sim.vcd"
    assert vcd_path.exists(), f"expected VCD at {vcd_path}"

    work = tmp_path / "artifacts"
    waves_dest = work / "waves"
    waves_dest.mkdir(parents=True)
    shutil.copy(vcd_path, waves_dest / vcd_path.name)
    (work / "results.xml").write_text((demo / "results.xml").read_text(encoding="utf-8"))

    db_path = tmp_path / "index.duckdb"
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(work)],
            index={"type": "duckdb", "path": str(db_path)},
            adapters=AdaptersConfig(waveform_summary=True, cocotb=True),
        )
    )
    stats = ArtifactIndexer(
        [str(work)],
        db_path,
        adapters=AdaptersConfig(waveform_summary=True, cocotb=True),
    ).index_all()
    assert stats["tests"] == 1
    assert stats["waveforms"] == 1

    with IndexStore(db_path) as store:
        tests = core.list_tests(store)
        test_id = tests["tests"][0]["test_id"]
        signals = core.wave_signals(store, test_id)
        names = {s["name"] for s in signals["signals"]}
        assert {"clk", "rst", "count"}.issubset(names)

        summary = core.wave_summary(store, test_id)
        assert summary["format"] == "vcd-summary"
        assert summary["end_time_ns"] is not None
        assert summary["end_time_ns"] >= 5_000  # ~10 µs trace (1ps timescale)
        assert summary["highlights"]

        # 2–3 µs window on real Verilator VCD (nanoseconds)
        windowed = core.wave_signals(
            store, test_id, start_time_ns=2_000, end_time_ns=3_000
        )
        assert windowed["start_time_ns"] == 2_000
        assert windowed["end_time_ns"] == 3_000
        by_name = {s["name"]: s for s in windowed["signals"]}
        assert by_name["clk"]["toggles"] >= 5
        assert by_name["clk"]["value_at_start"] in ("0", "1")
        assert by_name["clk"]["value_at_end"] in ("0", "1")

        win_summary = core.wave_summary(
            store, test_id, start_time_ns=2_000, end_time_ns=3_000
        )
        assert win_summary["start_time_ns"] == 2_000
        assert win_summary["highlights"]
        assert any(h.get("note", "").find("window") >= 0 for h in win_summary["highlights"])
