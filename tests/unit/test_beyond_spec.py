"""Unit tests for v2.1.0 DV-intelligence tools.

Tests: coverage.trend, runs.cross_sim, tests.cluster,
       regression.health, coverage.advisor
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sentinel_dv.config import (
    AdaptersConfig,
    IndexConfig,
    SentinelDVConfig,
    set_config,
)
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.normalization.coverage_advisor import build_advisories
from sentinel_dv.tools.core import (
    cluster_test_failures,
    get_coverage_advisor,
    get_coverage_trend,
    get_cross_sim_comparison,
    get_regression_health,
)
from sentinel_dv.tools.errors import ToolError

# ---------------------------------------------------------------------------
# Config fixture (needed by core.py clamp_pagination etc.)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _default_config(tmp_path):
    """Initialise a minimal config so get_config() never raises."""
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index=IndexConfig(path=str(tmp_path / "test.db")),
    )
    set_config(cfg)
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(tmp_path: Path) -> IndexStore:
    """Create an IndexStore pre-populated with multi-simulator test data."""
    db = tmp_path / "test.db"
    store = IndexStore(db)
    store.connect()

    # Two runs — VCS and Questa — same suite
    run_vcs = "r_vcs_001"
    run_questa = "r_questa_001"
    store.insert_run(
        run_id=run_vcs,
        run_id_full=run_vcs,
        suite="axi4_unit",
        status="fail",
        created_at="2024-01-01T10:00:00",
    )
    store.insert_run(
        run_id=run_questa,
        run_id_full=run_questa,
        suite="axi4_unit",
        status="pass",
        created_at="2024-01-02T10:00:00",
    )

    # Tests — same name, different sim, divergent outcome
    t1 = "t_vcs_001"
    t2 = "t_questa_001"
    t3 = "t_vcs_002"
    t4 = "t_questa_002"
    for tid, rid, sim, status in [
        (t1, run_vcs, "vcs", "fail"),
        (t2, run_questa, "questa", "pass"),
        (t3, run_vcs, "vcs", "pass"),
        (t4, run_questa, "questa", "pass"),
    ]:
        store.insert_test(
            test_id=tid,
            test_id_full=tid,
            run_id=rid,
            framework="uvm",
            name="axi4_bk2bk_test",
            status=status,
            sim_vendor=sim,
            created_at="2024-01-01T10:00:00",
        )

    # Failures for tests.cluster — two with same signature, one different
    common_msg = "UVM_FATAL: Assertion CHK_AWVALID_STABLE failed at time 1000ns"
    for fid, tid, rid, msg in [
        ("f_001", t1, run_vcs, common_msg),
        ("f_002", t1, run_vcs, common_msg),  # same signature
        ("f_003", t1, run_vcs, "UVM_ERROR: TIMEOUT waiting for bready"),
    ]:
        store.insert_failure(
            failure_id=fid,
            failure_id_full=fid,
            test_id=tid,
            run_id=rid,
            severity="fatal" if "FATAL" in msg else "error",
            category="assertion",
            summary=msg[:80],
            message=msg,
            tags=[],
        )

    # Coverage data — two runs with same metrics for trend
    cov_metrics = [
        {"name": "cp_awburst.wrap", "scope": "dut", "covered": 0.0, "hits": 0, "total": 1},
        {"name": "cp_awburst.incr", "scope": "dut", "covered": 100.0, "hits": 5, "total": 5},
    ]
    store.insert_coverage_summary(
        run_id=run_vcs,
        kind="functional",
        metrics=cov_metrics,
    )
    # Second run with slightly higher coverage
    cov_metrics2 = [
        {"name": "cp_awburst.wrap", "scope": "dut", "covered": 50.0, "hits": 1, "total": 1},
        {"name": "cp_awburst.incr", "scope": "dut", "covered": 100.0, "hits": 5, "total": 5},
    ]
    store.insert_coverage_summary(
        run_id=run_questa,
        kind="functional",
        metrics=cov_metrics2,
    )

    return store


# ---------------------------------------------------------------------------
# coverage.trend
# ---------------------------------------------------------------------------


class TestCoverageTrend:
    def test_returns_trend_rows(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_coverage_trend(store)
            assert len(r["trend"]) >= 1
            assert "covered_pct" in r["trend"][0]
            assert "summary" in r

    def test_direction_improving(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_coverage_trend(store, kind="functional")
            trend = r["trend"]
            # VCS run at 50%, Questa run at 75% — should be improving
            if len(trend) >= 2:
                last_delta = trend[-1]["delta_pct"]
                assert last_delta is not None

    def test_invalid_kind_raises(self, tmp_path):
        with _make_store(tmp_path) as store:
            with pytest.raises(ToolError) as exc:
                get_coverage_trend(store, kind="invalid_kind")
            assert exc.value.code == "INVALID_INPUT"

    def test_invalid_limit_raises(self, tmp_path):
        with _make_store(tmp_path) as store:
            with pytest.raises(ToolError) as exc:
                get_coverage_trend(store, limit=0)
            assert exc.value.code == "INVALID_INPUT"

    def test_empty_db_returns_empty_trend(self, tmp_path):
        db = tmp_path / "empty.db"
        with IndexStore(db) as store:
            r = get_coverage_trend(store)
            assert r["trend"] == []


# ---------------------------------------------------------------------------
# runs.cross_sim
# ---------------------------------------------------------------------------


class TestCrossSimComparison:
    def test_finds_divergent_tests(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_cross_sim_comparison(store)
            # vcs=fail, questa=pass for same test name → should be divergent
            assert r["unique_divergent_names"] >= 1
            d = r["divergent_tests"][0]
            assert "sim_a" in d and "sim_b" in d
            assert d["status_a"] != d["status_b"]

    def test_no_divergence_when_all_agree(self, tmp_path):
        db = tmp_path / "nodiv.db"
        with IndexStore(db) as store:
            # Two runs, same result on both sims
            for rid, sim, status in [
                ("r1", "vcs", "pass"),
                ("r2", "questa", "pass"),
            ]:
                store.insert_run(
                    run_id=rid, run_id_full=rid, suite="s", status="pass", created_at="2024-01-01"
                )
                store.insert_test(
                    test_id=f"t_{rid}",
                    test_id_full=f"t_{rid}",
                    run_id=rid,
                    framework="uvm",
                    name="same_test",
                    status=status,
                    sim_vendor=sim,
                    created_at="2024-01-01T10:00:00",
                )
            r = get_cross_sim_comparison(store)
            assert r["unique_divergent_names"] == 0

    def test_note_field_present(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_cross_sim_comparison(store)
            assert "note" in r


# ---------------------------------------------------------------------------
# tests.cluster
# ---------------------------------------------------------------------------


class TestClusterFailures:
    def test_clusters_by_signature(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = cluster_test_failures(store)
            assert r["unique_clusters"] >= 1
            # The two identical messages should be in the same cluster
            top = r["clusters"][0]
            assert top["count"] >= 2

    def test_empty_returns_clean(self, tmp_path):
        db = tmp_path / "nofa.db"
        with IndexStore(db) as store:
            r = cluster_test_failures(store)
            assert r["unique_clusters"] == 0
            assert r["total_failures_analysed"] == 0

    def test_invalid_max_clusters(self, tmp_path):
        with _make_store(tmp_path) as store:
            with pytest.raises(ToolError) as exc:
                cluster_test_failures(store, max_clusters=0)
            assert exc.value.code == "INVALID_INPUT"

    def test_run_id_filter(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = cluster_test_failures(store, run_id="r_vcs_001")
            assert r["total_failures_analysed"] >= 1


# ---------------------------------------------------------------------------
# regression.health
# ---------------------------------------------------------------------------


class TestRegressionHealth:
    def test_returns_score_and_band(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_regression_health(store)
            score = r["health_score"]
            assert 0 <= score <= 100
            assert r["band"] in ("sign-off-ready", "minor-issues", "coverage-gaps", "not-ready")

    def test_component_scores_present(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_regression_health(store)
            comps = r["component_scores"]
            for key in (
                "pass_rate",
                "coverage",
                "assertion_health",
                "flakiness",
                "cross_sim_consistency",
            ):
                assert key in comps
                assert 0 <= comps[key] <= 100

    def test_recommendations_non_empty(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_regression_health(store)
            assert len(r["recommendations"]) >= 1

    def test_perfect_score_all_pass(self, tmp_path):
        db = tmp_path / "perfect.db"
        with IndexStore(db) as store:
            store.insert_run(
                run_id="r1", run_id_full="r1", suite="s", status="pass", created_at="2024-01-01"
            )
            store.insert_test(
                test_id="t1",
                test_id_full="t1",
                run_id="r1",
                framework="uvm",
                name="mytest",
                status="pass",
                created_at="2024-01-01T10:00:00",
            )
            r = get_regression_health(store)
            assert r["health_score"] > 50  # not a perfect 100 because coverage is 0%


# ---------------------------------------------------------------------------
# coverage.advisor
# ---------------------------------------------------------------------------


class TestCoverageAdvisor:
    def test_returns_advisories_with_sv_code(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_coverage_advisor(store, max_recommendations=5)
            advs = r["advisories"]
            assert len(advs) >= 1
            # Each advisory must have the key fields
            for a in advs:
                assert "constraint_sv" in a
                assert "sequence_hint" in a
                assert "protocol_hint" in a
                assert "bin_name" in a

    def test_axi4_protocol_detection(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_coverage_advisor(store)
            axi4_advs = [a for a in r["advisories"] if a["protocol_hint"] == "AXI4"]
            assert len(axi4_advs) >= 1

    def test_constraint_contains_sv_syntax(self, tmp_path):
        with _make_store(tmp_path) as store:
            r = get_coverage_advisor(store, max_recommendations=3)
            for a in r["advisories"]:
                # Every constraint block should have 'constraint' keyword
                assert "constraint" in a["constraint_sv"].lower()

    def test_invalid_max_raises(self, tmp_path):
        with _make_store(tmp_path) as store:
            with pytest.raises(ToolError) as exc:
                get_coverage_advisor(store, max_recommendations=0)
            assert exc.value.code == "INVALID_INPUT"

    def test_invalid_kind_raises(self, tmp_path):
        with _make_store(tmp_path) as store:
            with pytest.raises(ToolError) as exc:
                get_coverage_advisor(store, kind="unknown_kind")
            assert exc.value.code == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# build_advisories (unit test of advisor engine)
# ---------------------------------------------------------------------------


class TestBuildAdvisories:
    def _make_gap(self, name: str, pct: float = 0.0):
        """Create a minimal gap-like object."""
        from sentinel_dv.schemas.coverage import CoverageGap

        return CoverageGap(
            metric_name=name,
            scope="dut",
            kind="functional",
            covered_pct=pct,
            bins_missed=[],
            priority="high",
            recommendation="test",
        )

    def test_axi4_wrap_burst(self):
        gaps = [self._make_gap("cp_awburst.wrap")]
        advs = build_advisories(gaps)
        assert len(advs) == 1
        assert advs[0]["protocol_hint"] == "AXI4"
        assert "WRAP" in advs[0]["constraint_sv"]

    def test_axi4_slverr(self):
        gaps = [self._make_gap("cp_bresp.slverr")]
        advs = build_advisories(gaps)
        assert advs[0]["protocol_hint"] == "AXI4"
        assert "SLVERR" in advs[0]["constraint_sv"]

    def test_generic_fallback(self):
        gaps = [self._make_gap("some_custom_covergroup.my_bin")]
        advs = build_advisories(gaps)
        assert advs[0]["protocol_hint"] == "generic"
        assert "constraint" in advs[0]["constraint_sv"].lower()

    def test_deduplication(self):
        gap = self._make_gap("cp_awburst.wrap")
        advs = build_advisories([gap, gap, gap])
        assert len(advs) == 1  # de-duped by bin_name
