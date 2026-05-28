"""Assertion and coverage parser fixtures."""

from pathlib import Path

from sentinel_dv.adapters.assertion_reports import AssertionReportParser
from sentinel_dv.adapters.coverage_reports import CoverageReportParser
from sentinel_dv.ids import generate_assertion_id


def test_assertion_json_parse(tmp_path: Path) -> None:
    path = tmp_path / "dut.assert.json"
    path.write_text(
        """
        {
          "test_name": "tb.test",
          "assertions": [{
            "name": "axi_awvalid_stable_chk",
            "language": "sva",
            "scope": "axi_master",
            "file": "rtl/axi.sv",
            "line": 10,
            "tags": ["axi4"]
          }],
          "failures": []
        }
        """,
        encoding="utf-8",
    )
    parsed = AssertionReportParser().parse(path)
    assert parsed["assertions"][0]["intent_protocol"] == "axi4"
    aid, _ = generate_assertion_id("axi_awvalid_stable_chk", "axi_master", "rtl/axi.sv", 10)
    assert aid.startswith("a_")


def test_coverage_json_bounds(tmp_path: Path) -> None:
    import json

    path = tmp_path / "coverage.json"
    metrics = [{"name": f"m{i}", "scope": "top", "covered": float(i)} for i in range(300)]
    path.write_text(
        json.dumps({"kind": "functional", "metrics": metrics}),
        encoding="utf-8",
    )
    parsed = CoverageReportParser(max_metrics=10).parse(path)
    assert len(parsed["metrics"]) == 10
    assert parsed["kind"] == "functional"


def test_assertion_text_line(tmp_path: Path) -> None:
    path = tmp_path / "assertions.rpt"
    path.write_text("apb_pslverr_chk @ rtl/apb.sv:42\n", encoding="utf-8")
    parsed = AssertionReportParser().parse(path)
    assert parsed["assertions"][0]["intent_protocol"] == "apb"
