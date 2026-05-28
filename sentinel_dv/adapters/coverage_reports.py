"""Parse exported coverage summaries (JSON, text, XML) — no proprietary DB APIs."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

COVERAGE_GLOBS: tuple[str, ...] = (
    "coverage.json",
    "coverage_summary.json",
    "coverage.txt",
    "coverage_summary.txt",
    "coverage.xml",
    "*.cov.json",
    "*.cov.txt",
    "coverage.dat.summary",
)

_KIND_MAP = {
    "line": "code",
    "branch": "code",
    "toggle": "toggle",
    "fsm": "fsm",
    "functional": "functional",
    "assert": "assertion",
    "assertion": "assertion",
    "code": "code",
}

_LINE_PATTERN = re.compile(
    r"^(?P<scope>[\w.$]+)?\s*:?\s*(?P<kind>\w+)\s+coverage:\s*(?P<pct>[\d.]+)\s*%",
    re.IGNORECASE | re.MULTILINE,
)


class CoverageReportParser:
    """Parse bounded coverage summaries for indexing."""

    def __init__(
        self,
        max_metrics: int = 200,
        max_bins_missed: int = 50,
    ) -> None:
        self.max_metrics = max_metrics
        self.max_bins_missed = max_bins_missed

    def can_handle(self, path: Path) -> bool:
        name = path.name.lower()
        if name in {"coverage.json", "coverage_summary.json", "coverage.xml"}:
            return True
        if name.endswith(".cov.json") or name.endswith(".cov.txt"):
            return True
        if name == "coverage.dat.summary":
            return True
        if name in {"coverage.txt", "coverage_summary.txt"}:
            return True
        return False

    def parse(self, path: Path) -> dict[str, Any]:
        """Return {test_name?, kind, metrics: [...], source_path}."""
        name = path.name.lower()
        if path.suffix.lower() == ".json" or name.endswith(".cov.json"):
            return self._parse_json(path)
        if path.suffix.lower() == ".xml" or name == "coverage.xml":
            return self._parse_xml(path)
        return self._parse_text(path)

    def _parse_json(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        kind = _detect_kind(data.get("kind"), data.get("metrics", []))
        metrics = [_normalize_metric(m) for m in data.get("metrics", [])]
        metrics = self._bound_metrics(metrics)
        return {
            "test_name": data.get("test_name"),
            "kind": kind,
            "metrics": metrics,
            "source_path": path.name,
        }

    def _parse_xml(self, path: Path) -> dict[str, Any]:
        root = ET.parse(path).getroot()
        metrics: list[dict[str, Any]] = []
        for elem in root.iter():
            if elem.tag.lower() in {"class", "package", "counter"}:
                line_rate = elem.get("line-rate") or elem.get("line_rate")
                if line_rate is not None:
                    metrics.append(
                        _normalize_metric(
                            {
                                "name": "line",
                                "scope": elem.get("name", "top"),
                                "covered": float(line_rate) * 100.0,
                                "hits": int(float(line_rate) * 100),
                                "total": 100,
                            }
                        )
                    )
        metrics = self._bound_metrics(metrics) or [
            _normalize_metric({"name": "line", "scope": "top", "covered": 0.0})
        ]
        return {
            "test_name": None,
            "kind": "code",
            "metrics": metrics,
            "source_path": path.name,
        }

    def _parse_text(self, path: Path) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8", errors="replace")
        metrics: list[dict[str, Any]] = []
        for match in _LINE_PATTERN.finditer(content):
            raw_kind = match.group("kind").lower()
            metrics.append(
                _normalize_metric(
                    {
                        "name": raw_kind,
                        "scope": (match.group("scope") or "top").strip(),
                        "covered": float(match.group("pct")),
                        "hits": int(float(match.group("pct"))),
                        "total": 100,
                    }
                )
            )
        if not metrics and "line" in content.lower():
            for match in re.finditer(r"([\w.]+)\s+coverage:\s*([\d.]+)%", content, re.IGNORECASE):
                raw = match.group(1).lower()
                metrics.append(
                    _normalize_metric(
                        {
                            "name": raw,
                            "scope": "top",
                            "covered": float(match.group(2)),
                            "hits": int(float(match.group(2))),
                            "total": 100,
                        }
                    )
                )
        metrics = self._bound_metrics(metrics) or [
            _normalize_metric({"name": "line", "scope": "top", "covered": 0.0})
        ]
        kind = _detect_kind(None, metrics)
        return {
            "test_name": None,
            "kind": kind,
            "metrics": metrics,
            "source_path": path.name,
        }

    def _bound_metrics(self, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        metrics = sorted(metrics, key=lambda m: (m["scope"], m["name"]))
        out: list[dict[str, Any]] = []
        for m in metrics[: self.max_metrics]:
            bins = m.get("bins_missed") or []
            if len(bins) > self.max_bins_missed:
                m = {**m, "bins_missed": bins[: self.max_bins_missed], "bins_truncated": True}
            out.append(m)
        return out


def _normalize_metric(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name", "line")).lower()
    scope = str(raw.get("scope", "top"))
    covered = float(raw.get("covered", 0.0))
    hits = raw.get("hits")
    total = raw.get("total")
    if hits is None and total is None:
        hits = int(covered)
        total = 100
    metric: dict[str, Any] = {
        "name": name,
        "scope": scope,
        "covered": covered,
        "hits": int(hits) if hits is not None else None,
        "total": int(total) if total is not None else None,
    }
    if raw.get("bins_missed"):
        metric["bins_missed"] = list(raw["bins_missed"])
    return metric


def _detect_kind(explicit: str | None, metrics: list[dict[str, Any]]) -> str:
    if explicit:
        k = str(explicit).lower()
        return _KIND_MAP.get(k, k if k in _KIND_MAP.values() else "functional")
    names = " ".join(m["name"] for m in metrics).lower()
    for key, kind in _KIND_MAP.items():
        if key in names:
            return kind
    return "functional"
