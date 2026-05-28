"""Artifact indexing for Sentinel DV."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sentinel_dv.adapters.cocotb import CocotbParser
from sentinel_dv.adapters.uvm_log import UVMLogParser
from sentinel_dv.adapters.vcd_summary import VcdSummaryParser
from sentinel_dv.adapters.waveform_summary import WAVEFORM_GLOBS, WaveformSummaryParser
from sentinel_dv.config import AdaptersConfig, RedactionConfig, SecurityLimits, SentinelDVConfig
from sentinel_dv.ids import (
    generate_failure_id,
    generate_run_id,
    generate_signature_id,
    generate_test_id,
)
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.normalization.redaction import Redactor
from sentinel_dv.utils.bounded_text import truncate_text


class ArtifactIndexer:
    """Scan artifact roots and populate the DuckDB index."""

    def __init__(
        self,
        artifact_roots: list[str],
        db_path: Path | str,
        adapters: AdaptersConfig | None = None,
        *,
        redaction: RedactionConfig | None = None,
        security: SecurityLimits | None = None,
        config: SentinelDVConfig | None = None,
    ):
        self.artifact_roots = [Path(root).resolve() for root in artifact_roots]
        self.db_path = Path(db_path)
        if config is not None:
            self.adapters = config.adapters
            redaction = config.redaction
            security = config.security
        else:
            self.adapters = adapters or AdaptersConfig()
        self.security = security or SecurityLimits()
        redaction_cfg = redaction or RedactionConfig()
        redactor = Redactor.from_config(redaction_cfg)
        self.uvm_parser = UVMLogParser(redactor=redactor)
        self.cocotb_parser = CocotbParser(redactor=redactor)
        self.waveform_json_parser = WaveformSummaryParser()
        self.vcd_parser = VcdSummaryParser()

    def scan_artifacts(self) -> list[Path]:
        """Collect indexable artifact paths under configured roots."""
        patterns = ("*.log", "results.xml", "junit.xml")
        found: list[Path] = []
        for root in self.artifact_roots:
            if not root.exists():
                continue
            for pattern in patterns:
                found.extend(p for p in root.rglob(pattern) if not p.is_symlink())
        return sorted(set(found))

    def scan_waveform_artifacts(self) -> list[Path]:
        """Collect waveform summary JSON and VCD trace files."""
        found: list[Path] = []
        for root in self.artifact_roots:
            if not root.exists():
                continue
            for pattern in (*WAVEFORM_GLOBS, "*.vcd"):
                found.extend(p for p in root.rglob(pattern) if not p.is_symlink())
        return sorted(
            {
                path
                for path in found
                if self.waveform_json_parser.can_handle(path) or self.vcd_parser.can_handle(path)
            }
        )

    def index_all(self) -> dict[str, int]:
        """Index all discovered artifacts into the store."""
        artifacts = self.scan_artifacts()
        waveform_artifacts = (
            self.scan_waveform_artifacts() if self.adapters.waveform_summary else []
        )
        stats: dict[str, int | list[str]] = {
            "artifacts": len(artifacts) + len(waveform_artifacts),
            "runs": 0,
            "tests": 0,
            "failures": 0,
            "waveforms": 0,
            "warnings": [],
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

        if self.adapters.assertions:
            stats["warnings"].append(
                "adapters.assertions is enabled but assertion ingestion is not implemented yet"
            )
        if self.adapters.coverage:
            stats["warnings"].append(
                "adapters.coverage is enabled but coverage ingestion is not implemented yet"
            )

        return stats

    def _artifact_within_limit(self, path: Path) -> bool:
        try:
            return path.stat().st_size <= self.security.max_artifact_bytes
        except OSError:
            return False

    def _index_uvm_log(
        self, store: IndexStore, log_path: Path, stats: dict[str, int | list[str]]
    ) -> None:
        if not self._artifact_within_limit(log_path):
            return
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
            self._index_failure(store, failure, test_id, test_id_full, run_id, stats)

    def _index_cocotb_xml(
        self, store: IndexStore, xml_path: Path, stats: dict[str, int | list[str]]
    ) -> None:
        if not self._artifact_within_limit(xml_path):
            return
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
                self._index_failure(store, failure, test_id, test_id_full, run_id, stats)

    def _index_failure(
        self,
        store: IndexStore,
        failure: dict,
        test_id: str,
        test_id_full: str,
        run_id: str,
        stats: dict[str, int | list[str]],
    ) -> None:
        category = failure.get("category") or "unknown"
        summary = truncate_text(failure.get("summary", ""), 500)
        message = truncate_text(
            failure.get("message", ""),
            self.security.max_message_length,
        )
        tags = list(failure.get("tags", []))[: self.security.max_tags_per_event]
        protocol = next(
            (t for t in tags if t in {"axi4", "ahb", "apb", "pcie", "usb", "spi", "i2c"}),
            None,
        )
        failure_id, failure_id_full = generate_failure_id(
            test_id_full=test_id_full,
            severity=failure.get("severity", "error"),
            category=category,
            summary=summary,
        )
        signature_id, _sig_full = generate_signature_id(
            category=category,
            summary=summary,
            protocol=protocol,
        )
        store.insert_failure(
            failure_id=failure_id,
            failure_id_full=failure_id_full,
            test_id=test_id,
            run_id=run_id,
            severity=failure.get("severity", "error"),
            category=category,
            summary=summary,
            message=message,
            tags=tags,
            time_ns=failure.get("time_ns"),
            phase=failure.get("phase"),
            component=failure.get("component"),
            signature_id=signature_id,
        )
        stats["failures"] += 1

    def _index_waveform_summary(
        self, store: IndexStore, artifact_path: Path, stats: dict[str, int | list[str]]
    ) -> None:
        if not self._artifact_within_limit(artifact_path):
            return
        try:
            if self.vcd_parser.can_handle(artifact_path):
                parsed = self.vcd_parser.parse(artifact_path)
            else:
                parsed = self.waveform_json_parser.parse(artifact_path)
        except (OSError, ValueError, json.JSONDecodeError):
            return

        framework = parsed.get("framework")
        if isinstance(framework, str):
            framework = framework.lower()

        test = store.find_test_by_name(parsed["test_name"], framework=framework)
        if not test:
            test = store.find_test_by_name(parsed["test_name"])
        if not test:
            return

        rel = self._relative_path(artifact_path)
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
