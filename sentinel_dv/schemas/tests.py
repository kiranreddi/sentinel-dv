"""Test-related schemas for Sentinel DV."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel_dv.schemas.common import EvidenceRef, RunRef

# Framework types
Framework = Literal["uvm", "cocotb", "sv_unit", "unknown"]

# Test status
TestStatus = Literal["pass", "fail", "error", "skipped", "unknown"]

# UVM component roles
UvmRole = Literal["env", "agent", "driver", "monitor", "scoreboard", "sequencer", "other"]

# Protocol types
Protocol = Literal[
    "AXI4",
    "AXI3",
    "AHB",
    "APB",
    "PCIe",
    "USB",
    "Ethernet",
    "I2C",
    "SPI",
    "UART",
    "CAN",
    "unknown",
]

# Interface direction
Direction = Literal["master", "slave", "monitor", "unknown"]


class SimulatorInfo(BaseModel):
    """Simulator information."""

    vendor: str = Field(..., description="Simulator vendor (VCS, Xcelium, Questa, etc.)")
    version: str | None = Field(None, description="Simulator version")


class DutInfo(BaseModel):
    """Design Under Test information."""

    top: str = Field(..., description="Top-level module name")
    config: dict[str, str] | None = Field(None, description="DUT configuration parameters")


class TestCase(BaseModel):
    """Unified representation of a test result."""

    id: str = Field(..., description="Stable test identifier", min_length=1)
    framework: Framework = Field(..., description="Verification framework used")
    name: str = Field(..., description="Test name", min_length=1)
    seed: int | None = Field(None, description="Random seed used")
    simulator: SimulatorInfo | None = Field(None, description="Simulator information")
    dut: DutInfo | None = Field(None, description="DUT information")
    status: TestStatus = Field(..., description="Test result status")
    duration_ms: int | None = Field(None, ge=0, description="Test duration in milliseconds")
    run: RunRef = Field(..., description="Run this test belongs to")
    evidence: list[EvidenceRef] = Field(
        default_factory=list, description="Evidence for test result"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "T20260125_142305_axi_burst_test",
                "framework": "uvm",
                "name": "axi_burst_test",
                "seed": 12345,
                "simulator": {"vendor": "VCS", "version": "2023.12"},
                "dut": {"top": "axi_interconnect", "config": {"NUM_MASTERS": "4"}},
                "status": "fail",
                "duration_ms": 15420,
                "run": {
                    "run_id": "R20260125_142305",
                    "suite": "nightly",
                    "created_at": "2026-01-25T14:23:05Z",
                },
                "evidence": [
                    {
                        "kind": "log",
                        "path": "regression/axi_burst_test.log",
                        "span": {"start_line": 1, "end_line": 5000},
                    }
                ],
            }
        }
    )


class UvmComponent(BaseModel):
    """UVM component in the testbench hierarchy."""

    path: str = Field(
        ..., description="Hierarchical path (e.g., uvm_test_top.env.agent.driver)", min_length=1
    )
    type: str = Field(..., description="Component class type", min_length=1)
    role: UvmRole = Field(..., description="Component role in verification")


class UvmTopology(BaseModel):
    """UVM testbench topology."""

    test_class: str = Field(..., description="UVM test class name")
    envs: list[UvmComponent] = Field(default_factory=list, description="Environment components")
    agents: list[UvmComponent] = Field(default_factory=list, description="Agent components")
    scoreboards: list[UvmComponent] = Field(
        default_factory=list, description="Scoreboard components"
    )
    sequencers: list[UvmComponent] = Field(default_factory=list, description="Sequencer components")
    drivers: list[UvmComponent] = Field(default_factory=list, description="Driver components")
    monitors: list[UvmComponent] = Field(default_factory=list, description="Monitor components")


class SignalInfo(BaseModel):
    """Signal information for interface binding."""

    clk: str | None = Field(None, description="Clock signal name")
    rst: str | None = Field(None, description="Reset signal name")


class EndpointInfo(BaseModel):
    """Endpoint information for interface binding."""

    driver: str | None = Field(None, description="Driver component path or object name")
    monitor: str | None = Field(None, description="Monitor component path or object name")


class InterfaceBinding(BaseModel):
    """Interface binding in the testbench.

    This unifies UVM and cocotb interface representations.
    """

    name: str = Field(..., description="Interface instance name (e.g., axi_m0, apb_s0)")
    protocol: Protocol = Field(..., description="Interface protocol type")
    direction: Direction = Field(..., description="Interface direction")
    signals: SignalInfo | None = Field(None, description="Key signal names")
    endpoints: EndpointInfo | None = Field(None, description="Connected components")


class TestTopology(BaseModel):
    """Complete test topology combining framework-specific and unified views."""

    test_id: str = Field(..., description="Test identifier this topology belongs to")
    uvm: UvmTopology | None = Field(None, description="UVM-specific topology (if applicable)")
    interfaces: list[InterfaceBinding] = Field(
        default_factory=list, description="Unified interface bindings"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_id": "T20260125_142305_axi_burst_test",
                "uvm": {
                    "test_class": "axi_burst_test",
                    "envs": [
                        {
                            "path": "uvm_test_top.env",
                            "type": "axi_env",
                            "role": "env",
                        }
                    ],
                    "agents": [
                        {
                            "path": "uvm_test_top.env.axi_master_agent",
                            "type": "axi_master_agent",
                            "role": "agent",
                        }
                    ],
                    "drivers": [
                        {
                            "path": "uvm_test_top.env.axi_master_agent.driver",
                            "type": "axi_master_driver",
                            "role": "driver",
                        }
                    ],
                    "monitors": [
                        {
                            "path": "uvm_test_top.env.axi_master_agent.monitor",
                            "type": "axi_master_monitor",
                            "role": "monitor",
                        }
                    ],
                    "sequencers": [],
                    "scoreboards": [],
                },
                "interfaces": [
                    {
                        "name": "axi_m0",
                        "protocol": "AXI4",
                        "direction": "master",
                        "signals": {"clk": "aclk", "rst": "aresetn"},
                        "endpoints": {
                            "driver": "uvm_test_top.env.axi_master_agent.driver",
                            "monitor": "uvm_test_top.env.axi_master_agent.monitor",
                        },
                    }
                ],
            }
        }
    )
