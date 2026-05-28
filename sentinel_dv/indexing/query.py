"""Query layer for the DuckDB index (delegates from IndexStore)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel_dv.indexing.store import IndexStore


def query_assertions(
    store: IndexStore,
    *,
    scope: str | None = None,
    name_pattern: str | None = None,
    protocol: str | None = None,
    tag: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """List assertion definitions with filters."""
    return store.query_assertions(
        scope=scope,
        name_pattern=name_pattern,
        protocol=protocol,
        tag=tag,
        page=page,
        page_size=page_size,
    )


def query_runs(
    store: IndexStore,
    *,
    suite: str | None = None,
    status: str | None = None,
    ci_system: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """List runs with filters."""
    return store.query_runs(
        suite=suite,
        status=status,
        ci_system=ci_system,
        page=page,
        page_size=page_size,
    )


def query_tests(
    store: IndexStore,
    *,
    run_id: str | None = None,
    framework: str | None = None,
    status: str | None = None,
    name_pattern: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """List tests with filters."""
    return store.query_tests(
        run_id=run_id,
        framework=framework,
        status=status,
        name_pattern=name_pattern,
        page=page,
        page_size=page_size,
    )


def query_failures(
    store: IndexStore,
    *,
    test_id: str | None = None,
    run_id: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    tags_any: list[str] | None = None,
    include_evidence: bool = False,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """List failure events with filters."""
    return store.query_failures(
        test_id=test_id,
        run_id=run_id,
        category=category,
        severity=severity,
        tags_any=tags_any,
        include_evidence=include_evidence,
        page=page,
        page_size=page_size,
    )


def query_assertion_failures(
    store: IndexStore,
    *,
    run_id: str | None = None,
    test_id: str | None = None,
    assertion_id: str | None = None,
    start_time_ns: int | None = None,
    end_time_ns: int | None = None,
    include_evidence: bool = False,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """List runtime assertion failures with filters."""
    return store.query_assertion_failures(
        run_id=run_id,
        test_id=test_id,
        assertion_id=assertion_id,
        start_time_ns=start_time_ns,
        end_time_ns=end_time_ns,
        include_evidence=include_evidence,
        page=page,
        page_size=page_size,
    )


def query_coverage_summaries(
    store: IndexStore,
    *,
    run_id: str | None = None,
    kind: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """List coverage summaries with filters."""
    return store.query_coverage_summaries(
        run_id=run_id,
        kind=kind,
        page=page,
        page_size=page_size,
    )
