"""MCP tool registry metadata (names align with server.py decorators)."""

from __future__ import annotations

TOOL_NAMES: tuple[str, ...] = (
    "runs.list",
    "runs.get",
    "tests.list",
    "tests.get",
    "tests.topology",
    "assertions.list",
    "assertions.get",
    "assertions.failures",
    "coverage.list",
    "coverage.summary",
    "failures.list",
    "regressions.summary",
    "runs.diff",
    "wave.signals",
    "wave.summary",
)

TOOL_COUNT = len(TOOL_NAMES)
