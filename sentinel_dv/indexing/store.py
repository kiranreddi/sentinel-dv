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
