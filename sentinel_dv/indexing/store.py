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

    _TESTS_SORT_COLUMNS = frozenset({"created_at", "name", "status", "test_id", "duration_ms"})

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

        if sort_by not in self._TESTS_SORT_COLUMNS:
            raise ValueError(f"Invalid sort_by: {sort_by}")

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

    _RUNS_SORT_COLUMNS = frozenset({"created_at", "suite", "status", "run_id"})

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

        if sort_by not in self._RUNS_SORT_COLUMNS:
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
        order = "DESC" if sort_desc else "ASC"

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
            ORDER BY r.{sort_by} {order}, r.run_id ASC
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
        return json.loads(result[0])

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

    def query_assertions(
        self,
        scope: str | None = None,
        name_pattern: str | None = None,
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

        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row, strict=False)) for row in results], total

    def get_assertion(self, assertion_id: str) -> dict[str, Any] | None:
        """Get assertion definition by ID."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        result = self._conn.execute(
            "SELECT * FROM assertions WHERE assertion_id = ?", [assertion_id]
        ).fetchone()
        if not result:
            return None
        columns = [desc[0] for desc in self._conn.description]
        return dict(zip(columns, result, strict=False))

    def query_assertion_failures(
        self,
        run_id: str | None = None,
        test_id: str | None = None,
        assertion_id: str | None = None,
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

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        count_result = self._conn.execute(
            f"SELECT COUNT(*) FROM assertion_failures WHERE {where_sql}", params
        ).fetchone()
        total = count_result[0] if count_result else 0

        offset = (page - 1) * page_size
        results = self._conn.execute(
            f"""
            SELECT * FROM assertion_failures
            WHERE {where_sql}
            ORDER BY time_ns DESC, id ASC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        ).fetchall()

        columns = [desc[0] for desc in self._conn.description]
        return [dict(zip(columns, row, strict=False)) for row in results], total

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
        metrics: dict[str, Any],
        test_id: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """Insert a coverage summary row."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        self._conn.execute(
            """
            INSERT INTO coverage_summaries (run_id, test_id, kind, metrics_json, evidence_json)
            VALUES (?, ?, ?, ?, ?)
        """,
            [
                run_id,
                test_id,
                kind,
                json.dumps(metrics),
                json.dumps(evidence) if evidence else None,
            ],
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

    def regression_summary(self, suite: str, window_days: int) -> dict[str, Any]:
        """Compute regression summary for a suite over a time window."""
        if not self._conn:
            raise RuntimeError("Not connected to database")

        from datetime import UTC, datetime, timedelta

        cutoff = (
            (datetime.now(UTC) - timedelta(days=window_days)).isoformat().replace("+00:00", "Z")
        )

        runs = self._conn.execute(
            """
            SELECT run_id, suite, status, created_at
            FROM runs
            WHERE suite = ? AND created_at >= ?
            ORDER BY created_at DESC
        """,
            [suite, cutoff],
        ).fetchall()

        run_ids = [r[0] for r in runs]
        if not run_ids:
            return {
                "suite": suite,
                "window_days": window_days,
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

        total_tests = stats[0] or 0
        passed = stats[1] or 0
        pass_rate = (100.0 * passed / total_tests) if total_tests else 0.0

        sig_rows = self._conn.execute(
            f"""
            SELECT COALESCE(signature_id, summary) AS sig, category, summary, COUNT(*) AS cnt
            FROM failures
            WHERE run_id IN ({placeholders})
            GROUP BY sig, category, summary
            ORDER BY cnt DESC
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
            "pass_rate": round(pass_rate, 2),
            "runs": [
                {"run_id": r[0], "suite": r[1], "status": r[2], "created_at": r[3]} for r in runs
            ],
            "top_signatures": top_signatures,
        }
