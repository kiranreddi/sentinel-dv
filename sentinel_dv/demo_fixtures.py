"""Reusable demo fixture helpers for scripts, tests, and gallery generation."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentinel_dv import server
from sentinel_dv.config import AdaptersConfig, IndexConfig, SentinelDVConfig, set_config
from sentinel_dv.indexing.indexer import ArtifactIndexer, IndexStats
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.registry import TOOL_NAMES
from sentinel_dv.tools import core
from sentinel_dv.tools.errors import ToolError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "demo"
VERILATOR_DEMO_DIR = DEMO_ROOT / "verilator_counter"
SIMULATOR_DEMO_DIRS: dict[str, str] = {
    "verilator": "verilator_counter",
    "vcs": "vcs_counter",
    "questa": "questa_counter",
    "cadence": "cadence_counter",
}
DEMO_AS_OF: str | None = None


@dataclass(frozen=True)
class ProjectFixtures:
    """Indexed entity IDs discovered after indexing demo artifacts."""

    suites: frozenset[str]
    pass_run_id: str
    fail_run_id: str
    wave_test_id: str
    uvm_topology_test_id: str
    assertion_id: str
    regression_suite: str

    @property
    def cocotb_wave_test_id(self) -> str:
        """Backward-compatible alias for older tests/scripts."""
        return self.wave_test_id

    @property
    def axi_suite(self) -> str:
        """Backward-compatible alias for regression examples."""
        return self.regression_suite

    @property
    def verilator_suite(self) -> str:
        """Backward-compatible alias for older Verilator-only tests."""
        return "verilator_counter" if "verilator_counter" in self.suites else self.regression_suite


def simulator_demo_dir(simulator: str) -> Path:
    """Return the checked-in demo directory for a simulator key."""
    try:
        dirname = SIMULATOR_DEMO_DIRS[simulator]
    except KeyError as exc:
        supported = ", ".join(sorted(SIMULATOR_DEMO_DIRS))
        raise ValueError(
            f"Unsupported simulator {simulator!r}; choose one of: {supported}"
        ) from exc
    return DEMO_ROOT / dirname


def verilator_available() -> bool:
    """Return True when the Verilator executable is available."""
    return shutil.which("verilator") is not None


def ensure_verilator_vcd(demo_dir: Path = VERILATOR_DEMO_DIR) -> Path:
    """Build and run the Verilator TB if waves/test_counter_sim.vcd is missing."""
    vcd = demo_dir / "waves" / "test_counter_sim.vcd"
    if vcd.is_file():
        return vcd
    if not verilator_available():
        raise RuntimeError("Verilator not on PATH and demo VCD not present")
    subprocess.run(["make", "run"], check=True, cwd=demo_dir)
    if not vcd.is_file():
        raise RuntimeError(f"Expected VCD at {vcd} after make run")
    return vcd


def build_demo_config(work_dir: Path, db_path: Path) -> SentinelDVConfig:
    """Build a config that enables every artifact adapter for a demo tree."""
    return SentinelDVConfig(
        artifact_roots=[str(work_dir.resolve())],
        index=IndexConfig(type="duckdb", path=str(db_path)),
        adapters=AdaptersConfig(
            uvm=True,
            cocotb=True,
            assertions=True,
            coverage=True,
            waveform_summary=True,
        ),
    )


def build_multi_config(demo_root: Path, db_path: Path) -> SentinelDVConfig:
    """Build a config for the full checked-in demo corpus."""
    return build_demo_config(demo_root, db_path)


def _copy_demo(source: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("obj_dir", "__pycache__", "*.db", "*.sqlite"),
    )
    return destination


def prepare_work_dir(
    tmp_path: Path,
    *,
    simulator: str = "verilator",
    use_repo_demo: bool = False,
) -> Path:
    """Populate a temp artifact tree from a checked-in simulator demo."""
    demo_dir = simulator_demo_dir(simulator)
    if use_repo_demo:
        if simulator == "verilator" and not any(demo_dir.rglob("*.wave.json")):
            ensure_verilator_vcd(demo_dir)
        return demo_dir
    return _copy_demo(demo_dir, tmp_path / "artifacts")


def index_demo(work_dir: Path, db_path: Path) -> IndexStats:
    """Index a single demo artifact tree."""
    cfg = build_demo_config(work_dir, db_path)
    set_config(cfg)
    return ArtifactIndexer([str(work_dir.resolve())], db_path, config=cfg).index_all()


def index_demo_tree(demo_root: Path, db_path: Path) -> IndexStats:
    """Index the full checked-in demo tree without requiring simulator executables."""
    cfg = build_multi_config(demo_root, db_path)
    set_config(cfg)
    return ArtifactIndexer([str(demo_root.resolve())], db_path, config=cfg).index_all()


def _runs_by_id(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {run["run_id"]: run for run in runs}


def _suite_filter(suite: str | None) -> Callable[[dict[str, Any]], bool]:
    if suite is None:
        return lambda _row: True
    return lambda row: row.get("suite") == suite


def discover_fixtures(store: IndexStore, suite: str | None = None) -> ProjectFixtures:
    """Collect stable handles for one complete all-tools verification matrix."""
    all_runs, _ = store.query_runs(page_size=1000)
    if not all_runs:
        raise AssertionError("No runs indexed")
    runs_by_id = _runs_by_id(all_runs)
    in_suite = _suite_filter(suite)
    suite_runs = [run for run in all_runs if in_suite(run)]
    if not suite_runs:
        raise AssertionError(f"No runs indexed for suite {suite!r}")

    tests, _ = store.query_tests(page_size=2000)
    suite_run_ids = {run["run_id"] for run in suite_runs}
    suite_tests = [test for test in tests if test["run_id"] in suite_run_ids]

    wave_test = next(
        (test for test in suite_tests if store.get_waveform_summary(test["test_id"])),
        None,
    )
    if wave_test is None:
        raise AssertionError(f"No waveform-indexed test found for suite {suite!r}")

    topology_test = next(
        (test for test in suite_tests if store.get_topology(test["test_id"]) is not None),
        None,
    )
    if topology_test is None:
        raise AssertionError(f"No topology-indexed test found for suite {suite!r}")

    assertions, _ = store.query_assertions(protocol="axi4", page_size=100)
    if not assertions:
        assertions, _ = store.query_assertions(page_size=100)
    if not assertions:
        raise AssertionError("No assertions indexed")

    pass_run = runs_by_id.get(wave_test["run_id"])
    if pass_run is None or pass_run["status"] != "pass":
        pass_run = next((run for run in suite_runs if run["status"] == "pass"), suite_runs[0])
    fail_run = next(
        (
            run
            for run in suite_runs
            if run["status"] == "fail" and run["run_id"] != pass_run["run_id"]
        ),
        None,
    )
    if fail_run is None:
        fail_run = next((run for run in all_runs if run["status"] == "fail"), None)
    if fail_run is None:
        raise AssertionError("No failing run indexed")

    return ProjectFixtures(
        suites=frozenset(run["suite"] for run in all_runs),
        pass_run_id=pass_run["run_id"],
        fail_run_id=fail_run["run_id"],
        wave_test_id=wave_test["test_id"],
        uvm_topology_test_id=topology_test["test_id"],
        assertion_id=assertions[0]["assertion_id"],
        regression_suite=pass_run["suite"],
    )


def tool_call_matrix(fix: ProjectFixtures) -> list[tuple[str, dict[str, Any]]]:
    """Exactly one MCP invocation per registered tool."""
    return [
        ("runs.list", {"suite": fix.regression_suite, "page": 1, "page_size": 200}),
        ("runs.get", {"run_id": fix.pass_run_id}),
        ("runs.submit", {"suite": fix.regression_suite}),
        ("tests.list", {"run_id": fix.pass_run_id, "page": 1, "page_size": 100}),
        ("tests.get", {"test_id": fix.wave_test_id}),
        ("tests.topology", {"test_id": fix.uvm_topology_test_id}),
        ("tests.replay", {"test_id": fix.wave_test_id}),
        ("assertions.list", {"protocol": "axi4", "page": 1, "page_size": 50}),
        ("assertions.get", {"assertion_id": fix.assertion_id}),
        ("assertions.failures", {"include_evidence": True, "page": 1, "page_size": 50}),
        ("assertions.sva_status", {"run_id": fix.pass_run_id, "page": 1, "page_size": 50}),
        ("assertions.vacuity", {"run_id": fix.pass_run_id, "page": 1, "page_size": 50}),
        ("coverage.list", {"run_id": fix.pass_run_id, "page": 1, "page_size": 50}),
        ("coverage.summary", {"run_id": fix.pass_run_id}),
        ("coverage.gaps", {"suite": fix.regression_suite, "threshold_pct": 100.0}),
        ("failures.list", {"category": "scoreboard", "page": 1, "page_size": 50}),
        (
            "regressions.summary",
            {
                "suite": fix.regression_suite,
                "window_days": 30,
                "as_of": DEMO_AS_OF,
            },
        ),
        ("runs.diff", {"base_run_id": fix.fail_run_id, "compare_run_id": fix.pass_run_id}),
        ("sim.status", {"suite": fix.regression_suite}),
        ("wave.signals", {"test_id": fix.wave_test_id}),
        (
            "wave.summary",
            {"test_id": fix.wave_test_id, "start_time_ns": 1000, "end_time_ns": 25000},
        ),
        # DV Intelligence tools — v2.1.0
        ("coverage.trend", {"suite": fix.regression_suite}),
        ("runs.cross_sim", {}),
        ("tests.cluster", {}),
        ("regression.health", {"suite": fix.regression_suite}),
        ("coverage.advisor", {"suite": fix.regression_suite}),
    ]


def invoke_core_tool(store: IndexStore, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke a tool implementation directly with the same arguments as MCP."""
    dispatch: dict[str, Callable[[], dict[str, Any]]] = {
        "runs.list": lambda: core.list_runs(store, **args),
        "runs.get": lambda: core.get_run_details(store, args["run_id"]),
        "runs.submit": lambda: core.generate_submit_command(store, **args),
        "tests.list": lambda: core.list_tests(store, **args),
        "tests.get": lambda: core.get_test_details(store, args["test_id"]),
        "tests.topology": lambda: core.get_test_topology(store, args["test_id"]),
        "tests.replay": lambda: core.generate_replay_command(store, **args),
        "assertions.list": lambda: core.list_assertions(store, **args),
        "assertions.get": lambda: core.get_assertion_details(store, args["assertion_id"]),
        "assertions.failures": lambda: core.list_assertion_failures(store, **args),
        "assertions.sva_status": lambda: core.get_sva_status(store, **args),
        "assertions.vacuity": lambda: core.get_vacuous_assertions(store, **args),
        "coverage.list": lambda: core.list_coverage(store, **args),
        "coverage.summary": lambda: core.get_coverage_summary(
            store,
            args["run_id"],
            kind=args.get("kind"),
            include_evidence=args.get("include_evidence", False),
        ),
        "coverage.gaps": lambda: core.get_coverage_gaps(store, **args),
        "failures.list": lambda: core.list_failures(store, **args),
        "regressions.summary": lambda: core.get_regression_summary(store, **args),
        "runs.diff": lambda: core.compare_runs(store, args["base_run_id"], args["compare_run_id"]),
        "sim.status": lambda: core.get_sim_status(store, **args),
        "wave.signals": lambda: core.wave_signals(store, **args),
        "wave.summary": lambda: core.wave_summary(store, **args),
        # DV Intelligence tools — v2.1.0
        "coverage.trend": lambda: core.get_coverage_trend(store, **args),
        "runs.cross_sim": lambda: core.get_cross_sim_comparison(store),
        "tests.cluster": lambda: core.cluster_test_failures(store),
        "regression.health": lambda: core.get_regression_health(store, **args),
        "coverage.advisor": lambda: core.get_coverage_advisor(store, **args),
    }
    try:
        return dispatch[tool_name]()
    except ToolError as exc:
        return exc.to_dict()


def mcp_payload(result: Any) -> dict[str, Any]:
    """Extract tool JSON from a FastMCP CallToolResult."""
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    structured_content = getattr(result, "structured_content", None)
    if isinstance(structured_content, dict):
        return structured_content
    raise AssertionError("MCP tool result has no structured payload")


def assert_tool_ok(payload: dict[str, Any], tool_name: str) -> None:
    """Assert a tool payload succeeded and includes a schema version.

    Some v2.0.0 tools are feature-gated (require config flags). When they return
    CONFIG_ERROR or NOT_FOUND that is expected and acceptable in tests that use the
    demo fixtures (which don't have submit templates or live_status files).
    """
    _ALLOWED_DEMO_ERRORS = {"CONFIG_ERROR", "NOT_FOUND"}
    _FEATURE_GATED_TOOLS = {
        "runs.submit",
        "tests.replay",
        "sim.status",
    }

    if payload.get("error"):
        err = payload["error"]
        error_code = err.get("code", "") if isinstance(err, dict) else str(err)
        if tool_name in _FEATURE_GATED_TOOLS and error_code in _ALLOWED_DEMO_ERRORS:
            return  # Expected — these tools need config flags not set in demo fixtures
        raise AssertionError(f"{tool_name} failed: {payload['error']}")
    assert payload.get("schema_version"), f"{tool_name} missing schema_version"


def expected_tool_names() -> tuple[str, ...]:
    """Return the registered tool names."""
    return TOOL_NAMES


def verify_core_tools(store: IndexStore, fix: ProjectFixtures) -> None:
    """Exercise core handlers with cross-project assertions."""
    all_runs = core.list_runs(store, page_size=200)
    assert all_runs["pagination"]["total_items"] >= 1, all_runs["pagination"]

    for suite in fix.suites:
        filtered = core.list_runs(store, suite=suite)
        assert filtered["pagination"]["total_items"] >= 1, suite

    assert core.list_tests(store, framework="uvm", page_size=100)["pagination"]["total_items"] >= 1
    assert (
        core.list_tests(store, framework="cocotb", page_size=100)["pagination"]["total_items"] >= 1
    )
    assert core.list_assertion_failures(store, page_size=50)["pagination"]["total_items"] >= 1

    for tool_name, args in tool_call_matrix(fix):
        result = invoke_core_tool(store, tool_name, args)
        if result.get("error"):
            err = result["error"]
            error_code = err.get("code", "") if isinstance(err, dict) else str(err)
            _FEATURE_GATED = {"runs.submit", "tests.replay", "sim.status"}
            _OK_CODES = {"CONFIG_ERROR", "NOT_FOUND"}
            if tool_name in _FEATURE_GATED and error_code in _OK_CODES:
                continue
            raise AssertionError(f"{tool_name} failed: {result['error']}")

    reg = core.get_regression_summary(
        store,
        suite=fix.regression_suite,
        window_days=30,
        as_of=DEMO_AS_OF,
    )
    assert reg["runs"], reg


async def verify_mcp_tools(config_path: Path, fix: ProjectFixtures) -> None:
    """Invoke every registered MCP tool through FastMCP."""
    from fastmcp import Client

    server.init_server(config_path)
    async with Client(server.mcp) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed} == set(TOOL_NAMES)

        matrix = tool_call_matrix(fix)
        assert len(matrix) == len(TOOL_NAMES)

        for tool_name, arguments in matrix:
            result = await client.call_tool(tool_name, arguments)
            assert_tool_ok(mcp_payload(result), tool_name)


def run_mcp_verification(config_path: Path, fix: ProjectFixtures) -> None:
    """Synchronous wrapper for MCP all-tool verification."""
    asyncio.run(verify_mcp_tools(config_path, fix))
