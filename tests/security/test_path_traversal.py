"""Security tests for artifact path resolution."""

from pathlib import Path

import pytest

from sentinel_dv.config import SentinelDVConfig, set_config
from sentinel_dv.indexing.indexer import ArtifactIndexer
from sentinel_dv.tools import core
from sentinel_dv.tools.errors import ToolError


def test_resolve_rejects_path_outside_roots(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    set_config(
        SentinelDVConfig(
            artifact_roots=[str(root)],
            index={"type": "duckdb", "path": str(tmp_path / "t.duckdb")},
        )
    )
    with pytest.raises(ToolError) as exc:
        core._resolve_artifact_path("../outside.txt")
    assert exc.value.code == "NOT_FOUND"


def test_indexer_drops_traversal_evidence_paths(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    indexer = ArtifactIndexer([str(root)], tmp_path / "idx.duckdb")

    refs = indexer._normalize_evidence_refs(
        [
            {"kind": "log", "path": "logs/sim.log", "extract": "safe"},
            {"kind": "log", "path": "../secrets.txt", "extract": "unsafe"},
            {"kind": "log", "path": "logs/../../secrets.txt", "extract": "unsafe"},
        ]
    )

    assert [ref["path"] for ref in refs] == ["logs/sim.log"]
