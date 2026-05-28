"""Index assertion/coverage artifacts with Verilator demo layout."""

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
def test_verilator_assertion_coverage_mcp(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    demo = repo / "demo" / "verilator_counter"

    build_dir = tmp_path / "obj_dir"
    wave_dir = tmp_path / "sim"
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
    )
    subprocess.run([str(build_dir / "Vcounter")], check=True, cwd=wave_dir, capture_output=True)

    work = tmp_path / "artifacts"
    shutil.copytree(demo / "assertions", work / "assertions", dirs_exist_ok=True)
    shutil.copytree(demo / "coverage", work / "coverage")
    (work / "waves").mkdir(parents=True)
    shutil.copy(
        wave_dir / "waves" / "test_counter_sim.vcd",
        work / "waves" / "test_counter_sim.vcd",
    )
    (work / "results.xml").write_text((demo / "results.xml").read_text(encoding="utf-8"))

    db = tmp_path / "index.duckdb"
    cfg = SentinelDVConfig(
        artifact_roots=[str(work)],
        index={"type": "duckdb", "path": str(db)},
        adapters=AdaptersConfig(
            uvm=False,
            cocotb=True,
            assertions=True,
            coverage=True,
            waveform_summary=True,
        ),
    )
    set_config(cfg)
    stats = ArtifactIndexer([str(work)], db, config=cfg).index_all()
    assert stats["assertions"] >= 2
    assert stats["coverage"] >= 1
    assert stats["waveforms"] == 1
    assert stats["warnings"] == []

    with IndexStore(db) as store:
        tests = core.list_tests(store)
        run_id = tests["tests"][0]["run_id"]

        axi = core.list_assertions(store, protocol="axi4")
        assert len(axi["assertions"]) >= 1

        detail = core.get_assertion_details(store, axi["assertions"][0]["assertion_id"])
        assert detail["item"]["name"]

        cov = core.get_coverage_summary(store, run_id)
        assert cov["summaries"][0]["metrics"]

        runs = core.list_runs(store)
        reg = core.get_regression_summary(
            store,
            suite=runs["runs"][0]["suite"],
            window_days=30,
            as_of="2026-05-27T12:00:00Z",
        )
        assert reg["as_of"] == "2026-05-27T12:00:00Z"
