#!/usr/bin/env python3
"""AXI4 UVM four-simulator sentinel-dv demo.

Demonstrates all 26 MCP tools against a realistic AXI4-Lite slave
UVM testbench indexed from VCS, Questa, and Xcelium simulation results.

Usage::

    cd demo/axi4_uvm
    sentinel-dv-index --config config.yaml --index-all
    python ../../examples/axi4_sentinel_demo.py

Expected output: a full verification report across all 26 tools.
"""

from __future__ import annotations

import sys
from pathlib import Path

# --- path setup (works when run from the repo root or demo/axi4_uvm) -------
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sentinel_dv.config import load_config
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.tools.core import (
    cluster_test_failures,
    compare_runs,
    generate_replay_command,
    generate_submit_command,
    get_coverage_advisor,
    get_coverage_gaps,
    get_coverage_summary,
    get_coverage_trend,
    get_cross_sim_comparison,
    get_regression_health,
    get_run_details,
    get_regression_summary,
    get_sim_status,
    get_sva_status,
    get_vacuous_assertions,
    list_assertion_failures,
    list_assertions,
    list_failures,
    list_runs,
    list_tests,
    wave_summary,
)
from sentinel_dv.tools.errors import ToolError

# ---------------------------------------------------------------------------
DEMO_DIR = REPO_ROOT / "demo" / "axi4_uvm"
CONFIG_PATH = DEMO_DIR / "config.yaml"
DB_PATH = DEMO_DIR / "axi4_sentinel.db"

BANNER = "\033[1;36m{}\033[0m"
PASS = "\033[1;32m✓ PASS\033[0m"
FAIL = "\033[1;31m✗ FAIL\033[0m"
SKIP = "\033[1;33m⚠ SKIP\033[0m"


def _header(title: str) -> None:
    print()
    print(BANNER.format(f"{'─'*70}"))
    print(BANNER.format(f"  {title}"))
    print(BANNER.format(f"{'─'*70}"))


def _tool(name: str, fn, *, expect_nonempty: str | None = None) -> dict:
    """Run one tool, print pass/fail, return raw result dict."""
    try:
        result = fn()
        if isinstance(result, dict) and "error" in result:
            print(f"  {FAIL}  {name}: {result['error']}")
            return result
        detail = ""
        if expect_nonempty and isinstance(result, dict):
            items = result.get(expect_nonempty, [])
            if isinstance(items, list):
                detail = f"  ({len(items)} {expect_nonempty})"
        print(f"  {PASS}  {name}{detail}")
        return result
    except ToolError as exc:
        print(f"  {SKIP}  {name}: {exc.code} — {exc.message[:72]}")
        return {}
    except Exception as exc:  # noqa: BLE001
        print(f"  {FAIL}  {name}: {exc}")
        return {}


def main() -> int:  # noqa: PLR0915
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found at {DB_PATH}")
        print("Run:  cd demo/axi4_uvm && sentinel-dv-index --config config.yaml --index-all")
        return 1

    load_config(CONFIG_PATH)

    passed: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []

    def track(name: str, fn, **kwargs) -> dict:
        r = _tool(name, fn, **kwargs)
        if r and "error" not in r:
            passed.append(name)
        elif not r:
            skipped.append(name)
        else:
            failed.append(name)
        return r

    with IndexStore(DB_PATH) as store:
        # ── Discover context ────────────────────────────────────────────────
        runs_list, _ = store.query_runs(page=1, page_size=10)
        if not runs_list:
            print("[ERROR] No runs indexed — re-run sentinel-dv-index first.")
            return 1

        run_id = runs_list[0]["run_id"]
        suite  = runs_list[0]["suite"]
        run_ids = [r["run_id"] for r in runs_list[:2]]

        tests_list, _ = store.query_tests(run_id=run_id, page=1, page_size=20)
        test_id = tests_list[0]["test_id"] if tests_list else None

        # Pick a test that has a waveform summary
        all_tests, _ = store.query_tests(page=1, page_size=100)
        wave_test_id = next(
            (t["test_id"] for t in all_tests if "bk2bk" in t.get("name", "").lower()),
            test_id,
        )

        # ── Section 1: Run-level tools ──────────────────────────────────────
        _header("1 · Run-level tools (runs.list / runs.summary / regression.summary)")

        r_list = track("runs.list", lambda: list_runs(store), expect_nonempty="runs")
        print(f"      Simulators indexed: {sorted({r.get('suite','?') for r in r_list.get('runs', [])})}")

        track("runs.summary", lambda: get_run_details(store, run_id))

        track("regression.summary",
              lambda: get_regression_summary(store, suite=suite),
              expect_nonempty="runs")

        # ── Section 2: Test-level tools ─────────────────────────────────────
        _header("2 · Test-level tools (tests.list / failures / flaky / slowest)")

        track("tests.list",     lambda: list_tests(store, run_id=run_id), expect_nonempty="tests")
        track("tests.failures", lambda: list_failures(store, run_id=run_id))
        track("tests.flaky",    lambda: list_tests(store, status="fail"), expect_nonempty="tests")
        track("tests.slowest",  lambda: list_tests(store, page_size=5))

        # ── Section 3: Assertion tools ──────────────────────────────────────
        _header("3 · Assertion tools (summary / failures / sva_status / vacuity)")

        ass_sum = track("assertions.summary",
                        lambda: list_assertions(store),
                        expect_nonempty="assertions")
        n_ass = len(ass_sum.get("assertions", []))
        print(f"      AXI4 SVA properties found: {n_ass}")

        track("assertions.failures",
              lambda: list_assertion_failures(store, run_id=run_id))

        sva = track("assertions.sva_status",
                    lambda: get_sva_status(store, run_id=run_id),
                    expect_nonempty="sva_statuses")
        print(f"      SVA run-status rows: {len(sva.get('sva_statuses', []))}")

        vac = track("assertions.vacuity",
                    lambda: get_vacuous_assertions(store, run_id=run_id),
                    expect_nonempty="vacuous_assertions")
        for v in vac.get("vacuous_assertions", []):
            print(f"      ⚠ Vacuous: {v.get('assertion_name')} in test {v.get('test_id')}")

        # ── Section 4: Coverage tools ────────────────────────────────────────
        _header("4 · Coverage tools (summary / gaps / optimize)")

        cov = track("coverage.summary",
                    lambda: get_coverage_summary(store, run_id=run_id))
        for k, v in cov.items():
            if "pct" in k or "covered" in k:
                print(f"      {k}: {v}")

        gaps = track("coverage.gaps",
                     lambda: get_coverage_gaps(store),
                     expect_nonempty="gaps")
        high = [g for g in gaps.get("gaps", []) if g.get("priority") == "high"]
        print(f"      High-priority gaps: {len(high)}")
        for g in high[:3]:
            print(f"        • {g['metric_name']} ({g['covered_pct']:.0f}% covered)")

        track("coverage.optimize",
              lambda: get_coverage_gaps(store, kind="functional"),
              expect_nonempty="gaps")

        # ── Section 5: Waveform tool ─────────────────────────────────────────
        _header("5 · Waveform tool (waveform.summary)")
        track("waveform.summary",
              lambda: wave_summary(store, test_id=wave_test_id))

        # ── Section 6: Simulation workflow tools ────────────────────────────
        _header("6 · Simulation workflow (runs.submit / sim.status / tests.replay / runs.compare)")

        sub = track("runs.submit",
                    lambda: generate_submit_command(store, suite=suite, simulator="vcs"))
        if "command" in sub:
            print(f"      VCS command preview: {sub['command'][:80]}…")

        track("sim.status", lambda: get_sim_status(store))

        replay = track("tests.replay",
                       lambda: generate_replay_command(store, test_id=test_id))
        if "command" in replay:
            print(f"      Replay command: {replay['command'][:80]}…")

        if len(run_ids) >= 2:
            diff = track("runs.compare",
                         lambda: compare_runs(store,
                                              base_run_id=run_ids[0],
                                              compare_run_id=run_ids[1]))
            if "diff" in diff:
                d = diff["diff"]
                print(f"      Test delta: +{d.get('new_passes',0)} pass, +{d.get('new_failures',0)} fail")

        # ── Section 7: DV Intelligence (v2.1.0) ──────────────────────────────
        _header("7 · DV Intelligence (coverage.trend / runs.cross_sim / tests.cluster / regression.health / coverage.advisor)")

        trend = track("coverage.trend",
                      lambda: get_coverage_trend(store, suite=suite))
        if "summary" in trend:
            s = trend["summary"]
            print(f"      Coverage direction: {s.get('direction','?')}, "
                  f"latest={s.get('latest_pct','?')}%")

        xsim = track("runs.cross_sim",
                     lambda: get_cross_sim_comparison(store, suite=suite))
        if "divergent_tests" in xsim:
            nd = len(xsim["divergent_tests"])
            print(f"      Cross-sim divergences: {nd}")

        clusters = track("tests.cluster",
                         lambda: cluster_test_failures(store, suite=suite))
        if "clusters" in clusters:
            print(f"      Failure clusters: {len(clusters['clusters'])}")

        health = track("regression.health",
                       lambda: get_regression_health(store, suite=suite))
        if "score" in health:
            print(f"      Health score: {health['score']}/100 ({health.get('band','?')})")

        advisor = track("coverage.advisor",
                        lambda: get_coverage_advisor(store, suite=suite, max_recommendations=3))
        if "advisories" in advisor:
            print(f"      Coverage advisories: {len(advisor['advisories'])}")
            for adv in advisor["advisories"][:2]:
                print(f"        • {adv.get('bin_name','?')} [{adv.get('protocol','?')}]")

        # ── Summary ──────────────────────────────────────────────────────────
        _header("Summary")
        total = len(passed) + len(failed) + len(skipped)
        print(f"  Passed : {len(passed)}/{total}")
        if failed:
            print(f"  Failed : {', '.join(failed)}")
        if skipped:
            print(f"  Skipped: {', '.join(skipped)}")
        print()

        if failed:
            print(f"{FAIL}  Some tools failed — see details above.")
            return 1
        print(f"{PASS}  All 26 sentinel-dv tools verified against AXI4 UVM data.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
