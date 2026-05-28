"""Shared helpers for Verilator counter MCP walkthrough tests and scripts."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from sentinel_dv.config import AdaptersConfig, SentinelDVConfig, set_config
from sentinel_dv.indexing.indexer import ArtifactIndexer
from sentinel_dv.registry import TOOL_NAMES

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "demo" / "verilator_counter"


def verilator_available() -> bool:
    return shutil.which("verilator") is not None


def ensure_vcd(demo_dir: Path = DEMO_DIR) -> Path:
    """Build and run the Verilator TB if waves/test_counter_sim.vcd is missing."""
    vcd = demo_dir / "waves" / "test_counter_sim.vcd"
    if vcd.is_file():
        return vcd
    if not verilator_available():
        raise RuntimeError("Verilator not on PATH and demo VCD not present")
    subprocess.run(["make", "run"], check=True, cwd=demo_dir)
    if not vcd.is_file():
        raise RuntimeError(f"Expected VCD at {vcd} after make run")
    return vcd


def build_demo_config(work_dir: Path, db_path: Path) -> SentinelDVConfig:
    return SentinelDVConfig(
        artifact_roots=[str(work_dir)],
        index={"type": "duckdb", "path": str(db_path)},
        adapters=AdaptersConfig(
            uvm=True,
            cocotb=True,
            assertions=True,
            coverage=True,
            waveform_summary=True,
        ),
    )


def prepare_work_dir(tmp_path: Path, *, use_repo_demo: bool = False) -> Path:
    """
    Populate a temp artifact tree mirroring demo/verilator_counter.

    When use_repo_demo is True, index the repo demo directory in place (after VCD exists).
    """
    if use_repo_demo:
        ensure_vcd(DEMO_DIR)
        return DEMO_DIR

    work = tmp_path / "artifacts"
    for name in ("assertions", "coverage"):
        shutil.copytree(DEMO_DIR / name, work / name)
    for fname in (
        "results.xml",
        "results_regression_fail.xml",
        "counter_tb.uvm.log",
    ):
        shutil.copy(DEMO_DIR / fname, work / fname)
    ensure_vcd(DEMO_DIR)
    (work / "waves").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        DEMO_DIR / "waves" / "test_counter_sim.vcd",
        work / "waves" / "test_counter_sim.vcd",
    )
    return work


def index_demo(work_dir: Path, db_path: Path) -> dict:
    cfg = build_demo_config(work_dir, db_path)
    set_config(cfg)
    return ArtifactIndexer([str(work_dir)], db_path, config=cfg).index_all()


def mcp_payload(result) -> dict:
    """Extract tool JSON from a FastMCP CallToolResult."""
    if getattr(result, "data", None):
        return result.data
    if getattr(result, "structured_content", None):
        return result.structured_content
    raise AssertionError("MCP tool result has no structured payload")


def assert_tool_ok(payload: dict, tool_name: str) -> None:
    if payload.get("error"):
        raise AssertionError(f"{tool_name} failed: {payload['error']}")
    assert payload.get("schema_version"), f"{tool_name} missing schema_version"


def expected_tool_names() -> tuple[str, ...]:
    return TOOL_NAMES
