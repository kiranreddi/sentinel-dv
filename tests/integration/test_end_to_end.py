"""
Integration tests for Sentinel DV.

These tests verify end-to-end workflows including:
- Parsing artifacts
- Indexing to DuckDB
- Querying via store
- ID generation consistency
"""

import tempfile
from pathlib import Path

import pytest

from sentinel_dv.adapters.cocotb import CocotbParser
from sentinel_dv.adapters.uvm_log import UVMLogParser
from sentinel_dv.ids import generate_failure_id, generate_run_id, generate_test_id
from sentinel_dv.indexing.store import IndexStore


class TestEndToEndWorkflow:
    """Test complete indexing and query workflow."""

    def test_uvm_log_parsing_and_indexing(self, tmp_path):
        """Test parsing UVM log and indexing to DuckDB."""
        # Create sample UVM log
        log_content = """
UVM_INFO @ 0 ns: (uvm_test_top) [TEST] Running test my_test...
UVM_ERROR @ 100 ns: (uvm_test_top.env.scoreboard) [SCB] DATA MISMATCH
UVM_INFO @ 200 ns: (uvm_test_top) [TEST] Test completed
"""
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        # Parse log
        parser = UVMLogParser()
        result = parser.parse_log(log_file)

        assert result["test"] is not None
        assert result["test"]["framework"] == "uvm"
        assert len(result["failures"]) > 0

        # Create index store
        db_path = tmp_path / "test.duckdb"
        store = IndexStore(db_path)

        with store:
            # Generate IDs
            run_id, run_id_full = generate_run_id(
                suite="demo", artifact_manifest=[(str(log_file), "abc123")]
            )

            test_id, test_id_full = generate_test_id(
                run_id_full=run_id_full, framework="uvm", test_name=result["test"]["name"]
            )

            # Insert run
            store.insert_run(
                run_id=run_id,
                run_id_full=run_id_full,
                suite="demo",
                created_at="2026-01-25T10:00:00Z",
                status="fail",
            )

            # Insert test
            store.insert_test(
                test_id=test_id,
                test_id_full=test_id_full,
                run_id=run_id,
                framework="uvm",
                name=result["test"]["name"],
                status="fail",
                created_at="2026-01-25T10:00:00Z",
            )

            # Insert failure
            failure = result["failures"][0]
            failure_id, failure_id_full = generate_failure_id(
                test_id_full=test_id_full,
                severity=failure["severity"],
                category=failure["category"],
                summary=failure["summary"],
            )

            store.insert_failure(
                failure_id=failure_id,
                failure_id_full=failure_id_full,
                test_id=test_id,
                run_id=run_id,
                severity=failure["severity"],
                category=failure["category"],
                summary=failure["summary"],
                message=failure["message"],
                tags=failure["tags"],
            )

            # Query back
            tests, total = store.query_tests(run_id=run_id)
            assert total == 1
            assert tests[0]["test_id"] == test_id

            failures, total_failures = store.query_failures(test_id=test_id)
            assert total_failures == 1
            assert failures[0]["category"] == "scoreboard"

    def test_cocotb_parsing_and_indexing(self, tmp_path):
        """Test parsing cocotb results and indexing."""
        # Create sample cocotb XML
        xml_content = """<?xml version="1.0"?>
<testsuites>
  <testsuite name="test_suite" tests="1" failures="1">
    <testcase name="test_fail" classname="tests" time="0.1">
      <failure message="Test failed">AssertionError</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
        xml_file = tmp_path / "results.xml"
        xml_file.write_text(xml_content)

        # Parse XML
        parser = CocotbParser()
        results = parser.parse_junit_xml(xml_file)

        # CocotbParser now returns a list of test dicts
        assert len(results) == 1
        assert results[0]["status"] == "fail"
        assert results[0]["failure_message"] is not None

    def test_id_generation_determinism(self):
        """Test that ID generation is deterministic."""
        # Generate same run ID twice
        run_id_1, run_id_full_1 = generate_run_id(
            suite="test_suite", ci_system="github", ci_build_id="12345"
        )

        run_id_2, run_id_full_2 = generate_run_id(
            suite="test_suite", ci_system="github", ci_build_id="12345"
        )

        assert run_id_1 == run_id_2
        assert run_id_full_1 == run_id_full_2

        # Test ID should be deterministic
        test_id_1, test_id_full_1 = generate_test_id(
            run_id_full=run_id_full_1, framework="uvm", test_name="my_test", seed=42
        )

        test_id_2, test_id_full_2 = generate_test_id(
            run_id_full=run_id_full_2, framework="uvm", test_name="my_test", seed=42
        )

        assert test_id_1 == test_id_2
        assert test_id_full_1 == test_id_full_2

    def test_taxonomy_classification(self):
        """Test failure taxonomy classification."""
        from sentinel_dv.taxonomy_engine import classify_failure

        # Test scoreboard classification
        result = classify_failure(
            message="DATA MISMATCH: Expected 0xDEAD, Got 0xBEEF",
            severity="UVM_ERROR",
            framework="uvm",
        )

        assert result.category == "scoreboard"
        assert "scoreboard" in result.tags

        # Test assertion classification
        result = classify_failure(
            message="ASSERTION FAILED: data_valid_check", severity="UVM_ERROR"
        )

        assert result.category == "assertion"
        assert "assertion" in result.tags

        # Test timeout classification
        result = classify_failure(
            message="TIMEOUT: objection timeout in run phase", severity="UVM_FATAL"
        )

        assert result.category == "timeout"
        assert "timeout" in result.tags
