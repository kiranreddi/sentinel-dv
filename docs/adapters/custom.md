# Custom Adapters

Sentinel DV currently ships a **fixed built-in adapter set**:

- `sentinel_dv.adapters.uvm_log.UVMLogParser`
- `sentinel_dv.adapters.cocotb.CocotbParser`
- `sentinel_dv.adapters.assertion_reports.AssertionReportParser`
- `sentinel_dv.adapters.coverage_reports.CoverageReportParser`
- `sentinel_dv.adapters.waveform_summary.WaveformSummaryParser`
- `sentinel_dv.adapters.vcd_summary.VcdSummaryParser`

## Important: What is and is not supported today

- There is **no runtime plugin registry API** today.
- There is **no** `SentinelDV.register_adapter(...)` public API.
- There is **no config-driven dynamic adapter loading** (`module/class/priority`) yet.

This page describes the current internal adapter contract and the safest extension path for contributors.

## Current internal adapter contract

Built-in adapters generally follow:

- `can_handle(path: Path) -> bool`
- `parse(path: Path) -> dict[str, Any]`

The indexer calls these directly and normalizes output into store tables.

## Recommended extension path (current architecture)

If you need a new format:

1. Add a parser under `sentinel_dv/adapters/` with `can_handle` + `parse`.
2. Add focused tests under `tests/unit/` for malformed and happy-path inputs.
3. Wire discovery + ingestion in `sentinel_dv/indexing/indexer.py`.
4. Keep outputs bounded and deterministic:
   - relative paths only
   - redacted excerpts
   - deterministic sorting and IDs

## Future plugin model

A first-class adapter plugin registry is planned but not implemented in `v1.2.x`.
Until then, adapter additions are code changes in-repo.
