"""
JUnit XML and cocotb test result parser for Sentinel DV.

Parses JUnit XML output from various frameworks and simulators:
- cocotb (Python-based)
- UVM/SystemVerilog test suites exported as JUnit (VCS, Questa, Xcelium)
- Verilator-based testbenches

Extracts:
- Test results (pass/fail status)
- Failure events from exceptions / UVM errors
- Test metadata (seed, simulator, duration)
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from sentinel_dv.normalization.redaction import Redactor
from sentinel_dv.taxonomy_engine import classify_failure
from sentinel_dv.utils.bounded_text import truncate_text

# Patterns to detect simulator from classname or test name
_SIM_VENDOR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bvcs\b", re.IGNORECASE), "vcs"),
    (re.compile(r"\bquesta\b|\bvsim\b|\bmodelsim\b", re.IGNORECASE), "questa"),
    (re.compile(r"\bxcelium\b|\bxrun\b|\bcadence\b", re.IGNORECASE), "xcelium"),
    (re.compile(r"\briviera\b|\baldec\b", re.IGNORECASE), "riviera"),
]

# Patterns to detect UVM (vs cocotb) test suites from JUnit XML
_UVM_CLASSNAME_PATTERNS = re.compile(
    r"(?:uvm|svt|regr|regression|_test|_sim|_tb)\b",
    re.IGNORECASE,
)


def _detect_framework(classname: str, name: str) -> str:
    """Detect test framework from classname and test name."""
    combined = f"{classname} {name}"
    if _UVM_CLASSNAME_PATTERNS.search(combined):
        return "uvm"
    return "cocotb"


def _detect_sim_vendor(classname: str, name: str, xml_classname: str = "") -> str | None:
    """Detect simulator vendor from classname, test name, or attribute."""
    combined = f"{classname} {name} {xml_classname}"
    for pat, vendor in _SIM_VENDOR_PATTERNS:
        if pat.search(combined):
            return vendor
    return None


def _extract_seed_from_name(test_name: str) -> int | None:
    """Extract seed appended to test name: test_name_SEED or test_name.SEED."""
    m = re.search(r"[_.](\d{5,})$", test_name)
    if m:
        return int(m.group(1))
    return None


def _strip_seed_from_name(test_name: str) -> str:
    """Remove trailing seed suffix to get the base test name."""
    return re.sub(r"[_.](\d{5,})$", "", test_name)


class CocotbParser:
    """
    Parser for JUnit XML test results (cocotb, UVM regression, Verilator).

    Supports:
    - JUnit XML output (cocotb, Questa, VCS, Xcelium regressions)
    - Python exception traces
    """

    def __init__(self, redactor: Redactor | None = None):
        """
        Initialize parser.

        Args:
            redactor: Redactor instance
        """
        self.redactor = redactor or Redactor()

    def parse_junit_xml(self, xml_path: Path) -> dict:
        """
        Parse JUnit XML output from cocotb, UVM regression runners, or Verilator.

        Automatically detects framework (cocotb vs uvm) from classname/test name patterns.
        Extracts simulator vendor, seed, and duration.

        Args:
            xml_path: Path to results.xml / TestResults.xml / junit.xml file

        Returns:
            Dictionary with tests and failures
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        tests = []
        failures = []

        # Parse each testcase
        for testcase in root.findall(".//testcase"):
            name = testcase.get("name", "unknown")
            classname = testcase.get("classname", "")
            time_sec = float(testcase.get("time", "0"))
            seed_str = testcase.get("seed")
            seed_val = int(seed_str) if seed_str and seed_str.isdigit() else None
            # Inherit simulator from parent testsuite if not on testcase
            parent_ts = next(
                (ts for ts in root.findall(".//testsuite") if testcase in list(ts)), None
            )
            sim_attr = testcase.get("simulator") or (
                parent_ts.get("simulator") if parent_ts is not None else None
            )

            # Auto-detect framework and simulator
            framework = _detect_framework(classname, name)
            if sim_attr is None:
                sim_attr = _detect_sim_vendor(classname, name)

            # Extract seed from test name if not already found
            if seed_val is None:
                seed_val = _extract_seed_from_name(name)

            # Use base test name (without seed suffix) for cleaner naming
            base_name = _strip_seed_from_name(f"{classname}.{name}" if classname else name)

            # Check for failure/error elements
            failure_elem = testcase.find("failure")
            error_elem = testcase.find("error")

            if failure_elem is not None or error_elem is not None:
                status = "fail"
                elem = failure_elem if failure_elem is not None else error_elem
                assert elem is not None

                message = elem.get("message", "")
                details = elem.text or ""

                # Classify failure
                taxonomy = classify_failure(
                    message=message + "\n" + details, severity="error", framework=framework
                )

                # Create failure event dict (IDs added during indexing)
                failure = {
                    "test_name": base_name,
                    "severity": taxonomy.severity,
                    "category": taxonomy.category,
                    "summary": self.redactor.redact(truncate_text(message, 200)),
                    "message": self.redactor.redact(truncate_text(details, 2000)),
                    "time_ns": None,
                    "phase": None,
                    "component": None,
                    "tags": taxonomy.tags,
                    "evidence": [
                        {
                            "kind": "artifact",
                            "path": xml_path.name,  # Use relative path (just filename)
                            "span": None,
                            "extract": self.redactor.redact(truncate_text(details, 1000)),
                            "hash": None,
                        }
                    ],
                }
                failures.append(failure)
            else:
                status = "pass"

            # Create test case dict (IDs and run ref added during indexing)
            test = {
                "name": base_name,
                "status": status,
                "framework": framework,
                "duration_ms": int(time_sec * 1000),  # Convert to ms
                "seed": seed_val,
                "simulator": sim_attr,
                "dut": None,
                "evidence": [
                    {
                        "kind": "artifact",
                        "path": xml_path.name,
                        "span": None,
                        "extract": None,
                        "hash": None,
                    }
                ],
            }
            tests.append(test)

        return {"tests": tests, "failures": failures}
