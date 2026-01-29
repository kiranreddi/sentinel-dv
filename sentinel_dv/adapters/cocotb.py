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


class CocotbAdapter:
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

    def parse_junit_xml(self, xml_path: Path) -> list[dict]:
        """
        Parse cocotb JUnit XML output.

        Args:
            xml_path: Path to results.xml file

        Returns:
            List of test result dictionaries
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        tests = []

        # Parse each testcase
        for testcase in root.findall(".//testcase"):
            name = testcase.get("name", "unknown")
            classname = testcase.get("classname", "")
            time_sec = float(testcase.get("time", "0"))

            # Check for failure/error elements
            failure_elem = testcase.find("failure")
            error_elem = testcase.find("error")

            failure_message = None
            category = "unknown"
            tags = []

            if failure_elem is not None or error_elem is not None:
                status = "fail"
                elem = failure_elem if failure_elem is not None else error_elem

                message = elem.get("message", "")
                details = elem.text or ""

                # Classify failure
                taxonomy = classify_failure(
                    message=message + "\n" + details, severity="error", framework="cocotb"
                )

                failure_message = self.redactor.redact(truncate_text(message + "\n" + details, 2000))
                category = taxonomy.category
                tags = taxonomy.tags
            else:
                status = "pass"

            # Create test result dict
            test = {
                "name": f"{classname}.{name}" if classname else name,
                "status": status,
                "duration_s": time_sec,
                "failure_message": failure_message,
                "category": category,
                "tags": tags,
            }
            tests.append(test)

        return tests


# Alias for backward compatibility
CocotbParser = CocotbAdapter
