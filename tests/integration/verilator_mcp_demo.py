"""Compatibility imports for the Verilator counter MCP walkthrough tests."""

from sentinel_dv.demo_fixtures import (  # noqa: F401
    VERILATOR_DEMO_DIR as DEMO_DIR,
)
from sentinel_dv.demo_fixtures import (
    assert_tool_ok,
    build_demo_config,
    expected_tool_names,
    index_demo,
    mcp_payload,
    prepare_work_dir,
    verilator_available,
)
from sentinel_dv.demo_fixtures import (
    ensure_verilator_vcd as ensure_vcd,
)
