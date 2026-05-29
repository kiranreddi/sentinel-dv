"""Compatibility imports for multi-project demo indexing and MCP verification."""

from sentinel_dv.demo_fixtures import (  # noqa: F401
    DEMO_ROOT,
    SIMULATOR_DEMO_DIRS,
    ProjectFixtures,
    assert_tool_ok,
    build_multi_config,
    discover_fixtures,
    index_demo_tree,
    invoke_core_tool,
    mcp_payload,
    run_mcp_verification,
    simulator_demo_dir,
    tool_call_matrix,
    verify_core_tools,
)

EXPECTED_SUITES = frozenset(
    {
        "verilator_counter",
        "vcs_counter",
        "questa_counter",
        "cadence_counter",
        "axi_burst",
        "apb_register",
        "alu_core",
        "fifo_sync",
        "counter_block",
    }
)
