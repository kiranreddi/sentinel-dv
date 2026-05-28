"""Indexer surfaces warnings for unimplemented adapter flags."""

from pathlib import Path

from sentinel_dv.config import AdaptersConfig, SentinelDVConfig
from sentinel_dv.indexing.indexer import ArtifactIndexer


def test_warnings_when_assertions_and_coverage_enabled(tmp_path: Path) -> None:
    work = tmp_path / "empty"
    work.mkdir()
    db = tmp_path / "index.duckdb"
    cfg = SentinelDVConfig(
        artifact_roots=[str(work)],
        index={"type": "duckdb", "path": str(db)},
        adapters=AdaptersConfig(
            uvm=False,
            cocotb=False,
            assertions=True,
            coverage=True,
            waveform_summary=False,
        ),
    )
    stats = ArtifactIndexer([str(work)], db, config=cfg).index_all()
    warnings = stats["warnings"]
    assert len(warnings) == 2
    assert any("assertions" in w for w in warnings)
    assert any("coverage" in w for w in warnings)
