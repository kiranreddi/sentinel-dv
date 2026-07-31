---
hide:
  - navigation
  - toc
---

<div class="sdv-landing" markdown>

<section class="sdv-hero" markdown>

<div class="sdv-hero__content" markdown>

<p class="sdv-kicker">Read-only MCP for design verification</p>

# Sentinel DV

<p class="sdv-hero__lead">
Give Codex, Claude, Copilot, and other MCP clients structured access to SystemVerilog, UVM, cocotb, assertion, coverage, regression, and waveform evidence.
</p>

<div class="sdv-hero__actions" markdown>

[Start with the demo](getting-started/quick-start.md){ .md-button .md-button--primary }
[Connect an agent](getting-started/agent-setup.md){ .md-button }
[Watch 45s](getting-started/video-walkthrough.md){ .md-button }

</div>

<p class="sdv-hero__meta">v2.3.1 · 28 tools · 3 workflow skills · Apache-2.0</p>

</div>

</section>

<section class="sdv-fact-strip" aria-label="Sentinel DV architecture facts">
  <div><strong>Read-only</strong><span>No simulation or artifact mutation</span></div>
  <div><strong>Schema-first</strong><span>Versioned, bounded JSON responses</span></div>
  <div><strong>DuckDB</strong><span>Indexed queries across regressions</span></div>
  <div><strong>Simulator-neutral</strong><span>VCS, Xcelium, Questa, Verilator</span></div>
</section>

## From regression noise to traceable evidence

<div class="sdv-workflow" markdown>

1. **Index** exported logs, JUnit XML, assertion status, coverage reports, and waveform summaries.
2. **Query** 28 read-only MCP tools with stable IDs, filters, pagination, schemas, and evidence references.
3. **Investigate** with focused skills for regression triage, failure debugging, and coverage closure.
4. **Decide** with observations, inference, missing-data warnings, and reproducible follow-up criteria kept separate.

</div>

[Explore the tool model](tools/overview.md){ .md-button }

## Three engineering workflows

<div class="sdv-workflow-table" markdown>

| Workflow | Engineering question | Evidence path |
| --- | --- | --- |
| [Regression triage](skills/regression-triage.md) | What changed, and which failures matter first? | Run summary → health quality → clusters → baseline diff → focused evidence |
| [Failure debugging](skills/failure-debugging.md) | What initiated this test failure? | Test context → chronological events → assertions → topology → bounded waveform window |
| [Coverage closure](skills/coverage-closure.md) | Which valid gap should we close next? | Summary → trend → run-scoped gaps → vacuity → reviewed constraint candidate |

</div>

## Watch the real workflow

<div class="sdv-video sdv-video--home">
  <video
    controls
    playsinline
    preload="metadata"
    poster="assets/videos/sentinel-dv-quickstart-poster.jpg"
    aria-label="Sentinel DV setup and workflow walkthrough"
  >
    <source src="assets/videos/sentinel-dv-quickstart.mp4" type="video/mp4">
    Your browser does not support embedded MP4 video.
  </video>
</div>

[Open the scene index and verification commands](getting-started/video-walkthrough.md){ .md-button }

## Verification data model

<div class="sdv-capabilities" markdown>

<section markdown>

### Execution

Runs, tests, framework, simulator metadata, seeds, duration, CI context, replay command generation, and live status snapshots.

</section>

<section markdown>

### Debug

Normalized failure categories, stable signatures, bounded evidence, UVM topology, assertion definitions and failures, VCD and JSON waveform summaries.

</section>

<section markdown>

### Closure

Functional, code, toggle, and FSM metrics; run diffs; vacuity and SVA status; trend analysis; gap ranking; protocol-aware candidate constraints.

</section>

</div>

## Designed for controlled agent access

Sentinel DV exposes exported verification artifacts, not EDA control. Every MCP tool is annotated read-only. Paths are constrained to configured artifact roots; excerpts and response sizes are bounded; optional redaction protects credentials, email addresses, and local paths.

`runs.submit` and `tests.replay` are intentionally named workflow tools, but they only generate dry-run commands for engineer review.

[Review the security model](architecture/security.md){ .md-button }

## Supported artifacts

| Source | Indexed evidence |
| --- | --- |
| UVM logs | Reports, components, topology hints, failures, phases |
| cocotb / JUnit XML | Test status, duration, exception and failure details |
| Assertion exports | Definitions, intent, runtime failures, SVA pass/fail/vacuity status |
| Coverage exports | Functional, code, toggle, FSM, per-scope metrics and gaps |
| Waveforms | Precomputed `*.wave.json` and bounded VCD summaries |
| CI metadata | Suite, run, build identifiers, status and timestamps |

Commercial waveform databases such as FSDB and WLF are not streamed. Export a bounded summary or VCD inside an allowed artifact root.

## Verify before adoption

The repository includes deterministic checks for the complete MCP surface and the published skills:

```bash
.venv/bin/python scripts/verify_all_mcp_tools.py
.venv/bin/python scripts/verify_skill_workflows.py
```

The checked-in demo corpus covers UVM, cocotb, AXI4, assertions, coverage, JSON waveform summaries, VCD, and exported VCS, Xcelium, Questa, and Verilator artifacts.

<div class="sdv-final-links" markdown>

[Install Sentinel DV](getting-started/installation.md){ .md-button .md-button--primary }
[Read all 28 tool contracts](tools/mcp-tools-reference.md){ .md-button }
[View real tool output](tools/mcp-tool-gallery.md){ .md-button }

</div>

</div>
