"""Indexer discovery rules for cocotb JUnit XML filenames."""

from __future__ import annotations

from pathlib import Path

from sentinel_dv.config import SentinelDVConfig
from sentinel_dv.indexing.indexer import ArtifactIndexer
from sentinel_dv.indexing.store import IndexStore


def test_is_cocotb_junit_xml_accepts_results_variants():
    assert ArtifactIndexer._is_cocotb_junit_xml(Path("results.xml"))
    assert ArtifactIndexer._is_cocotb_junit_xml(Path("results_regression_fail.xml"))
    assert ArtifactIndexer._is_cocotb_junit_xml(Path("nightly_junit_report.xml"))
    assert not ArtifactIndexer._is_cocotb_junit_xml(Path("coverage.xml"))
    assert not ArtifactIndexer._is_cocotb_junit_xml(Path("counter_tb.uvm.log"))


def test_scan_artifacts_dedupes_common_junit_result_variants(tmp_path: Path):
    result_dir = tmp_path / "jenkins_wk" / "artifacts_jks02" / "job_a" / "42" / "git" / "python"
    result_dir.mkdir(parents=True)
    for name in ("results.xml", "combined_results.xml", "filtered_results.xml"):
        (result_dir / name).write_text("<testsuites />", encoding="utf-8")

    artifacts = ArtifactIndexer([str(tmp_path)], tmp_path / "idx.duckdb").scan_artifacts()

    assert [path.name for path in artifacts] == ["filtered_results.xml"]


def test_junit_indexing_infers_jenkins_metadata_and_artifact_evidence(tmp_path: Path):
    result_dir = (
        tmp_path / "jenkins_wk" / "artifacts_jks02" / "navarro_demo" / "42" / "git" / "python"
    )
    result_dir.mkdir(parents=True)
    local_log = result_dir / "demo_simulate.log"
    local_log.write_text("sim log", encoding="utf-8")
    (result_dir / "filtered_results.xml").write_text(
        """
        <testsuites>
          <testsuite name="demo" tests="1" failures="1">
            <testcase classname="demo.Test" name="test_timeout" time="1.5">
              <properties>
                <property name="test_artifacts" value="/jenkins_wk/workspaces/job/demo_simulate.log" />
              </properties>
              <failure message="Timeout waiting for interrupt">stack trace</failure>
            </testcase>
          </testsuite>
        </testsuites>
        """,
        encoding="utf-8",
    )
    db = tmp_path / "idx.duckdb"
    cfg = SentinelDVConfig(
        artifact_roots=[str(tmp_path)],
        index={"type": "duckdb", "path": str(db)},
        adapters={"uvm": False, "cocotb": True, "assertions": False, "coverage": False},
    )

    stats = ArtifactIndexer([str(tmp_path)], db, config=cfg).index_all()

    assert stats["runs"] == 1
    assert stats["tests"] == 1
    assert stats["failures"] == 1
    with IndexStore(db) as store:
        runs, total = store.query_runs(page=1, page_size=10)
        assert total == 1
        assert runs[0]["suite"] == "navarro_demo"
        assert runs[0]["ci_system"] == "jenkins"
        assert runs[0]["ci_build_id"] == "42"
        failures, _ = store.query_failures(include_evidence=True, page=1, page_size=10)
        evidence_paths = {item["path"] for item in failures[0]["evidence"]}
        assert (
            "jenkins_wk/artifacts_jks02/navarro_demo/42/git/python/filtered_results.xml"
            in evidence_paths
        )
        assert (
            "jenkins_wk/artifacts_jks02/navarro_demo/42/git/python/demo_simulate.log"
            in evidence_paths
        )
