"""Parse exported assertion reports and simulator assertion output."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sentinel_dv.adapters.protocol_tags import (
    detect_protocols,
    normalize_assertion_file,
    normalize_scope,
    primary_protocol,
)
from sentinel_dv.normalization.redaction import Redactor
from sentinel_dv.utils.bounded_text import truncate_text

ASSERTION_GLOBS: tuple[str, ...] = (
    "assertions*.rpt",
    "assert*.txt",
    "assertion_summary*.txt",
    "vsim_assertions*.log",
    "questa_assertions*.txt",
    "urgReport/assertions*.txt",
    "vcs_assert*.log",
    "*.assert.json",
    "*.assertions.txt",
)

# Generic text: name @ file:line or Assertion "name" failed ...
_LINE_AT_PATTERN = re.compile(
    r"^(?P<name>[\w.$]+)\s+@\s+(?P<file>[\S]+):(?P<line>\d+)",
    re.MULTILINE,
)
_FAILED_PATTERN = re.compile(
    r'Assertion\s+"(?P<name>[^"]+)"\s+failed(?:\s+at\s+(?P<time>\d+)\s*(?P<unit>ns|ps|us|ms)?)?',
    re.IGNORECASE,
)
_SVA_FAIL_PATTERN = re.compile(
    r"(?P<name>[\w.$]+):\s+failed\s+at\s+(?P<time>\d+)\s*(?P<unit>ns|ps|us|ms)?",
    re.IGNORECASE,
)


def _time_to_ns(value: int, unit: str | None) -> int:
    if not unit:
        return value
    u = unit.lower()
    if u == "ps":
        return value // 1000 if value >= 1000 else 0
    if u == "us":
        return value * 1000
    if u == "ms":
        return value * 1_000_000
    return value


class AssertionReportParser:
    """Ingest assertion definitions and runtime failures from text/JSON exports."""

    def __init__(self, redactor: Redactor | None = None) -> None:
        self.redactor = redactor or Redactor()

    def can_handle(self, path: Path) -> bool:
        name = path.name.lower()
        if path.suffix.lower() == ".json" and name.endswith(".assert.json"):
            return True
        if name.endswith(".assertions.txt"):
            return True
        for pattern in ASSERTION_GLOBS:
            stem = pattern.replace("*", "")
            if stem in name:
                return True
        return False

    def parse(self, path: Path) -> dict[str, Any]:
        """Return {test_name?, assertions: [...], failures: [...], source_path}."""
        rel = path.name
        if path.suffix.lower() == ".json" or path.name.endswith(".assert.json"):
            return self._parse_json(path, rel)
        return self._parse_text(path, rel)

    def parse_log_assertions(self, log_path: Path, test_name: str) -> dict[str, Any]:
        """Extract assertion failures from simulation logs (fallback)."""
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        failures: list[dict[str, Any]] = []
        for match in _FAILED_PATTERN.finditer(content):
            failures.append(
                {
                    "name": match.group("name"),
                    "time_ns": (
                        _time_to_ns(
                            int(match.group("time") or 0),
                            match.group("unit"),
                        )
                        if match.group("time")
                        else None
                    ),
                    "message": self.redactor.redact(truncate_text(match.group(0), 500)),
                }
            )
        for match in _SVA_FAIL_PATTERN.finditer(content):
            failures.append(
                {
                    "name": match.group("name"),
                    "time_ns": _time_to_ns(
                        int(match.group("time") or 0),
                        match.group("unit"),
                    ),
                    "message": self.redactor.redact(truncate_text(match.group(0), 500)),
                }
            )
        return {
            "test_name": test_name,
            "assertions": [],
            "failures": failures,
            "source_path": log_path.name,
        }

    def _parse_json(self, path: Path, rel: str) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        assertions_out: list[dict[str, Any]] = []
        for entry in data.get("assertions", []):
            assertions_out.append(self._normalize_definition(entry))
        failures_out: list[dict[str, Any]] = []
        for entry in data.get("failures", []):
            failures_out.append(
                {
                    "name": entry.get("name") or entry.get("assertion_name", "unknown"),
                    "time_ns": entry.get("time_ns"),
                    "message": self.redactor.redact(
                        truncate_text(str(entry.get("message", "")), 2000)
                    ),
                }
            )
        return {
            "test_name": data.get("test_name"),
            "assertions": assertions_out,
            "failures": failures_out,
            "source_path": rel,
        }

    def _parse_text(self, path: Path, rel: str) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8", errors="replace")
        assertions: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        for match in _LINE_AT_PATTERN.finditer(content):
            name = match.group("name")
            scope = name.rsplit(".", 1)[0] if "." in name else "top"
            tags = detect_protocols(name, scope)
            assertions.append(
                {
                    "name": name,
                    "language": "sva",
                    "scope": normalize_scope(scope),
                    "file": normalize_assertion_file(match.group("file")),
                    "line": int(match.group("line")),
                    "signals": [],
                    "intent_protocol": primary_protocol(tags),
                    "intent_requirement": None,
                    "tags": tags,
                }
            )

        for match in _FAILED_PATTERN.finditer(content):
            failures.append(
                {
                    "name": match.group("name"),
                    "time_ns": (
                        _time_to_ns(
                            int(match.group("time") or 0),
                            match.group("unit"),
                        )
                        if match.group("time")
                        else None
                    ),
                    "message": self.redactor.redact(truncate_text(match.group(0), 2000)),
                }
            )

        return {
            "test_name": None,
            "assertions": assertions,
            "failures": failures,
            "source_path": rel,
        }

    def _normalize_definition(self, entry: dict[str, Any]) -> dict[str, Any]:
        name = str(entry.get("name", "unnamed_assertion"))
        scope = normalize_scope(str(entry.get("scope", "top")))
        file = normalize_assertion_file(str(entry.get("file", "unknown.sv")))
        line = int(entry.get("line", 1))
        intent = entry.get("intent") or {}
        tags = list(entry.get("tags") or [])
        detected = detect_protocols(name, scope, str(intent.get("protocol", "")))
        tags = sorted(set(tags + detected))
        protocol = intent.get("protocol") or primary_protocol(tags)
        return {
            "name": name,
            "language": str(entry.get("language", "sva")).lower(),
            "scope": scope,
            "file": file,
            "line": max(1, line),
            "signals": list(entry.get("signals") or [])[:50],
            "intent_protocol": protocol,
            "intent_requirement": intent.get("requirement"),
            "tags": tags,
        }
