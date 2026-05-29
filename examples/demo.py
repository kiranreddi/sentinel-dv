#!/usr/bin/env python3
"""
Sentinel DV - Interactive Demo

This demo showcases all features of Sentinel DV with mock data.
No actual verification artifacts required!
"""


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_tool(name: str):
    """Print tool name"""
    print(f"\n📋 Tool: {name}")
    print("-" * 80)


def demo_discovery_tools():
    """Demo discovery tools"""
    print_header("🔍 Discovery Tools - Find Verification Artifacts")

    print_tool("runs.list")
    print("  Purpose: List indexed verification runs")
    print("\n  Example query:")
    print('    {"suite": "nightly", "status": "fail", "page": 1, "page_size": 10}')
    print("\n  📊 Results (3 runs found):")

    runs = [
        {
            "run_id": "R20260125_143000",
            "suite": "nightly",
            "status": "fail",
            "total_tests": 150,
            "failed_tests": 12,
            "created_at": "2026-01-25T14:30:00Z",
        },
        {
            "run_id": "R20260125_120000",
            "suite": "smoke",
            "status": "pass",
            "total_tests": 50,
            "failed_tests": 0,
            "created_at": "2026-01-25T12:00:00Z",
        },
        {
            "run_id": "R20260124_220000",
            "suite": "nightly",
            "status": "fail",
            "total_tests": 150,
            "failed_tests": 8,
            "created_at": "2026-01-24T22:00:00Z",
        },
    ]

    for run in runs:
        status_icon = "❌" if run["status"] == "fail" else "✅"
        print(
            f"  {status_icon} {run['run_id']:<25} [{run['suite']:<10}] "
            f"{run['failed_tests']}/{run['total_tests']} failures"
        )

    print_tool("tests.list")
    print("  Purpose: List tests from a run")
    print("\n  Example query:")
    print('    {"run_id": "R20260125_143000", "status": "fail", "framework": "uvm"}')
    print("\n  📊 Results (5 failed tests):")

    tests = [
        {
            "test_id": "T20260125_143000_axi_burst",
            "name": "axi_burst_test",
            "framework": "uvm",
            "status": "fail",
            "duration_ms": 15420,
        },
        {
            "test_id": "T20260125_143000_axi_interleave",
            "name": "axi_interleave_test",
            "framework": "uvm",
            "status": "fail",
            "duration_ms": 18930,
        },
        {
            "test_id": "T20260125_143000_protocol_check",
            "name": "protocol_violation_test",
            "framework": "uvm",
            "status": "fail",
            "duration_ms": 12100,
        },
    ]

    for test in tests:
        print(
            f"  ❌ {test['name']:<30} [{test['framework']:<8}] " f"{test['duration_ms']/1000:.2f}s"
        )


def demo_detail_tools():
    """Demo detail tools"""
    print_header("📊 Detail Tools - Get Comprehensive Information")

    print_tool("tests.get")
    print("  Purpose: Get full test details with evidence")
    print("\n  Example query:")
    print('    {"test_id": "T20260125_143000_axi_burst"}')
    print("\n  📄 Test Details:")
    print("    ID: T20260125_143000_axi_burst")
    print("    Name: axi_burst_test")
    print("    Framework: UVM")
    print("    Status: FAIL")
    print("    Duration: 15.42s")
    print("    Seed: 42")
    print("    Simulator: VCS 2023.12")
    print("\n  📎 Evidence:")
    print("    • sim.log (450 lines)")
    print("    • coverage.xml (functional + code coverage)")
    print("    • waveform.fsdb (signal traces)")

    print_tool("tests.topology")
    print("  Purpose: Get UVM testbench hierarchy and interface bindings")
    print("\n  Example query:")
    print('    {"test_id": "T20260125_143000_axi_burst"}')
    print("\n  🏗️  UVM Topology:")
    print("    Test: axi_burst_test")
    print("    └── uvm_test_top")
    print("        └── env (axi_env)")
    print("            ├── master_agent")
    print("            │   ├── driver")
    print("            │   ├── monitor")
    print("            │   └── sequencer")
    print("            ├── slave_agent")
    print("            │   ├── driver")
    print("            │   ├── monitor")
    print("            │   └── sequencer")
    print("            └── scoreboard")
    print("\n  🔌 Interface Bindings:")
    print("    • axi_m0 (AXI4, master)")
    print("    • axi_s0 (AXI4, slave)")


def demo_analysis_tools():
    """Demo analysis tools"""
    print_header("🔬 Analysis Tools - Failure & Coverage Analysis")

    print_tool("failures.list")
    print("  Purpose: List categorized failure events")
    print("\n  Example query:")
    print('    {"run_id": "R20260125_143000", "severity": "error", "category": "scoreboard"}')
    print("\n  📋 Failures (3 found):")

    failures = [
        {
            "severity": "error",
            "category": "scoreboard",
            "summary": "DATA MISMATCH: Expected 0xDEAD, Got 0xBEEF",
            "component": "uvm_test_top.env.scoreboard",
            "time_ns": 100000,
            "tags": ["scoreboard", "data-integrity"],
        },
        {
            "severity": "error",
            "category": "protocol",
            "summary": "AXI PROTOCOL VIOLATION: AWVALID without AWREADY",
            "component": "uvm_test_top.env.master_agent.monitor",
            "time_ns": 250000,
            "tags": ["protocol", "axi4", "handshake"],
        },
        {
            "severity": "fatal",
            "category": "timeout",
            "summary": "TIMEOUT: Objection timeout in run phase",
            "component": "uvm_test_top",
            "time_ns": 1000000000,
            "tags": ["timeout", "objection"],
        },
    ]

    for f in failures:
        severity_icon = "🔴" if f["severity"] == "fatal" else "🟠"
        print(f"  {severity_icon} [{f['category']:<12}] {f['summary'][:60]}")
        print(f"      @ {f['time_ns']/1000:.0f} us | {f['component']}")

    print_tool("coverage.summary")
    print("  Purpose: Get coverage metrics with missed bins")
    print("\n  Example query:")
    print('    {"run_id": "R20260125_143000", "kind": "functional"}')
    print("\n  📈 Coverage Summary:")
    print("    Overall: 87.5% (target: 90%)")
    print("    Line: 92.3%")
    print("    Branch: 85.7%")
    print("    Toggle: 89.1%")
    print("    Functional: 84.2%")
    print("\n  ⚠️  Missed Coverage (top 5):")
    missed = [
        ("error_injection_covergroup.error_type", "47.2%"),
        ("axi_transaction.burst_len[12-15]", "33.3%"),
        ("corner_cases.unaligned_access", "12.5%"),
        ("power_modes.low_power_wakeup", "25.0%"),
        ("reset_scenarios.async_reset", "40.0%"),
    ]
    for name, coverage in missed:
        print(f"    • {name:<40} {coverage:>6}")


def demo_regression_tools():
    """Demo regression tools"""
    print_header("📈 Regression Tools - Trend Analysis & Comparison")

    print_tool("regressions.summary")
    print("  Purpose: Get regression health summary")
    print("\n  Example query:")
    print('    {"suite": "nightly", "days": 7}')
    print("\n  📊 Regression Health (Last 7 Days):")
    print("    Total runs: 14")
    print("    Pass rate: 85.7% (12/14 passed)")
    print("    Average duration: 2.5 hours")
    print("    Flaky tests detected: 3")
    print("\n  🔝 Top Failure Signatures:")
    signatures = [
        ("Scoreboard data mismatch in AXI write", 8, ["axi_burst_test", "axi_write_test"]),
        ("Protocol violation: AWVALID/AWREADY", 5, ["protocol_test", "handshake_test"]),
        ("Timeout in run phase objection", 3, ["long_test", "stress_test"]),
    ]
    for sig, count, tests in signatures:
        print(f"    [{count:2d}] {sig}")
        print(f"         Tests: {', '.join(tests)}")

    print_tool("runs.diff")
    print("  Purpose: Compare two runs to identify regressions")
    print("\n  Example query:")
    print('    {"base_run_id": "R20260124_220000", "compare_run_id": "R20260125_143000"}')
    print("\n  🔄 Run Comparison:")
    print("    Base:    R20260124_220000 (8 failures)")
    print("    Compare: R20260125_143000 (12 failures)")
    print("\n  ❌ New Failures (4):")
    print("    • axi_burst_test - Scoreboard mismatch")
    print("    • protocol_check_test - Protocol violation")
    print("    • coverage_test - Coverage regression")
    print("    • performance_test - Timing failure")
    print("\n  ✅ Fixed (0):")
    print("    (none)")
    print("\n  📉 Coverage Delta:")
    print("    Overall: -2.3% (89.8% → 87.5%)")
    print("    Functional: -3.1% (87.3% → 84.2%)")


def demo_security_features():
    """Demo security features"""
    print_header("🛡️  Security Features")

    print("\n🔒 Automatic Redaction:")
    print("  Sensitive data automatically redacted from all outputs:")
    print("    • AWS keys: aws_access_key_id=AKIA...")
    print("    • GitHub tokens: ghp_...")
    print("    • OpenAI keys: sk-...")
    print("    • Absolute paths: /home/user/project → [REDACTED]")
    print("    • Email addresses (optional)")

    print("\n📁 Path Sandboxing:")
    print("  All file paths validated and sandboxed:")
    print("    ✅ Allowed: relative/path/to/log.txt")
    print("    ✅ Allowed: sim_results/coverage.xml")
    print("    ❌ Blocked: /etc/passwd")
    print("    ❌ Blocked: ../../../secret.key")
    print("    ❌ Blocked: ~/.ssh/id_rsa")

    print("\n📊 Bounded Outputs:")
    print("  All responses have size limits to prevent DoS:")
    print("    • Log excerpts: max 1000 lines")
    print("    • Text fields: max 50KB")
    print("    • Arrays: max 1000 items")
    print("    • Pagination: max 100 items per page")

    print("\n👀 Read-Only Access:")
    print("  No simulator control or artifact modification:")
    print("    ✅ Read logs, coverage, assertions")
    print("    ✅ Query indexed data")
    print("    ❌ Cannot run simulations")
    print("    ❌ Cannot modify artifacts")
    print("    ❌ Cannot execute commands")


def demo_usage_example():
    """Demo typical usage example"""
    print_header("💡 Typical Usage Example")

    print("\n🎯 Task: Debug why nightly regression is failing")
    print("\n1️⃣  Find the failing run:")
    print('   → runs.list(suite="nightly", status="fail")')
    print("   ✓ Found: R20260125_143000")

    print("\n2️⃣  Get failed tests:")
    print('   → tests.list(run_id="R20260125_143000", status="fail")')
    print("   ✓ Found: 12 failed tests")

    print("\n3️⃣  Analyze failures:")
    print('   → failures.list(run_id="R20260125_143000")')
    print("   ✓ Found: 8 scoreboard mismatches, 3 protocol violations, 1 timeout")

    print("\n4️⃣  Check if it's a regression:")
    print('   → runs.diff(base="R20260124_220000", compare="R20260125_143000")')
    print("   ✓ Found: 4 new failures, coverage dropped 2.3%")

    print("\n5️⃣  Get test topology for context:")
    print('   → tests.topology(test_id="T20260125_143000_axi_burst")')
    print("   ✓ Got: Full UVM hierarchy + AXI interface bindings")

    print("\n6️⃣  Check assertion failures:")
    print('   → assertions.failures(test_id="T20260125_143000_axi_burst")')
    print("   ✓ Found: axi_protocol_check failed at 250us")

    print("\n✅ Conclusion: AXI protocol violation introduced in latest code change")


def main():
    """Run the demo"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "SENTINEL DV - INTERACTIVE DEMO" + " " * 28 + "║")
    print("║" + " " * 15 + "Verification Intelligence for AI Agents" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")

    print("\n📚 This demo showcases Sentinel DV capabilities with mock data.")
    print("   No actual verification artifacts or database required!")

    demos = [
        ("1", "Discovery Tools", demo_discovery_tools),
        ("2", "Detail Tools", demo_detail_tools),
        ("3", "Analysis Tools", demo_analysis_tools),
        ("4", "Regression Tools", demo_regression_tools),
        ("5", "Security Features", demo_security_features),
        ("6", "Usage Example", demo_usage_example),
        ("0", "Run All", None),
    ]

    print("\n📋 Available Demos:")
    for num, name, _ in demos:
        if num != "0":
            print(f"   {num}. {name}")
    print("   0. Run All Demos")

    print("\n" + "─" * 80)
    choice = input("\n🎮 Select demo (0-6, or press Enter for all): ").strip()

    if choice == "" or choice == "0":
        for _, _, demo_func in demos:
            if demo_func:
                demo_func()
    else:
        for num, _, demo_func in demos:
            if num == choice and demo_func:
                demo_func()
                break
        else:
            print("❌ Invalid choice. Please run again and select 0-6.")

    print("\n" + "=" * 80)
    print("✅ Demo complete!")
    print("\n📖 Next Steps:")
    print("   • Read the docs: https://kiranreddi.github.io/sentinel-dv/")
    print("   • Try with real data: python -m sentinel_dv index /path/to/artifacts")
    print("   • Configure Claude Desktop: see how-to-use.md")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
