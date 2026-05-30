"""Tests for sentinel-dv-index CLI (__main__)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_dv.indexing import __main__ as indexing_cli


def test_index_cli_requires_index_all(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"artifact_roots: [{tmp_path!s}]\nindex:\n  type: duckdb\n  path: {tmp_path / 'idx.db'}\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        indexing_cli.main(["--config", str(cfg)])
    assert exc.value.code == 0
    assert "Nothing to do" in capsys.readouterr().err


def test_index_cli_missing_config_exits(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        indexing_cli.main(["--config", str(tmp_path / "missing.yaml"), "--index-all"])
    assert exc.value.code == 1


def test_index_cli_index_all_empty_roots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"artifact_roots: [{tmp_path!s}]\nindex:\n  type: duckdb\n  path: {tmp_path / 'idx.db'}\n",
        encoding="utf-8",
    )
    indexing_cli.main(["--config", str(cfg), "--index-all"])
    out = capsys.readouterr().out
    assert "Indexed runs=" in out
