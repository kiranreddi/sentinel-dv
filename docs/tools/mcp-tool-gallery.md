# MCP tool gallery

!!! note "Auto-generated"
    Regenerate after demo or tool changes:
    ```bash
    python scripts/generate_mcp_tool_gallery.py
    ```

Visual cards below are produced from a real `demo/` index (multi-project).
Each image shows the **request arguments** and a **truncated JSON response**
exactly as MCP clients receive it (`schema_version` + payload or `error`).

[Open interactive HTML gallery](../assets/mcp-tools/gallery.html){ .md-button }

---

## `runs.list`

![MCP tool runs.list](../assets/mcp-tools/runs-list.svg)

??? example "Request"
    ```json
    {
      "suite": "verilator_counter",
      "page": 1,
      "page_size": 200
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "runs": [
        {
          "run_id": "r_d39bb5009606",
          "suite": "verilator_counter",
          "status": "fail",
          "created_at": "2026-05-30T04:01:56.006241Z",
          "ci_system": null,
          "ci_build_id": null,
          "total_tests": 1,
          "passed_tests": 0,
          "failed_tests": 1
        },
        {
          "run_id": "r_85b1d3f70e48",
          "suite": "verilator_counter",
          "status": "pass",
          "created_at": "2026-05-30T04:01:55.989538Z",
          "ci_system": null,
          "ci_build_id": null,
          "total_tests": 1,
          "passed_tests": 1,
          "failed_tests": 0
        },
        {
          "run_id": "r_566fd6e9a21b",
          "suite": "verilator_counter",
          "status": "fail",
          "created_at": "2026-05-30T04:01:55.958292Z",
          "ci_system": null,
          "ci_build_id": null,
          "total_tests": 1,
          "passed_tests": 0,
          "failed_tests": 1
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 200,
        "total_items": 3,
        "total_pages": 1
      }
    }
    ```

## `runs.get`

![MCP tool runs.get](../assets/mcp-tools/runs-get.svg)

??? example "Request"
    ```json
    {
      "run_id": "r_85b1d3f70e48"
    }
    ```

??? success "Response"
    ```json
    {
      "run": {
        "run_id": "r_85b1d3f70e48",
        "run_id_full": "85b1d3f70e48fc8d1d4135b83ba53a9aeaa116a8a7775b50b1bf731beaf0eb33",
        "suite": "verilator_counter",
        "created_at": "2026-05-30T04:01:55.989538Z",
        "status": "pass",
        "ci_system": null,
        "ci_build_id": null,
        "ci_job_url": null,
        "artifact_manifest_hash": null,
        "index_built_at": "2026-05-30T04:01:55.990338Z",
        "created_at_ms": 1780113715989
      },
      "schema_version": "1.0.0"
    }
    ```

## `runs.submit`

![MCP tool runs.submit](../assets/mcp-tools/runs-submit.svg)

??? example "Request"
    ```json
    {
      "suite": "verilator_counter"
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "error": {
        "code": "CONFIG_ERROR",
        "message": "Regression submission is not enabled. Set submit.enabled=true in config.yaml and configure at least one simulator template."
      }
    }
    ```

## `tests.list`

![MCP tool tests.list](../assets/mcp-tools/tests-list.svg)

??? example "Request"
    ```json
    {
      "run_id": "r_85b1d3f70e48",
      "page": 1,
      "page_size": 100
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "tests": [
        {
          "test_id": "t_3bb6bfc925aa",
          "test_id_full": "3bb6bfc925aae6acf97f11e409203ddc88654087de1717626f929993e218be86",
          "run_id": "r_85b1d3f70e48",
          "framework": "cocotb",
          "name": "counter_tb.test_counter_sim",
          "seed": null,
          "status": "pass",
          "duration_ms": 10,
          "sim_vendor": null,
          "sim_version": null,
          "dut_top": null,
          "created_at": "2026-05-30T04:01:55.989538Z",
          "created_at_ms": 1780113715989
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 100,
        "total_items": 1,
        "total_pages": 1
      }
    }
    ```

## `tests.get`

![MCP tool tests.get](../assets/mcp-tools/tests-get.svg)

??? example "Request"
    ```json
    {
      "test_id": "t_3bb6bfc925aa"
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "item": {
        "test_id": "t_3bb6bfc925aa",
        "test_id_full": "3bb6bfc925aae6acf97f11e409203ddc88654087de1717626f929993e218be86",
        "run_id": "r_85b1d3f70e48",
        "framework": "cocotb",
        "name": "counter_tb.test_counter_sim",
        "seed": null,
        "status": "pass",
        "duration_ms": 10,
        "sim_vendor": null,
        "sim_version": null,
        "dut_top": null,
        "created_at": "2026-05-30T04:01:55.989538Z",
        "created_at_ms": 1780113715989
      }
    }
    ```

## `tests.topology`

![MCP tool tests.topology](../assets/mcp-tools/tests-topology.svg)

??? example "Request"
    ```json
    {
      "test_id": "t_7a0a37762958"
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "item": {
        "test_id": "t_7a0a37762958",
        "uvm": {
          "test_class": "unknown",
          "envs": [],
          "agents": [],
          "scoreboards": [],
          "sequencers": [],
          "drivers": [],
          "monitors": []
        },
        "interfaces": []
      }
    }
    ```

## `tests.replay`

![MCP tool tests.replay](../assets/mcp-tools/tests-replay.svg)

??? example "Request"
    ```json
    {
      "test_id": "t_3bb6bfc925aa"
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "error": {
        "code": "CONFIG_ERROR",
        "message": "Regression submission is not enabled. Set submit.enabled=true in config.yaml."
      }
    }
    ```

## `assertions.list`

![MCP tool assertions.list](../assets/mcp-tools/assertions-list.svg)

??? example "Request"
    ```json
    {
      "protocol": "axi4",
      "page": 1,
      "page_size": 50
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "assertions": [
        {
          "assertion_id": "a_c0ae7a3d319c",
          "language": "sva",
          "name": "CHK_ARVALID_STABLE",
          "scope": "axi4_tb_top.dut",
          "file": "axi4_slave.sv",
          "line": 146,
          "signals": [
            "ACLK",
            "ARESETn",
            "ARVALID",
            "ARREADY"
          ],
          "tags": [
            "axi4",
            "handshake",
            "protocol",
            "read-address"
          ],
          "intent": {
            "protocol": "axi4",
            "requirement": "AXI4 spec \u00a7A3.2.1: master must not de-assert ARVALID before the handshake"
          }
        },
        {
          "assertion_id": "a_11ed387e66f6",
          "language": "sva",
          "name": "CHK_AWVALID_STABLE",
          "scope": "axi4_tb_top.dut",
          "file": "axi4_slave.sv",
          "line": 138,
          "signals": [
            "ACLK",
            "ARESETn",
            "AWVALID",
            "AWREADY"
          ],
          "tags": [
            "axi4",
            "handshake",
            "protocol",
            "write-address"
          ],
          "intent": {
            "protocol": "axi4",
            "requirement": "AXI4 spec \u00a7A3.2.1: master must not de-assert AWVALID before the handshake"
          }
        },
        {
          "assertion_id": "a_39857bc021fc",
          "language": "sva",
          "name": "CHK_BRESP_ACCEPTED",
          "scope": "axi4_tb_top.dut",
          "file": "axi4_slave.sv",
          "line": 162,
          "signals": [
            "ACLK",
            "ARESETn",
            "BVALID",
            "BREADY"
          ],
          "tags": [
            "axi4",
            "protocol",
            "timeout",
            "write-response"
          ],
          "intent": {
            "protocol": "axi4",
            "requirement": "AXI4 compliance: BVALID must be accepted within a bounded number of cycles"
          }
        },
        {
          "assertion_id": "a_825670dc11bc",
          "language": "sva",
          "name": "CHK_RESP_AFTER_DATA",
          "scope": "axi4_tb_top.dut",
          "file": "axi4_slave.sv",
          "line": 178,
          "signals": [
            "ACLK",
            "ARESETn",
            "wstate",
            "wbeat_cnt"
          ],
          "tags": [
            "axi4",
            "ordering",
            "protocol",
            "write-response"
          ],
          "intent": {
            "protocol": "axi4",
            "requirement": "Write response must only be issued after at least one write data beat has occurred"
          }
        },
        {
          "assertion_id": "a_6548339b9337",
          "language": "sva",
          "name": "CHK_RLAST_ON_FINAL",
          "scope": "axi4_tb_top.dut",
          "file": "axi4_slave.sv",
          "line": 170,
          "signals": [
            "ACLK",
            "ARESETn",
            "RVALID",
            "RREADY",
            "RLAST",
            "rbeat_cnt",
            "rlen_q"
          ],
          "tags": [
            "axi4",
            "burst",
            "protocol",
            "read"
          ],
          "intent": {
            "protocol": "axi4",
            "requirement": "AXI4 spec \u00a7A3.4.3: RLAST must be asserted on the final data beat of a read burst"
          }
        },
        {
          "assertion_id": "a_fe48551b6a35",
          "language": "sva",
          "name": "CHK_WVALID_STABLE",
          "scope": "axi4_tb_top.dut",
          "file": "axi4_slave.sv",
          "line": 154,
          "signals": [
            "ACLK",
            "ARESETn",
            "WVALID",
            "WREADY"
          ],
          "tags": [
            "axi4",
            "handshake",
            "protocol",
            "write-data"
          ],
          "intent": {
            "protocol": "axi4",
            "requirement": "AXI4 spec \u00a7A3.2.1: WVALID must not drop without handshake during a burst"
          }
        },
        {
          "assertion_id": "a_03847f8e5b0f",
          "language": "sva",
          "name": "axi_awvalid_stable_chk",
          "scope": "counter_tb",
          "file": "counter.sv",
          "line": 12,
          "signals": [
            "clk",
            "count"
          ],
          "tags": [
            "axi4",
            "vcs"
          ],
          "intent": {
            "protocol": "axi4",
            "requirement": "demo assertion tagged for protocol filtering"
          }
        },
        {
          "assertion_id": "a_1288a531c038",
          "language": "sva",
          "name": "axi_awvalid_stable_chk",
          "scope": "counter_tb",
          "file": "counter.sv",
          "line": 20,
          "signals": [
            "clk"
          ],
          "tags": [
            "axi4"
          ],
          "intent": {
            "protocol": "axi4",
            "requirement": "Demo protocol tag (illustrative)"
          }
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 50,
        "total_items": 8,
        "total_pages": 1
      }
    }
    ```

## `assertions.get`

![MCP tool assertions.get](../assets/mcp-tools/assertions-get.svg)

??? example "Request"
    ```json
    {
      "assertion_id": "a_c0ae7a3d319c"
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "item": {
        "assertion_id": "a_c0ae7a3d319c",
        "language": "sva",
        "name": "CHK_ARVALID_STABLE",
        "scope": "axi4_tb_top.dut",
        "file": "axi4_slave.sv",
        "line": 146,
        "signals": [
          "ACLK",
          "ARESETn",
          "ARVALID",
          "ARREADY"
        ],
        "tags": [
          "axi4",
          "handshake",
          "protocol",
          "read-address"
        ],
        "intent": {
          "protocol": "axi4",
          "requirement": "AXI4 spec \u00a7A3.2.1: master must not de-assert ARVALID before the handshake"
        }
      }
    }
    ```

## `assertions.failures`

![MCP tool assertions.failures](../assets/mcp-tools/assertions-failures.svg)

??? example "Request"
    ```json
    {
      "include_evidence": true,
      "page": 1,
      "page_size": 50
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "assertion_failures": [
        {
          "id": 1,
          "assertion_id": "a_39857bc021fc",
          "test_id": "t_b439c1f1e40d",
          "run_id": "r_e0e82e0b1722",
          "time_ns": 1248000,
          "message": "Assertion \"CHK_BRESP_ACCEPTED\" failed at time 1248000ns \u2014 BVALID not accepted within 16 cycles (master held BREADY low)",
          "evidence": [
            {
              "kind": "log",
              "path": "axi4_uvm/vcs/assertions/axi4_error_resp.assert.json",
              "span": {},
              "extract": "Assertion \"CHK_BRESP_ACCEPTED\" failed at time 1248000ns \u2014 BVALID not accepted within 16 cycles (master held BREADY low)",
              "hash": null
            }
          ]
        },
        {
          "id": 2,
          "assertion_id": "a_03847f8e5b0f",
          "test_id": "t_1f8ec97914c0",
          "run_id": "r_e05edc733d2b",
          "time_ns": 2500,
          "message": "Assertion \"axi_awvalid_stable_chk\" failed at 2500 ns",
          "evidence": [
            {
              "kind": "log",
              "path": "cadence_counter/assertions/counter.assert.json",
              "span": {},
              "extract": "Assertion \"axi_awvalid_stable_chk\" failed at 2500 ns",
              "hash": null
            }
          ]
        },
        {
          "id": 3,
          "assertion_id": "a_03847f8e5b0f",
          "test_id": "t_2a2b1eecc369",
          "run_id": "r_4625bceb1d6e",
          "time_ns": 2500,
          "message": "Assertion \"axi_awvalid_stable_chk\" failed at 2500 ns",
          "evidence": [
            {
              "kind": "log",
              "path": "questa_counter/assertions/counter.assert.json",
              "span": {},
              "extract": "Assertion \"axi_awvalid_stable_chk\" failed at 2500 ns",
              "hash": null
            }
          ]
        },
        {
          "id": 4,
          "assertion_id": "a_03847f8e5b0f",
          "test_id": "t_ed09d88e1f1a",
          "run_id": "r_8f85ecd85936",
          "time_ns": 2500,
          "message": "Assertion \"axi_awvalid_stable_chk\" failed at 2500 ns",
          "evidence": [
            {
              "kind": "log",
              "path": "vcs_counter/assertions/counter.assert.json",
              "span": {},
              "extract": "Assertion \"axi_awvalid_stable_chk\" failed at 2500 ns",
              "hash": null
            }
          ]
        },
        {
          "id": 5,
          "assertion_id": "a_c00ae0788840",
          "test_id": "t_3bb6bfc925aa",
          "run_id": "r_85b1d3f70e48",
          "time_ns": 2500,
          "message": "count changed while rst asserted",
          "evidence": [
            {
              "kind": "log",
              "path": "verilator_counter/assertions/counter_fail.assert.json",
              "span": {},
              "extract": "count changed while rst asserted",
              "hash": null
            }
          ]
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 50,
        "total_items": 5,
        "total_pages": 1
      }
    }
    ```

## `assertions.sva_status`

![MCP tool assertions.sva_status](../assets/mcp-tools/assertions-sva_status.svg)

??? example "Request"
    ```json
    {
      "run_id": "r_85b1d3f70e48",
      "page": 1,
      "page_size": 50
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "sva_status": [],
      "pagination": {
        "page": 1,
        "page_size": 50,
        "total_items": 0,
        "total_pages": 0
      },
      "counts": {}
    }
    ```

## `assertions.vacuity`

![MCP tool assertions.vacuity](../assets/mcp-tools/assertions-vacuity.svg)

??? example "Request"
    ```json
    {
      "run_id": "r_85b1d3f70e48",
      "page": 1,
      "page_size": 50
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "vacuous_assertions": [],
      "pagination": {
        "page": 1,
        "page_size": 50,
        "total_items": 0,
        "total_pages": 0
      }
    }
    ```

## `coverage.list`

![MCP tool coverage.list](../assets/mcp-tools/coverage-list.svg)

??? example "Request"
    ```json
    {
      "run_id": "r_85b1d3f70e48",
      "page": 1,
      "page_size": 50
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "coverage": [
        {
          "id": 7,
          "run_id": "r_85b1d3f70e48",
          "test_id": "t_3bb6bfc925aa",
          "kind": "functional",
          "metrics": [
            {
              "name": "line",
              "scope": "counter",
              "covered": 87.5,
              "hits": 14,
              "total": 16,
              "bins_missed": [
                "line_12",
                "line_15"
              ]
            },
            {
              "name": "toggle",
              "scope": "counter",
              "covered": 75.0,
              "hits": 6,
              "total": 8
            }
          ],
          "evidence": [
            {
              "kind": "coverage",
              "path": "verilator_counter/coverage/coverage.json",
              "span": null,
              "extract": null,
              "hash": null
            }
          ]
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 50,
        "total_items": 1,
        "total_pages": 1
      }
    }
    ```

## `coverage.summary`

![MCP tool coverage.summary](../assets/mcp-tools/coverage-summary.svg)

??? example "Request"
    ```json
    {
      "run_id": "r_85b1d3f70e48"
    }
    ```

??? success "Response"
    ```json
    {
      "run_id": "r_85b1d3f70e48",
      "summaries": [
        {
          "id": 7,
          "run_id": "r_85b1d3f70e48",
          "test_id": "t_3bb6bfc925aa",
          "kind": "functional",
          "metrics": [
            {
              "name": "line",
              "scope": "counter",
              "covered": 87.5,
              "hits": 14,
              "total": 16,
              "bins_missed": [
                "line_12",
                "line_15"
              ]
            },
            {
              "name": "toggle",
              "scope": "counter",
              "covered": 75.0,
              "hits": 6,
              "total": 8
            }
          ]
        }
      ],
      "total_summaries": 1,
      "truncated": false,
      "schema_version": "1.0.0"
    }
    ```

## `coverage.gaps`

![MCP tool coverage.gaps](../assets/mcp-tools/coverage-gaps.svg)

??? example "Request"
    ```json
    {
      "suite": "verilator_counter",
      "threshold_pct": 100.0
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "gaps": [
        {
          "metric_name": "toggle",
          "scope": "counter",
          "kind": "functional",
          "covered_pct": 75.0,
          "bins_missed": [],
          "priority": "low",
          "recommendation": "Functional coverage gap in 'toggle' (scope: counter, 75.0% covered). Add constrained-random or directed tests targeting the uncovered bins. Consider increasing the test seed space or adding a dedicated directed test."
        },
        {
          "metric_name": "line",
          "scope": "counter",
          "kind": "functional",
          "covered_pct": 87.5,
          "bins_missed": [
            "line_12",
            "line_15"
          ],
          "priority": "low",
          "recommendation": "Functional coverage gap in 'line' (scope: counter, 87.5% covered). Add constrained-random or directed tests targeting the uncovered bins. Consider increasing the test seed space or adding a dedicated directed test. Specifically, target: 'line_12', 'line_15'."
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 50,
        "total_items": 2,
        "total_pages": 1
      },
      "suite": "verilator_counter",
      "kind": null,
      "threshold_pct": 100.0,
      "total_metrics": 2,
      "gaps_found": 2,
      "note": "Gaps are sorted by priority (high\u2192medium\u2192low) then by coverage percentage. Use tests.replay to reproduce specific failures. Showing page 1 of 1."
    }
    ```

## `failures.list`

![MCP tool failures.list](../assets/mcp-tools/failures-list.svg)

??? example "Request"
    ```json
    {
      "category": "scoreboard",
      "page": 1,
      "page_size": 50
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "failures": [
        {
          "failure_id": "f_9225893b0dd9",
          "failure_id_full": "9225893b0dd9c7a90564117f97246cb99b62a292dab2e53af327e498d90cac2f",
          "test_id": "t_bdf825c67e63",
          "run_id": "r_c93470980bbc",
          "severity": "error",
          "category": "scoreboard",
          "summary": "[SCB] counter_scoreboard.sv:(88) @ 1250 DATA MISMATCH: expected count=3 got 5",
          "message": "[SCB] counter_scoreboard.sv:(88) @ 1250 DATA MISMATCH: expected count=3 got 5",
          "time_ns": 1250,
          "phase": null,
          "component": "unknown",
          "tags_json": "[\"scoreboard\", \"uvm\"]",
          "tags_flat": "scoreboard uvm",
          "signature_id": "s_167aa5eb920e"
        },
        {
          "failure_id": "f_e28595124a71",
          "failure_id_full": "e28595124a71dc81b63b4d4764ec36f0e37ea0ed965aaa824b98bcd4a31ebd54",
          "test_id": "t_3fb5c5afeb62",
          "run_id": "r_b1d6f6071a8b",
          "severity": "error",
          "category": "scoreboard",
          "summary": "[SCB] DATA MISMATCH: expected count=3 got 5",
          "message": "[SCB] DATA MISMATCH: expected count=3 got 5",
          "time_ns": 1250,
          "phase": null,
          "component": "uvm_test_top.env.scoreboard",
          "tags_json": "[\"scoreboard\", \"uvm\"]",
          "tags_flat": "scoreboard uvm",
          "signature_id": "s_31f7c4e8d3fa"
        },
        {
          "failure_id": "f_f5047a164e15",
          "failure_id_full": "f5047a164e15479a42931a6ffc6ccb5af290afa266c5536b1ec5c7c4081d8f8a",
          "test_id": "t_7a0a37762958",
          "run_id": "r_566fd6e9a21b",
          "severity": "error",
          "category": "scoreboard",
          "summary": "uvm_test_top.env.scoreboard [SCB] DATA MISMATCH: expected count=3 got 5",
          "message": "uvm_test_top.env.scoreboard [SCB] DATA MISMATCH: expected count=3 got 5",
          "time_ns": 1250,
          "phase": null,
          "component": "unknown",
          "tags_json": "[\"scoreboard\", \"uvm\"]",
          "tags_flat": "scoreboard uvm",
          "signature_id": "s_71de94577c0f"
        },
        {
          "failure_id": "f_fbcd0a68cb83",
          "failure_id_full": "fbcd0a68cb83115822432efd0db24e0de2d90ff6014cf029eb962638390e5235",
          "test_id": "t_81f11ef7e513",
          "run_id": "r_3bd942f45ef3",
          "severity": "error",
          "category": "scoreboard",
          "summary": "[SCB] (uvm_test_top.env.scoreboard): DATA MISMATCH: expected count=3 got 5",
          "message": "[SCB] (uvm_test_top.env.scoreboard): DATA MISMATCH: expected count=3 got 5",
          "time_ns": 1250,
          "phase": null,
          "component": "unknown",
          "tags_json": "[\"scoreboard\", \"uvm\"]",
          "tags_flat": "scoreboard uvm",
          "signature_id": "s_2940b1f3a20a"
        },
        {
          "failure_id": "f_b1128d5281f7",
          "failure_id_full": "b1128d5281f7d07f2b569f4a431978bb8d993e7a20be422068d4926fc46826cb",
          "test_id": "t_7dd03c3d152f",
          "run_id": "r_2968fa34e74e",
          "severity": "error",
          "category": "scoreboard",
          "summary": "uvm_test_top.axi_env.scoreboard [SCB] AXI DATA MISMATCH: AW beat 3 expected 0xDEAD got 0xBEEF",
          "message": "uvm_test_top.axi_env.scoreboard [SCB] AXI DATA MISMATCH: AW beat 3 expected 0xDEAD got 0xBEEF",
          "time_ns": 850,
          "phase": null,
          "component": "unknown",
          "tags_json": "[\"scoreboard\", \"uvm\", \"axi4\"]",
          "tags_flat": "scoreboard uvm axi4",
          "signature_id": "s_accaf1efb76e"
        },
        {
          "failure_id": "f_52ca140d72a4",
          "failure_id_full": "52ca140d72a4828303a2fe7d74203a3da9d0832f5d2d3a5589972f0837c21ce9",
          "test_id": "t_e65285b55eec",
          "run_id": "r_bcde15e0d7db",
          "severity": "error",
          "category": "scoreboard",
          "summary": "Scoreboard mismatch: counter wrap check failed",
          "message": "\nExpected count to wrap at 15; observed 16 without wrap.\n      ",
          "time_ns": null,
          "phase": null,
          "component": null,
          "tags_json": "[\"scoreboard\", \"cocotb\"]",
          "tags_flat": "scoreboard cocotb",
          "signature_id": "s_171ee2cbf014"
        },
        {
          "failure_id": "f_81bb456a74ac",
          "failure_id_full": "81bb456a74acc3bf5ace5f82eddfd82a388fd613914b28235320bb43e512cb3b",
          "test_id": "t_b439c1f1e40d",
          "run_id": "r_e0e82e0b1722",
          "severity": "error",
          "category": "scoreboard",
          "summary": "Write-readback mismatch at address 0x000001C0",
          "message": "\n        UVM_ERROR @ 1248000: uvm_test_top.env.scbd [SCBD] FAIL: addr=0x000001C0 exp=0xDEADBEEF got=0x00000000\n        UVM_ERROR @ 1248000: uvm_test_top.env.scbd [SCBD] SCOREBOARD MISMATCHES DETECTED\n      ",
          "time_ns": null,
          "phase": null,
          "component": null,
          "tags_json": "[\"scoreboard\", \"cocotb\"]",
          "tags_flat": "scoreboard cocotb",
          "signature_id": "s_11ffe14f53ed"
        },
        {
          "failure_id": "f_b0e75506b88c",
          "failure_id_full": "b0e75506b88c8ed940b5c06dde26159fcf6ccd430f599ac2d7fa44cb57c1f5fa",
          "test_id": "t_731e321ad3c0",
          "run_id": "r_399aa82757dd",
          "severity": "error",
          "category": "scoreboard",
          "summary": "Scoreboard mismatch: counter wrap check failed",
          "message": "\nExpected count to wrap at 15; observed 16 without wrap.\n      ",
          "time_ns": null,
          "phase": null,
          "component": null,
          "tags_json": "[\"scoreboard\", \"cocotb\"]",
          "tags_flat": "scoreboard cocotb",
          "signature_id": "s_171ee2cbf014"
        },
        {
          "failure_id": "f_bc9b5cf421b9",
          "failure_id_full": "bc9b5cf421b9ab5df0919fef6c80eb490c6efa4e3b7e4f77c98b497e261e68fc",
          "test_id": "t_7f5785415392",
          "run_id": "r_12ec8baa2f30",
          "severity": "error",
          "category": "scoreboard",
          "summary": "Scoreboard mismatch: counter wrap check failed",
          "message": "\nExpected count to wrap at 15; observed 16 without wrap.\n      ",
          "time_ns": null,
          "phase": null,
          "component": null,
          "tags_json": "[\"scoreboard\", \"cocotb\"]",
          "tags_flat": "scoreboard cocotb",
          "signature_id": "s_171ee2cbf014"
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 50,
        "total_items": 9,
        "total_pages": 1
      }
    }
    ```

## `regressions.summary`

![MCP tool regressions.summary](../assets/mcp-tools/regressions-summary.svg)

??? example "Request"
    ```json
    {
      "suite": "verilator_counter",
      "window_days": 30,
      "as_of": null
    }
    ```

??? success "Response"
    ```json
    {
      "suite": "verilator_counter",
      "window_days": 30,
      "as_of": "2026-05-30T04:01:56.810072Z",
      "pass_rate": 33.33,
      "runs": [
        {
          "run_id": "r_d39bb5009606",
          "suite": "verilator_counter",
          "status": "fail",
          "created_at": "2026-05-30T04:01:56.006241Z"
        },
        {
          "run_id": "r_85b1d3f70e48",
          "suite": "verilator_counter",
          "status": "pass",
          "created_at": "2026-05-30T04:01:55.989538Z"
        },
        {
          "run_id": "r_566fd6e9a21b",
          "suite": "verilator_counter",
          "status": "fail",
          "created_at": "2026-05-30T04:01:55.958292Z"
        }
      ],
      "top_signatures": [
        {
          "signature_id": "s_71de94577c0f",
          "category": "scoreboard",
          "summary": "uvm_test_top.env.scoreboard [SCB] DATA MISMATCH: expected count=3 got 5",
          "count": 1
        },
        {
          "signature_id": "s_ea51e615c938",
          "category": "unknown",
          "summary": "Counter overflow not handled",
          "count": 1
        }
      ],
      "schema_version": "1.0.0"
    }
    ```

## `runs.diff`

![MCP tool runs.diff](../assets/mcp-tools/runs-diff.svg)

??? example "Request"
    ```json
    {
      "base_run_id": "r_d39bb5009606",
      "compare_run_id": "r_85b1d3f70e48"
    }
    ```

??? success "Response"
    ```json
    {
      "base_run_id": "r_d39bb5009606",
      "compare_run_id": "r_85b1d3f70e48",
      "test_changes": [
        {
          "kind": "test_removed",
          "name": "counter_tb.test_counter_overflow",
          "base_status": "fail"
        },
        {
          "kind": "test_added",
          "name": "counter_tb.test_counter_sim",
          "compare_status": "pass"
        }
      ],
      "new_failures": [],
      "resolved_failures": [
        {
          "signature_id": "s_ea51e615c938",
          "count": 1
        }
      ],
      "schema_version": "1.0.0"
    }
    ```

## `sim.status`

![MCP tool sim.status](../assets/mcp-tools/sim-status.svg)

??? example "Request"
    ```json
    {
      "suite": "verilator_counter"
    }
    ```

??? success "Response"
    ```json
    {
      "schema_version": "1.0.0",
      "error": {
        "code": "CONFIG_ERROR",
        "message": "Live simulation adapter is not enabled. Set adapters.live_sim=true in config.yaml."
      }
    }
    ```

## `wave.signals`

![MCP tool wave.signals](../assets/mcp-tools/wave-signals.svg)

??? example "Request"
    ```json
    {
      "test_id": "t_3bb6bfc925aa"
    }
    ```

??? success "Response"
    ```json
    {
      "test_id": "t_3bb6bfc925aa",
      "format": "precomputed-vcd",
      "end_time_ns": 10000,
      "start_time_ns": null,
      "end_time_ns_query": null,
      "signals": [
        {
          "name": "clk",
          "group": "counter",
          "width": 1,
          "toggles": 100,
          "last_value": "0"
        },
        {
          "name": "count",
          "group": "counter",
          "width": 4,
          "toggles": 16,
          "last_value": "0xf"
        },
        {
          "name": "rst",
          "group": "counter",
          "width": 1,
          "toggles": 2,
          "last_value": "0"
        }
      ],
      "signal_count": 3,
      "truncated": false,
      "source_path": "verilator_counter/test_counter_sim.wave.json",
      "schema_version": "1.0.0"
    }
    ```

## `wave.summary`

![MCP tool wave.summary](../assets/mcp-tools/wave-summary.svg)

??? example "Request"
    ```json
    {
      "test_id": "t_3bb6bfc925aa",
      "start_time_ns": 1000,
      "end_time_ns": 25000
    }
    ```

??? success "Response"
    ```json
    {
      "test_id": "t_3bb6bfc925aa",
      "format": "precomputed-vcd",
      "end_time_ns": 25000,
      "start_time_ns": 1000,
      "end_time_ns_query": 25000,
      "signal_count": 3,
      "highlights": [
        {
          "time_ns": 1000,
          "signal": "rst",
          "value": "0",
          "note": "reset released"
        },
        {
          "time_ns": 2500,
          "signal": "count",
          "value": "0x3",
          "note": "counter increment window"
        }
      ],
      "highlight_groups": {
        "reset_event": [
          {
            "time_ns": 1000,
            "signal": "rst",
            "value": "0",
            "note": "reset released"
          }
        ],
        "event": [
          {
            "time_ns": 2500,
            "signal": "count",
            "value": "0x3",
            "note": "counter increment window"
          }
        ]
      },
      "signal_groups": null,
      "metadata": {
        "source": "checked-in demo fixture",
        "generator": "verilator-vcd-summary",
        "window": {
          "start_time_ns": 1000,
          "end_time_ns": 25000,
          "note": "JSON summaries filter highlights only; use VCD for per-signal window values"
        }
      },
      "evidence": {
        "kind": "waveform_summary",
        "path": "verilator_counter/test_counter_sim.wave.json"
      },
      "source_path": "verilator_counter/test_counter_sim.wave.json",
      "schema_version": "1.0.0"
    }
    ```
