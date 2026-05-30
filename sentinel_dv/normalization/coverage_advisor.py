"""Protocol-aware SystemVerilog constraint and UVM sequence advisor.

Given a list of high-priority coverage gaps (CoverageGap objects from
coverage_hints.py), this module generates ready-to-use SV constraint blocks
and UVM sequence hints that engineers can paste directly into their testbench.

Protocol knowledge is embedded as a pattern dictionary keyed by coverpoint
name fragments.  If no specific protocol match is found, a generic
constraint template is emitted.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Protocol knowledge-base
# Each entry: (pattern_regex, constraint_template, sequence_hint, protocol)
# Template uses {bin} for the bin name, {cg} for the coverage group name.
# ---------------------------------------------------------------------------
_PROTOCOL_RULES: list[tuple[str, str, str, str]] = [
    # AXI4 burst type
    (
        r"cp_awburst.*wrap|awburst.*wrap",
        """// AXI4 WRAP burst — hit cp_awburst.wrap bin
constraint c_awburst_wrap_{safe} {{
    awburst == 2'b10;  // WRAP burst type
    awlen  inside {{1, 3, 7, 15}};  // WRAP requires power-of-2 lengths
}}""",
        "Send AXI4 write transaction with AWBURST=2'b10 (WRAP). "
        "Use uvm_do_with(wr_seq, {it.awburst == 2'b10; it.awlen inside {1,3,7,15};}).",
        "AXI4",
    ),
    (
        r"cp_arburst.*wrap|arburst.*wrap",
        """// AXI4 WRAP burst read — hit cp_arburst.wrap bin
constraint c_arburst_wrap_{safe} {{
    arburst == 2'b10;  // WRAP burst type
    arlen   inside {{1, 3, 7, 15}};
}}""",
        "Send AXI4 read with ARBURST=2'b10 (WRAP) and power-of-2 ARLEN.",
        "AXI4",
    ),
    # AXI4 long burst
    (
        r"(aw|ar)len.*long|burst.*long|cp_.*len.*long",
        """// AXI4 long burst — hit cp_awlen.long / cp_arlen.long bin
constraint c_long_burst_{safe} {{
    awlen inside {{[8:15]}};   // burst length > 8 beats
    // or for read:  arlen inside {{[8:15]}};
}}""",
        "Issue AXI4 burst with AWLEN/ARLEN >= 8 (9–16 beat burst). "
        "Confirm slave supports burst lengths > 8 before adding this constraint.",
        "AXI4",
    ),
    # AXI4 error responses
    (
        r"bresp.*slverr|rresp.*slverr",
        """// AXI4 SLVERR response — hit cp_bresp.slverr / cp_rresp.slverr
// Force the slave to generate SLVERR by writing to an error-mapped address.
// Configure your address map so addr_range triggers SLVERR in the slave.
constraint c_slverr_addr_{safe} {{
    addr inside {{[ERROR_ADDR_BASE : ERROR_ADDR_TOP]}};
}}""",
        "Access an address that the slave decodes as an error region (SLVERR). "
        "Add an error-response agent or configure the address map. "
        "Use axi4_err_seq.sv with `force_slverr = 1`.",
        "AXI4",
    ),
    (
        r"bresp.*decerr|rresp.*decerr",
        """// AXI4 DECERR response — hit cp_bresp.decerr / cp_rresp.decerr
// Access an unmapped/decode-error address region.
constraint c_decerr_addr_{safe} {{
    addr inside {{[UNMAPPED_ADDR_BASE : UNMAPPED_ADDR_TOP]}};
}}""",
        "Access an address outside any mapped slave region to trigger DECERR. "
        "Verify your interconnect/fabric returns DECERR for unmapped space.",
        "AXI4",
    ),
    (
        r"bresp.*exokay|rresp.*exokay",
        """// AXI4 EXOKAY — exclusive access success
// Issue locked (exclusive) read followed by exclusive write to same address.
constraint c_exclusive_{safe} {{
    arlock == 1'b1;   // exclusive read
    // Match ARID/AWID for exclusive monitor pairing
}}""",
        "Issue an exclusive read (ARLOCK=1) followed by an exclusive write to the same "
        "address within the exclusive monitor window. "
        "Use uvm_do_with(excl_seq, {it.arlock == 1;}).",
        "AXI4",
    ),
    # AXI4 backpressure / ready
    (
        r"(aw|ar|w|r|b)_bp|backpressure|cp_.*(bp|ready)",
        """// AXI4 backpressure — hold READY low for N cycles
// Add a reactive agent or use a UVM callback to assert backpressure.
class axi4_bp_cb extends uvm_callback;
    task pre_drive(axi4_item item);
        if ($urandom_range(0,3) == 0) begin
            drive_ready = 0;
            repeat($urandom_range(1,8)) @(posedge clk);
            drive_ready = 1;
        end
    endtask
endclass""",
        "Add a backpressure callback that randomly de-asserts READY. "
        "Register it on the slave driver: "
        "`uvm_add_to_seq_lib(axi4_bp_cb, axi4_slave_seq_lib)`.",
        "AXI4",
    ),
    # AHB burst
    (
        r"hburst.*wrap|ahb.*wrap",
        """// AHB WRAP burst — hit hburst wrap bin
constraint c_ahb_wrap_{safe} {{
    hburst inside {{WRAP4, WRAP8, WRAP16}};  // 3'b010, 3'b100, 3'b110
}}""",
        "Issue AHB WRAP4/WRAP8/WRAP16 burst. "
        "Use uvm_do_with(ahb_seq, {it.hburst inside {3'b010, 3'b100, 3'b110};}).",
        "AHB",
    ),
    # APB
    (
        r"pslverr|apb.*error",
        """// APB PSLVERR — slave error response
// Configure a register at ERROR_ADDR to assert PSLVERR.
constraint c_apb_err_{safe} {{
    addr == APB_ERROR_ADDR;
}}""",
        "Access the APB error-mapped register address. "
        "Ensure the APB slave model asserts PSLVERR for this address.",
        "APB",
    ),
    # CHI
    (
        r"chi.*resp|snoop.*resp|chi.*order",
        """// CHI response/ordering — hit chi_resp bin
// Issue CHI transaction with specific resp field constraint.
constraint c_chi_resp_{safe} {{
    resp inside {{CHI_RESP_COMP_ACK, CHI_RESP_RETRY}};
}}""",
        "Issue CHI transaction targeting the specific response code. "
        "Use the CHI VIP sequence with resp_type constrained.",
        "CHI",
    ),
    # Generic toggle
    (
        r"toggle|cp.*bit",
        """// Toggle coverage — ensure both 0→1 and 1→0 transitions
// Drive the target signal to both values in sequence.
task drive_toggle;
    @(posedge clk); target_signal = 0; @(posedge clk);
    @(posedge clk); target_signal = 1; @(posedge clk);
    @(posedge clk); target_signal = 0;
endtask""",
        "Drive the uncovered signal through a 0→1→0 (or 1→0→1) transition. "
        "Check if reset holds the signal high/low and prevents toggling.",
        "generic",
    ),
]


def _safe_id(name: str) -> str:
    """Convert a bin name to a valid SV identifier fragment."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)[:30]


def _find_rule(metric_name: str) -> tuple[str, str, str] | None:
    """Return (constraint_sv, sequence_hint, protocol) for the best matching rule."""
    lower = metric_name.lower()
    for pattern, constraint_tmpl, hint, protocol in _PROTOCOL_RULES:
        if re.search(pattern, lower):
            safe = _safe_id(metric_name)
            constraint_sv = constraint_tmpl.replace("{safe}", safe).replace("{bin}", metric_name)
            return constraint_sv, hint, protocol
    return None


def _generic_constraint(metric_name: str, scope: str) -> tuple[str, str, str]:
    """Fallback generic constraint for unknown coverpoint patterns."""
    safe = _safe_id(metric_name)
    parts = metric_name.split(".")
    bin_name = parts[-1] if parts else metric_name
    cg_name = parts[0] if len(parts) > 1 else "cg"

    constraint_sv = f"""// Uncovered bin: {metric_name}
// Scope: {scope}
// Add a constraint to the transaction object that forces the
// value corresponding to bin '{bin_name}' in covergroup '{cg_name}'.
constraint c_{safe} {{
    // TODO: replace 'target_field' with the actual field sampled by this coverpoint
    target_field == <BIN_VALUE>;
}}"""
    hint = (
        f"Identify the field in your UVM sequence item that is sampled by "
        f"coverpoint '{metric_name}'. "
        f"Add a constraint forcing that field to the value corresponding to bin '{bin_name}'. "
        "Run with +UVM_TESTNAME=<your_directed_test> to verify the bin is now hit."
    )
    return constraint_sv, hint, "generic"


def build_advisories(gaps: list[Any]) -> list[dict[str, Any]]:
    """Convert a list of CoverageGap objects into advisory dicts.

    Each advisory contains:
    - bin_name: str
    - scope: str
    - covered_pct: float
    - priority: str
    - protocol_hint: str  (AXI4 / AHB / APB / CHI / generic)
    - constraint_sv: str  (ready-to-paste SV code block)
    - sequence_hint: str  (plain-English action)

    Args:
        gaps: List of CoverageGap named-tuples / Pydantic objects from
              coverage_hints.generate_recommendations().

    Returns:
        List of advisory dicts.
    """
    advisories: list[dict[str, Any]] = []
    seen: set[str] = set()

    for gap in gaps:
        metric_name = getattr(gap, "metric_name", "unknown")
        scope = getattr(gap, "scope", "unknown")
        covered_pct = getattr(gap, "covered_pct", 0.0)
        priority = getattr(gap, "priority", "high")

        # De-dup by bin name to avoid identical snippets for cross-sim duplicates
        dedup_key = metric_name
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        match = _find_rule(metric_name)
        if match:
            constraint_sv, sequence_hint, protocol = match
        else:
            constraint_sv, sequence_hint, protocol = _generic_constraint(metric_name, scope)

        advisories.append(
            {
                "bin_name": metric_name,
                "scope": scope,
                "covered_pct": covered_pct,
                "priority": priority,
                "protocol_hint": protocol,
                "constraint_sv": constraint_sv,
                "sequence_hint": sequence_hint,
            }
        )

    return advisories
