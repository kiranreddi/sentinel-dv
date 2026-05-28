"""Indexer populates signature_id on failures."""

from pathlib import Path

import pytest

from sentinel_dv.config import AdaptersConfig, SentinelDVConfig
from sentinel_dv.indexing.indexer import ArtifactIndexer
from sentinel_dv.indexing.store import IndexStore


def test_cocotb_failure_gets_signature_id(tmp_path: Path) -> None:
    demo_xml = Path(__file__).resolve().parents[2] / "demo" / "cocotb_results" / "results.xml"
    if not demo_xml.exists():
        pytest.skip("demo cocotb results missing")

    work = tmp_path / "work"
    cocotb_dir = work / "cocotb_results"
    cocotb_dir.mkdir(parents=True)
    (cocotb_dir / "results.xml").write_text(demo_xml.read_text(encoding="utf-8"))

    db = tmp_path / "index.duckdb"
    cfg = SentinelDVConfig(
        artifact_roots=[str(work)],
        index={"type": "duckdb", "path": str(db)},
        adapters=AdaptersConfig(uvm=False, cocotb=True, waveform_summary=False),
    )
    stats = ArtifactIndexer([str(work)], db, config=cfg).index_all()
    assert stats["failures"] >= 1

    with IndexStore(db) as store:
        failures, _ = store.query_failures(page=1, page_size=10)
        assert failures
        assert failures[0].get("signature_id")
