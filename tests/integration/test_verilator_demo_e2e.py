"""End-to-end: Verilator demo + index + exercise MCP tool surface."""

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
def test_verilator_demo_all_wave_and_discovery_tools(tmp_path: Path) -> None:
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
    subprocess.run([str(build_dir / "Vcounter")], check=True, cwd=wave_dir, capture_output=True)

    vcd_path = wave_dir / "waves" / "test_counter_sim.vcd"
    assert vcd_path.exists()

    work = tmp_path / "artifacts"
    waves_dest = work / "waves"
    waves_dest.mkdir(parents=True)
    shutil.copy(vcd_path, waves_dest / vcd_path.name)
    (work / "results.xml").write_text((demo / "results.xml").read_text(encoding="utf-8"))

    db_path = tmp_path / "index.duckdb"
    cfg = SentinelDVConfig(
        artifact_roots=[str(work)],
        index={"type": "duckdb", "path": str(db_path)},
        adapters=AdaptersConfig(
            uvm=False,
            cocotb=True,
            assertions=False,
            coverage=False,
            waveform_summary=True,
        ),
    )
    set_config(cfg)
    stats = ArtifactIndexer([str(work)], db_path, config=cfg).index_all()
    assert stats["runs"] == 1
    assert stats["tests"] == 1
    assert stats["waveforms"] == 1
    assert stats["warnings"] == []

    with IndexStore(db_path) as store:
        runs, _ = store.query_runs(page=1, page_size=10)
        assert runs
        run_id = runs[0]["run_id"]

        listed_runs = core.list_runs(store)
        assert listed_runs["runs"]
        assert "error" not in listed_runs

        run_detail = core.get_run_details(store, run_id)
        assert run_detail.get("run")

        tests = core.list_tests(store, run_id=run_id)
        test_id = tests["tests"][0]["test_id"]

        detail = core.get_test_details(store, test_id)
        assert detail["item"]["framework"] == "cocotb"

        summary = core.wave_summary(store, test_id)
        assert summary["format"] == "vcd-summary"
        assert summary["end_time_ns"] >= 5000

        windowed = core.wave_signals(store, test_id, start_time_ns=2000, end_time_ns=3000)
        clk = next(s for s in windowed["signals"] if s["name"] == "clk")
        assert clk["toggles"] >= 5

        regressions = core.get_regression_summary(store, suite=runs[0]["suite"])
        assert "pass_rate" in regressions

        assertions, _ = store.query_assertions(page=1, page_size=5)
        assert assertions == []

        cov_list = core.list_coverage(store, run_id=run_id)
        assert cov_list["coverage"] == []
