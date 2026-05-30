# AXI4 UVM Four-Simulator Demo

A complete AXI4-Lite slave UVM verification environment demonstrating all
26 sentinel-dv MCP tools against **VCS**, **Questa**, and **Xcelium** simulation results.

## Design under test

`axi4_slave.sv` — AXI4-Lite slave with:
- FSM-based write / read channels
- 6 SVA protocol properties (`CHK_AWVALID_STABLE`, `CHK_ARVALID_STABLE`,
  `CHK_WVALID_STABLE`, `CHK_BRESP_ACCEPTED`, `CHK_RLAST_ON_FINAL`, `CHK_RESP_AFTER_DATA`)
- 3 functional coverage groups (burst type, backpressure, error responses)

## Testbench

`axi4_tb_top.sv` — UVM testbench with:
- AXI4 driver + scoreboard
- `axi4_bk2bk_test` — back-to-back write/read transactions
- `axi4_incr_burst_test` — incrementing burst sequences
- `axi4_error_resp_test` — error response coverage

## Artifact layout

```
demo/axi4_uvm/
├── config.yaml          # sentinel-dv config (4-simulator demo)
├── axi4_slave.sv        # RTL with SVA properties
├── axi4_tb_top.sv       # UVM testbench
├── vcs/
│   ├── results.xml      # JUnit XML (6 tests, 1 intentional failure)
│   ├── simulation.log
│   ├── assertions/      # *.assert.json — per-assertion status
│   ├── coverage/        # coverage.json — functional coverage metrics
│   ├── sva_status/      # *_sva.json — SVA run status per test
│   ├── waveforms/       # *.wave.json — signal transition summaries
│   └── live_status.json # live sim status (for sim.status demo)
├── questa/              # same structure
└── xcelium/             # same structure
```

## Quick start

```bash
# Index all all four simulators
cd demo/axi4_uvm
sentinel-dv-index --config config.yaml --index-all

# Run the full 19-tool demo
python ../../examples/axi4_sentinel_demo.py
```

Expected output:

```
✓ PASS  runs.list  (6 runs)
    Simulators indexed: ['questa', 'vcs', 'xcelium']
...
✓ PASS  All sentinel-dv tools verified against AXI4 UVM data.
```

## What each tool demonstrates

| Tool | What you see |
|------|-------------|
| `runs.list` | 6 runs — 2 per simulator (bk2bk + incr suites) |
| `runs.summary` | Per-run test counts, pass/fail status |
| `regression.summary` | 7-day pass-rate trend per suite |
| `tests.list` | All 33 tests with simulator label |
| `tests.failures` | VCS error-response test failure with log excerpt |
| `tests.flaky` | Tests that flip between sims |
| `assertions.summary` | 6 AXI4 SVA properties with scope + protocol |
| `assertions.sva_status` | Per-test pass/fail/vacuous counts |
| `assertions.vacuity` | `CHK_RESP_AFTER_DATA` fires vacuously (antecedent never true) |
| `coverage.summary` | Functional coverage roll-up per run |
| `coverage.gaps` | 27 gaps — wrap burst, long burst, error resp bins at 0% |
| `coverage.optimize` | Same as gaps filtered to `functional` kind |
| `waveform.summary` | AXI4 signal transitions for `axi4_bk2bk_test` |
| `runs.submit` | Dry-run VCS/Questa/Xcelium bsub command |
| `sim.status` | Live progress from `live_status.json` |
| `tests.replay` | Seed-locked re-run command for a failing test |
| `runs.compare` | Cross-run delta (new failures / new passes) |

## SVA vacuity example

The `CHK_RESP_AFTER_DATA` assertion checks that a write response always
follows a data phase.  In the `axi4_bk2bk_test` the scoreboard never
issues a data-phase-only burst, so the assertion antecedent is never
sampled — **vacuous pass**.  sentinel-dv flags this automatically via
`assertions.vacuity`.

## Coverage gaps

Three bins are permanently at 0% across all simulators:

| Bin | Description |
|-----|-------------|
| `cp_awburst.wrap` | WRAP burst type not exercised |
| `cp_awlen.long` | AXI4 burst length > 8 not exercised |
| `cp_bresp.decerr / slverr / exokay` | Non-OKAY response codes not generated |

These appear as **high-priority gaps** in `coverage.gaps` with actionable
recommendations to add directed test sequences.
