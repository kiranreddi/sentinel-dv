"""Indexer discovery rules for cocotb JUnit XML filenames."""

from __future__ import annotations

from pathlib import Path

from sentinel_dv.indexing.indexer import ArtifactIndexer


def test_is_cocotb_junit_xml_accepts_results_variants():
    assert ArtifactIndexer._is_cocotb_junit_xml(Path("results.xml"))
    assert ArtifactIndexer._is_cocotb_junit_xml(Path("results_regression_fail.xml"))
    assert ArtifactIndexer._is_cocotb_junit_xml(Path("nightly_junit_report.xml"))
    assert not ArtifactIndexer._is_cocotb_junit_xml(Path("coverage.xml"))
    assert not ArtifactIndexer._is_cocotb_junit_xml(Path("counter_tb.uvm.log"))
