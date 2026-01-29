"""Artifact indexer for Sentinel DV.

Scans artifact roots and builds index using adapters.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sentinel_dv.adapters.cocotb import CocotbAdapter
from sentinel_dv.adapters.uvm_log import UVMLogParser
from sentinel_dv.ids import generate_failure_id, generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.normalization.redaction import Redactor
from sentinel_dv.normalization.signatures import (
    generate_failure_signature,
    normalize_failure_summary,
)

logger = logging.getLogger(__name__)


class ArtifactIndexer:
    """Artifact indexer for Sentinel DV."""

    def __init__(
        self,
        artifact_roots: list[str],
        store: IndexStore,
        redactor: Redactor | None = None,
    ):
        """Initialize indexer.

        Args:
            artifact_roots: List of artifact root directories.
            store: Index store instance
            redactor: Optional redactor for sensitive data
        """
        self.artifact_roots = [Path(root) for root in artifact_roots]
        self.store = store
        self.redactor = redactor or Redactor()
        self.uvm_parser = UVMLogParser(redactor=self.redactor)
        self.cocotb_adapter = CocotbAdapter()

    def scan_artifacts(self) -> list[Path]:
        """Scan artifact roots and find artifact files.

        Returns:
            List of artifact file paths.
        """
        artifacts = []
        for root in self.artifact_roots:
            if not root.exists():
                logger.warning(f"Artifact root does not exist: {root}")
                continue

            # Scan for UVM logs
            artifacts.extend(root.rglob("*.log"))

            # Scan for cocotb results (JUnit XML)
            artifacts.extend(root.rglob("results.xml"))
            artifacts.extend(root.rglob("*junit*.xml"))

        logger.info(f"Found {len(artifacts)} artifact files")
        return artifacts

    def index_all(self, suite_name: str | None = None) -> dict[str, Any]:
        """Index all artifacts.

        Args:
            suite_name: Optional suite name for the run

        Returns:
            Dictionary with indexing statistics
        """
        artifacts = self.scan_artifacts()
        stats = {
            "artifacts_scanned": len(artifacts),
            "runs_indexed": 0,
            "tests_indexed": 0,
            "failures_indexed": 0,
            "errors": [],
        }

        for artifact_path in artifacts:
            try:
                if artifact_path.suffix == ".log":
                    self._index_uvm_log(artifact_path, suite_name, stats)
                elif artifact_path.suffix == ".xml":
                    self._index_cocotb_xml(artifact_path, suite_name, stats)
            except Exception as e:
                error_msg = f"Error indexing {artifact_path}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        logger.info(
            f"Indexing complete: {stats['runs_indexed']} runs, "
            f"{stats['tests_indexed']} tests, {stats['failures_indexed']} failures"
        )
        return stats

    def _index_uvm_log(
        self,
        log_path: Path,
        suite_name: str | None,
        stats: dict[str, Any],
    ) -> None:
        """Index a UVM log file.

        Args:
            log_path: Path to log file
            suite_name: Optional suite name
            stats: Statistics dictionary to update
        """
        logger.debug(f"Indexing UVM log: {log_path}")

        # Parse the log file
        result = self.uvm_parser.parse_log(log_path)

        # Create run ID
        run_data = {
            "suite": suite_name or "default",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "artifact_path": str(log_path),
        }
        run_id_full, run_id_short = generate_run_id(run_data)

        # Determine test status
        test_info = result.get("test")
        if not test_info:
            # Skip if no test found
            logger.warning(f"No test found in {log_path}")
            return

        # Insert run
        self.store.insert_run(
            run_id=run_id_short,
            run_id_full=run_id_full,
            suite=suite_name or "default",
            created_at=datetime.utcnow().isoformat() + "Z",
            status=test_info.get("status", "unknown"),
        )
        stats["runs_indexed"] += 1

        # Insert test
        test_data = {
            "run_id": run_id_short,
            "name": test_info["name"],
            "framework": "uvm",
        }
        test_id_full, test_id_short = generate_test_id(test_data)

        self.store.insert_test(
            test_id=test_id_short,
            test_id_full=test_id_full,
            run_id=run_id_short,
            framework="uvm",
            name=test_info["name"],
            status=test_info.get("status", "unknown"),
            created_at=datetime.utcnow().isoformat() + "Z",
            sim_vendor=test_info.get("simulator"),
        )
        stats["tests_indexed"] += 1

        # Insert failures
        for failure in result.get("failures", []):
            failure_data = {
                "test_id": test_id_short,
                "message": failure["message"],
                "time_ns": failure.get("time_ns", 0),
            }
            failure_id_full, failure_id_short = generate_failure_id(failure_data)

            # Compute signature
            summary = normalize_failure_summary(failure["message"])
            signature = generate_failure_signature(
                category=failure["category"],
                summary=summary,
            )

            self.store.insert_failure(
                failure_id=failure_id_short,
                failure_id_full=failure_id_full,
                test_id=test_id_short,
                run_id=run_id_short,
                severity=failure["severity"],
                category=failure["category"],
                summary=failure["message"][:200],  # Truncate
                message=failure["message"],
                tags=failure.get("tags", []),
                time_ns=failure.get("time_ns"),
                phase=failure.get("phase"),
                component=failure.get("component"),
                signature_id=signature,
            )
            stats["failures_indexed"] += 1

    def _index_cocotb_xml(
        self,
        xml_path: Path,
        suite_name: str | None,
        stats: dict[str, Any],
    ) -> None:
        """Index a cocotb JUnit XML file.

        Args:
            xml_path: Path to XML file
            suite_name: Optional suite name
            stats: Statistics dictionary to update
        """
        logger.debug(f"Indexing cocotb XML: {xml_path}")

        # Parse the XML file
        results = self.cocotb_adapter.parse_junit_xml(xml_path)

        # Create run ID once for the entire XML file
        run_data = {
            "suite": suite_name or "cocotb",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "artifact_path": str(xml_path),
        }
        run_id_full, run_id_short = generate_run_id(run_data)

        # Insert run once
        try:
            self.store.insert_run(
                run_id=run_id_short,
                run_id_full=run_id_full,
                suite=suite_name or "cocotb",
                created_at=datetime.utcnow().isoformat() + "Z",
                status="completed",
            )
            stats["runs_indexed"] += 1
        except Exception as e:
            # Run might already exist if re-indexing
            logger.debug(f"Run {run_id_short} already exists: {e}")

        # Insert all tests from this XML file
        for result in results:
            # Insert test
            test_data = {
                "run_id": run_id_short,
                "name": result["name"],
                "framework": "cocotb",
            }
            test_id_full, test_id_short = generate_test_id(test_data)

            self.store.insert_test(
                test_id=test_id_short,
                test_id_full=test_id_full,
                run_id=run_id_short,
                framework="cocotb",
                name=result["name"],
                status=result["status"],
                created_at=datetime.utcnow().isoformat() + "Z",
                duration_ms=int(result.get("duration_s", 0) * 1000),
            )
            stats["tests_indexed"] += 1

            # Insert failure if test failed
            if result["status"] == "fail" and result.get("failure_message"):
                failure_data = {
                    "test_id": test_id_short,
                    "message": result["failure_message"],
                    "time_ns": 0,
                }
                failure_id_full, failure_id_short = generate_failure_id(failure_data)

                # Compute signature
                summary = normalize_failure_summary(result["failure_message"])
                signature = generate_failure_signature(
                    category=result.get("category", "unknown"),
                    summary=summary,
                )

                self.store.insert_failure(
                    failure_id=failure_id_short,
                    failure_id_full=failure_id_full,
                    test_id=test_id_short,
                    run_id=run_id_short,
                    severity="error",
                    category=result.get("category", "unknown"),
                    summary=result["failure_message"][:200],
                    message=result["failure_message"],
                    tags=result.get("tags", []),
                    signature_id=signature,
                )
                stats["failures_indexed"] += 1
