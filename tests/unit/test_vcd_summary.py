"""Unit tests for VCD summary parser."""

from __future__ import annotations

from pathlib import Path

from sentinel_dv.adapters.vcd_summary import VcdSummaryParser


def test_parse_minimal_vcd(tmp_path: Path) -> None:
    vcd = tmp_path / "test_counter_sim.vcd"
    vcd.write_text(
        """
$var wire 1 ! clk $end
$var wire 1 " rst $end
$var wire 4 # count [3:0] $end
$enddefinitions $end
#0
1!
1"
b0000 #
#1
0!
#2
1!
0"
b0001 #
""".strip(),
        encoding="utf-8",
    )

    parsed = VcdSummaryParser().parse(vcd)
    assert parsed["test_name"] == "test_counter_sim"
    assert parsed["format"] == "vcd-summary"
    names = {s["name"] for s in parsed["signals"]}
    assert names == {"clk", "rst", "count"}
    clk = next(s for s in parsed["signals"] if s["name"] == "clk")
    assert clk["toggles"] >= 1
