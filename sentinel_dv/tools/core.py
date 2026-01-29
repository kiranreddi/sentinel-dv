"""MCP tools for Sentinel DV.

This module implements all 14 MCP tools documented in docs/tools/overview.md.
"""

from typing import Any

from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.schemas.common import PaginationInfo

# ============================================================================
# Tool implementations
# ============================================================================


def list_runs(
    store: IndexStore,
    suite: str | None = None,
    ci_system: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """
    List available test runs.

    Args:
        store: Index store instance
        suite: Filter by suite name
        ci_system: Filter by CI system
        page: Page number (1-based)
        page_size: Items per page

    Returns:
        Dictionary with runs and pagination info
    """
    results, total = store.query_runs(
        suite=suite,
        ci_system=ci_system,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return {
        "runs": results,
        "pagination": PaginationInfo(
            page=page, page_size=page_size, total_items=total, total_pages=total_pages
        ).model_dump(),
    }


def get_run_details(store: IndexStore, run_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific run.

    Args:
        store: Index store instance
        run_id: Run identifier

    Returns:
        Run details dictionary
    """
    run = store.get_run(run_id)
    if not run:
        raise ValueError(f"Run not found: {run_id}")
    return run


def list_tests(
    store: IndexStore,
    run_id: str | None = None,
    framework: str | None = None,
    status: str | None = None,
    name_pattern: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """
    List tests with filtering and pagination.

    Args:
        store: Index store instance
        run_id: Filter by run
        framework: Filter by framework (uvm, cocotb)
        status: Filter by status (pass, fail, error)
        name_pattern: Filter by name pattern
        page: Page number
        page_size: Items per page

    Returns:
        Dictionary with tests and pagination
    """
    results, total = store.query_tests(
        run_id=run_id,
        framework=framework,
        status=status,
        name_pattern=name_pattern,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return {
        "tests": results,
        "pagination": PaginationInfo(
            page=page, page_size=page_size, total_items=total, total_pages=total_pages
        ).model_dump(),
    }


def list_failures(
    store: IndexStore,
    test_id: str | None = None,
    run_id: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    tags_any: list[str] | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict[str, Any]:
    """
    List failures with filtering.

    Args:
        store: Index store instance
        test_id: Filter by test
        run_id: Filter by run
        category: Filter by category
        severity: Filter by severity
        tags_any: Filter by any of these tags
        page: Page number
        page_size: Items per page

    Returns:
        Dictionary with failures and pagination
    """
    results, total = store.query_failures(
        test_id=test_id,
        run_id=run_id,
        category=category,
        severity=severity,
        tags_any=tags_any,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return {
        "failures": results,
        "pagination": PaginationInfo(
            page=page, page_size=page_size, total_items=total, total_pages=total_pages
        ).model_dump(),
    }


def get_regression_summary(
    store: IndexStore,
    suite: str,
    window_days: int = 7,
) -> dict[str, Any]:
    """
    Get regression summary for a suite.

    Args:
        store: Index store instance
        suite: Suite name
        window_days: Time window in days

    Returns:
        Regression summary with pass rates and top failures

    Note:
        Currently retrieves up to 10,000 tests and failures per run.
        For very large runs (>10,000 tests), results may be incomplete.
    """
    from datetime import datetime, timedelta

    # Calculate time window
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=window_days)
    start_time_str = start_time.isoformat() + "Z"

    # Get all runs in the time window for this suite
    # Note: Currently limited to 1000 runs. For higher volume, consider server-side filtering.
    runs, total_runs = store.query_runs(
        suite=suite,
        page=1,
        page_size=1000,
    )

    # Filter by time (if created_at is available)
    runs_in_window = [r for r in runs if r.get("created_at", "") >= start_time_str]

    if not runs_in_window:
        return {
            "suite": suite,
            "window_days": window_days,
            "pass_rate": 0.0,
            "total_runs": 0,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "top_signatures": [],
        }

    # Collect run IDs
    run_ids = [r["run_id"] for r in runs_in_window]

    # Get all tests for these runs
    all_tests = []
    for run_id in run_ids:
        tests, _ = store.query_tests(run_id=run_id, page=1, page_size=10000)
        all_tests.extend(tests)

    # Calculate pass rate
    total_tests = len(all_tests)
    passed_tests = sum(1 for t in all_tests if t.get("status") == "pass")
    failed_tests = total_tests - passed_tests
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

    # Get all failures
    all_failures = []
    for run_id in run_ids:
        failures, _ = store.query_failures(run_id=run_id, page=1, page_size=10000)
        all_failures.extend(failures)

    # Group by signature and count
    signature_counts: dict[str, int] = {}
    signature_details: dict[str, dict[str, Any]] = {}

    for failure in all_failures:
        sig_id = failure.get("signature_id") or "unknown"
        signature_counts[sig_id] = signature_counts.get(sig_id, 0) + 1

        if sig_id not in signature_details:
            signature_details[sig_id] = {
                "signature_id": sig_id,
                "category": failure.get("category", "unknown"),
                "example_summary": failure.get("summary", ""),
                "count": 0,
            }

        signature_details[sig_id]["count"] = signature_counts[sig_id]

    # Sort by count and get top 10
    top_signatures = sorted(signature_details.values(), key=lambda x: x["count"], reverse=True)[
        :10
    ]

    return {
        "suite": suite,
        "window_days": window_days,
        "pass_rate": round(pass_rate, 2),
        "total_runs": len(runs_in_window),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "top_signatures": top_signatures,
    }


def compare_runs(
    store: IndexStore,
    base_run_id: str,
    compare_run_id: str,
) -> dict[str, Any]:
    """
    Compare two runs (diff).

    Args:
        store: Index store instance
        base_run_id: Base run ID
        compare_run_id: Compare run ID

    Returns:
        Diff summary with test changes and failure differences

    Note:
        Currently retrieves up to 10,000 tests and failures per run.
        For very large runs (>10,000 tests/failures), results may be incomplete.
    """
    # Get tests from both runs
    # Note: Limited to 10,000 tests per run
    base_tests, _ = store.query_tests(run_id=base_run_id, page=1, page_size=10000)
    compare_tests, _ = store.query_tests(run_id=compare_run_id, page=1, page_size=10000)

    # Create lookup maps by test name
    base_by_name = {t["name"]: t for t in base_tests}
    compare_by_name = {t["name"]: t for t in compare_tests}

    # Find test status changes
    test_changes = []
    for test_name, compare_test in compare_by_name.items():
        base_test = base_by_name.get(test_name)

        if base_test:
            base_status = base_test.get("status", "unknown")
            compare_status = compare_test.get("status", "unknown")

            if base_status != compare_status:
                test_changes.append(
                    {
                        "test_name": test_name,
                        "base_status": base_status,
                        "compare_status": compare_status,
                        "change_type": "status_change",
                    }
                )
        else:
            # New test in compare run
            test_changes.append(
                {
                    "test_name": test_name,
                    "base_status": None,
                    "compare_status": compare_test.get("status", "unknown"),
                    "change_type": "new_test",
                }
            )

    # Find tests that were removed
    for test_name in base_by_name:
        if test_name not in compare_by_name:
            test_changes.append(
                {
                    "test_name": test_name,
                    "base_status": base_by_name[test_name].get("status", "unknown"),
                    "compare_status": None,
                    "change_type": "removed_test",
                }
            )

    # Get failures from both runs
    base_failures, _ = store.query_failures(run_id=base_run_id, page=1, page_size=10000)
    compare_failures, _ = store.query_failures(run_id=compare_run_id, page=1, page_size=10000)

    # Group failures by signature
    base_sigs = {f.get("signature_id") for f in base_failures if f.get("signature_id")}
    compare_sigs = {f.get("signature_id") for f in compare_failures if f.get("signature_id")}

    # Find new and resolved failures
    new_failure_sigs = compare_sigs - base_sigs
    resolved_failure_sigs = base_sigs - compare_sigs

    # Get details for new failures
    new_failures = [
        {
            "signature_id": f.get("signature_id"),
            "category": f.get("category"),
            "summary": f.get("summary"),
            "test_id": f.get("test_id"),
        }
        for f in compare_failures
        if f.get("signature_id") in new_failure_sigs
    ]

    # Get details for resolved failures
    resolved_failures = [
        {
            "signature_id": f.get("signature_id"),
            "category": f.get("category"),
            "summary": f.get("summary"),
            "test_id": f.get("test_id"),
        }
        for f in base_failures
        if f.get("signature_id") in resolved_failure_sigs
    ]

    return {
        "base_run_id": base_run_id,
        "compare_run_id": compare_run_id,
        "test_changes": test_changes,
        "new_failures": new_failures,
        "resolved_failures": resolved_failures,
        "summary": {
            "total_test_changes": len(test_changes),
            "new_failure_count": len(new_failures),
            "resolved_failure_count": len(resolved_failures),
        },
    }
