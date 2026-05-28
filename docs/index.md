---
hide:
  - navigation
  - toc
---

<div class="sdv-landing" markdown>

<div class="sdv-hero" markdown>

<div class="sdv-hero__inner" markdown>

<span class="sdv-hero__badge">:material-shield-check: MCP · Security-first</span>
<span class="sdv-hero__badge">v1.2.0</span>

# Sentinel DV

<p class="sdv-hero__tagline">Verification intelligence for AI agents</p>

<p class="sdv-hero__lead">
Read-only Model Context Protocol access to SystemVerilog, UVM, and cocotb artifacts—indexed with DuckDB, validated against versioned schemas, and bounded for safe LLM reasoning.
</p>

<div class="sdv-hero__actions" markdown>

[Get started](getting-started/quick-start.md){ .md-button .md-button--primary }
[MCP tool gallery](tools/mcp-tool-gallery.md){ .md-button }
[View on GitHub](https://github.com/kiranreddi/sentinel-dv){ .md-button .sdv-btn-outline target=_blank }

</div>

</div>

</div>

<div class="sdv-stats" markdown>

<div class="sdv-stat" markdown>
<span class="sdv-stat__value">15</span>
<span class="sdv-stat__label">MCP tools</span>
</div>

<div class="sdv-stat" markdown>
<span class="sdv-stat__value">Read-only</span>
<span class="sdv-stat__label">By design</span>
</div>

<div class="sdv-stat" markdown>
<span class="sdv-stat__value">DuckDB</span>
<span class="sdv-stat__label">Fast indexing</span>
</div>

<div class="sdv-stat" markdown>
<span class="sdv-stat__value">Schemas</span>
<span class="sdv-stat__label">Typed responses</span>
</div>

</div>

## Why Sentinel DV

<div class="grid cards" markdown>

-   :material-shield-lock:{ .lg .middle } __Security first__

    ---

    Read-only MCP tools with path sandboxing, automatic redaction, and bounded outputs. No simulator control or artifact modification.

    [:octicons-arrow-right-24: Security model](architecture/security.md)

-   :material-file-document-check:{ .lg .middle } __Schema-driven__

    ---

    Every response conforms to versioned, typed contracts. Deterministic outputs support reliable agent reasoning.

    [:octicons-arrow-right-24: Schema reference](architecture/schemas.md)

-   :material-database-search:{ .lg .middle } __Rich verification data__

    ---

    Tests, failures, UVM topology, assertions, coverage, and regression analytics—across **15 MCP tools**.

    [:octicons-arrow-right-24: Tool reference](tools/overview.md)

-   :material-server-network:{ .lg .middle } __Simulator agnostic__

    ---

    VCS, Xcelium, Questa, Verilator, and more via adapter plugins and unified schemas.

    [:octicons-arrow-right-24: Simulator support](guides/simulator-support.md)

-   :material-speedometer:{ .lg .middle } __Indexed queries__

    ---

    DuckDB-backed indexing with pagination and selective projection for fast, bounded reads.

    [:octicons-arrow-right-24: Performance guide](guides/performance.md)

-   :material-puzzle-outline:{ .lg .middle } __Extensible adapters__

    ---

    Plugin architecture for custom parsers and new artifact formats.

    [:octicons-arrow-right-24: Custom adapters](adapters/custom.md)

</div>

## Quick start

<div class="sdv-code-band" markdown>

=== "Configure"

    ```yaml title="config.yaml"
    artifact_roots:
      - /path/to/verification/regressions

    index:
      type: duckdb
      path: ./sentinel_dv.db

    adapters:
      uvm: true
      cocotb: true
      assertions: true
      coverage: true
    ```

=== "Index & serve"

    ```bash
    # Index artifacts
    python -m sentinel_dv.indexing.indexer --config config.yaml --index-all

    # Start MCP server
    python -m sentinel_dv.server --config config.yaml
    ```

=== "Ask an agent"

    ```text
    "Why did test axi_burst_test fail?"
    → tests.list, failures.list, assertions.failures

    "Compare coverage between R123 and R124"
    → runs.diff, coverage.summary
    ```

</div>

[Full installation guide](getting-started/installation.md){ .md-button }

## Supported ecosystems

<div class="sdv-panels" markdown>

<div class="sdv-panel" markdown>

### UVM

- Test topology extraction
- UVM report parsing (INFO/WARNING/ERROR/FATAL)
- Phase tracking
- Component hierarchy mapping

</div>

<div class="sdv-panel" markdown>

### cocotb

- JUnit/XML result parsing
- Python exception tracing
- Coroutine tracking
- Custom JSON dumps

</div>

<div class="sdv-panel" markdown>

### SystemVerilog

- SVA and immediate assertions
- Functional, code, toggle, and FSM coverage
- Compile and elaboration logs

</div>

<div class="sdv-panel" markdown>

### Waveforms

- Precomputed `*.wave.json` or Verilator **`*.vcd`** via built-in `VcdSummaryParser`
- MCP tools `wave.signals` and `wave.summary` ([all 15 tools](tools/mcp-tools-reference.md))
- [Guide](guides/waveforms.md) · [Verilator example](examples/verilator-counter.md) · [Tool gallery (screenshots)](tools/mcp-tool-gallery.md)

</div>

</div>

## Use cases

!!! example "Automated triage"

    **"Why did this test fail?"**

    Structured failure events with categorization, evidence, and topology context.

!!! example "Regression analytics"

    **"What changed between passing and failing runs?"**

    Compare runs with structured diffs: new failures, resolved issues, coverage deltas.

!!! example "Coverage analysis"

    **"Which tests cover the AXI write channel?"**

    Query coverage metrics by scope, interface, and protocol.

!!! example "Assertion mapping"

    **"Show assertions related to the APB protocol"**

    Discover assertions by protocol, scope, or intent with runtime failure tracking.

## Install

```bash
pip install sentinel-dv
```

```bash
git clone https://github.com/kiranreddi/sentinel-dv.git
cd sentinel-dv
pip install -e ".[dev]"
```

<div class="grid cards" markdown>

-   :fontawesome-brands-github:{ .lg .middle } __GitHub__

    ---

    Issues, features, and contributions

    [:octicons-arrow-right-24: kiranreddi/sentinel-dv](https://github.com/kiranreddi/sentinel-dv)

-   :material-forum:{ .lg .middle } __Discussions__

    ---

    Questions and community help

    [:octicons-arrow-right-24: GitHub Discussions](https://github.com/kiranreddi/sentinel-dv/discussions)

-   :material-book-open-variant:{ .lg .middle } __Documentation__

    ---

    Guides, architecture, and tool reference

    [:octicons-arrow-right-24: Browse docs](getting-started/quick-start.md)

</div>

## License

Sentinel DV is licensed under the [Apache License 2.0](about/license.md).

<div class="sdv-cta" markdown>

Ready to connect your verification workspace to AI agents?

[Get started →](getting-started/quick-start.md){ .md-button .md-button--primary }

</div>

</div>
