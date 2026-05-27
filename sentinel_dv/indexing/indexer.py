"""Artifact indexing for Sentinel DV."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sentinel_dv.adapters.cocotb import CocotbParser
from sentinel_dv.adapters.uvm_log import UVMLogParser
from sentinel_dv.adapters.waveform_summary import WAVEFORM_GLOBS, WaveformSummaryParser
from sentinel_dv.config import AdaptersConfig
from sentinel_dv.ids import generate_failure_id, generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore


class ArtifactIndexer:
    """Scan artifact roots and populate the DuckDB index."""

    def __init__(
        self,
        artifact_roots: list[str],
        db_path: Path | str,
        adapters: AdaptersConfig | None = None,
    ):
        self.artifact_roots = [Path(root).resolve() for root in artifact_roots]
        self.db_path = Path(db_path)
        self.adapters = adapters or AdaptersConfig()
        self.uvm_parser = UVMLogParser()
        self.cocotb_parser = CocotbParser()
        self.waveform_parser = WaveformSummaryParser()

    def scan_artifacts(self) -> list[Path]:
        """Collect indexable artifact paths under configured roots."""
        patterns = ("*.log", "results.xml", "junit.xml")
        found: list[Path] = []
        for root in self.artifact_roots:
            if not root.exists():
                continue
            for pattern in patterns:
                found.extend(root.rglob(pattern))
        return sorted(set(found))

    def scan_waveform_artifacts(self) -> list[Path]:
        """Collect precomputed waveform summary JSON files."""
        found: list[Path] = []
        for root in self.artifact_roots:
            if not root.exists():
                continue
            for pattern in WAVEFORM_GLOBS:
                found.extend(root.rglob(pattern))
        return sorted({path for path in found if self.waveform_parser.can_handle(path)})

    def index_all(self) -> dict[str, int]:
        """Index all discovered artifacts into the store."""
        artifacts = self.scan_artifacts()
        waveform_artifacts = self.scan_waveform_artifacts() if self.adapters.waveform_summary else []
        stats = {
            "artifacts": len(artifacts) + len(waveform_artifacts),
            "runs": 0,
            "tests": 0,
            "failures": 0,
            "waveforms": 0,
        }

        if self.db_path.exists():
            self.db_path.unlink()

        with IndexStore(self.db_path) as store:
            for path in artifacts:
                if path.suffix == ".log" and self.adapters.uvm:
                    self._index_uvm_log(store, path, stats)
                elif path.name in {"results.xml", "junit.xml"} and self.adapters.cocotb:
                    self._index_cocotb_xml(store, path, stats)

            if self.adapters.waveform_summary:
                for path in waveform_artifacts:
                    self._index_waveform_summary(store, path, stats)

        return stats

    def _index_uvm_log(self, store: IndexStore, log_path: Path, stats: dict[str, int]) -> None:
        result = self.uvm_parser.parse_log(log_path)
        if not result.get("test"):
            return

        rel = self._relative_path(log_path)
        run_id, run_id_full = generate_run_id(
            suite=log_path.parent.name or "uvm",
            artifact_manifest=[(rel, self._file_hash(log_path))],
        )
        status = "fail" if result.get("failures") else "pass"
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        if not store.get_run(run_id):
            store.insert_run(
                run_id=run_id,
                run_id_full=run_id_full,
                suite=log_path.parent.name or "uvm",
                created_at=created_at,
                status=status,
            )
            stats["runs"] += 1

        test_name = result["test"]["name"]
        test_id, test_id_full = generate_test_id(
            run_id_full=run_id_full,
            framework="uvm",
            test_name=test_name,
        )
        store.insert_test(
            test_id=test_id,
            test_id_full=test_id_full,
            run_id=run_id,
            framework="uvm",
            name=test_name,
            status=status,
            created_at=created_at,
        )
        stats["tests"] += 1

        if topology := result.get("topology"):
            store.insert_topology(test_id, topology)

        for failure in result.get("failures", []):
            failure_id, failure_id_full = generate_failure_id(
                test_id_full=test_id_full,
                severity=failure["severity"],
                category=failure["category"],
                summary=failure["summary"],
            )
            store.insert_failure(
                failure_id=failure_id,
                failure_id_full=failure_id_full,
                test_id=test_id,
                run_id=run_id,
                severity=failure["severity"],
                category=failure["category"],
                summary=failure["summary"],
                message=failure["message"],
                tags=failure.get("tags", []),
                time_ns=failure.get("time_ns"),
                phase=failure.get("phase"),
                component=failure.get("component"),
            )
            stats["failures"] += 1

    def _index_cocotb_xml(self, store: IndexStore, xml_path: Path, stats: dict[str, int]) -> None:
        result = self.cocotb_parser.parse_junit_xml(xml_path)
        if not result.get("tests"):
            return

        rel = self._relative_path(xml_path)
        run_id, run_id_full = generate_run_id(
            suite=xml_path.parent.name or "cocotb",
            artifact_manifest=[(rel, self._file_hash(xml_path))],
        )
        any_fail = any(t["status"] == "fail" for t in result["tests"])
        status = "fail" if any_fail else "pass"
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        if not store.get_run(run_id):
            store.insert_run(
                run_id=run_id,
                run_id_full=run_id_full,
                suite=xml_path.parent.name or "cocotb",
                created_at=created_at,
                status=status,
            )
            stats["runs"] += 1

        failures_by_test = {}
        for failure in result.get("failures", []):
            failures_by_test.setdefault(failure.get("test_name"), []).append(failure)

        for test in result["tests"]:
            test_id, test_id_full = generate_test_id(
                run_id_full=run_id_full,
                framework="cocotb",
                test_name=test["name"],
            )
            store.insert_test(
                test_id=test_id,
                test_id_full=test_id_full,
                run_id=run_id,
                framework="cocotb",
                name=test["name"],
                status=test["status"],
                created_at=created_at,
                duration_ms=test.get("duration_ms"),
            )
            stats["tests"] += 1

            for failure in failures_by_test.get(test["name"], []):
                failure_id, failure_id_full = generate_failure_id(
                    test_id_full=test_id_full,
                    severity=failure.get("severity", "error"),
                    category=failure.get("category", "functional"),
                    summary=failure.get("summary", failure.get("message", "failure")),
                )
                store.insert_failure(
                    failure_id=failure_id,
                    failure_id_full=failure_id_full,
                    test_id=test_id,
                    run_id=run_id,
                    severity=failure.get("severity", "error"),
                    category=failure.get("category", "functional"),
                    summary=failure.get("summary", failure.get("message", "failure")),
                    message=failure.get("message", ""),
                    tags=failure.get("tags", []),
                )
                stats["failures"] += 1

    def _index_waveform_summary(
        self, store: IndexStore, json_path: Path, stats: dict[str, int]
    ) -> None:
        try:
            parsed = self.waveform_parser.parse(json_path)
        except (OSError, ValueError, json.JSONDecodeError):
            return

        framework = parsed.get("framework")
        if isinstance(framework, str):
            framework = framework.lower()

        test = store.find_test_by_name(parsed["test_name"], framework=framework)
        if not test:
            return

        rel = self._relative_path(json_path)
        store.insert_waveform_summary(
            test_id=test["test_id"],
            summary={
                **parsed,
                "evidence": {
                    "kind": "waveform_summary",
                    "path": rel,
                },
            },
            source_path=rel,
        )
        stats["waveforms"] += 1

    def _relative_path(self, path: Path) -> str:
        for root in self.artifact_roots:
            try:
                return str(path.resolve().relative_to(root))
            except ValueError:
                continue
        return path.name

    @staticmethod
    def _file_hash(path: Path) -> str:
        import hashlib

        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
