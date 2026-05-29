"""
cocotb test result parser for Sentinel DV.

Parses cocotb JUnit XML output and Python exception traces to extract:
- Test results (pass/fail status)
- Failure events from exceptions
- Test metadata
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from sentinel_dv.normalization.redaction import Redactor
from sentinel_dv.taxonomy_engine import classify_failure
from sentinel_dv.utils.bounded_text import truncate_text


class CocotbParser:
    """
    Parser for cocotb test results.

    Supports:
    - JUnit XML output
    - Python exception traces
    """

    def __init__(self, redactor: Redactor | None = None):
        """
        Initialize cocotb parser.

        Args:
            redactor: Redactor instance
        """
        self.redactor = redactor or Redactor()

    def parse_junit_xml(self, xml_path: Path) -> dict:
        """
        Parse cocotb JUnit XML output.

        Args:
            xml_path: Path to results.xml file

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
                    message=message + "\n" + details, severity="error", framework="cocotb"
                )

                # Create failure event dict (IDs added during indexing)
                failure = {
                    "test_name": f"{classname}.{name}" if classname else name,
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
                "name": f"{classname}.{name}" if classname else name,
                "status": status,
                "framework": "cocotb",
                "duration_ms": int(time_sec * 1000),  # Convert to ms
                "seed": None,
                "simulator": None,
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
