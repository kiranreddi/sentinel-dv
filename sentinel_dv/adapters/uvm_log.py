"""
UVM log parser adapter for Sentinel DV.

Parses UVM simulation logs and extracts:
- Test information (name, status, duration)
- Failure events (UVM_ERROR, UVM_FATAL, etc.)
- Topology information (component hierarchy)
- Assertion failures
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from sentinel_dv.normalization.redaction import Redactor
from sentinel_dv.taxonomy_engine import classify_failure
from sentinel_dv.utils.bounded_text import extract_excerpt, truncate_text


@dataclass
class UVMMessage:
    """Parsed UVM message."""

    severity: str  # UVM_INFO, UVM_WARNING, UVM_ERROR, UVM_FATAL
    component: str
    message: str
    time_ns: int | None
    phase: str | None
    line_number: int


class UVMLogParser:
    """
    Parser for UVM simulation logs.

    Supports standard UVM report formats from major simulators:
    - Questa/ModelSim
    - VCS
    - Xcelium
    """

    # UVM message pattern (generic)
    # Format: UVM_[SEVERITY] @ [TIME]: [COMPONENT] [FILE]([LINE]) [MESSAGE]
    UVM_MSG_PATTERN = re.compile(
        r"(UVM_(?:INFO|WARNING|ERROR|FATAL))"  # Severity
        r"(?:\s+@\s*(\d+(?:\.\d+)?)\s*([a-z]+))?"  # Optional: @ time units
        r"(?::\s*)?"
        r"(?:\(([^)]+)\))?"  # Optional: (component)
        r"(?:\s+([^:]+):(\d+))?"  # Optional: file:line
        r"(?:\s+@\s*(\d+))?"  # Optional: @ time (alternative format)
        r"(?::|\s+)"
        r"(.+?)$",  # Message
        re.MULTILINE | re.IGNORECASE,
    )

    # Questa/VCS specific patterns
    QUESTA_PATTERN = re.compile(
        r"#\s*(UVM_(?:INFO|WARNING|ERROR|FATAL))\s+"
        r"(?:@\s*(\d+)\s*([a-z]+)\s*)?"
        r"(?:\[([^\]]+)\]\s*)?"  # Reporter ID
        r"(?:\(([^)]+)\):\s*)?"  # Component
        r"(.+?)$",
        re.MULTILINE | re.IGNORECASE,
    )

    # VCS specific patterns (file:line form)
    VCS_PATTERN = re.compile(
        r"(UVM_(?:INFO|WARNING|ERROR|FATAL))\s+"
        r"(?:@\s*(\d+)\s*([a-z]+)\s*)?"
        r"(?:\[([^\]]+)\]\s*)?"  # Reporter ID
        r"([^:]+\.sv[h]?):\((\d+)\)\s+"
        r"(?:@\s*(\d+)\s*)?"
        r"(.+?)$",
        re.MULTILINE,
    )

    # VCS Jenkins-style: UVM_ERROR <filepath>.svh @ <time_fs>: <component>  <msg>
    VCS_JENKINS_PATTERN = re.compile(
        r"^(UVM_(?:INFO|WARNING|ERROR|FATAL))\s+"
        r"(?:\S+\.sv[h]?\s+)?"  # Optional filepath (no colon before @)
        r"@\s*(\d+)\s*(?::\s*)?"  # @ time :
        r"(\S+)\s+"  # component path
        r"(.+?)$",  # message
        re.MULTILINE,
    )

    # Phase detection
    PHASE_PATTERN = re.compile(r'(?:UVM_INFO.*)?(?:phase|Phase)\s+["\']?(\w+)["\']?', re.IGNORECASE)

    # Test name extraction — ranked from most specific to least
    TEST_NAME_PATTERN = re.compile(
        r'(?:Running test|RNTST]\s+Running test)\s+["\']?(\w+)["\']?'
        r"|(?:\+test_name=)(\w+)"
        r"|(?:\+UVM_TESTNAME=)(\w+)"
        r'|(?:TEST|test_name|Starting test)[\s:]+["\']?(\w+)["\']?',
        re.IGNORECASE,
    )

    # Seed extraction patterns
    SEED_PATTERN = re.compile(
        r"(?:ntb_random_seed|test_seed)[=\s]+(\d+)" r"|(?:Simulation seed:\s*)(\d+)",
        re.IGNORECASE,
    )

    # Simulator detection
    SIMULATOR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"Chronologic VCS simulator|VCS\s+version\s+\S+", re.IGNORECASE), "vcs"),
        (re.compile(r"Questa Sim|ModelSim|vsim\s+\d", re.IGNORECASE), "questa"),
        (re.compile(r"Xcelium|xrun\s+\d|XCELIUM", re.IGNORECASE), "xcelium"),
        (re.compile(r"Riviera-PRO|ALDEC|vsimsa", re.IGNORECASE), "riviera"),
    ]

    # Test status patterns — anchored to avoid false positives
    TEST_PASSED_PATTERN = re.compile(
        r"\bTEST\s+PASSED\b"
        r"|\bAll\s+tests\s+passed\b"
        r"|\bFINAL\s+RESULT\s*:\s*PASS\b"
        r"|\$finish\b.*(?:PASSED|SUCCESS)",
        re.IGNORECASE,
    )

    TEST_FAILED_PATTERN = re.compile(
        r"\bTEST\s+FAILED\b"
        r"|\bFINAL\s+RESULT\s*:\s*FAIL\b"
        r"|\bUVM_FATAL\b"
        r"|\bSIMULATION\s+FAILED\b",
        re.IGNORECASE,
    )

    # Topology extraction
    COMPONENT_PATTERN = re.compile(r"(?:uvm_test_top|uvm_top)\.(\S+)", re.IGNORECASE)

    def __init__(self, redactor: Redactor | None = None):
        """
        Initialize UVM log parser.

        Args:
            redactor: Redactor instance for PII/credential removal
        """
        self.redactor = redactor or Redactor()

    def parse_log(self, log_path: Path) -> dict:
        """
        Parse a UVM log file.

        Args:
            log_path: Path to UVM log file

        Returns:
            Dictionary with:
                - test: TestCase or None
                - failures: List of FailureEvent
                - topology: TestTopology or None
        """
        log_path = Path(log_path)

        if not log_path.exists():
            raise FileNotFoundError(f"Log file not found: {log_path}")

        # Read log file
        with open(log_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Parse messages
        messages = list(self._extract_messages(content))

        # Extract test information
        test_name = self._extract_test_name(content)
        test_status = self._determine_test_status(content, messages)

        # Extract failures (UVM_ERROR and UVM_FATAL)
        failures = self._extract_failures(messages, log_path)

        # Extract topology (return raw dict, IDs added during indexing)
        topology = self._extract_topology(content)

        # Extract seed and simulator
        seed = self._extract_seed(content, log_path)
        simulator = self._extract_simulator(content)

        # Extract duration from VCS report line: "CPU Time: NNN.NNN seconds"
        duration_ms = self._extract_duration_ms(content)

        # Build test case dict (if we found a test name)
        # IDs and run ref will be added during indexing
        test = None
        if test_name:
            test = {
                "name": test_name,
                "status": test_status,
                "framework": "uvm",
                "duration_ms": duration_ms,
                "seed": seed,
                "simulator": simulator,
                "dut": None,
                "evidence": [
                    {
                        "kind": "log",
                        "path": log_path.name,  # Relative path
                        "span": None,
                        "extract": None,
                        "hash": None,
                    }
                ],
            }

        return {
            "test": test,
            "failures": failures,
            "topology": topology,
        }

    def _extract_messages(self, content: str) -> Iterator[UVMMessage]:
        """
        Extract all UVM messages from log content.

        Args:
            content: Log file content

        Yields:
            UVMMessage instances
        """
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Try VCS Jenkins-style first (most specific for real CI logs):
            # UVM_ERROR <filepath>.svh @ <time_fs>: <component>  <msg>
            match = self.VCS_JENKINS_PATTERN.match(line)
            if match:
                severity = match.group(1).upper()
                time_str = match.group(2)
                component = match.group(3) or "unknown"
                message = match.group(4).strip()
                # VCS Jenkins logs report time in femtoseconds
                time_ns = self._parse_time(time_str, "fs") if time_str else None
                phase = self._extract_phase(message)
                yield UVMMessage(
                    severity=severity,
                    component=component,
                    message=message,
                    time_ns=time_ns,
                    phase=phase,
                    line_number=line_num,
                )
                continue

            # Try Questa pattern (# prefix)
            match = self.QUESTA_PATTERN.search(line)
            if match:
                severity = match.group(1).upper()
                time_str = match.group(2)
                time_unit = match.group(3)
                component = match.group(5) or match.group(4) or "unknown"
                message = match.group(6).strip()

                time_ns = self._parse_time(time_str, time_unit) if time_str else None
                phase = self._extract_phase(message)

                yield UVMMessage(
                    severity=severity,
                    component=component,
                    message=message,
                    time_ns=time_ns,
                    phase=phase,
                    line_number=line_num,
                )
                continue

            # Try VCS file:line pattern
            match = self.VCS_PATTERN.search(line)
            if match:
                severity = match.group(1).upper()
                time_str = match.group(2) or match.group(7)
                time_unit = match.group(3)
                component = match.group(4) or "unknown"
                message = match.group(8).strip()

                time_ns = self._parse_time(time_str, time_unit) if time_str else None
                phase = self._extract_phase(message)

                yield UVMMessage(
                    severity=severity,
                    component=component,
                    message=message,
                    time_ns=time_ns,
                    phase=phase,
                    line_number=line_num,
                )
                continue

            # Try generic pattern (fallback)
            match = self.UVM_MSG_PATTERN.search(line)
            if match:
                severity = match.group(1).upper()
                time_str = match.group(2) or match.group(7)
                time_unit = match.group(3)
                component = match.group(4) or "unknown"
                message = match.group(8).strip()

                time_ns = self._parse_time(time_str, time_unit) if time_str else None
                phase = self._extract_phase(message)

                yield UVMMessage(
                    severity=severity,
                    component=component,
                    message=message,
                    time_ns=time_ns,
                    phase=phase,
                    line_number=line_num,
                )

    def _parse_time(self, time_str: str, unit: str | None) -> int | None:
        """
        Parse simulation time to nanoseconds.

        Args:
            time_str: Time value string
            unit: Time unit (ns, us, ms, s, ps, fs)

        Returns:
            Time in nanoseconds, or None if parsing fails
        """
        try:
            time_val = float(time_str)
        except (ValueError, TypeError):
            return None

        # Convert to nanoseconds
        if not unit:
            return int(time_val)  # Assume ns if no unit

        unit_lower = unit.lower()
        if unit_lower == "fs":
            return int(time_val / 1_000_000)
        elif unit_lower == "ps":
            return int(time_val / 1_000)
        elif unit_lower == "ns":
            return int(time_val)
        elif unit_lower in ("us", "μs"):
            return int(time_val * 1_000)
        elif unit_lower == "ms":
            return int(time_val * 1_000_000)
        elif unit_lower == "s":
            return int(time_val * 1_000_000_000)
        else:
            return int(time_val)  # Default to ns

    def _extract_phase(self, message: str) -> str | None:
        """Extract UVM phase from message."""
        match = self.PHASE_PATTERN.search(message)
        return match.group(1) if match else None

    def _extract_test_name(self, content: str) -> str | None:
        """Extract test name from log content, preferring the most specific patterns."""
        match = self.TEST_NAME_PATTERN.search(content)
        if match:
            # Return first non-None group (patterns are ordered most-to-least specific)
            return next((g for g in match.groups() if g is not None), None)
        return None

    def _determine_test_status(self, content: str, messages: list[UVMMessage]) -> str:
        """
        Determine overall test status.

        Priority order (highest to lowest):
        1. FATAL messages → always fail
        2. Explicit FAIL text (FINAL RESULT: FAIL, TEST FAILED) → fail
        3. ERROR messages → fail
        4. Explicit PASS text (TEST PASSED, FINAL RESULT: PASS) → pass
        5. Default → pass

        Args:
            content: Full log content
            messages: Parsed UVM messages

        Returns:
            Status string ("pass", "fail", etc.)
        """
        # UVM_FATAL always wins
        if any(msg.severity == "UVM_FATAL" for msg in messages):
            return "fail"

        # Explicit fail markers beat everything
        if self.TEST_FAILED_PATTERN.search(content):
            return "fail"

        # UVM_ERROR → fail (unless overridden by explicit PASS)
        if any(msg.severity == "UVM_ERROR" for msg in messages):
            return "fail"

        # Explicit pass markers
        if self.TEST_PASSED_PATTERN.search(content):
            return "pass"

        # Default to pass if no errors detected
        return "pass"

    def _extract_seed(self, content: str, log_path: Path) -> str | None:
        """Extract simulation seed from log content or filename."""
        # Try from log content first (most reliable)
        m = self.SEED_PATTERN.search(content)
        if m:
            return m.group(1) or m.group(2)
        # Fall back to filename convention: test_name_SEED.log
        stem = log_path.stem  # e.g., "my_test_1234567890"
        parts = stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) >= 5:
            return parts[1]
        return None

    def _extract_simulator(self, content: str) -> str | None:
        """Detect simulator vendor from log header."""
        # Only scan the first 100 lines for efficiency
        header = "\n".join(content.split("\n")[:100])
        for pattern, vendor in self.SIMULATOR_PATTERNS:
            if pattern.search(header):
                return vendor
        return None

    def _extract_duration_ms(self, content: str) -> int | None:
        """Extract simulation CPU wall time in milliseconds."""
        # VCS: "CPU Time: NNN.NNN seconds"
        m = re.search(r"CPU\s+Time:\s+([\d.]+)\s+seconds", content, re.IGNORECASE)
        if m:
            return int(float(m.group(1)) * 1000)
        # Questa: "# Total simulation time: NNN ns"
        m = re.search(r"Total\s+simulation\s+time[:\s]+([\d.]+)\s+ns", content, re.IGNORECASE)
        if m:
            return int(float(m.group(1)) / 1_000_000)
        return None

    def _extract_failures(self, messages: list[UVMMessage], log_path: Path) -> list[dict]:
        """
        Extract failure events from UVM messages.

        Args:
            messages: Parsed UVM messages
            log_path: Path to log file

        Returns:
            List of failure event dicts (IDs added during indexing)
        """
        failures = []

        for msg in messages:
            # Only extract ERROR and FATAL messages
            if msg.severity not in ("UVM_ERROR", "UVM_FATAL"):
                continue

            # Classify using taxonomy engine
            taxonomy = classify_failure(
                message=msg.message,
                severity=msg.severity,
                component=msg.component,
                phase=msg.phase,
                framework="uvm",
            )

            # Apply redaction
            summary = self.redactor.redact(truncate_text(msg.message, 200))
            message_full = self.redactor.redact(truncate_text(msg.message, 2000))

            # Create failure event dict (IDs added during indexing)
            failure = {
                "severity": taxonomy.severity,
                "category": taxonomy.category,
                "summary": summary,
                "message": message_full,
                "component": msg.component,
                "phase": msg.phase,
                "time_ns": msg.time_ns,
                "tags": taxonomy.tags,
                "evidence": [
                    {
                        "kind": "log",
                        "path": log_path.name,  # Use relative path (just filename)
                        "span": {
                            "start_line": msg.line_number,
                            "end_line": msg.line_number,
                        },
                        "extract": extract_excerpt(msg.message, 500),
                        "hash": None,
                    }
                ],
            }

            failures.append(failure)

        return failures

    def _extract_topology(self, content: str) -> dict | None:
        """
        Extract test topology from log content.

        Args:
            content: Log file content

        Returns:
            Dict representing TestTopology (test_id added during indexing)
        """
        # Extract component hierarchy (simplified)
        components = set()

        for match in self.COMPONENT_PATTERN.finditer(content):
            comp_path = match.group(1)
            components.add(comp_path)

        if not components:
            return None

        # Build simplified UVM topology dict
        # test_id will be added during indexing
        return {
            "uvm": {
                "test_class": "unknown",
                "envs": [],
                "agents": [],
                "scoreboards": [],
                "sequencers": [],
                "drivers": [],
                "monitors": [],
            },
            "interfaces": [],
        }
