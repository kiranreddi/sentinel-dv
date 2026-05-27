"""Extract a bounded waveform summary from VCD files (no EDA license required)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_VAR_RE = re.compile(
    r"^\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(\S+)\s+.*\$end\s*$"
)
_TIMESCALE_RE = re.compile(
    r"^\$timescale\s+(\d+)\s*(s|ms|us|ns|ps|fs)\s+\$end\s*$",
    re.IGNORECASE,
)

# VCD timestamp unit → nanoseconds per count
_UNIT_TO_NS: dict[str, float] = {
    "fs": 1e-6,
    "ps": 1e-3,
    "ns": 1.0,
    "us": 1e3,
    "ms": 1e6,
    "s": 1e9,
}


class VcdSummaryParser:
    """Parse VCD value-change dumps into precomputed summary dicts."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".vcd"

    def parse(
        self,
        path: Path,
        test_name: str | None = None,
        start_time_ns: int | None = None,
        end_time_ns: int | None = None,
    ) -> dict[str, Any]:
        """Parse VCD and return a waveform summary compatible with indexing."""
        if start_time_ns is not None and end_time_ns is not None and start_time_ns > end_time_ns:
            raise ValueError("start_time_ns must be <= end_time_ns")

        signals: dict[str, dict[str, Any]] = {}
        timescale_ns = 1.0  # default 1 ns per # tick if header missing
        current_time_raw = 0
        current_time_ns = 0.0

        pre_window: dict[str, str] = {}
        running: dict[str, str | None] = {}
        start_values: dict[str, str | None] = {}
        end_values: dict[str, str | None] = {}
        toggles: dict[str, int] = {}

        def in_window(time_ns: float) -> bool:
            if start_time_ns is not None and time_ns < start_time_ns:
                return False
            if end_time_ns is not None and time_ns > end_time_ns:
                return False
            return True

        def apply_value(sig_id: str, value: str, time_ns: float) -> None:
            if sig_id not in signals:
                return
            prev = running.get(sig_id)
            name = signals[sig_id]["name"]

            if start_time_ns is not None and time_ns < start_time_ns:
                pre_window[name] = value
                running[sig_id] = value
                return

            if end_time_ns is not None and time_ns > end_time_ns:
                return

            if name not in start_values:
                start_values[name] = pre_window.get(name, prev)

            if prev is not None and prev != value:
                toggles[name] = toggles.get(name, 0) + 1

            running[sig_id] = value
            end_values[name] = value

        with open(path, encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue

                if line.startswith("$timescale"):
                    match = _TIMESCALE_RE.match(line)
                    if match:
                        amount = int(match.group(1))
                        unit = match.group(2).lower()
                        timescale_ns = amount * _UNIT_TO_NS[unit]
                    continue

                if line.startswith("$"):
                    if line.startswith("$var"):
                        match = _VAR_RE.match(line)
                        if match:
                            _vtype, width, sig_id, name = match.groups()
                            signals[sig_id] = {
                                "name": name,
                                "width": int(width),
                                "group": "vcd",
                            }
                            running[sig_id] = None
                    continue

                if line.startswith("#"):
                    try:
                        current_time_raw = int(line[1:])
                    except ValueError:
                        continue
                    current_time_ns = current_time_raw * timescale_ns
                    continue

                if line.startswith("b") and " " in line:
                    value, sig_id = line[1:].split(" ", 1)
                    sig_id = sig_id.strip()
                else:
                    value = line[0]
                    sig_id = line[1:].strip()

                apply_value(sig_id, value, current_time_ns)

        merged: dict[str, dict[str, Any]] = {}
        for entry in signals.values():
            name = entry["name"]
            if name not in merged:
                merged[name] = {"name": name, "group": "vcd", "width": entry["width"]}
        signal_list = [
            {
                "name": name,
                "group": meta["group"],
                "width": meta["width"],
                "toggles": toggles.get(name, 0),
                "last_value": end_values.get(name) or pre_window.get(name),
                "value_at_start": start_values.get(name),
                "value_at_end": end_values.get(name),
            }
            for name, meta in sorted(merged.items(), key=lambda item: item[0])
        ]

        if not signal_list:
            raise ValueError(f"No signals found in VCD: {path}")

        trace_end_ns = int(current_time_ns)
        resolved_test_name = test_name or self._test_name_from_path(path)
        window_meta = {
            "start_time_ns": start_time_ns,
            "end_time_ns": end_time_ns,
            "timescale": f"{timescale_ns} ns per VCD tick",
            "trace_end_time_ns": trace_end_ns,
        }

        return {
            "test_name": resolved_test_name,
            "framework": "verilator",
            "format": "vcd-summary",
            "end_time_ns": end_time_ns if end_time_ns is not None else trace_end_ns,
            "signal_count": len(signal_list),
            "signals": signal_list,
            "highlights": self._highlights(signal_list, start_time_ns, end_time_ns, trace_end_ns),
            "metadata": {
                "source_vcd": path.name,
                "parser": "sentinel-dv-vcd-summary",
                "window": window_meta,
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
        signal_list: list[dict[str, Any]],
        start_time_ns: int | None,
        end_time_ns: int | None,
        trace_end_ns: int,
    ) -> list[dict[str, Any]]:
        """Build highlights for window boundaries and busiest signals."""
        highlights: list[dict[str, Any]] = []
        t_start = start_time_ns if start_time_ns is not None else 0
        t_end = end_time_ns if end_time_ns is not None else trace_end_ns

        for entry in sorted(signal_list, key=lambda s: s.get("toggles", 0), reverse=True)[:3]:
            highlights.append(
                {
                    "time_ns": t_end,
                    "signal": entry["name"],
                    "value": entry.get("value_at_end") or entry.get("last_value"),
                    "note": f"{entry.get('toggles', 0)} toggles in window",
                }
            )

        if signal_list:
            busiest = max(signal_list, key=lambda s: s.get("toggles", 0))
            highlights.insert(
                0,
                {
                    "time_ns": t_start,
                    "signal": busiest["name"],
                    "value": busiest.get("value_at_start"),
                    "note": "value at window start",
                },
            )
        return highlights[:5]
