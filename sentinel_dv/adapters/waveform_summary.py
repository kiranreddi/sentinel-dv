"""Parser for precomputed waveform summary JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WAVEFORM_GLOBS = ("*.wave.json", "*_waveform.json", "waveform_summary.json")


class WaveformSummaryParser:
    """Parse precomputed waveform summaries (no FSDB/VCD binary parsing)."""

    def can_handle(self, path: Path) -> bool:
        name = path.name.lower()
        if name == "waveform_summary.json":
            return True
        return name.endswith(".wave.json") or name.endswith("_waveform.json")

    def parse(self, path: Path) -> dict[str, Any]:
        """Parse and normalize a waveform summary JSON file."""
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise ValueError(f"Waveform summary must be a JSON object: {path}")

        test_name = data.get("test_name")
        if not test_name or not isinstance(test_name, str):
            raise ValueError(f"Waveform summary missing string test_name: {path}")

        signals = self._normalize_signals(data)
        if not signals:
            raise ValueError(f"Waveform summary has no signals: {path}")

        highlights = data.get("highlights", [])
        if highlights is not None and not isinstance(highlights, list):
            raise ValueError(f"Waveform highlights must be a list: {path}")

        return {
            "test_name": test_name,
            "framework": data.get("framework"),
            "format": str(data.get("format", "precomputed")),
            "end_time_ns": data.get("end_time_ns"),
            "signal_count": len(signals),
            "signals": signals,
            "highlights": highlights or [],
            "metadata": data.get("metadata", {}),
        }

    def _normalize_signals(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten signal_groups or top-level signals into a uniform list."""
        if isinstance(data.get("signals"), list):
            normalized = [self._normalize_signal(entry, group=None) for entry in data["signals"]]
            return sorted(normalized, key=lambda s: s["name"])

        groups = data.get("signal_groups")
        if not isinstance(groups, list):
            return []

        flattened: list[dict[str, Any]] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_name = group.get("name", "default")
            group_signals = group.get("signals", [])
            if not isinstance(group_signals, list):
                continue
            for entry in group_signals:
                flattened.append(self._normalize_signal(entry, group=str(group_name)))
        return sorted(flattened, key=lambda s: s["name"])

    @staticmethod
    def _normalize_signal(entry: Any, group: str | None) -> dict[str, Any]:
        if not isinstance(entry, dict):
            raise ValueError("Each signal entry must be an object")
        name = entry.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("Each signal must have a string name")

        signal: dict[str, Any] = {
            "name": name,
            "group": entry.get("group", group),
            "width": entry.get("width"),
            "toggles": entry.get("toggles"),
            "last_value": entry.get("last_value"),
        }
        if entry.get("note"):
            signal["note"] = str(entry["note"])
        return signal
