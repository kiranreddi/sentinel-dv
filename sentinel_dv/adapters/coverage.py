"""
Coverage data parser for Sentinel DV.

Parses vendor coverage reports and extracts metrics.
Supports simplified coverage formats from major EDA tools.
"""

import re
from pathlib import Path

from sentinel_dv.schemas.common import EvidenceRef
from sentinel_dv.schemas.coverage import CoverageKind, CoverageMetric, CoverageSummary


class CoverageParser:
    """
    Parser for coverage reports.

    Supports basic coverage formats from:
    - Questa/ModelSim
    - VCS
    - Xcelium
    """

    # Coverage patterns (simplified)
    COVERAGE_LINE_PATTERN = re.compile(r"(\w+)\s+coverage:\s*([\d.]+)%", re.IGNORECASE)
    _KIND_MAP = {
        "line": "code",
        "branch": "code",
        "toggle": "toggle",
        "fsm": "fsm",
        "functional": "functional",
        "assertion": "assertion",
    }

    def __init__(self):
        """Initialize coverage parser."""
        pass

    def parse_report(
        self,
        report_path: Path,
        run_id: str = "local",
        kind: str = "functional",
    ) -> CoverageSummary:
        """
        Parse a coverage report file.

        Args:
            report_path: Path to coverage report

        Returns:
            CoverageSummary with metrics
        """
        with open(report_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        metrics = []

        # Extract coverage metrics
        for match in self.COVERAGE_LINE_PATTERN.finditer(content):
            raw_kind = match.group(1).lower()
            percentage = float(match.group(2))

            metric = CoverageMetric(
                name=raw_kind,
                scope="module",
                covered=percentage,
                hits=int(percentage),
                total=100,
            )
            metrics.append(metric)

        # If no metrics found, create a default metric
        if not metrics:
            metrics.append(
                CoverageMetric(name="line", scope="module", covered=0.0, hits=0, total=0)
            )

        summary_kind: CoverageKind
        if kind == "code":
            summary_kind = "code"
        elif kind == "assertion":
            summary_kind = "assertion"
        elif kind == "toggle":
            summary_kind = "toggle"
        elif kind == "fsm":
            summary_kind = "fsm"
        elif kind == "unknown":
            summary_kind = "unknown"
        else:
            summary_kind = "functional"
        rel_path = report_path.name
        return CoverageSummary(
            run_id=run_id,
            test_id=None,
            kind=summary_kind,
            metrics=metrics,
            evidence=[
                EvidenceRef(kind="coverage", path=rel_path, span=None, extract=None, hash=None)
            ],
        )
