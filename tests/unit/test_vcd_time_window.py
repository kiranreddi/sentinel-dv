"""VCD time-window parsing and MCP wave tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel_dv.adapters.vcd_summary import VcdSummaryParser
from sentinel_dv.config import AdaptersConfig, SentinelDVConfig, set_config
from sentinel_dv.ids import generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore
from sentinel_dv.tools import core
from sentinel_dv.tools.errors import ToolError


@pytest.fixture
def sample_vcd(tmp_path: Path) -> Path:
    """VCD with 1ns timescale; clk toggles at 10ns, 20ns, 30ns."""
    path = tmp_path / "test_window.vcd"
    path.write_text(
        """
$timescale 1 ns $end
$var wire 1 ! clk $end
$enddefinitions $end
#0
0!
#10
1!
#20
0!
#30
1!
#40
0!
""".strip(),
        encoding="utf-8",
    )
    return path


def test_vcd_timescale_and_full_trace(sample_vcd: Path) -> None:
    parsed = VcdSummaryParser().parse(sample_vcd)
    assert parsed["end_time_ns"] == 40
    clk = parsed["signals"][0]
    assert clk["name"] == "clk"
    assert clk["toggles"] == 4


@pytest.fixture
def us_scale_vcd(tmp_path: Path) -> Path:
    """VCD with 1us timescale; edges at 20us and 30us."""
    path = tmp_path / "us_trace.vcd"
    path.write_text(
        """
$timescale 1 us $end
$var wire 1 ! clk $end
$enddefinitions $end
#0
0!
#20
1!
#30
0!
""".strip(),
        encoding="utf-8",
    )
    return path


def test_vcd_window_20_30us_in_ns(us_scale_vcd: Path) -> None:
    # 20 µs = 20_000 ns, 30 µs = 30_000 ns (with $timescale 1 us)
    parsed = VcdSummaryParser().parse(
        us_scale_vcd, start_time_ns=20_000, end_time_ns=30_000
    )
    clk = parsed["signals"][0]
    assert clk["value_at_start"] == "0"
    assert clk["value_at_end"] == "0"
    assert clk["toggles"] == 2
    assert parsed["metadata"]["window"]["start_time_ns"] == 20_000


def test_vcd_window_sub_nanosecond(sample_vcd: Path) -> None:
    parsed = VcdSummaryParser().parse(sample_vcd, start_time_ns=15, end_time_ns=25)
    clk = parsed["signals"][0]
    assert clk["value_at_start"] == "1"  # held high after #10ns until #20ns
    assert clk["value_at_end"] == "0"  # last edge in window is #20ns
    assert clk["toggles"] == 1


def test_wave_tools_reparse_vcd_window(tmp_path: Path, sample_vcd: Path) -> None:
    set_config(
        SentinelDVConfig(
            artifact_roots=[str(tmp_path)],
            index={"type": "duckdb", "path": str(tmp_path / "t.duckdb")},
        )
    )
    rel = "trace.vcd"
    (tmp_path / rel).write_text(sample_vcd.read_text(encoding="utf-8"))

    db = tmp_path / "t.duckdb"
    with IndexStore(db) as store:
        run_id, run_full = generate_run_id(suite="s", ci_system="local", ci_build_id="1")
        store.insert_run(
            run_id=run_id,
            run_id_full=run_full,
            suite="s",
            created_at="2026-05-26T00:00:00Z",
            status="pass",
        )
        test_id, test_full = generate_test_id(
            run_id_full=run_full, framework="verilator", test_name="test_window"
        )
        store.insert_test(
            test_id=test_id,
            test_id_full=test_full,
            run_id=run_id,
            framework="verilator",
            name="test_window",
            status="pass",
            created_at="2026-05-26T00:00:00Z",
        )
        full = VcdSummaryParser().parse(tmp_path / rel)
        store.insert_waveform_summary(test_id, full, rel)

        windowed = core.wave_signals(store, test_id, start_time_ns=20, end_time_ns=30)
        assert windowed["signals"][0]["toggles"] == 2
        assert windowed["start_time_ns"] == 20

        with pytest.raises(ToolError) as exc:
            core.wave_signals(store, test_id, start_time_ns=30, end_time_ns=20)
        assert exc.value.code == "INVALID_ARGUMENT"
