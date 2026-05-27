"""Extract a bounded waveform summary from VCD files (no EDA license required)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_VAR_RE = re.compile(
    r"^\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(\S+)\s+.*\$end\s*$"
)


class VcdSummaryParser:
    """Parse VCD value-change dumps into precomputed summary dicts."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".vcd"

    def parse(self, path: Path, test_name: str | None = None) -> dict[str, Any]:
        """Parse VCD and return a waveform summary compatible with indexing."""
        signals: dict[str, dict[str, Any]] = {}
        current_time = 0
        end_time_ns = 0

        with open(path, encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("$"):
                    if line.startswith("$var"):
                        match = _VAR_RE.match(line)
                        if match:
                            _vtype, width, sig_id, name = match.groups()
                            signals[sig_id] = {
                                "name": name,
                                "width": int(width),
                                "toggles": 0,
                                "last_value": None,
                                "group": "vcd",
                            }
                    continue

                if line.startswith("#"):
                    try:
                        current_time = int(line[1:])
                    except ValueError:
                        continue
                    end_time_ns = max(end_time_ns, current_time)
                    continue

                if line.startswith("b") and " " in line:
                    value, sig_id = line[1:].split(" ", 1)
                    sig_id = sig_id.strip()
                else:
                    value = line[0]
                    sig_id = line[1:].strip()

                entry = signals.get(sig_id)
                if not entry:
                    continue
                if entry["last_value"] is not None and entry["last_value"] != value:
                    entry["toggles"] += 1
                entry["last_value"] = value

        merged: dict[str, dict[str, Any]] = {}
        for entry in signals.values():
            name = entry["name"]
            if name in merged:
                merged[name]["toggles"] += entry["toggles"]
                merged[name]["last_value"] = entry["last_value"]
            else:
                merged[name] = dict(entry)

        signal_list = [
            {
                "name": s["name"],
                "group": s["group"],
                "width": s["width"],
                "toggles": s["toggles"],
                "last_value": s["last_value"],
            }
            for s in sorted(merged.values(), key=lambda item: item["name"])
        ]
        if not signal_list:
            raise ValueError(f"No signals found in VCD: {path}")

        resolved_test_name = test_name or self._test_name_from_path(path)
        return {
            "test_name": resolved_test_name,
            "framework": "verilator",
            "format": "vcd-summary",
            "end_time_ns": end_time_ns,
            "signal_count": len(signal_list),
            "signals": signal_list,
            "highlights": self._highlights(signal_list, end_time_ns),
            "metadata": {
                "source_vcd": path.name,
                "parser": "sentinel-dv-vcd-summary",
            },
        }

    @staticmethod
    def _test_name_from_path(path: Path) -> str:
        stem = path.stem
        if stem.endswith(".wave"):
            stem = stem[: -len(".wave")]
        return stem

    @staticmethod
    def _highlights(
        signal_list: list[dict[str, Any]], end_time_ns: int
    ) -> list[dict[str, Any]]:
        """Pick a few interesting signals for summary highlights."""
        by_toggles = sorted(signal_list, key=lambda s: s.get("toggles", 0), reverse=True)
        highlights: list[dict[str, Any]] = []
        for entry in by_toggles[:3]:
            highlights.append(
                {
                    "time_ns": end_time_ns,
                    "signal": entry["name"],
                    "value": entry.get("last_value"),
                    "note": f"{entry.get('toggles', 0)} toggles in VCD window",
                }
            )
        return highlights
