"""End-to-end MCP indexing from demo artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_dv.config import SentinelDVConfig, set_config
from sentinel_dv.indexing.indexer import ArtifactIndexer
from sentinel_dv.tools import core


@pytest.fixture
def demo_index(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    demo = repo / "demo"
    if not (demo / "cocotb_results" / "counter_block" / "results.xml").exists():
        pytest.skip("demo artifacts missing")

    db_path = tmp_path / "demo.duckdb"
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(demo)],
            index={"type": "duckdb", "path": str(db_path)},
        )
    )
    stats = ArtifactIndexer([str(demo)], db_path).index_all()
    assert stats["artifacts"] >= 1
    return db_path


def test_index_demo_and_list_tests(demo_index):
    from sentinel_dv.indexing.store import IndexStore

    with IndexStore(demo_index) as store:
        runs = core.list_runs(store)
        assert runs["pagination"]["total_items"] >= 1
        tests = core.list_tests(store)
        assert tests["pagination"]["total_items"] >= 1
