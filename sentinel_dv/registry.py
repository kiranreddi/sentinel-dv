"""MCP tool registry metadata (names align with server.py decorators)."""

from __future__ import annotations

TOOL_NAMES: tuple[str, ...] = (
    "runs.list",
    "runs.get",
    "runs.summary",
    "runs.submit",
    "tests.list",
    "tests.get",
    "tests.history",
    "tests.topology",
    "tests.replay",
    "assertions.list",
    "assertions.get",
    "assertions.failures",
    "assertions.sva_status",
    "assertions.vacuity",
    "coverage.list",
    "coverage.summary",
    "coverage.gaps",
    "failures.list",
    "regressions.summary",
    "runs.diff",
    "sim.status",
    "wave.signals",
    "wave.summary",
    # DV Intelligence tools — v2.1.0
    "coverage.trend",
    "runs.cross_sim",
    "tests.cluster",
    "regression.health",
    "coverage.advisor",
)

TOOL_COUNT = len(TOOL_NAMES)
