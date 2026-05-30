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
    # VCS URG HTML report (from 'urg -report')
    "dashboard.html",
    # Questa HTML report data file (from 'vcover -html')
    "overalldu.js",
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

# Optional "scope : kind coverage: pct%" pattern — scope requires a colon delimiter
# to avoid greedy scope eating part of a bare "kind coverage: pct%" line.
_LINE_PATTERN = re.compile(
    r"^(?:(?P<scope>[\w.$]+)\s*:\s*)?(?P<kind>\w+)\s+coverage:\s*(?P<pct>[\d.]+)\s*%",
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
        if name == "dashboard.html":
            return self._is_urg_dashboard(path)
        if name == "overalldu.js":
            return self._is_questa_overalldu(path)
        return False

    @staticmethod
    def _is_urg_dashboard(path: Path) -> bool:
        """Return True if this is a VCS URG dashboard.html (not some other dashboard)."""
        try:
            snippet = path.read_text(encoding="utf-8", errors="replace")[:2000]
            return "Total Coverage Summary" in snippet or "Unified Coverage Report" in snippet
        except OSError:
            return False

    @staticmethod
    def _is_questa_overalldu(path: Path) -> bool:
        """Return True if this is a Questa vcover overalldu.js data file."""
        try:
            # File is one long line; read enough to find both patterns
            snippet = path.read_text(encoding="utf-8", errors="replace")[:8000]
            return "processOverallduData" in snippet or (
                "var g_data" in snippet and '"ds":{' in snippet
            )
        except OSError:
            return False

    def parse(self, path: Path) -> dict[str, Any]:
        """Return {test_name?, kind, metrics: [...], source_path}."""
        name = path.name.lower()
        if name == "dashboard.html":
            return self._parse_urg_html(path)
        if name == "overalldu.js":
            return self._parse_questa_overalldu(path)
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

    def _parse_urg_html(self, path: Path) -> dict[str, Any]:
        """Parse VCS URG dashboard.html for overall coverage metrics.

        VCS URG 'Total Coverage Summary' table layout:
          SCORE | LINE | TOGGLE | ASSERT | GROUP
          48.57 | 65.68 | 52.08 | 27.97 | 48.53
        """
        content = path.read_text(encoding="utf-8", errors="replace")
        metrics: list[dict[str, Any]] = []

        # Find the "Total Coverage Summary" block
        tcs_match = re.search(
            r"Total Coverage Summary.*?<tr[^>]*>(.*?)</tr>",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if tcs_match:
            # Header row: SCORE LINE TOGGLE ASSERT GROUP
            header_match = re.search(
                r"Total Coverage Summary.*?<tr[^>]*>(.*?)</tr>\s*<tr[^>]*>(.*?)</tr>",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if header_match:
                header_html = header_match.group(1)
                data_html = header_match.group(2)
                headers = re.findall(r"<td[^>]*>\s*([A-Z]+)\s*</td>", header_html, re.IGNORECASE)
                values = re.findall(r"<td[^>]*>\s*([\d.]+)\s*</td>", data_html)
                col_map = {
                    "LINE": "line",
                    "TOGGLE": "toggle",
                    "ASSERT": "assertion",
                    "GROUP": "functional",
                    "SCORE": "code",
                }
                for col, val in zip(headers, values, strict=False):
                    kind_name = col_map.get(col.upper())
                    if kind_name:
                        metrics.append(
                            _normalize_metric(
                                {
                                    "name": kind_name,
                                    "scope": "top",
                                    "covered": float(val),
                                    "hits": int(float(val)),
                                    "total": 100,
                                }
                            )
                        )

        # Also extract verification plan score if present
        vplan_match = re.search(
            r"Scores for Verification Plan.*?<td[^>]*>\s*([\d.]+)\s*</td>",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if vplan_match:
            metrics.append(
                _normalize_metric(
                    {
                        "name": "functional",
                        "scope": "verification_plan",
                        "covered": float(vplan_match.group(1)),
                        "hits": int(float(vplan_match.group(1))),
                        "total": 100,
                    }
                )
            )

        if not metrics:
            # Generic fallback: pick any percentage numbers after summary headers
            for m in re.finditer(
                r"(LINE|TOGGLE|ASSERT|SCORE|GROUP)\b.*?([\d.]+)", content, re.IGNORECASE | re.DOTALL
            ):
                col = m.group(1).upper()
                kind_name = {
                    "LINE": "line",
                    "TOGGLE": "toggle",
                    "ASSERT": "assertion",
                    "GROUP": "functional",
                    "SCORE": "code",
                }.get(col)
                if kind_name:
                    metrics.append(
                        _normalize_metric(
                            {
                                "name": kind_name,
                                "scope": "top",
                                "covered": float(m.group(2)),
                                "hits": int(float(m.group(2))),
                                "total": 100,
                            }
                        )
                    )

        metrics = self._bound_metrics(metrics) or [
            _normalize_metric({"name": "code", "scope": "top", "covered": 0.0})
        ]
        return {
            "test_name": None,
            "kind": "code",
            "metrics": metrics,
            "source_path": path.name,
            "tool": "vcs_urg",
        }

    # Questa overalldu.js field key mapping
    # ds.s = statement, ds.b = branch, ds.t = toggle, ds.a = assertion
    # ds.g = covergroup/functional, ds.tc = total coverage
    _QUESTA_DS_MAP = {
        "s": ("statement", "code"),
        "b": ("branch", "code"),
        "t": ("toggle", "toggle"),
        "a": ("assertion", "assertion"),
        "g": ("functional", "functional"),
    }

    def _parse_questa_overalldu(self, path: Path) -> dict[str, Any]:
        """Parse Questa vcover overalldu.js for overall coverage metrics.

        Questa data format in overalldu.js:
          var g_data = {..., "ds": {"s":[total,covered,pct], "b":[...], ...}};
        Keys: s=statement, b=branch, t=toggle, a=assertion, g=functional, tc=total
        """
        content = path.read_text(encoding="utf-8", errors="replace")
        metrics: list[dict[str, Any]] = []

        # Extract the g_data object using a balanced-brace scan
        m_start = re.search(r"var\s+g_data\s*=\s*\{", content)
        if m_start:
            start = m_start.end() - 1  # position of opening '{'
            depth = 0
            end = start
            for i, ch in enumerate(content[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            try:
                data = json.loads(content[start:end])
                ds = data.get("ds", {})
                for key, (metric_name, _kind_name) in self._QUESTA_DS_MAP.items():
                    entry = ds.get(key)
                    if entry and isinstance(entry, list) and len(entry) >= 3:
                        total_items, covered_items, pct = entry[0], entry[1], entry[2]
                        if pct >= 0:  # -1.00 means not applicable
                            metrics.append(
                                _normalize_metric(
                                    {
                                        "name": metric_name,
                                        "scope": "top",
                                        "covered": float(pct),
                                        "hits": int(covered_items) if covered_items >= 0 else None,
                                        "total": int(total_items) if total_items >= 0 else None,
                                    }
                                )
                            )
                # Overall total coverage
                tc = ds.get("tc")
                if tc is not None and float(tc) >= 0:
                    metrics.append(
                        _normalize_metric(
                            {
                                "name": "total",
                                "scope": "top",
                                "covered": float(tc),
                                "hits": int(tc),
                                "total": 100,
                            }
                        )
                    )
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        metrics = self._bound_metrics(metrics) or [
            _normalize_metric({"name": "functional", "scope": "top", "covered": 0.0})
        ]
        return {
            "test_name": None,
            "kind": "functional",
            "metrics": metrics,
            "source_path": path.name,
            "tool": "questa_vcover",
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
