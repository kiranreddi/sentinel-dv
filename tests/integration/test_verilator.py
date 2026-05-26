"""Integration test using local Verilator when available."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from sentinel_dv.adapters.coverage import CoverageParser


@pytest.fixture
def verilator_available() -> bool:
    return shutil.which("verilator") is not None


@pytest.fixture
def counter_fixture(tmp_path: Path) -> Path:
    """Minimal SystemVerilog design for Verilator smoke test."""
    design_dir = tmp_path / "counter"
    design_dir.mkdir()
    (design_dir / "counter.sv").write_text(textwrap.dedent("""
            module counter (
                input  logic clk,
                input  logic rst,
                output logic [3:0] count
            );
              always_ff @(posedge clk) begin
                if (rst)
                  count <= 4'd0;
                else
                  count <= count + 4'd1;
              end
            endmodule

            """).strip())
    return design_dir


@pytest.mark.skipif(not shutil.which("verilator"), reason="Verilator not installed")
def test_verilator_build_and_coverage_report(counter_fixture: Path, tmp_path: Path) -> None:
    """Compile with Verilator, run sim, and parse a text coverage report."""
    obj_dir = tmp_path / "obj_dir"
    result = subprocess.run(
        [
            "verilator",
            "--binary",
            "--coverage",
            "-Mdir",
            str(obj_dir),
            str(counter_fixture / "counter.sv"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    sim_bin = obj_dir / "Vcounter"
    assert sim_bin.exists()
    subprocess.run([str(sim_bin)], check=True, cwd=obj_dir, capture_output=True, text=True)

    report_path = tmp_path / "coverage_report.txt"
    report_path.write_text("line coverage: 87.5%\nbranch coverage: 50.0%\n")

    summary = CoverageParser().parse_report(report_path)
    assert summary.metrics
    assert any(m.covered > 0 for m in summary.metrics)
