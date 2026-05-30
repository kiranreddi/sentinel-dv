"""Coverage gap analysis and recommendation engine.

Analyses indexed coverage metrics to identify uncovered areas and
generate actionable, prioritised recommendations for test engineers.

This module does *not* run any simulators — it operates only on data
already stored in the :class:`~sentinel_dv.indexing.store.IndexStore`.
"""

from __future__ import annotations

import re
from typing import Any

from sentinel_dv.schemas.coverage import CoverageGap, GapPriority

# Patterns whose metric names indicate higher-priority coverage targets.
_HIGH_PRIORITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\berror\b", re.I),
    re.compile(r"\bexception\b", re.I),
    re.compile(r"\bfault\b", re.I),
    re.compile(r"\bcorner\b", re.I),
    re.compile(r"\bboundary\b", re.I),
    re.compile(r"\bmax\b", re.I),
    re.compile(r"\bmin\b", re.I),
    re.compile(r"\boverflow\b", re.I),
    re.compile(r"\bunderflow\b", re.I),
    re.compile(r"\btimeout\b", re.I),
    re.compile(r"\bbackpressure\b", re.I),
]

_MEDIUM_PRIORITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bburst\b", re.I),
    re.compile(r"\bnarrow\b", re.I),
    re.compile(r"\bunaligned\b", re.I),
    re.compile(r"\bwrap\b", re.I),
    re.compile(r"\bincr\b", re.I),
    re.compile(r"\bfixed\b", re.I),
]


def _classify_priority(metric_name: str, covered_pct: float) -> GapPriority:
    """Classify gap priority from metric name keywords and coverage depth.

    Very low coverage (< 25%) is always high priority regardless of name.
    Matching high-priority keywords → high.
    Matching medium-priority keywords → medium.
    Remaining → low if > 50%, else medium.
    """
    if covered_pct < 25.0:
        return "high"

    name_lower = metric_name.lower()
    for pattern in _HIGH_PRIORITY_PATTERNS:
        if pattern.search(name_lower):
            return "high"
    for pattern in _MEDIUM_PRIORITY_PATTERNS:
        if pattern.search(name_lower):
            return "medium"
    return "low" if covered_pct >= 50.0 else "medium"


def _build_recommendation(
    metric_name: str,
    scope: str,
    bins_missed: list[str],
    kind: str,
    covered_pct: float,
) -> str:
    """Generate an actionable recommendation string for a coverage gap.

    Recommendations are deterministic based on metric name patterns.
    They are guidance only — no simulator commands are generated here.
    """
    name_lower = metric_name.lower()

    if bins_missed:
        bin_list = ", ".join(f"'{b}'" for b in bins_missed[:5])
        suffix = f" Specifically, target: {bin_list}." if bins_missed else ""
    else:
        suffix = ""

    if kind == "toggle":
        return (
            f"Toggle coverage gap in '{metric_name}' (scope: {scope}, "
            f"{covered_pct:.1f}% covered). "
            "Add directed sequences that drive all logic values (0→1 and 1→0) on "
            "these signals. Consider adding constrained-random tests targeting the "
            "uncovered pins." + suffix
        )

    if kind == "fsm":
        return (
            f"FSM state/transition gap in '{metric_name}' (scope: {scope}, "
            f"{covered_pct:.1f}% covered). "
            "Add tests that exercise the missing FSM states and transitions. "
            "Check whether the uncovered arcs require specific protocol sequences "
            "or error injection to reach." + suffix
        )

    if kind == "code":
        return (
            f"Code coverage gap in '{metric_name}' (scope: {scope}, "
            f"{covered_pct:.1f}% covered). "
            "Add directed tests targeting the uncovered branches/lines. "
            "Review conditional expressions — the uncovered path may require "
            "a specific input value combination." + suffix
        )

    if "error" in name_lower or "fault" in name_lower or "exception" in name_lower:
        return (
            f"Error/exception coverage gap in '{metric_name}' (scope: {scope}, "
            f"{covered_pct:.1f}% covered). "
            "Add error injection tests that trigger the uncovered error conditions. "
            "These are high-priority — error handling paths are often regression-critical." + suffix
        )

    if "burst" in name_lower or "len" in name_lower:
        return (
            f"Burst/length coverage gap in '{metric_name}' (scope: {scope}, "
            f"{covered_pct:.1f}% covered). "
            "Add transactions spanning the full range of allowed burst lengths. "
            "Include both minimum and maximum length values." + suffix
        )

    return (
        f"Functional coverage gap in '{metric_name}' (scope: {scope}, "
        f"{covered_pct:.1f}% covered). "
        "Add constrained-random or directed tests targeting the uncovered bins. "
        "Consider increasing the test seed space or adding a dedicated directed test." + suffix
    )


def generate_recommendations(
    metrics: list[dict[str, Any]],
    threshold_pct: float = 100.0,
    max_gaps: int = 100,
) -> list[CoverageGap]:
    """Analyse coverage metrics and return prioritised gap recommendations.

    Args:
        metrics: List of metric dicts from ``IndexStore.query_coverage_metrics``
            (or compatible dicts with keys: ``name``, ``scope``, ``covered``,
            ``kind``, ``bins_missed``).
        threshold_pct: Metrics with ``covered`` below this threshold are gaps.
            Pass ``100.0`` (default) to report any metric below full coverage.
        max_gaps: Maximum gaps to return.

    Returns:
        List of :class:`~sentinel_dv.schemas.coverage.CoverageGap` instances,
        sorted by priority (high→medium→low) then by coverage percentage ascending.
    """
    _PRIORITY_ORDER: dict[GapPriority, int] = {"high": 0, "medium": 1, "low": 2}
    gaps: list[CoverageGap] = []

    for metric in metrics:
        covered_pct = float(metric.get("covered", 100.0))
        if covered_pct >= threshold_pct:
            continue

        name = str(metric.get("name", "unknown"))
        scope = str(metric.get("scope", "unknown"))
        kind = str(metric.get("kind", "functional"))
        bins_missed: list[str] = metric.get("bins_missed") or []
        if isinstance(bins_missed, str):
            import json as _json
            try:
                bins_missed = _json.loads(bins_missed)
            except Exception:
                bins_missed = []

        priority = _classify_priority(name, covered_pct)
        recommendation = _build_recommendation(name, scope, bins_missed, kind, covered_pct)

        gaps.append(
            CoverageGap(
                metric_name=name,
                scope=scope,
                kind=kind,  # type: ignore[arg-type]
                covered_pct=round(covered_pct, 2),
                bins_missed=bins_missed[:50],
                priority=priority,
                recommendation=recommendation,
            )
        )

    gaps.sort(key=lambda g: (_PRIORITY_ORDER[g.priority], g.covered_pct))
    return gaps[:max_gaps]
