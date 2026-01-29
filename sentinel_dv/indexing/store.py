"""
Index storage backend for Sentinel DV.

This module provides the DuckDB-based storage layer for indexed verification artifacts.
Implements the schema documented in docs/index-store.md.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb


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
                signals_json TEXT NOT NULL
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

        index_built_at = datetime.utcnow().isoformat() + "Z"

        self._conn.execute(
            """
            INSERT INTO runs (
                run_id, run_id_full, suite, created_at, status,
                ci_system, ci_build_id, ci_job_url,
                artifact_manifest_hash, index_built_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                run_id,
                run_id_full,
                suite,
                created_at,
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

        self._conn.execute(
            """
            INSERT INTO tests (
                test_id, test_id_full, run_id, framework, name, seed,
                status, duration_ms, sim_vendor, sim_version, dut_top,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def count_failures(self) -> int:
        """Get total number of indexed failures."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute("SELECT COUNT(*) FROM failures").fetchone()
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

        # Build WHERE clause
        where_clauses = []
        params = []

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
        order = "DESC" if sort_desc else "ASC"

        results = self._conn.execute(
            f"""
            SELECT * FROM tests
            WHERE {where_sql}
            ORDER BY {sort_by} {order}, test_id ASC
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
        return [dict(zip(columns, row, strict=False)) for row in results], total

    def query_runs(
        self,
        suite: str | None = None,
        ci_system: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Query runs with filters and pagination.

        Args:
            suite: Filter by suite name
            ci_system: Filter by CI system
            status: Filter by status
            page: Page number (1-based)
            page_size: Items per page
            sort_by: Column to sort by
            sort_desc: Sort in descending order

        Returns:
            Tuple of (results, total_count)
        """
        if not self._conn:
            raise RuntimeError("Not connected to database")

        # Validate sort_by to prevent SQL injection
        allowed_sort_columns = ["created_at", "run_id", "suite", "status", "ci_system"]
        if sort_by not in allowed_sort_columns:
            raise ValueError(
                f"Invalid sort_by column: {sort_by}. Allowed: {allowed_sort_columns}"
            )

        # Build WHERE clause
        where_clauses = []
        params = []

        if suite:
            where_clauses.append("suite = ?")
            params.append(suite)

        if ci_system:
            where_clauses.append("ci_system = ?")
            params.append(ci_system)

        if status:
            where_clauses.append("status = ?")
            params.append(status)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_result = self._conn.execute(
            f"SELECT COUNT(*) FROM runs WHERE {where_sql}", params
        ).fetchone()
        total = count_result[0] if count_result else 0

        # Get paginated results
        offset = (page - 1) * page_size
        order = "DESC" if sort_desc else "ASC"

        results = self._conn.execute(
            f"""
            SELECT * FROM runs
            WHERE {where_sql}
            ORDER BY {sort_by} {order}, run_id ASC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        ).fetchall()

        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row, strict=False)) for row in results], total
