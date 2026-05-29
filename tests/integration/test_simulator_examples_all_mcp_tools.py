"""Verify checked-in VCS, Questa, and Cadence examples exercise every MCP tool."""

from __future__ import annotations

import pytest

from sentinel_dv.demo_fixtures import (
    build_demo_config,
    discover_fixtures,
    index_demo,
    prepare_work_dir,
    run_mcp_verification,
    verify_core_tools,
)
from sentinel_dv.indexing.store import IndexStore


@pytest.mark.parametrize("simulator", ["vcs", "questa", "cadence"])
def test_vendor_example_exercises_all_mcp_tools(simulator: str, tmp_path) -> None:
    work = prepare_work_dir(tmp_path, simulator=simulator)
    db = tmp_path / f"{simulator}.duckdb"
    stats = index_demo(work, db)
    assert stats["runs"] >= 3, stats
    assert stats["tests"] >= 3, stats
    assert stats["failures"] >= 2, stats
    assert stats["assertions"] >= 1, stats
    assert stats["assertion_failures"] >= 1, stats
    assert stats["coverage"] >= 1, stats
    assert stats["waveforms"] >= 1, stats

    cfg_path = tmp_path / f"{simulator}.yaml"
    build_demo_config(work, db).to_yaml(str(cfg_path))

    with IndexStore(db) as store:
        fix = discover_fixtures(store, suite=work.name)
        verify_core_tools(store, fix)

    run_mcp_verification(cfg_path, fix)
