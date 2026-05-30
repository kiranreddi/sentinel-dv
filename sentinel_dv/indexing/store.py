"""
Index storage backend for Sentinel DV.

This module provides the DuckDB-based storage layer for indexed verification artifacts.
Implements the schema documented in docs/index-store.md.
"""

import contextlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

# Fixed ORDER BY fragments (never interpolate user input into SQL).
_TESTS_ORDER_BY: dict[str, str] = {
    "created_at": "created_at",
    "name": "name",
    "status": "status",
    "test_id": "test_id",
    "duration_ms": "duration_ms",
}
_RUNS_ORDER_BY: dict[str, str] = {
    "created_at": "r.created_at",
    "suite": "r.suite",
    "status": "r.status",
    "run_id": "r.run_id",
}
_ID_SEQUENCES: dict[str, str] = {
    "assertion_failures": "assertion_failures_id_seq",
    "evidence": "evidence_id_seq",
    "coverage_summaries": "coverage_summaries_id_seq",
    "sva_run_status": "sva_run_status_id_seq",
}


def _iso_to_epoch_ms(iso_timestamp: str) -> int | None:
    """Parse RFC3339 UTC timestamps to epoch milliseconds for window queries."""
    try:
        normalized = iso_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (TypeError, ValueError):
        return None


class IndexStore:
    """
    DuckDB-based index store for verification artifacts.

    Provides efficient storage and querying of runs, tests, failures,
    assertions, and coverage data.
    """

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, db_path: Path | str):
        """
        Initialize the index store.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = Path(db_path)
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> None:
        """Open connection to the database and create schema if needed."""
        self._conn = duckdb.connect(str(self.db_path))
        self._create_schema()
        self._set_metadata("schema_version", self.SCHEMA_VERSION)

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "IndexStore":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    # ========================================================================
    # Schema creation
    # ========================================================================

    def _create_schema(self) -> None:
        """Create all database tables and indexes."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        # Metadata table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Runs table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                run_id_full TEXT UNIQUE NOT NULL,
                suite TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                ci_system TEXT,
                ci_build_id TEXT,
                ci_job_url TEXT,
                artifact_manifest_hash TEXT,
                index_built_at TEXT NOT NULL
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_suite_created_at
            ON runs(suite, created_at)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_ci_build
            ON runs(ci_system, ci_build_id)
        """)

        # Tests table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                test_id TEXT PRIMARY KEY,
                test_id_full TEXT UNIQUE NOT NULL,
                run_id TEXT NOT NULL,
                framework TEXT NOT NULL,
                name TEXT NOT NULL,
                seed INTEGER,
                status TEXT NOT NULL,
                duration_ms INTEGER,
                sim_vendor TEXT,
                sim_version TEXT,
                dut_top TEXT,
                created_at TEXT NOT NULL
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tests_run_status
            ON tests(run_id, status)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tests_name
            ON tests(name)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tests_framework
            ON tests(framework)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tests_created_at
            ON tests(created_at)
        """)

        # Failures table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS failures (
                failure_id TEXT PRIMARY KEY,
                failure_id_full TEXT UNIQUE NOT NULL,
                test_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT NOT NULL,
                message TEXT NOT NULL,
                time_ns BIGINT,
                phase TEXT,
                component TEXT,
                tags_json TEXT NOT NULL,
                tags_flat TEXT NOT NULL,
                signature_id TEXT
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failures_run_category
            ON failures(run_id, category)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failures_test
            ON failures(test_id)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failures_signature
            ON failures(signature_id)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_failures_time
            ON failures(time_ns)
        """)

        # Assertions table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS assertions (
                assertion_id TEXT PRIMARY KEY,
                assertion_id_full TEXT UNIQUE NOT NULL,
                language TEXT NOT NULL,
                name TEXT NOT NULL,
                scope TEXT NOT NULL,
                file TEXT NOT NULL,
                line INTEGER NOT NULL,
                intent_protocol TEXT,
                intent_requirement TEXT,
                signals_json TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                tags_flat TEXT NOT NULL DEFAULT ''
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assertions_name
            ON assertions(name)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assertions_scope
            ON assertions(scope)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_assertions_file
            ON assertions(file)
        """)

        # Assertion failures table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS assertion_failures (
                id INTEGER PRIMARY KEY,
                assertion_id TEXT NOT NULL,
                test_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                time_ns BIGINT,
                message TEXT NOT NULL
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_asfail_run
            ON assertion_failures(run_id)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_asfail_test
            ON assertion_failures(test_id)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_asfail_assertion
            ON assertion_failures(assertion_id)
        """)

        # Coverage summaries table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS coverage_summaries (
                id INTEGER PRIMARY KEY,
                run_id TEXT NOT NULL,
                test_id TEXT,
                kind TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                evidence_json TEXT
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cov_run_kind
            ON coverage_summaries(run_id, kind)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cov_test_kind
            ON coverage_summaries(test_id, kind)
        """)

        # Topologies table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS topologies (
                test_id TEXT PRIMARY KEY,
                topology_json TEXT NOT NULL
            )
        """)

        # Precomputed waveform summaries (per test)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS waveform_summaries (
                test_id TEXT PRIMARY KEY,
                format TEXT NOT NULL,
                end_time_ns BIGINT,
                summary_json TEXT NOT NULL,
                source_path TEXT NOT NULL
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_waveform_end_time
            ON waveform_summaries(end_time_ns)
        """)

        # Evidence table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY,
                owner_kind TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                start_line INTEGER,
                end_line INTEGER,
                start_time_ns BIGINT,
                end_time_ns BIGINT,
                extract TEXT,
                hash TEXT
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_evidence_owner
            ON evidence(owner_kind, owner_id)
        """)

        # SVA run status table (per-assertion runtime status)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sva_run_status (
                id INTEGER PRIMARY KEY,
                assertion_id TEXT NOT NULL,
                test_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                status TEXT NOT NULL,
                pass_count INTEGER NOT NULL DEFAULT 0,
                fail_count INTEGER NOT NULL DEFAULT 0,
                vacuous_count INTEGER NOT NULL DEFAULT 0
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sva_run_status_assertion
            ON sva_run_status(assertion_id)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sva_run_status_run
            ON sva_run_status(run_id)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sva_run_status_test
            ON sva_run_status(test_id)
        """)

        self._migrate_schema()
        self._ensure_id_sequences()

    def _migrate_schema(self) -> None:
        """Add epoch-ms columns and backfill from legacy ISO created_at strings."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        for table in ("runs", "tests"):
            with contextlib.suppress(duckdb.Error):
                self._conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS created_at_ms BIGINT"
                )
            rows = self._conn.execute(
                f"SELECT rowid, created_at FROM {table} WHERE created_at_ms IS NULL"
            ).fetchall()
            for rowid, created_at in rows:
                epoch_ms = _iso_to_epoch_ms(created_at) if created_at else None
                if epoch_ms is not None:
                    self._conn.execute(
                        f"UPDATE {table} SET created_at_ms = ? WHERE rowid = ?",
                        [epoch_ms, rowid],
                    )

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_suite_created_at_ms
            ON runs(suite, created_at_ms)
        """)

    def _ensure_id_sequences(self) -> None:
        """Create monotonic ID sequences for tables that previously used MAX(id)+1."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        existing = {
            row[0]
            for row in self._conn.execute("SELECT sequence_name FROM duckdb_sequences()").fetchall()
        }
        for table, seq_name in _ID_SEQUENCES.items():
            if seq_name in existing:
                continue
            max_row = self._conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}").fetchone()
            max_id = int(max_row[0]) if max_row else 0
            start = max(max_id + 1, 1)
            self._conn.execute(f"CREATE SEQUENCE {seq_name} START {start}")

    def _next_row_id(self, sequence_name: str) -> int:
        """Allocate the next integer primary key from a named sequence."""
        if not self._conn:
            raise RuntimeError("Not connected to database")
        row = self._conn.execute(f"SELECT nextval('{sequence_name}')").fetchone()
        return int(row[0]) if row else 1

    # ========================================================================
    # Metadata operations
    # ========================================================================

    def _set_metadata(self, key: str, value: str) -> None:
        """Set metadata key-value pair."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        self._conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", [key, value])

    def _get_metadata(self, key: str) -> str | None:
        """Get metadata value by key."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute("SELECT value FROM meta WHERE key = ?", [key]).fetchone()

        return result[0] if result else None

    # ========================================================================
    # Run operations
    # ========================================================================

    def insert_run(
        self,
        run_id: str,
        run_id_full: str,
        suite: str,
        created_at: str,
        status: str,
        ci_system: str | None = None,
        ci_build_id: str | None = None,
        ci_job_url: str | None = None,
        artifact_manifest_hash: str | None = None,
    ) -> None:
        """Insert a new run record."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        index_built_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        created_at_ms = _iso_to_epoch_ms(created_at)

        self._conn.execute(
            """
            INSERT INTO runs (
                run_id, run_id_full, suite, created_at, created_at_ms, status,
                ci_system, ci_build_id, ci_job_url,
                artifact_manifest_hash, index_built_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (run_id) DO UPDATE SET
                run_id_full=excluded.run_id_full,
                suite=excluded.suite,
                created_at=excluded.created_at,
                created_at_ms=excluded.created_at_ms,
                status=excluded.status,
                ci_system=excluded.ci_system,
                ci_build_id=excluded.ci_build_id,
                ci_job_url=excluded.ci_job_url,
                artifact_manifest_hash=excluded.artifact_manifest_hash,
                index_built_at=excluded.index_built_at
        """,
            [
                run_id,
                run_id_full,
                suite,
                created_at,
                created_at_ms,
                status,
                ci_system,
                ci_build_id,
                ci_job_url,
                artifact_manifest_hash,
                index_built_at,
            ],
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get run by ID."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", [run_id]).fetchone()

        if not result:
            return None

        columns = [desc[0] for desc in self._conn.description]
        return dict(zip(columns, result, strict=False))

    def count_runs(self) -> int:
        """Get total number of indexed runs."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute("SELECT COUNT(*) FROM runs").fetchone()
        return result[0] if result else 0

    # ========================================================================
    # Test operations
    # ========================================================================

    def insert_test(
        self,
        test_id: str,
        test_id_full: str,
        run_id: str,
        framework: str,
        name: str,
        status: str,
        created_at: str,
        seed: int | None = None,
        duration_ms: int | None = None,
        sim_vendor: str | None = None,
        sim_version: str | None = None,
        dut_top: str | None = None,
    ) -> None:
        """Insert a new test record."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        created_at_ms = _iso_to_epoch_ms(created_at)

        self._conn.execute(
            """
            INSERT INTO tests (
                test_id, test_id_full, run_id, framework, name, seed,
                status, duration_ms, sim_vendor, sim_version, dut_top,
                created_at, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (test_id) DO UPDATE SET
                test_id_full=excluded.test_id_full,
                run_id=excluded.run_id,
                framework=excluded.framework,
                name=excluded.name,
                seed=excluded.seed,
                status=excluded.status,
                duration_ms=excluded.duration_ms,
                sim_vendor=excluded.sim_vendor,
                sim_version=excluded.sim_version,
                dut_top=excluded.dut_top,
                created_at=excluded.created_at,
                created_at_ms=excluded.created_at_ms
        """,
            [
                test_id,
                test_id_full,
                run_id,
                framework,
                name,
                seed,
                status,
                duration_ms,
                sim_vendor,
                sim_version,
                dut_top,
                created_at,
                created_at_ms,
            ],
        )

    def count_tests(self) -> int:
        """Get total number of indexed tests."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute("SELECT COUNT(*) FROM tests").fetchone()
        return result[0] if result else 0

    # ========================================================================
    # Failure operations
    # ========================================================================

    def insert_failure(
        self,
        failure_id: str,
        failure_id_full: str,
        test_id: str,
        run_id: str,
        severity: str,
        category: str,
        summary: str,
        message: str,
        tags: list[str],
        time_ns: int | None = None,
        phase: str | None = None,
        component: str | None = None,
        signature_id: str | None = None,
        evidence_refs: list[dict[str, Any]] | None = None,
    ) -> None:
        """Insert a new failure record."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        tags_json = json.dumps(tags)
        tags_flat = " ".join(t.lower() for t in tags)

        self._conn.execute(
            """
            INSERT INTO failures (
                failure_id, failure_id_full, test_id, run_id,
                severity, category, summary, message,
                time_ns, phase, component,
                tags_json, tags_flat, signature_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (failure_id) DO UPDATE SET
                failure_id_full=excluded.failure_id_full,
                test_id=excluded.test_id,
                run_id=excluded.run_id,
                severity=excluded.severity,
                category=excluded.category,
                summary=excluded.summary,
                message=excluded.message,
                time_ns=excluded.time_ns,
                phase=excluded.phase,
                component=excluded.component,
                tags_json=excluded.tags_json,
                tags_flat=excluded.tags_flat,
                signature_id=excluded.signature_id
        """,
            [
                failure_id,
                failure_id_full,
                test_id,
                run_id,
                severity,
                category,
                summary,
                message,
                time_ns,
                phase,
                component,
                tags_json,
                tags_flat,
                signature_id,
            ],
        )
        self._conn.execute(
            "DELETE FROM evidence WHERE owner_kind = ? AND owner_id = ?",
            ["failure", failure_id],
        )
        for ref in evidence_refs or []:
            self.insert_evidence(
                owner_kind="failure",
                owner_id=failure_id,
                kind=str(ref.get("kind", "log")),
                path=str(ref.get("path", "")),
                start_line=(ref.get("span") or {}).get("start_line"),
                end_line=(ref.get("span") or {}).get("end_line"),
                start_time_ns=(ref.get("span") or {}).get("start_time_ns"),
                end_time_ns=(ref.get("span") or {}).get("end_time_ns"),
                extract=ref.get("extract"),
            )

    def count_failures(self) -> int:
        """Get total number of indexed failures."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute("SELECT COUNT(*) FROM failures").fetchone()
        return result[0] if result else 0

    def insert_assertion(
        self,
        assertion_id: str,
        assertion_id_full: str,
        language: str,
        name: str,
        scope: str,
        file: str,
        line: int,
        signals: list[str],
        intent_protocol: str | None = None,
        intent_requirement: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Insert or replace an assertion definition."""
        if not self._conn:
            raise RuntimeError("Not connected to database")
        tag_list = tags or []
        self._conn.execute(
            """
            INSERT INTO assertions (
                assertion_id, assertion_id_full, language, name, scope, file, line,
                intent_protocol, intent_requirement, signals_json, tags_json, tags_flat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (assertion_id) DO UPDATE SET
                assertion_id_full=excluded.assertion_id_full,
                language=excluded.language,
                name=excluded.name,
                scope=excluded.scope,
                file=excluded.file,
                line=excluded.line,
                intent_protocol=excluded.intent_protocol,
                intent_requirement=excluded.intent_requirement,
                signals_json=excluded.signals_json,
                tags_json=excluded.tags_json,
                tags_flat=excluded.tags_flat
        """,
            [
                assertion_id,
                assertion_id_full,
                language,
                name,
                scope,
                file,
                line,
                intent_protocol,
                intent_requirement,
                json.dumps(signals),
                json.dumps(tag_list),
                " ".join(t.lower() for t in tag_list),
            ],
        )

    def insert_assertion_failure(
        self,
        assertion_id: str,
        test_id: str,
        run_id: str,
        message: str,
        time_ns: int | None = None,
        evidence_refs: list[dict[str, Any]] | None = None,
    ) -> None:
        """Insert a runtime assertion failure."""
        if not self._conn:
            raise RuntimeError("Not connected to database")
        next_id = self._next_row_id(_ID_SEQUENCES["assertion_failures"])
        self._conn.execute(
            """
            INSERT INTO assertion_failures (
                id, assertion_id, test_id, run_id, time_ns, message
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            [next_id, assertion_id, test_id, run_id, time_ns, message],
        )
        self._conn.execute(
            "DELETE FROM evidence WHERE owner_kind = ? AND owner_id = ?",
            ["assertion_failure", str(next_id)],
        )
        for ref in evidence_refs or []:
            self.insert_evidence(
                owner_kind="assertion_failure",
                owner_id=str(next_id),
                kind=str(ref.get("kind", "log")),
                path=str(ref.get("path", "")),
                start_line=(ref.get("span") or {}).get("start_line"),
                end_line=(ref.get("span") or {}).get("end_line"),
                start_time_ns=(ref.get("span") or {}).get("start_time_ns"),
                end_time_ns=(ref.get("span") or {}).get("end_time_ns"),
                extract=ref.get("extract"),
            )

    def insert_evidence(
        self,
        owner_kind: str,
        owner_id: str,
        kind: str,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        start_time_ns: int | None = None,
        end_time_ns: int | None = None,
        extract: str | None = None,
        hash_value: str | None = None,
    ) -> None:
        """Insert normalized evidence row."""
        if not self._conn:
            raise RuntimeError("Not connected to database")
        next_id = self._next_row_id(_ID_SEQUENCES["evidence"])
        self._conn.execute(
            """
            INSERT INTO evidence (
                id, owner_kind, owner_id, kind, path,
                start_line, end_line, start_time_ns, end_time_ns, extract, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                next_id,
                owner_kind,
                owner_id,
                kind,
                path,
                start_line,
                end_line,
                start_time_ns,
                end_time_ns,
                extract,
                hash_value,
            ],
        )

    def get_evidence(self, owner_kind: str, owner_id: str) -> list[dict[str, Any]]:
        """Get evidence rows for an owner."""
        if not self._conn:
            raise RuntimeError("Not connected to database")
        rows = self._conn.execute(
            """
            SELECT kind, path, start_line, end_line, start_time_ns, end_time_ns, extract, hash
            FROM evidence
            WHERE owner_kind = ? AND owner_id = ?
            ORDER BY id ASC
        """,
            [owner_kind, owner_id],
        ).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            span = {
                "start_line": row[2],
                "end_line": row[3],
                "start_time_ns": row[4],
                "end_time_ns": row[5],
            }
            items.append(
                {
                    "kind": row[0],
                    "path": row[1],
                    "span": {k: v for k, v in span.items() if v is not None},
                    "extract": row[6],
                    "hash": row[7],
                }
            )
        return items

    def count_assertions(self) -> int:
        if not self._conn:
            raise RuntimeError("Not connected to database")
        result = self._conn.execute("SELECT COUNT(*) FROM assertions").fetchone()
        return result[0] if result else 0

    # ========================================================================
    # Query operations
    # ========================================================================

    def query_tests(
        self,
        run_id: str | None = None,
        framework: str | None = None,
        status: str | None = None,
        name_pattern: str | None = None,
        seed: int | None = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Query tests with filters and pagination.

        Returns:
            Tuple of (results, total_count)
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        order_column = _TESTS_ORDER_BY.get(sort_by)
        if order_column is None:
            raise ValueError(f"Invalid sort_by: {sort_by}")

        # Build WHERE clause
        where_clauses: list[str] = []
        params: list[Any] = []

        if run_id:
            where_clauses.append("run_id = ?")
            params.append(run_id)

        if framework:
            where_clauses.append("framework = ?")
            params.append(framework)

        if status:
            where_clauses.append("status = ?")
            params.append(status)

        if name_pattern:
            where_clauses.append("name LIKE ?")
            params.append(f"%{name_pattern}%")

        if seed is not None:
            where_clauses.append("seed = ?")
            params.append(seed)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_result = self._conn.execute(
            f"SELECT COUNT(*) FROM tests WHERE {where_sql}", params
        ).fetchone()
        total = count_result[0] if count_result else 0

        # Get paginated results
        offset = (page - 1) * page_size
        order_dir = "DESC" if sort_desc else "ASC"

        results = self._conn.execute(
            f"""
            SELECT * FROM tests
            WHERE {where_sql}
            ORDER BY {order_column} {order_dir}, test_id ASC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        ).fetchall()

        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row, strict=False)) for row in results], total

    def query_failures(
        self,
        test_id: str | None = None,
        run_id: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        component_pattern: str | None = None,
        tags_any: list[str] | None = None,
        include_evidence: bool = False,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Query failures with filters and pagination.

        Returns:
            Tuple of (results, total_count)
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        # Build WHERE clause
        where_clauses = []
        params = []

        if test_id:
            where_clauses.append("test_id = ?")
            params.append(test_id)

        if run_id:
            where_clauses.append("run_id = ?")
            params.append(run_id)

        if category:
            where_clauses.append("category = ?")
            params.append(category)

        if severity:
            where_clauses.append("severity = ?")
            params.append(severity)

        if component_pattern:
            where_clauses.append("component LIKE ?")
            params.append(f"%{component_pattern}%")

        if tags_any:
            tag_conditions = " OR ".join(["tags_flat LIKE ?" for _ in tags_any])
            where_clauses.append(f"({tag_conditions})")
            params.extend([f"%{tag.lower()}%" for tag in tags_any])

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_result = self._conn.execute(
            f"SELECT COUNT(*) FROM failures WHERE {where_sql}", params
        ).fetchone()
        total = count_result[0] if count_result else 0

        # Get paginated results
        offset = (page - 1) * page_size

        results = self._conn.execute(
            f"""
            SELECT * FROM failures
            WHERE {where_sql}
            ORDER BY time_ns DESC, failure_id ASC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        ).fetchall()

        columns = [desc[0] for desc in self._conn.description]
        items = [dict(zip(columns, row, strict=False)) for row in results]
        if include_evidence:
            for item in items:
                item["evidence"] = self.get_evidence("failure", item["failure_id"])
        return items, total

    def query_runs(
        self,
        suite: str | None = None,
        status: str | None = None,
        ci_system: str | None = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query runs with optional filters and aggregated test counts."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        order_column = _RUNS_ORDER_BY.get(sort_by)
        if order_column is None:
            raise ValueError(f"Invalid sort_by: {sort_by}")

        where_clauses: list[str] = []
        params: list[Any] = []

        if suite:
            where_clauses.append("r.suite = ?")
            params.append(suite)
        if status:
            where_clauses.append("r.status = ?")
            params.append(status)
        if ci_system:
            where_clauses.append("r.ci_system = ?")
            params.append(ci_system)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        order_dir = "DESC" if sort_desc else "ASC"

        count_result = self._conn.execute(
            f"SELECT COUNT(*) FROM runs r WHERE {where_sql}", params
        ).fetchone()
        total = count_result[0] if count_result else 0

        offset = (page - 1) * page_size
        results = self._conn.execute(
            f"""
            SELECT
                r.run_id,
                r.suite,
                r.status,
                r.created_at,
                r.ci_system,
                r.ci_build_id,
                COUNT(t.test_id) AS total_tests,
                SUM(CASE WHEN t.status = 'pass' THEN 1 ELSE 0 END) AS passed_tests,
                SUM(CASE WHEN t.status = 'fail' THEN 1 ELSE 0 END) AS failed_tests
            FROM runs r
            LEFT JOIN tests t ON r.run_id = t.run_id
            WHERE {where_sql}
            GROUP BY r.run_id, r.suite, r.status, r.created_at, r.ci_system, r.ci_build_id
            ORDER BY {order_column} {order_dir}, r.run_id ASC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        ).fetchall()

        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row, strict=False)) for row in results], total

    def get_test(self, test_id: str) -> dict[str, Any] | None:
        """Get a single test record by ID."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute("SELECT * FROM tests WHERE test_id = ?", [test_id]).fetchone()
        if not result:
            return None
        columns = [desc[0] for desc in self._conn.description]
        return dict(zip(columns, result, strict=False))

    def get_topology(self, test_id: str) -> dict[str, Any] | None:
        """Get stored topology JSON for a test."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute(
            "SELECT topology_json FROM topologies WHERE test_id = ?", [test_id]
        ).fetchone()
        if not result:
            return None
        topology = json.loads(result[0])
        if not isinstance(topology, dict):
            raise ValueError(f"Invalid topology payload for test {test_id}")
        return topology

    def insert_topology(self, test_id: str, topology: dict[str, Any]) -> None:
        """Insert or replace topology for a test."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        self._conn.execute(
            """
            INSERT OR REPLACE INTO topologies (test_id, topology_json)
            VALUES (?, ?)
        """,
            [test_id, json.dumps(topology)],
        )

    def find_test_by_name(
        self,
        name: str,
        framework: str | None = None,
    ) -> dict[str, Any] | None:
        """Find the most recent test matching name (and optional framework)."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        exact_name = name
        suffix_pattern = f"%.{name}"
        contains_pattern = f"%{name}%"
        match_clauses = ["name = ?", "name LIKE ?", "name LIKE ?"]
        params: list[Any] = [exact_name, suffix_pattern, contains_pattern]
        framework_clause = ""
        if framework:
            framework_clause = "AND framework = ?"
            params.append(framework)

        result = self._conn.execute(
            f"""
            SELECT * FROM tests
            WHERE ({' OR '.join(match_clauses)}) {framework_clause}
            ORDER BY
                CASE
                    WHEN name = ? THEN 0
                    WHEN name LIKE ? THEN 1
                    ELSE 2
                END,
                created_at DESC,
                test_id ASC
            LIMIT 1
        """,
            params + [exact_name, suffix_pattern],
        ).fetchone()
        if not result:
            return None
        columns = [desc[0] for desc in self._conn.description]
        return dict(zip(columns, result, strict=False))

    def insert_waveform_summary(
        self,
        test_id: str,
        summary: dict[str, Any],
        source_path: str,
    ) -> None:
        """Insert or replace a precomputed waveform summary for a test."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        self._conn.execute(
            """
            INSERT OR REPLACE INTO waveform_summaries
            (test_id, format, end_time_ns, summary_json, source_path)
            VALUES (?, ?, ?, ?, ?)
        """,
            [
                test_id,
                summary.get("format", "precomputed"),
                summary.get("end_time_ns"),
                json.dumps(summary),
                source_path,
            ],
        )

    def get_waveform_summary(self, test_id: str) -> dict[str, Any] | None:
        """Get stored waveform summary for a test."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute(
            """
            SELECT format, end_time_ns, summary_json, source_path
            FROM waveform_summaries
            WHERE test_id = ?
        """,
            [test_id],
        ).fetchone()
        if not result:
            return None

        summary = json.loads(result[2])
        return {
            "test_id": test_id,
            "format": result[0],
            "end_time_ns": result[1],
            "source_path": result[3],
            "summary": summary,
        }

    def query_assertions(
        self,
        scope: str | None = None,
        name_pattern: str | None = None,
        protocol: str | None = None,
        tag: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        """List assertion definitions."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        where_clauses: list[str] = []
        params: list[Any] = []

        if scope:
            where_clauses.append("scope = ?")
            params.append(scope)
        if name_pattern:
            where_clauses.append("name LIKE ?")
            params.append(f"%{name_pattern}%")
        if protocol:
            where_clauses.append("intent_protocol = ?")
            params.append(protocol.lower())
        if tag:
            where_clauses.append("tags_flat LIKE ?")
            params.append(f"%{tag.lower()}%")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        count_result = self._conn.execute(
            f"SELECT COUNT(*) FROM assertions WHERE {where_sql}", params
        ).fetchone()
        total = count_result[0] if count_result else 0

        offset = (page - 1) * page_size
        results = self._conn.execute(
            f"""
            SELECT * FROM assertions
            WHERE {where_sql}
            ORDER BY name ASC, assertion_id ASC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        ).fetchall()

        return [self._format_assertion_row(row) for row in results], total

    @staticmethod
    def _format_assertion_row(row: tuple[Any, ...]) -> dict[str, Any]:
        """Map DB row to MCP-friendly assertion dict."""
        (
            assertion_id,
            _full,
            language,
            name,
            scope,
            file,
            line,
            intent_protocol,
            intent_requirement,
            signals_json,
            tags_json,
            _tags_flat,
        ) = row
        signals = json.loads(signals_json) if signals_json else []
        tags = json.loads(tags_json) if tags_json else []
        return {
            "assertion_id": assertion_id,
            "language": language,
            "name": name,
            "scope": scope,
            "file": file,
            "line": line,
            "signals": signals,
            "tags": tags,
            "intent": {
                "protocol": intent_protocol,
                "requirement": intent_requirement,
            },
        }

    def get_assertion(self, assertion_id: str) -> dict[str, Any] | None:
        """Get assertion definition by ID."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute(
            "SELECT * FROM assertions WHERE assertion_id = ?", [assertion_id]
        ).fetchone()
        if not result:
            return None
        return self._format_assertion_row(result)

    def query_assertion_failures(
        self,
        run_id: str | None = None,
        test_id: str | None = None,
        assertion_id: str | None = None,
        start_time_ns: int | None = None,
        end_time_ns: int | None = None,
        include_evidence: bool = False,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        """List runtime assertion failures."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        where_clauses: list[str] = []
        params: list[Any] = []

        if run_id:
            where_clauses.append("run_id = ?")
            params.append(run_id)
        if test_id:
            where_clauses.append("test_id = ?")
            params.append(test_id)
        if assertion_id:
            where_clauses.append("assertion_id = ?")
            params.append(assertion_id)
        if start_time_ns is not None:
            where_clauses.append("(time_ns IS NULL OR time_ns >= ?)")
            params.append(start_time_ns)
        if end_time_ns is not None:
            where_clauses.append("(time_ns IS NULL OR time_ns <= ?)")
            params.append(end_time_ns)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        count_result = self._conn.execute(
            f"SELECT COUNT(*) FROM assertion_failures WHERE {where_sql}", params
        ).fetchone()
        total = count_result[0] if count_result else 0

        offset = (page - 1) * page_size
        results = self._conn.execute(
            f"""
            SELECT id, assertion_id, test_id, run_id, time_ns, message
            FROM assertion_failures
            WHERE {where_sql}
            ORDER BY COALESCE(time_ns, -1) DESC, id ASC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        ).fetchall()

        items = [
            {
                "id": row[0],
                "assertion_id": row[1],
                "test_id": row[2],
                "run_id": row[3],
                "time_ns": row[4],
                "message": row[5],
            }
            for row in results
        ]
        if include_evidence:
            for item in items:
                item["evidence"] = self.get_evidence("assertion_failure", str(item["id"]))
        return items, total

    def query_coverage_summaries(
        self,
        run_id: str | None = None,
        kind: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        """List coverage summary rows."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        where_clauses: list[str] = []
        params: list[Any] = []

        if run_id:
            where_clauses.append("run_id = ?")
            params.append(run_id)
        if kind:
            where_clauses.append("kind = ?")
            params.append(kind)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        count_result = self._conn.execute(
            f"SELECT COUNT(*) FROM coverage_summaries WHERE {where_sql}", params
        ).fetchone()
        total = count_result[0] if count_result else 0

        offset = (page - 1) * page_size
        results = self._conn.execute(
            f"""
            SELECT id, run_id, test_id, kind, metrics_json, evidence_json
            FROM coverage_summaries
            WHERE {where_sql}
            ORDER BY run_id ASC, kind ASC, id ASC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        ).fetchall()

        items = []
        for row in results:
            items.append(
                {
                    "id": row[0],
                    "run_id": row[1],
                    "test_id": row[2],
                    "kind": row[3],
                    "metrics": json.loads(row[4]),
                    "evidence": json.loads(row[5]) if row[5] else None,
                }
            )
        return items, total

    def query_coverage_metrics(
        self,
        suite: str | None = None,
        kind: str | None = None,
        limit: int = 2000,
    ) -> list[dict[str, Any]]:
        """Return flattened coverage metric rows for gap analysis.

        Each element corresponds to a single metric entry within an indexed
        coverage summary, enriched with run and suite metadata.

        Args:
            suite: Filter to a specific suite (via runs table join).
            kind: Filter to a specific coverage kind.
            limit: Maximum number of metrics to return.

        Returns:
            List of metric dicts with keys: name, scope, covered, hits, total,
            bins_missed, kind, run_id, suite.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        where_clauses: list[str] = []
        params: list[Any] = []

        if suite:
            where_clauses.append("r.suite = ?")
            params.append(suite)
        if kind:
            where_clauses.append("cs.kind = ?")
            params.append(kind)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        params.append(limit)

        rows = self._conn.execute(
            f"""
            SELECT cs.metrics_json, cs.kind, cs.run_id,
                   COALESCE(r.suite, 'unknown') AS suite
            FROM coverage_summaries cs
            LEFT JOIN runs r ON cs.run_id = r.run_id
            {where_sql}
            ORDER BY cs.run_id DESC, cs.id ASC
            LIMIT ?
            """,
            params,
        ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            metrics_raw, cov_kind, run_id, run_suite = row
            try:
                metrics_list: list[dict[str, Any]] = json.loads(metrics_raw) if metrics_raw else []
            except (json.JSONDecodeError, TypeError):
                continue
            for metric in metrics_list:
                results.append(
                    {
                        "name": metric.get("name", "unknown"),
                        "scope": metric.get("scope", "unknown"),
                        "covered": metric.get("covered", 100.0),
                        "hits": metric.get("hits"),
                        "total": metric.get("total"),
                        "bins_missed": metric.get("bins_missed", []),
                        "kind": cov_kind,
                        "run_id": run_id,
                        "suite": run_suite,
                    }
                )
        return results

    def insert_coverage_summary(
        self,
        run_id: str,
        kind: str,
        metrics: list[dict[str, Any]] | dict[str, Any],
        test_id: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """Insert a coverage summary row."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        payload = metrics if isinstance(metrics, list) else metrics.get("metrics", metrics)
        next_id = self._next_row_id(_ID_SEQUENCES["coverage_summaries"])
        self._conn.execute(
            """
            INSERT INTO coverage_summaries (id, run_id, test_id, kind, metrics_json, evidence_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            [
                next_id,
                run_id,
                test_id,
                kind,
                json.dumps(payload),
                json.dumps(evidence) if evidence else None,
            ],
        )
        self._conn.execute(
            "DELETE FROM evidence WHERE owner_kind = ? AND owner_id = ?",
            ["coverage", str(next_id)],
        )
        if evidence:
            self.insert_evidence(
                owner_kind="coverage",
                owner_id=str(next_id),
                kind=str(evidence.get("kind", "coverage")),
                path=str(evidence.get("path", "")),
                start_line=(evidence.get("span") or {}).get("start_line"),
                end_line=(evidence.get("span") or {}).get("end_line"),
                start_time_ns=(evidence.get("span") or {}).get("start_time_ns"),
                end_time_ns=(evidence.get("span") or {}).get("end_time_ns"),
                extract=evidence.get("extract"),
            )

    def diff_runs(self, base_run_id: str, compare_run_id: str) -> dict[str, Any]:
        """Compute structured diff between two runs."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        base = self.get_run(base_run_id)
        compare = self.get_run(compare_run_id)
        if not base:
            raise ValueError(f"Run not found: {base_run_id}")
        if not compare:
            raise ValueError(f"Run not found: {compare_run_id}")

        base_tests, _ = self.query_tests(run_id=base_run_id, page_size=10_000)
        compare_tests, _ = self.query_tests(run_id=compare_run_id, page_size=10_000)

        base_by_name = {t["name"]: t for t in base_tests}
        compare_by_name = {t["name"]: t for t in compare_tests}

        test_changes: list[dict[str, Any]] = []
        for name in sorted(set(base_by_name) | set(compare_by_name)):
            b = base_by_name.get(name)
            c = compare_by_name.get(name)
            if b and c and b["status"] != c["status"]:
                test_changes.append(
                    {
                        "kind": "test_status_change",
                        "name": name,
                        "base_status": b["status"],
                        "compare_status": c["status"],
                    }
                )
            elif b and not c:
                test_changes.append(
                    {"kind": "test_removed", "name": name, "base_status": b["status"]}
                )
            elif c and not b:
                test_changes.append(
                    {"kind": "test_added", "name": name, "compare_status": c["status"]}
                )

        base_sigs = self._failure_signatures_for_run(base_run_id)
        compare_sigs = self._failure_signatures_for_run(compare_run_id)

        new_failures = [
            {"signature_id": sig, "count": compare_sigs[sig]}
            for sig in sorted(compare_sigs.keys() - base_sigs.keys())
        ]
        resolved_failures = [
            {"signature_id": sig, "count": base_sigs[sig]}
            for sig in sorted(base_sigs.keys() - compare_sigs.keys())
        ]

        return {
            "base_run_id": base_run_id,
            "compare_run_id": compare_run_id,
            "test_changes": test_changes,
            "new_failures": new_failures,
            "resolved_failures": resolved_failures,
        }

    def _failure_signatures_for_run(self, run_id: str) -> dict[str, int]:
        """Count failures grouped by signature_id for a run."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        rows = self._conn.execute(
            """
            SELECT COALESCE(signature_id, failure_id) AS sig, COUNT(*) AS cnt
            FROM failures
            WHERE run_id = ?
            GROUP BY sig
        """,
            [run_id],
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def regression_summary(
        self,
        suite: str,
        window_days: int,
        as_of: str | None = None,
    ) -> dict[str, Any]:
        """Compute regression summary for a suite over a time window."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        from datetime import datetime, timedelta, timezone

        if as_of:
            end_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        else:
            end_dt = datetime.now(timezone.utc)
        cutoff_dt = end_dt - timedelta(days=window_days)
        as_of_iso = end_dt.isoformat().replace("+00:00", "Z")
        cutoff_ms = int(cutoff_dt.timestamp() * 1000)
        as_of_ms = int(end_dt.timestamp() * 1000)

        runs = self._conn.execute(
            """
            SELECT run_id, suite, status, created_at
            FROM runs
            WHERE suite = ?
              AND created_at_ms IS NOT NULL
              AND created_at_ms >= ?
              AND created_at_ms <= ?
            ORDER BY created_at_ms DESC, run_id ASC
        """,
            [suite, cutoff_ms, as_of_ms],
        ).fetchall()

        run_ids = [r[0] for r in runs]
        if not run_ids:
            return {
                "suite": suite,
                "window_days": window_days,
                "as_of": as_of_iso,
                "pass_rate": 0.0,
                "runs": [],
                "top_signatures": [],
            }

        placeholders = ",".join("?" * len(run_ids))
        stats = self._conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) AS passed
            FROM tests
            WHERE run_id IN ({placeholders})
        """,
            run_ids,
        ).fetchone()

        if stats is None:
            total_tests = 0
            passed = 0
        else:
            total_tests = stats[0] or 0
            passed = stats[1] or 0
        pass_rate = (100.0 * passed / total_tests) if total_tests else 0.0

        sig_rows = self._conn.execute(
            f"""
            SELECT COALESCE(signature_id, summary) AS sig, category, summary, COUNT(*) AS cnt
            FROM failures
            WHERE run_id IN ({placeholders})
            GROUP BY sig, category, summary
            ORDER BY cnt DESC, sig ASC
            LIMIT 20
        """,
            run_ids,
        ).fetchall()

        top_signatures = [
            {
                "signature_id": row[0],
                "category": row[1],
                "summary": row[2],
                "count": row[3],
            }
            for row in sig_rows
        ]

        return {
            "suite": suite,
            "window_days": window_days,
            "as_of": as_of_iso,
            "pass_rate": round(pass_rate, 2),
            "runs": [
                {"run_id": r[0], "suite": r[1], "status": r[2], "created_at": r[3]} for r in runs
            ],
            "top_signatures": top_signatures,
        }

    # ========================================================================
    # SVA run status operations
    # ========================================================================

    def insert_sva_run_status(
        self,
        assertion_id: str,
        test_id: str,
        run_id: str,
        status: str,
        pass_count: int = 0,
        fail_count: int = 0,
        vacuous_count: int = 0,
    ) -> None:
        """Insert or replace SVA run status for an assertion in a test."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        row_id = self._next_row_id("sva_run_status_id_seq")
        self._conn.execute(
            """
            INSERT INTO sva_run_status
                (id, assertion_id, test_id, run_id, status, pass_count, fail_count, vacuous_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                status=excluded.status,
                pass_count=excluded.pass_count,
                fail_count=excluded.fail_count,
                vacuous_count=excluded.vacuous_count
            """,
            [row_id, assertion_id, test_id, run_id, status, pass_count, fail_count, vacuous_count],
        )

    def query_sva_run_status(
        self,
        run_id: str | None = None,
        test_id: str | None = None,
        status_filter: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Query SVA run status records.

        Args:
            run_id: Filter to a specific run.
            test_id: Filter to a specific test.
            status_filter: Filter to a specific status (passing|failing|vacuous|disabled|unknown).
            limit: Maximum rows to return.

        Returns:
            List of status dicts matching the filters.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        clauses: list[str] = []
        params: list[Any] = []

        if run_id is not None:
            clauses.append("s.run_id = ?")
            params.append(run_id)
        if test_id is not None:
            clauses.append("s.test_id = ?")
            params.append(test_id)
        if status_filter is not None:
            clauses.append("s.status = ?")
            params.append(status_filter)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)

        rows = self._conn.execute(
            f"""
            SELECT s.id, s.assertion_id, s.test_id, s.run_id,
                   s.status, s.pass_count, s.fail_count, s.vacuous_count,
                   a.name AS assertion_name, a.scope
            FROM sva_run_status s
            LEFT JOIN assertions a ON s.assertion_id = a.assertion_id
            {where}
            ORDER BY s.status ASC, s.assertion_id ASC
            LIMIT ?
            """,
            params,
        ).fetchall()

        cols = [
            "id", "assertion_id", "test_id", "run_id",
            "status", "pass_count", "fail_count", "vacuous_count",
            "assertion_name", "scope",
        ]
        return [dict(zip(cols, row, strict=False)) for row in rows]

    def query_vacuous_assertions(
        self,
        run_id: str | None = None,
        test_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return assertions that fired vacuously in the specified run/test.

        A vacuous assertion has ``status = 'vacuous'`` or ``vacuous_count > 0``.

        Args:
            run_id: Filter to a specific run.
            test_id: Filter to a specific test.
            limit: Maximum rows to return.

        Returns:
            List of dicts compatible with the VacuousAssertion schema.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        clauses: list[str] = ["(s.status = 'vacuous' OR s.vacuous_count > 0)"]
        params: list[Any] = []

        if run_id is not None:
            clauses.append("s.run_id = ?")
            params.append(run_id)
        if test_id is not None:
            clauses.append("s.test_id = ?")
            params.append(test_id)

        where = "WHERE " + " AND ".join(clauses)
        params.append(limit)

        rows = self._conn.execute(
            f"""
            SELECT s.assertion_id, a.name AS assertion_name,
                   COALESCE(a.scope, 'unknown') AS scope,
                   s.test_id, s.vacuous_count
            FROM sva_run_status s
            LEFT JOIN assertions a ON s.assertion_id = a.assertion_id
            {where}
            ORDER BY s.vacuous_count DESC, s.assertion_id ASC
            LIMIT ?
            """,
            params,
        ).fetchall()

        cols = ["assertion_id", "assertion_name", "scope", "test_id", "vacuous_count"]
        return [dict(zip(cols, row, strict=False)) for row in rows]

    def count_sva_status_by_category(
        self,
        run_id: str,
    ) -> dict[str, int]:
        """Return counts of assertions per status category for a run."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        rows = self._conn.execute(
            """
            SELECT status, COUNT(*) AS cnt
            FROM sva_run_status
            WHERE run_id = ?
            GROUP BY status
            ORDER BY status
            """,
            [run_id],
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    # ------------------------------------------------------------------
    # DV-intelligence methods (beyond-spec tools)
    # ------------------------------------------------------------------

    def coverage_trend(
        self,
        suite: str | None = None,
        kind: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Return per-run coverage averages ordered by run date (oldest first).

        One row per (run_id, kind) pair so callers can plot trajectory.

        Args:
            suite: Filter by suite name.
            kind: Filter to one coverage kind.
            limit: Maximum runs to return.

        Returns:
            List of dicts with keys: run_id, suite, created_at, kind,
            covered_pct, metric_count, delta_pct (vs previous run).
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        clauses: list[str] = []
        params: list[Any] = []
        if suite:
            clauses.append("r.suite = ?")
            params.append(suite)
        if kind:
            clauses.append("cs.kind = ?")
            params.append(kind)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)

        rows = self._conn.execute(
            f"""
            SELECT
                r.run_id,
                COALESCE(r.suite, 'unknown') AS suite,
                r.created_at,
                cs.kind,
                cs.metrics_json,
                COUNT(*) OVER (PARTITION BY r.run_id, cs.kind) AS row_count
            FROM coverage_summaries cs
            JOIN runs r ON cs.run_id = r.run_id
            {where}
            ORDER BY r.created_at ASC
            LIMIT ?
            """,
            params,
        ).fetchall()

        # Aggregate per (run_id, kind)
        from collections import defaultdict
        buckets: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {"total": 0.0, "count": 0}
        )
        meta: dict[tuple[str, str], dict[str, Any]] = {}
        for run_id, run_suite, created_at, cov_kind, metrics_raw, _ in rows:
            key = (run_id, cov_kind)
            if key not in meta:
                meta[key] = {
                    "run_id": run_id,
                    "suite": run_suite,
                    "created_at": created_at,
                    "kind": cov_kind,
                }
            try:
                metrics_list = json.loads(metrics_raw) if metrics_raw else []
            except (json.JSONDecodeError, TypeError):
                continue
            for m in metrics_list:
                cov = m.get("covered")
                if cov is not None:
                    buckets[key]["total"] += float(cov)
                    buckets[key]["count"] += 1

        ordered = sorted(meta.keys(), key=lambda k: meta[k]["created_at"])
        result: list[dict[str, Any]] = []
        prev_pct: dict[str, float | None] = {}  # keyed by kind
        for key in ordered:
            run_id, cov_kind = key
            b = buckets[key]
            covered_pct = (b["total"] / b["count"]) if b["count"] else 0.0
            covered_pct = round(covered_pct, 2)
            prev = prev_pct.get(cov_kind)
            delta = round(covered_pct - prev, 2) if prev is not None else None
            prev_pct[cov_kind] = covered_pct
            entry = {**meta[key], "covered_pct": covered_pct, "metric_count": b["count"], "delta_pct": delta}
            result.append(entry)
        return result

    def cross_sim_divergence(
        self,
        suite_prefix: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Find tests whose pass/fail status diverges across simulators.

        Matches tests by name (ignoring suite prefix), groups by sim_vendor,
        returns rows where at least one sim passes and another fails.

        Args:
            suite_prefix: Optional filter on suite name prefix.
            limit: Max divergent tests returned.

        Returns:
            List of dicts: test_name, sim_a, status_a, sim_b, status_b,
            run_id_a, run_id_b.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        params: list[Any] = []
        suite_filter = ""
        if suite_prefix:
            suite_filter = "AND (r.suite LIKE ?)"
            params.append(f"{suite_prefix}%")

        params.append(limit)

        rows = self._conn.execute(
            f"""
            SELECT
                t1.name,
                t1.sim_vendor AS sim_a,
                t1.status    AS status_a,
                t1.run_id    AS run_id_a,
                t2.sim_vendor AS sim_b,
                t2.status    AS status_b,
                t2.run_id    AS run_id_b
            FROM tests t1
            JOIN tests t2
                ON  t1.name = t2.name
                AND t1.sim_vendor IS NOT NULL
                AND t2.sim_vendor IS NOT NULL
                AND t1.sim_vendor < t2.sim_vendor
                AND t1.status != t2.status
            JOIN runs r ON t1.run_id = r.run_id
            WHERE 1=1 {suite_filter}
            ORDER BY t1.name ASC
            LIMIT ?
            """,
            params,
        ).fetchall()

        cols = ["test_name", "sim_a", "status_a", "run_id_a", "sim_b", "status_b", "run_id_b"]
        return [dict(zip(cols, row, strict=False)) for row in rows]

    def cluster_failures(
        self,
        run_id: str | None = None,
        max_clusters: int = 20,
    ) -> list[dict[str, Any]]:
        """Cluster test failures by normalised error signature.

        Groups failures with similar error messages so engineers can identify
        the root cause behind many simultaneous failures.

        Args:
            run_id: Limit to a single run; None means all runs.
            max_clusters: Maximum number of distinct clusters to return.

        Returns:
            List of dicts: signature, count, representative_test_id,
            representative_message, test_ids.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        params: list[Any] = []
        where = ""
        if run_id:
            where = "WHERE f.run_id = ?"
            params.append(run_id)

        rows = self._conn.execute(
            f"""
            SELECT f.test_id, f.message, f.summary, f.failure_id
            FROM failures f
            {where}
            ORDER BY f.failure_id ASC
            """,
            params,
        ).fetchall()

        import re

        def _normalise(msg: str) -> str:
            """Strip addresses/IDs/timestamps to expose structural signature."""
            if not msg:
                return "unknown"
            msg = re.sub(r"0x[0-9a-fA-F]+", "ADDR", msg)
            msg = re.sub(r"\b[0-9a-fA-F]{6,}\b", "HEX", msg)
            msg = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\S+", "TIMESTAMP", msg)
            msg = re.sub(r"\b\d+\b", "N", msg)
            msg = re.sub(r"\s+", " ", msg)
            return msg[:80].strip().lower()

        from collections import defaultdict
        clusters: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "test_ids": [], "representative_test_id": None, "representative_message": None}
        )
        for test_id, message, summary, _ in rows:
            raw = message or summary or ""
            sig = _normalise(raw[:200])
            c = clusters[sig]
            c["count"] += 1
            if c["representative_test_id"] is None:
                c["representative_test_id"] = test_id
                c["representative_message"] = raw[:200]
            c["test_ids"].append(test_id)

        sorted_clusters = sorted(clusters.items(), key=lambda kv: kv[1]["count"], reverse=True)
        return [
            {"signature": sig, **data, "test_ids": data["test_ids"][:50]}
            for sig, data in sorted_clusters[:max_clusters]
        ]

    def regression_health_data(
        self,
        run_id: str | None = None,
        suite: str | None = None,
    ) -> dict[str, Any]:
        """Collect raw data for the regression health score computation.

        Returns all metrics needed by `get_regression_health()` in core.py.
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        # -- pass rate -------------------------------------------------------
        run_filter_clause = ""
        run_params: list[Any] = []
        suite_filter_clause = ""
        suite_params: list[Any] = []

        if run_id:
            run_filter_clause = "WHERE t.run_id = ?"
            run_params.append(run_id)
        elif suite:
            run_filter_clause = "WHERE r.suite = ?"
            run_params.append(suite)

        if suite:
            suite_filter_clause = "WHERE r.suite = ?"
            suite_params.append(suite)

        test_counts = self._conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN t.status = 'pass' THEN 1 ELSE 0 END) AS passed,
                SUM(CASE WHEN t.status = 'fail' THEN 1 ELSE 0 END) AS failed
            FROM tests t
            LEFT JOIN runs r ON t.run_id = r.run_id
            {run_filter_clause}
            """,
            run_params,
        ).fetchone()
        total_tests, passed_tests, failed_tests = (test_counts or (0, 0, 0))

        # -- coverage --------------------------------------------------------
        cov_rows = self._conn.execute(
            f"""
            SELECT cs.metrics_json, cs.kind
            FROM coverage_summaries cs
            JOIN runs r ON cs.run_id = r.run_id
            {suite_filter_clause}
            """,
            suite_params,
        ).fetchall()
        cov_totals: dict[str, list[float]] = {}
        for metrics_raw, cov_kind in cov_rows:
            try:
                metrics_list = json.loads(metrics_raw) if metrics_raw else []
            except (json.JSONDecodeError, TypeError):
                continue
            for m in metrics_list:
                cov = m.get("covered")
                if cov is not None:
                    cov_totals.setdefault(cov_kind, []).append(float(cov))
        coverage_by_kind = {
            k: round(sum(v) / len(v), 2) for k, v in cov_totals.items() if v
        }
        overall_coverage = (
            round(sum(coverage_by_kind.values()) / len(coverage_by_kind), 2)
            if coverage_by_kind
            else None
        )

        # -- assertion health ------------------------------------------------
        row = self._conn.execute(
            "SELECT COUNT(*) FROM sva_run_status WHERE vacuous_count > 0 OR status = 'vacuous'"
        ).fetchone()
        vacuous_count = (row[0] if row else 0) or 0

        row = self._conn.execute(
            "SELECT COUNT(*) FROM sva_run_status WHERE fail_count > 0 OR status = 'fail'"
        ).fetchone()
        failing_assertions = (row[0] if row else 0) or 0

        row = self._conn.execute(
            "SELECT COUNT(DISTINCT assertion_id) FROM assertions"
        ).fetchone()
        total_assertions = (row[0] if row else 0) or 0

        # -- flakiness (tests with both pass and fail across runs) -----------
        row = self._conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT name
                FROM tests
                GROUP BY name
                HAVING COUNT(DISTINCT status) > 1
            )
            """
        ).fetchone()
        flaky_count = (row[0] if row else 0) or 0

        # -- cross-sim divergence -------------------------------------------
        divergent_count = len(self.cross_sim_divergence(limit=500))

        return {
            "total_tests": int(total_tests or 0),
            "passed_tests": int(passed_tests or 0),
            "failed_tests": int(failed_tests or 0),
            "overall_coverage": overall_coverage,
            "coverage_by_kind": coverage_by_kind,
            "total_assertions": int(total_assertions),
            "vacuous_assertions": int(vacuous_count),
            "failing_assertions": int(failing_assertions),
            "flaky_tests": int(flaky_count),
            "divergent_tests": int(divergent_count),
        }

