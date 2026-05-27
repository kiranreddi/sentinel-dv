#include "Vcounter.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

#include <cerrno>
#include <cstdint>
#include <cstring>
#include <memory>
#include <sys/stat.h>

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);

    const std::unique_ptr<Vcounter> top{new Vcounter};
    const std::unique_ptr<VerilatedVcdC> tfp{new VerilatedVcdC};

    Verilated::traceEverOn(true);
    top->trace(tfp.get(), 99);
    const char* vcd_path = "waves/test_counter_sim.vcd";
    if (mkdir("waves", 0755) != 0 && errno != EEXIST) {
        VL_PRINTF("mkdir waves failed: %s\n", strerror(errno));
        return 1;
    }
    tfp->open(vcd_path);

    // VCD uses $timescale 1ps; each dump advances 100_000 ps (= 100 ns).
    // 100 steps → last timestamp #9_900_000 ps ≈ 9.9 µs (good for MCP window demos).
    constexpr uint64_t kStepPs = 100000;
    constexpr int kCycles = 100;

    uint64_t sim_time = 0;
    top->rst = 1;
    top->clk = 0;

    for (int cycle = 0; cycle < kCycles; ++cycle) {
        top->clk = !top->clk;
        if (cycle == 2) {
            top->rst = 0;
        }
        top->eval();
        tfp->dump(sim_time);
        sim_time += kStepPs;
    }

    tfp->close();
    return 0;
}
