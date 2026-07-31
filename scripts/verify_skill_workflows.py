#!/usr/bin/env python3
"""Exercise every published Sentinel DV skill against the checked-in demo corpus."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sentinel_dv.demo_fixtures import DEMO_ROOT, index_demo_tree  # noqa: E402
from sentinel_dv.indexing.store import IndexStore  # noqa: E402
from sentinel_dv.tools import core  # noqa: E402


def _first(items: list[dict[str, Any]], **expected: Any) -> dict[str, Any]:
    for item in items:
        if all(item.get(key) == value for key, value in expected.items()):
            return item
    raise AssertionError(f"No item matched {expected}")


def verify_skill_workflows() -> dict[str, Any]:
    """Run the three skill workflows and return a compact evidence summary."""
    with TemporaryDirectory(prefix="sentinel-dv-skills-") as temp_dir:
        db_path = Path(temp_dir) / "demo.duckdb"
        stats = index_demo_tree(DEMO_ROOT, db_path)
        with IndexStore(db_path) as store:
            all_runs = core.list_runs(store, page=1, page_size=100)["runs"]
            failing_tests = core.list_tests(store, status="fail", page=1, page_size=100)["tests"]

            # Regression triage: one scoped failing AXI4 VCS run.
            triage_run = _first(all_runs, suite="vcs", status="fail")
            triage_run_id = triage_run["run_id"]
            triage_summary = core.get_run_summary(store, triage_run_id)
            triage_health = core.get_regression_health(store, run_id=triage_run_id)
            triage_clusters = core.cluster_test_failures(store, run_id=triage_run_id)
            triage_failures = core.list_failures(
                store,
                run_id=triage_run_id,
                include_evidence=True,
                page=1,
                page_size=100,
            )
            triage_assertions = core.list_assertion_failures(
                store,
                run_id=triage_run_id,
                include_evidence=True,
                page=1,
                page_size=100,
            )
            cross_sim = core.get_cross_sim_comparison(store, limit=100)

            assert triage_summary["status"] == "fail"
            assert triage_summary["test_counts"]["fail"] > 0
            assert triage_clusters["clusters"]
            assert triage_failures["failures"]
            assert triage_failures["failures"][0]["evidence"]
            assert triage_assertions["assertion_failures"]
            assert triage_health["data_quality"]["cross_sim_consistency_available"] is False

            # Failure debugging: a UVM failure with topology and an indexed VCD.
            debug_test = _first(failing_tests, name="test_counter_sim")
            debug_test_id = debug_test["test_id"]
            debug_details = core.get_test_details(store, debug_test_id)
            debug_failures = core.list_failures(
                store,
                test_id=debug_test_id,
                include_evidence=True,
                page=1,
                page_size=100,
            )
            debug_assertions = core.list_assertion_failures(
                store,
                test_id=debug_test_id,
                include_evidence=True,
                page=1,
                page_size=100,
            )
            debug_topology = core.get_test_topology(store, debug_test_id)
            debug_history = core.get_test_history(
                store,
                test_name=debug_test["name"],
                suite="verilator_counter",
                framework=debug_test["framework"],
                window_days=30,
                limit=50,
            )
            debug_wave = core.wave_summary(store, debug_test_id, include_signals=True)
            debug_signals = core.wave_signals(
                store,
                debug_test_id,
                start_time_ns=0,
                end_time_ns=1_000,
            )

            assert debug_details["item"]["status"] == "fail"
            assert debug_failures["failures"][0]["category"] == "scoreboard"
            assert debug_failures["failures"][0]["evidence"]
            assert debug_assertions["assertion_failures"] == []
            assert debug_topology["item"]["uvm"] is not None
            assert debug_history["entries_returned"] >= 1
            assert debug_wave["format"] == "vcd-summary"
            assert debug_signals["signals"]

            # Coverage closure: AXI4 functional gaps, vacuity, and one targeted advisor result.
            coverage_run = _first(all_runs, suite="xcelium", status="pass")
            coverage_run_id = coverage_run["run_id"]
            coverage_records = core.list_coverage(
                store, run_id=coverage_run_id, page=1, page_size=100
            )
            coverage_summary = core.get_coverage_summary(store, coverage_run_id)
            coverage_trend = core.get_coverage_trend(
                store, suite="xcelium", kind="functional", limit=20
            )
            coverage_gaps = core.get_coverage_gaps(
                store,
                run_id=coverage_run_id,
                kind="functional",
                threshold_pct=100.0,
                page=1,
                page_size=100,
            )
            sva_status = core.get_sva_status(store, run_id=coverage_run_id, page=1, page_size=100)
            vacuity = core.get_vacuous_assertions(
                store, run_id=coverage_run_id, page=1, page_size=100
            )
            target_gap = _first(
                coverage_gaps["gaps"],
                metric_name="axi4_burst_cg.cp_awburst.wrap",
            )
            advisor = core.get_coverage_advisor(
                store,
                run_id=coverage_run_id,
                kind="functional",
                metric_name=target_gap["metric_name"],
                protocol="axi4",
                max_recommendations=1,
            )

            candidate = advisor["advisories"][0]["constraint_sv"]
            assert coverage_records["coverage"]
            assert coverage_summary["summaries"]
            assert coverage_trend["trend"]
            assert coverage_trend["summary"]["direction"] == "stable"
            assert target_gap["covered_pct"] == 0.0
            assert sva_status["counts"]["vacuous"] == 1
            assert vacuity["vacuous_assertions"]
            assert advisor["total_gaps"] == 1
            assert "{{" not in candidate and "}}" not in candidate
            assert "inside {1, 3, 7, 15}" in candidate

            return {
                "index": stats,
                "regression_triage": {
                    "run_id": triage_run_id,
                    "failed_tests": triage_summary["test_counts"]["fail"],
                    "clusters": triage_clusters["clusters_returned"],
                    "assertion_failures": len(triage_assertions["assertion_failures"]),
                    "health_score": triage_health["health_score"],
                    "unavailable_health_components": [
                        key
                        for key, value in triage_health["component_scores"].items()
                        if value is None
                    ],
                    "cross_sim_divergences": cross_sim["unique_divergent_tests"],
                },
                "failure_debugging": {
                    "test_id": debug_test_id,
                    "category": debug_failures["failures"][0]["category"],
                    "waveform_format": debug_wave["format"],
                    "signals_in_window": len(debug_signals["signals"]),
                    "history_entries": debug_history["entries_returned"],
                },
                "coverage_closure": {
                    "run_id": coverage_run_id,
                    "gaps": coverage_gaps["gaps_found"],
                    "vacuous_assertions": len(vacuity["vacuous_assertions"]),
                    "advisor_metric": target_gap["metric_name"],
                    "candidate_sv_validated": True,
                },
            }


def main() -> None:
    """Run the verifier and print its evidence summary."""
    result = verify_skill_workflows()
    print(json.dumps(result, indent=2, sort_keys=True))
    print("\nAll 3 Sentinel DV skill workflows verified.")


if __name__ == "__main__":
    main()
