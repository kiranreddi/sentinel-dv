"""Artifact indexing for Sentinel DV."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, TypedDict

from sentinel_dv.adapters.assertion_reports import ASSERTION_GLOBS, AssertionReportParser
from sentinel_dv.adapters.cocotb import CocotbParser
from sentinel_dv.adapters.coverage_reports import COVERAGE_GLOBS, CoverageReportParser
from sentinel_dv.adapters.uvm_log import UVMLogParser
from sentinel_dv.adapters.vcd_summary import VcdSummaryParser
from sentinel_dv.adapters.waveform_summary import WAVEFORM_GLOBS, WaveformSummaryParser
from sentinel_dv.config import AdaptersConfig, RedactionConfig, SecurityLimits, SentinelDVConfig
from sentinel_dv.ids import (
    generate_assertion_id,
    generate_failure_id,
    generate_run_id,
    generate_signature_id,
    generate_test_id,
    generate_unknown_assertion_id,
)
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.normalization.redaction import Redactor
from sentinel_dv.utils.bounded_text import truncate_text


class IndexStats(TypedDict):
    """Counters returned by a full artifact indexing pass."""

    artifacts: int
    runs: int
    tests: int
    failures: int
    waveforms: int
    assertions: int
    assertion_failures: int
    coverage: int
    warnings: list[str]


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
        self.assertion_parser = AssertionReportParser(redactor=redactor)
        self.coverage_parser = CoverageReportParser(
            max_metrics=self.security.max_coverage_metrics,
            max_bins_missed=self.security.max_bins_missed,
        )

    @staticmethod
    def _is_cocotb_junit_xml(path: Path) -> bool:
        """True for cocotb/Verilator JUnit exports (results.xml, results_*.xml, *junit*.xml)."""
        name = path.name.lower()
        if path.suffix != ".xml":
            return False
        if name in {"results.xml", "junit.xml"}:
            return True
        return "results" in name or "junit" in name

    def scan_artifacts(self) -> list[Path]:
        """Collect indexable artifact paths under configured roots."""
        found: list[Path] = []
        for root in self.artifact_roots:
            if not root.exists():
                continue
            found.extend(p for p in root.rglob("*.log") if not p.is_symlink())
            found.extend(
                p
                for p in root.rglob("*.xml")
                if not p.is_symlink() and self._is_cocotb_junit_xml(p)
            )
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

    def index_all(self) -> IndexStats:
        """Index all discovered artifacts into the store."""
        artifacts = self.scan_artifacts()
        waveform_artifacts = (
            self.scan_waveform_artifacts() if self.adapters.waveform_summary else []
        )
        assertion_artifacts = self.scan_assertion_artifacts() if self.adapters.assertions else []
        coverage_artifacts = self.scan_coverage_artifacts() if self.adapters.coverage else []
        sva_status_artifacts = self._scan_sva_status_artifacts()
        stats: IndexStats = {
            "artifacts": len(artifacts)
            + len(waveform_artifacts)
            + len(assertion_artifacts)
            + len(coverage_artifacts)
            + len(sva_status_artifacts),
            "runs": 0,
            "tests": 0,
            "failures": 0,
            "waveforms": 0,
            "assertions": 0,
            "assertion_failures": 0,
            "coverage": 0,
            "warnings": [],
        }

        if self.db_path.exists():
            self.db_path.unlink()

        with IndexStore(self.db_path) as store:
            for path in artifacts:
                if path.suffix == ".log" and self.adapters.uvm:
                    self._index_uvm_log(store, path, stats)
                elif self._is_cocotb_junit_xml(path) and self.adapters.cocotb:
                    self._index_cocotb_xml(store, path, stats)

            if self.adapters.waveform_summary:
                for path in waveform_artifacts:
                    self._index_waveform_summary(store, path, stats)

            if self.adapters.assertions:
                for path in assertion_artifacts:
                    self._index_assertion_artifact(store, path, stats)
                if self.adapters.uvm:
                    for path in artifacts:
                        if path.suffix == ".log":
                            self._index_log_assertions(store, path, stats)

            if self.adapters.coverage:
                for path in coverage_artifacts:
                    self._index_coverage_artifact(store, path, stats)

            # Index SVA run status files (assertions.sva_status + assertions.vacuity tools)
            for path in sva_status_artifacts:
                self._index_sva_status_artifact(store, path, stats)

        return stats

    def scan_assertion_artifacts(self) -> list[Path]:
        found: list[Path] = []
        for root in self.artifact_roots:
            if not root.exists():
                continue
            for pattern in ASSERTION_GLOBS:
                found.extend(p for p in root.rglob(pattern) if not p.is_symlink())
        return sorted({p for p in found if self.assertion_parser.can_handle(p)})

    def scan_coverage_artifacts(self) -> list[Path]:
        found: list[Path] = []
        for root in self.artifact_roots:
            if not root.exists():
                continue
            for pattern in COVERAGE_GLOBS:
                found.extend(p for p in root.rglob(pattern) if not p.is_symlink())
        return sorted({p for p in found if self.coverage_parser.can_handle(p)})

    def _artifact_within_limit(self, path: Path) -> bool:
        try:
            return path.stat().st_size <= self.security.max_artifact_bytes
        except OSError:
            return False

    @staticmethod
    def _coerce_taxonomy_value(value: object, default: str) -> str:
        """Normalize taxonomy Enum/str values for DuckDB storage."""
        if value is None:
            return default
        if isinstance(value, Enum):
            return str(value.value)
        return str(value)

    def _index_uvm_log(self, store: IndexStore, log_path: Path, stats: IndexStats) -> None:
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

    def _index_cocotb_xml(self, store: IndexStore, xml_path: Path, stats: IndexStats) -> None:
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

        failures_by_test: dict[str | None, list[dict[str, Any]]] = {}
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
        stats: IndexStats,
    ) -> None:
        category = self._coerce_taxonomy_value(failure.get("category"), "unknown")
        severity = self._coerce_taxonomy_value(failure.get("severity", "error"), "error")
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
            severity=severity,
            category=category,
            summary=summary,
        )
        signature_id, _sig_full = generate_signature_id(
            category=category,
            summary=summary,
            protocol=protocol,
        )
        evidence_refs = self._normalize_evidence_refs(failure.get("evidence", []))
        store.insert_failure(
            failure_id=failure_id,
            failure_id_full=failure_id_full,
            test_id=test_id,
            run_id=run_id,
            severity=severity,
            category=category,
            summary=summary,
            message=message,
            tags=tags,
            time_ns=failure.get("time_ns"),
            phase=failure.get("phase"),
            component=failure.get("component"),
            signature_id=signature_id,
            evidence_refs=evidence_refs,
        )
        stats["failures"] += 1

    def _index_waveform_summary(
        self, store: IndexStore, artifact_path: Path, stats: IndexStats
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

    def _resolve_test_context(
        self, store: IndexStore, test_name: str, framework: str | None = None
    ) -> tuple[str, str, str] | None:
        """Return (test_id, run_id, test_id_full) for an indexed test name."""
        test = store.find_test_by_name(test_name, framework=framework)
        if not test:
            test = store.find_test_by_name(test_name)
        if not test:
            return None
        run = store.get_run(test["run_id"])
        if not run:
            return None
        return test["test_id"], test["run_id"], test["test_id_full"]

    def _index_assertion_artifact(self, store: IndexStore, path: Path, stats: IndexStats) -> None:
        if not self._artifact_within_limit(path):
            return
        try:
            parsed = self.assertion_parser.parse(path)
        except (OSError, ValueError, json.JSONDecodeError):
            return
        test_name = parsed.get("test_name")
        if not test_name:
            return
        ctx = self._resolve_test_context(store, test_name, framework="cocotb")
        if not ctx:
            ctx = self._resolve_test_context(store, test_name)
        if not ctx:
            return
        test_id, run_id, test_id_full = ctx
        self._persist_assertion_bundle(
            store,
            parsed,
            test_id,
            run_id,
            test_id_full,
            stats,
            source_rel=self._relative_path(path),
        )

    def _persist_assertion_bundle(
        self,
        store: IndexStore,
        parsed: dict,
        test_id: str,
        run_id: str,
        test_id_full: str,
        stats: IndexStats,
        source_rel: str = "unknown.log",
    ) -> None:
        name_to_id: dict[str, str] = {}
        for adef in parsed.get("assertions", []):
            assertion_id, assertion_id_full = generate_assertion_id(
                adef["name"],
                adef["scope"],
                adef["file"],
                adef["line"],
                adef.get("language", "sva"),
            )
            store.insert_assertion(
                assertion_id=assertion_id,
                assertion_id_full=assertion_id_full,
                language=adef.get("language", "sva"),
                name=adef["name"],
                scope=adef["scope"],
                file=adef["file"],
                line=adef["line"],
                signals=adef.get("signals", []),
                intent_protocol=adef.get("intent_protocol"),
                intent_requirement=adef.get("intent_requirement"),
                tags=adef.get("tags", []),
            )
            name_to_id[adef["name"]] = assertion_id
            stats["assertions"] += 1

        for fail in parsed.get("failures", []):
            fail_name = str(fail.get("name") or "unknown")
            failure_assertion_id = name_to_id.get(fail_name)
            if not failure_assertion_id:
                failure_assertion_id, assertion_id_full = generate_unknown_assertion_id(
                    test_id_full, fail.get("message", fail_name)
                )
                store.insert_assertion(
                    assertion_id=failure_assertion_id,
                    assertion_id_full=assertion_id_full,
                    language="unknown",
                    name=f"unknown_assertion_{failure_assertion_id[2:10]}",
                    scope="synthetic",
                    file="unknown.sv",
                    line=1,
                    signals=[],
                    intent_protocol=None,
                    intent_requirement=None,
                    tags=["unknown"],
                )
                name_to_id[fail_name] = failure_assertion_id
                stats["assertions"] += 1
            store.insert_assertion_failure(
                assertion_id=failure_assertion_id,
                test_id=test_id,
                run_id=run_id,
                message=fail.get("message", ""),
                time_ns=fail.get("time_ns"),
                evidence_refs=self._normalize_evidence_refs(
                    [{"kind": "log", "path": source_rel, "extract": fail.get("message", "")}]
                ),
            )
            stats["assertion_failures"] += 1

    def _index_log_assertions(self, store: IndexStore, log_path: Path, stats: IndexStats) -> None:
        if not self._artifact_within_limit(log_path):
            return
        result = self.uvm_parser.parse_log(log_path)
        test_name = (result.get("test") or {}).get("name")
        if not test_name:
            return
        parsed = self.assertion_parser.parse_log_assertions(log_path, test_name)
        if not parsed.get("failures"):
            return
        ctx = self._resolve_test_context(store, test_name, framework="uvm")
        if not ctx:
            return
        parsed["assertions"] = []
        self._persist_assertion_bundle(
            store, parsed, *ctx, stats, source_rel=self._relative_path(log_path)
        )

    def _index_coverage_artifact(self, store: IndexStore, path: Path, stats: IndexStats) -> None:
        if not self._artifact_within_limit(path):
            return
        try:
            parsed = self.coverage_parser.parse(path)
        except (OSError, ValueError, json.JSONDecodeError):
            return
        test_name = parsed.get("test_name")
        test_id = None
        run_id = None
        if test_name:
            ctx = self._resolve_test_context(store, test_name, framework="cocotb")
            if not ctx:
                ctx = self._resolve_test_context(store, test_name)
            if ctx:
                test_id, run_id, _ = ctx
        if not run_id:
            rel = self._relative_path(path)
            run_id, run_id_full = generate_run_id(
                suite=path.parent.name or "coverage",
                artifact_manifest=[(rel, self._file_hash(path))],
            )
            created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            if not store.get_run(run_id):
                store.insert_run(
                    run_id=run_id,
                    run_id_full=run_id_full,
                    suite=path.parent.name or "coverage",
                    created_at=created_at,
                    status="pass",
                )
                stats["runs"] += 1

        rel = self._relative_path(path)
        store.insert_coverage_summary(
            run_id=run_id,
            kind=parsed["kind"],
            metrics=parsed["metrics"],
            test_id=test_id,
            evidence={"kind": "coverage", "path": rel},
        )
        stats["coverage"] += 1

    # ------------------------------------------------------------------
    # SVA run status indexing (assertions.sva_status + assertions.vacuity)
    # ------------------------------------------------------------------
    _SVA_STATUS_GLOBS: tuple[str, ...] = ("*sva_status*.json", "*sva*.json")

    def _scan_sva_status_artifacts(self) -> list[Path]:
        """Collect *sva_status*.json files from all artifact roots."""
        found: set[Path] = set()
        for root in self.artifact_roots:
            if not root.exists():
                continue
            for pat in self._SVA_STATUS_GLOBS:
                for p in root.rglob(pat):
                    if not p.is_symlink() and self._is_sva_status_file(p):
                        found.add(p)
        return sorted(found)

    @staticmethod
    def _is_sva_status_file(path: Path) -> bool:
        """Return True if the file looks like an SVA status report (has sva_status list)."""
        try:
            with path.open() as fh:
                first_chars = fh.read(512)
            return '"sva_status"' in first_chars
        except OSError:
            return False

    def _index_sva_status_artifact(self, store: IndexStore, path: Path, stats: IndexStats) -> None:
        """Index a *_sva.json file into the sva_run_status table."""
        if not self._artifact_within_limit(path):
            return
        try:
            with path.open() as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return

        sva_list = data.get("sva_status", [])
        if not isinstance(sva_list, list) or not sva_list:
            return

        test_name = data.get("test_name")
        test_id = run_id = None
        if test_name:
            ctx = self._resolve_test_context(store, test_name)
            if ctx:
                test_id, run_id, _ = ctx

        for entry in sva_list:
            if not isinstance(entry, dict):
                continue
            assertion_name = entry.get("name", "")
            status = entry.get("status", "unknown")
            attempts = int(entry.get("attempts", 0))
            failures = int(entry.get("failures", 0))
            is_vacuous = bool(entry.get("vacuous", status == "vacuous"))

            # Look up assertion_id from the assertions table
            assertion_id = None
            if assertion_name and test_id:
                row = store._conn.execute(
                    "SELECT assertion_id FROM assertions WHERE name = ? LIMIT 1",
                    [assertion_name],
                ).fetchone()
                if row:
                    assertion_id = row[0]

            try:
                store.insert_sva_run_status(
                    assertion_id=assertion_id or "",
                    run_id=run_id or "",
                    test_id=test_id or "",
                    status="vacuous" if is_vacuous else status,
                    pass_count=attempts - failures,
                    fail_count=failures,
                    vacuous_count=1 if is_vacuous else 0,
                )
            except Exception:
                continue

    def _normalize_evidence_refs(self, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize evidence refs to bounded, relative-path-only payloads."""
        normalized: list[dict[str, Any]] = []
        max_refs = self.security.max_evidence_refs
        max_extract = self.security.max_excerpt_length
        for ref in refs[:max_refs]:
            path_value = str(ref.get("path", "")).strip().replace("\\", "/")
            if not path_value:
                continue
            p = Path(path_value)
            if p.is_absolute():
                try:
                    path_value = self._relative_path(p)
                except ValueError:
                    continue
            if path_value.startswith("/") or path_value.startswith("//"):
                continue
            if len(path_value) >= 2 and path_value[1] == ":":
                continue
            normalized_path = PurePosixPath(path_value)
            if ".." in normalized_path.parts:
                continue
            path_value = normalized_path.as_posix()
            span = ref.get("span") or {}
            item: dict[str, Any] = {
                "kind": str(ref.get("kind", "log")),
                "path": path_value,
                "span": {
                    k: span.get(k)
                    for k in ("start_line", "end_line", "start_time_ns", "end_time_ns")
                    if span.get(k) is not None
                },
                "extract": (
                    truncate_text(str(ref.get("extract", "")), max_extract)
                    if ref.get("extract")
                    else None
                ),
            }
            normalized.append(item)
        return normalized

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
