"""Unit tests for v2.0.0 features: submission, live sim, SVA status, replay, coverage gaps."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sentinel_dv.config import (
    AdaptersConfig,
    IndexConfig,
    SecurityLimits,
    SentinelDVConfig,
    SimulatorTemplate,
    SubmitConfig,
    set_config,
)
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.normalization.coverage_hints import generate_recommendations
from sentinel_dv.schemas.assertions import SVARunStatus, VacuousAssertion
from sentinel_dv.schemas.coverage import CoverageGap, CoverageGapsResponse
from sentinel_dv.schemas.live_sim import LiveSimProgress
from sentinel_dv.schemas.submission import ReplayResponse, SubmitResponse
from sentinel_dv.tools import core
from sentinel_dv.tools.errors import ToolError

# ==============================================================================
# Feature 1: Regression Job Submission
# ==============================================================================


@pytest.fixture
def submit_config(tmp_path: Path) -> SentinelDVConfig:
    """Config with submit enabled and a VCS template."""
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index=IndexConfig(path=str(tmp_path / "test.db")),
        submit=SubmitConfig(
            enabled=True,
            default_simulator="vcs",
            templates=[
                SimulatorTemplate(
                    simulator="vcs",
                    template="make regression SUITE={suite} SEED={seed} TESTFILTER={test_filter} EXTRA={extra_args}",
                    default_args="",
                    replay_template="make replay TEST={test_name} SEED={seed} SUITE={suite}",
                ),
                SimulatorTemplate(
                    simulator="questa",
                    template="vsim -do run.do SUITE={suite} SEED={seed}",
                    default_args="",
                ),
            ],
        ),
    )
    set_config(cfg)
    return cfg


def test_generate_submit_command_basic(tmp_path: Path, submit_config: SentinelDVConfig) -> None:
    """Basic submission command generation."""
    with IndexStore(tmp_path / "test.db") as store:
        result = core.generate_submit_command(store, suite="axi4_regression", seed=42)

    assert result["dry_run"] is True
    assert "axi4_regression" in result["command"]
    assert "42" in result["command"]
    assert result["simulator"] == "vcs"
    assert result["suite"] == "axi4_regression"
    assert result["seed"] == 42


def test_generate_submit_command_simulator_override(
    tmp_path: Path, submit_config: SentinelDVConfig
) -> None:
    """Simulator override works correctly."""
    with IndexStore(tmp_path / "test.db") as store:
        result = core.generate_submit_command(store, suite="fifo_test", simulator="questa")

    assert result["simulator"] == "questa"
    assert "vsim" in result["command"]


def test_generate_submit_command_invalid_suite(
    tmp_path: Path, submit_config: SentinelDVConfig
) -> None:
    """Rejects suite names with unsafe characters."""
    with IndexStore(tmp_path / "test.db") as store:
        with pytest.raises(ToolError) as exc_info:
            core.generate_submit_command(store, suite="../evil; rm -rf /")
    assert exc_info.value.code == "INVALID_INPUT"


def test_generate_submit_command_disabled(tmp_path: Path) -> None:
    """Raises CONFIG_ERROR when submit is not enabled."""
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index=IndexConfig(path=str(tmp_path / "test.db")),
        # submit.enabled defaults to False
    )
    set_config(cfg)

    with IndexStore(tmp_path / "test.db") as store:
        with pytest.raises(ToolError) as exc_info:
            core.generate_submit_command(store, suite="axi4_regression")
    assert exc_info.value.code == "CONFIG_ERROR"


def test_generate_submit_command_unknown_simulator(
    tmp_path: Path, submit_config: SentinelDVConfig
) -> None:
    """Raises CONFIG_ERROR for unknown simulator."""
    with IndexStore(tmp_path / "test.db") as store:
        with pytest.raises(ToolError) as exc_info:
            core.generate_submit_command(store, suite="axi4", simulator="xcelium_unknown")
    assert exc_info.value.code == "CONFIG_ERROR"


def test_generate_submit_command_shell_quoting(
    tmp_path: Path, submit_config: SentinelDVConfig
) -> None:
    """extra_args are shell-quoted — no injection possible."""
    with IndexStore(tmp_path / "test.db") as store:
        result = core.generate_submit_command(store, suite="axi4", extra_args="--foo=bar")

    assert result["dry_run"] is True
    assert "--foo=bar" in result["command"]


# ==============================================================================
# Feature 2: Live Simulation Status
# ==============================================================================


def test_live_sim_adapter_reads_status_file(tmp_path: Path) -> None:
    """LiveSimAdapter reads and parses a live_status.json file."""
    from sentinel_dv.adapters.live_sim import LiveSimAdapter

    status_data = {
        "suite": "axi4_regression",
        "phase": "running",
        "tests_total": 100,
        "tests_done": 47,
        "tests_passing": 44,
        "tests_failing": 3,
        "current_test": "axi4_random_burst_test",
        "elapsed_seconds": 183.5,
    }
    suite_dir = tmp_path / "axi4_regression"
    suite_dir.mkdir()
    status_file = suite_dir / "live_status.json"
    status_file.write_text(json.dumps(status_data))

    adapter = LiveSimAdapter(artifact_roots=[tmp_path], max_age_seconds=300)
    progress = adapter.read(suite="axi4_regression")

    assert progress is not None
    assert progress.suite == "axi4_regression"
    assert progress.phase == "running"
    assert progress.tests_total == 100
    assert progress.tests_done == 47
    assert progress.percent_done == pytest.approx(47.0)


def test_live_sim_adapter_returns_none_no_file(tmp_path: Path) -> None:
    """LiveSimAdapter returns None when no file is found."""
    from sentinel_dv.adapters.live_sim import LiveSimAdapter

    adapter = LiveSimAdapter(artifact_roots=[tmp_path], max_age_seconds=300)
    result = adapter.read(suite="nonexistent_suite")
    assert result is None


def test_live_sim_adapter_stale_detection(tmp_path: Path) -> None:
    """LiveSimAdapter marks old files as stale."""
    import time

    from sentinel_dv.adapters.live_sim import LiveSimAdapter

    status_data = {"suite": "old_run", "phase": "done"}
    status_file = tmp_path / "live_status.json"
    status_file.write_text(json.dumps(status_data))

    # Set mtime to 1 hour ago
    old_mtime = time.time() - 3700
    import os

    os.utime(status_file, (old_mtime, old_mtime))

    adapter = LiveSimAdapter(artifact_roots=[tmp_path], max_age_seconds=300)
    progress = adapter.read()

    assert progress is not None
    assert progress.stale is True


def test_get_sim_status_config_error(tmp_path: Path) -> None:
    """get_sim_status raises CONFIG_ERROR when adapter is disabled."""
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index=IndexConfig(path=str(tmp_path / "test.db")),
        # adapters.live_sim defaults to False
    )
    set_config(cfg)

    with IndexStore(tmp_path / "test.db") as store:
        with pytest.raises(ToolError) as exc_info:
            core.get_sim_status(store, suite="axi4")
    assert exc_info.value.code == "CONFIG_ERROR"


def test_live_sim_progress_schema() -> None:
    """LiveSimProgress validates correctly."""
    p = LiveSimProgress(
        suite="test_suite",
        phase="running",
        tests_total=50,
        tests_done=25,
        tests_passing=24,
        tests_failing=1,
    )
    assert p.percent_done is None  # Not computed in schema, only in adapter


# ==============================================================================
# Feature 3: SVA Run Status
# ==============================================================================


def test_sva_run_status_schema() -> None:
    """SVARunStatus schema validates correctly."""
    s = SVARunStatus(
        assertion_id="a_001",
        test_id="t_001",
        status="passing",
        pass_count=10,
    )
    assert s.status == "passing"
    assert s.fail_count == 0


def test_store_insert_and_query_sva_status(tmp_path: Path) -> None:
    """Store correctly stores and queries SVA run status."""
    db = tmp_path / "test.db"
    with IndexStore(db) as store:
        store.insert_run("r_001", "R_001_full", "axi4", "2026-01-25T14:00:00Z", "pass")
        store.insert_sva_run_status(
            assertion_id="a_001",
            test_id="t_001",
            run_id="r_001",
            status="passing",
            pass_count=10,
            fail_count=0,
            vacuous_count=0,
        )
        store.insert_sva_run_status(
            assertion_id="a_002",
            test_id="t_001",
            run_id="r_001",
            status="vacuous",
            pass_count=0,
            fail_count=0,
            vacuous_count=5,
        )

        rows = store.query_sva_run_status(run_id="r_001")
        assert len(rows) == 2

        failing_rows = store.query_sva_run_status(run_id="r_001", status_filter="passing")
        assert len(failing_rows) == 1

        vacuous = store.query_vacuous_assertions(run_id="r_001")
        assert len(vacuous) == 1
        assert vacuous[0]["assertion_id"] == "a_002"


def test_get_sva_status_invalid_status_filter(tmp_path: Path) -> None:
    """get_sva_status raises INVALID_INPUT for unknown status_filter values."""
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index=IndexConfig(path=str(tmp_path / "test.db")),
    )
    set_config(cfg)

    with IndexStore(tmp_path / "test.db") as store:
        with pytest.raises(ToolError) as exc_info:
            core.get_sva_status(store, status_filter="invalid_status")
    assert exc_info.value.code == "INVALID_INPUT"


def test_get_vacuous_assertions_empty(tmp_path: Path) -> None:
    """get_vacuous_assertions returns empty list when no vacuous assertions."""
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index=IndexConfig(path=str(tmp_path / "test.db")),
    )
    set_config(cfg)

    with IndexStore(tmp_path / "test.db") as store:
        result = core.get_vacuous_assertions(store)

    assert result["vacuous_assertions"] == []
    assert result["pagination"]["total_items"] == 0


# ==============================================================================
# Feature 4: Seed Replay
# ==============================================================================


def test_generate_replay_command_with_seed(tmp_path: Path, submit_config: SentinelDVConfig) -> None:
    """Replay command uses indexed seed."""
    db = tmp_path / "test.db"
    with IndexStore(db) as store:
        store.insert_run("r_001", "R_001_full", "axi4_regression", "2026-01-25T14:00:00Z", "fail")
        store.insert_test(
            "t_001",
            "T_001_full",
            "r_001",
            "uvm",
            "axi_burst_test",
            "fail",
            "2026-01-25T14:00:00Z",
            seed=12345,
            sim_vendor="vcs",
        )
        result = core.generate_replay_command(store, test_id="t_001")

    assert result["dry_run"] is True
    assert result["seed"] == 12345
    assert "12345" in result["command"]
    assert result["warning"] is None


def test_generate_replay_command_no_seed_warning(
    tmp_path: Path, submit_config: SentinelDVConfig
) -> None:
    """Replay command warns when no seed recorded."""
    db = tmp_path / "test.db"
    with IndexStore(db) as store:
        store.insert_run("r_001", "R_001_full", "axi4_regression", "2026-01-25T14:00:00Z", "fail")
        store.insert_test(
            "t_001",
            "T_001_full",
            "r_001",
            "uvm",
            "axi_burst_test",
            "fail",
            "2026-01-25T14:00:00Z",
            seed=None,
            sim_vendor="vcs",
        )
        result = core.generate_replay_command(store, test_id="t_001")

    assert result["dry_run"] is True
    assert result["seed"] is None
    assert result["warning"] is not None
    assert "seed" in result["warning"].lower()


def test_generate_replay_command_not_found(tmp_path: Path, submit_config: SentinelDVConfig) -> None:
    """Raises NOT_FOUND for unknown test_id."""
    with IndexStore(tmp_path / "test.db") as store:
        with pytest.raises(ToolError) as exc_info:
            core.generate_replay_command(store, test_id="t_nonexistent")
    assert exc_info.value.code == "NOT_FOUND"


# ==============================================================================
# Feature 5: Coverage Closure Guidance
# ==============================================================================


def test_generate_recommendations_empty() -> None:
    """Empty metrics returns empty gaps."""
    gaps = generate_recommendations(metrics=[], threshold_pct=100.0)
    assert gaps == []


def test_generate_recommendations_all_covered() -> None:
    """Fully covered metrics produce no gaps."""
    metrics = [
        {
            "name": "axi.awlen_bins",
            "scope": "tb.env",
            "covered": 100.0,
            "kind": "functional",
            "bins_missed": [],
        },
    ]
    gaps = generate_recommendations(metrics=metrics, threshold_pct=100.0)
    assert gaps == []


def test_generate_recommendations_gap_detected() -> None:
    """Gaps are correctly identified."""
    metrics = [
        {
            "name": "axi.awlen_bins",
            "scope": "tb.env",
            "covered": 87.5,
            "kind": "functional",
            "bins_missed": ["awlen_15"],
        },
        {
            "name": "axi.error_resp",
            "scope": "tb.env",
            "covered": 0.0,
            "kind": "functional",
            "bins_missed": [],
        },
    ]
    gaps = generate_recommendations(metrics=metrics, threshold_pct=100.0)
    assert len(gaps) == 2

    # Error metric should be high priority
    assert gaps[0].metric_name == "axi.error_resp"
    assert gaps[0].priority == "high"  # 0% is below 25% threshold


def test_generate_recommendations_sorted_by_priority() -> None:
    """Gaps are sorted high → medium → low."""
    metrics = [
        {
            "name": "axi.burst_bins",
            "scope": "tb",
            "covered": 60.0,
            "kind": "functional",
            "bins_missed": [],
        },
        {
            "name": "axi.error_inject",
            "scope": "tb",
            "covered": 10.0,
            "kind": "functional",
            "bins_missed": [],
        },
        {
            "name": "axi.parity",
            "scope": "tb",
            "covered": 55.0,
            "kind": "functional",
            "bins_missed": [],
        },
    ]
    gaps = generate_recommendations(metrics=metrics, threshold_pct=100.0)

    priorities = [g.priority for g in gaps]
    priority_order = {"high": 0, "medium": 1, "low": 2}
    assert priorities == sorted(priorities, key=lambda p: priority_order[p])


def test_get_coverage_gaps_invalid_kind(tmp_path: Path) -> None:
    """coverage.gaps raises INVALID_INPUT for invalid kind values."""
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index=IndexConfig(path=str(tmp_path / "test.db")),
    )
    set_config(cfg)

    with IndexStore(tmp_path / "test.db") as store:
        with pytest.raises(ToolError) as exc_info:
            core.get_coverage_gaps(store, kind="invalid_kind")
    assert exc_info.value.code == "INVALID_INPUT"


def test_get_coverage_gaps_empty_index(tmp_path: Path) -> None:
    """coverage.gaps returns empty response for empty index."""
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index=IndexConfig(path=str(tmp_path / "test.db")),
    )
    set_config(cfg)

    with IndexStore(tmp_path / "test.db") as store:
        result = core.get_coverage_gaps(store)

    assert result["gaps"] == []
    assert result["gaps_found"] == 0
    assert result["total_metrics"] == 0


# ==============================================================================
# Config: SecurityLimits new fields
# ==============================================================================


def test_security_limits_new_fields() -> None:
    """SecurityLimits includes max_command_length and max_coverage_gaps."""
    lim = SecurityLimits()
    assert lim.max_command_length == 4096
    assert lim.max_coverage_gaps == 100


def test_submit_config_defaults() -> None:
    """SubmitConfig defaults are correct."""
    sc = SubmitConfig()
    assert sc.enabled is False
    assert sc.default_simulator == "vcs"
    assert sc.templates == []


def test_adapters_config_new_fields() -> None:
    """AdaptersConfig includes live_sim fields."""
    ac = AdaptersConfig()
    assert ac.live_sim is False
    assert ac.live_sim_max_age_seconds == 300


# ==============================================================================
# Bug Fix 2: resolve_config_with_demo_fallback warns
# ==============================================================================


def test_resolve_config_demo_fallback_warns(tmp_path: Path) -> None:
    """resolve_config_with_demo_fallback emits UserWarning before using demo."""
    from sentinel_dv.config import resolve_config_with_demo_fallback

    # Create a demo directory
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir()

    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        cfg = resolve_config_with_demo_fallback(demo_root=demo_dir)

    assert len(w) >= 1
    assert any(issubclass(warning.category, UserWarning) for warning in w)
    assert any("demo" in str(warning.message).lower() for warning in w)
    assert str(demo_dir) in cfg.artifact_roots
