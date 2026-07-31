---
name: sentinel-dv-failure-debugging
description: Debug individual SystemVerilog, UVM, or cocotb failures with Sentinel DV MCP tools. Use when asked why a test failed, whether a build, assertion, protocol, scoreboard, timeout, or infrastructure issue caused it, how to reproduce it, or which timeline and waveform evidence supports a hypothesis.
---

# Sentinel DV Failure Debugging

Build a causal explanation for one test from bounded indexed evidence. Do not mistake the last or loudest message for the initiating failure.

## Inputs

Accept a `test_id`, a logical test name plus run or suite context, or a failure description that can be resolved with `tests.list`. Keep ambiguous matches separate until the user or evidence selects one.

## Preflight

1. Confirm the Sentinel DV tools are available with `tests.list` using `page=1`.
2. If unavailable, report that the Sentinel DV MCP server must be configured and the relevant artifacts indexed.

## Workflow

1. Resolve the test using supported `tests.list` filters: `run_id`, `framework`, `status`, and `name_pattern`. Keep multiple matches separate by `test_id`.
2. Call `tests.get` for execution context such as run, framework, seed, simulator, DUT top, status, and duration. It does not supply artifact references.
3. Read every relevant page from `failures.list` with `test_id` and `include_evidence=true`. The API returns newest events first; collect pages, then sort known `time_ns` values ascending before causal analysis. Keep untimed events explicitly separate.
4. Read every relevant page from `assertions.failures` for the same test. Resolve important assertion definitions with `assertions.get`.
5. Branch by failure phase:
   - For `compile` or `elab`, focus on diagnostic excerpts, source location, options, generated files, and simulator version. Do not use waveform tools.
   - For `aborted` status with little or no simulation evidence, inspect `runs.get` CI metadata and artifact completeness. Do not call it infrastructure failure without supporting evidence.
   - For runtime failures, continue with topology and waveform correlation.
6. Call `tests.topology` only when ownership, bindings, or driver-monitor-scoreboard relationships matter.
7. Call `tests.history` for the logical name, matching suite and framework when known. `is_flaky` is a mixed-status signal within a bounded history, not proof of nondeterminism.
8. Use `wave.summary` to find relevant signal groups and windows. Call `wave.signals` only for a specific hypothesis and a bounded interval.
9. Call `tests.replay` only when reproduction guidance is requested. Present the returned command as a dry-run for review.

## Causal Rules

- Build the timeline from compile/elaboration diagnostics, then known simulation-time assertion, protocol, scoreboard, timeout, and status evidence.
- Prefer the earliest event that can explain later symptoms, but require component, assertion-intent, or waveform support before calling it the root cause.
- Keep observation, inference, and alternative hypotheses visibly separate.
- Missing topology, waveforms, seeds, assertion definitions, or timestamps are limitations, not evidence of absence.
- Preserve `run_id`, `test_id`, `signature_id`, `assertion_id`, simulator, seed, and concise returned evidence.

## Deliverable

Return:

1. Test identity and execution context.
2. Phase classification and chronological timeline.
3. Most likely cause with evidence and confidence.
4. Cascading symptoms.
5. Alternatives and missing evidence.
6. Dry-run reproduction command or next discriminating diagnostic action, when requested.

## Invocation Examples

- "Why did `test_axi_burst` fail in run R124?"
- "Correlate this scoreboard mismatch with assertion and waveform evidence."
- "Is this failure a build problem, a runtime design issue, or infrastructure noise?"
