"""Security tests for artifact path resolution."""

from pathlib import Path

import pytest

from sentinel_dv.config import SentinelDVConfig, set_config
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
