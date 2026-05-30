#!/usr/bin/env python3
"""live_sim_writer.py — Reference harness: write live_status.json for sim.status MCP tool.

The ``sim.status`` tool reads a ``live_status.json`` file from the artifact root
to provide real-time simulation progress to MCP clients.  Run this script from
your simulator wrapper / makefile alongside the simulator process to continuously
update the status file while the simulation runs.

Usage
-----
  # Wrap your simulator call:
  python examples/live_sim_writer.py --artifact-root /path/to/run/dir \\
      --total 500 -- vcs -R simv +plusarg=value ...

  # Or drive it from a Python test harness:
  from examples.live_sim_writer import LiveStatusWriter
  writer = LiveStatusWriter(artifact_root=Path("."), total_tests=100)
  writer.update(phase="running", tests_done=42)

Output
------
  <artifact_root>/live_status.json  — polled by ``sim.status`` MCP tool

JSON schema (subset supported by LiveSimAdapter)
-------------------------------------------------
  {
    "phase":        "compiling" | "running" | "done" | "failed",
    "tests_total":  <int>,
    "tests_done":   <int>,
    "tests_passed": <int>,
    "tests_failed": <int>,
    "percent_done": <float>,   # written by this script; adapter also computes it
    "simulator":    <str>,     # e.g. "vcs", "questa", "xcelium"
    "suite":        <str>,     # optional suite name
    "updated_at":   <ISO-8601> # wall-clock timestamp, used for staleness detection
  }
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Writer helper
# ---------------------------------------------------------------------------

class LiveStatusWriter:
    """Write / update ``live_status.json`` in *artifact_root*."""

    FILENAME = "live_status.json"

    def __init__(
        self,
        artifact_root: Path,
        *,
        total_tests: int = 0,
        simulator: str = "",
        suite: str = "",
    ) -> None:
        self.artifact_root = Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self._path = self.artifact_root / self.FILENAME
        self._total = total_tests
        self._simulator = simulator
        self._suite = suite
        self._done = 0
        self._passed = 0
        self._failed = 0

    # ------------------------------------------------------------------
    def update(
        self,
        *,
        phase: str = "running",
        tests_done: int | None = None,
        tests_passed: int | None = None,
        tests_failed: int | None = None,
    ) -> None:
        """Atomically update the status file."""
        if tests_done is not None:
            self._done = tests_done
        if tests_passed is not None:
            self._passed = tests_passed
        if tests_failed is not None:
            self._failed = tests_failed

        pct = (self._done / self._total * 100.0) if self._total > 0 else 0.0

        payload: dict = {
            "phase": phase,
            "tests_total": self._total,
            "tests_done": self._done,
            "tests_passed": self._passed,
            "tests_failed": self._failed,
            "percent_done": round(pct, 1),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._simulator:
            payload["simulator"] = self._simulator
        if self._suite:
            payload["suite"] = self._suite

        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self._path)  # atomic rename

    def finish(self, *, success: bool) -> None:
        """Mark the run as done / failed."""
        self.update(
            phase="done" if success else "failed",
            tests_done=self._total,
        )

    @property
    def path(self) -> Path:
        return self._path


# ---------------------------------------------------------------------------
# Subprocess wrapper
# ---------------------------------------------------------------------------

def _detect_simulator(cmd: list[str]) -> str:
    for token in cmd:
        base = Path(token).name.lower()
        if base in {"vcs", "simv"}:
            return "vcs"
        if base in {"vsim", "questa"}:
            return "questa"
        if base in {"xrun", "irun", "xcelium"}:
            return "xcelium"
    return ""


def run_with_live_status(
    cmd: list[str],
    artifact_root: Path,
    total_tests: int,
    suite: str = "",
    poll_seconds: float = 5.0,
) -> int:
    """Run *cmd* as a subprocess; update live_status.json while it runs.

    Returns the process exit code.
    """
    simulator = _detect_simulator(cmd)
    writer = LiveStatusWriter(
        artifact_root,
        total_tests=total_tests,
        simulator=simulator,
        suite=suite,
    )
    writer.update(phase="running")
    print(f"[live_sim_writer] status file: {writer.path}", file=sys.stderr)

    proc = subprocess.Popen(cmd)  # noqa: S603
    while proc.poll() is None:
        time.sleep(poll_seconds)
        writer.update(phase="running")  # refresh updated_at so client knows we're alive

    success = proc.returncode == 0
    writer.finish(success=success)
    print(
        f"[live_sim_writer] finished rc={proc.returncode} phase={'done' if success else 'failed'}",
        file=sys.stderr,
    )
    return proc.returncode


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Wrap a simulator command and emit live_status.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--artifact-root", required=True, help="Directory to write live_status.json")
    p.add_argument("--total", type=int, default=0, metavar="N", help="Total test count (0 = unknown)")
    p.add_argument("--suite", default="", help="Suite name for the status file")
    p.add_argument("--poll", type=float, default=5.0, metavar="SECONDS", help="Heartbeat interval")
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="Simulator command (after --)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("Error: no simulator command provided after --", file=sys.stderr)
        sys.exit(1)

    rc = run_with_live_status(
        cmd,
        artifact_root=Path(args.artifact_root),
        total_tests=args.total,
        suite=args.suite,
        poll_seconds=args.poll,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
