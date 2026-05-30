// axi4_tb_top.sv — UVM testbench top for AXI4 slave sentinel-dv demo
// Wires up the DUT and provides the UVM environment

`timescale 1ns/1ps
`include "uvm_macros.svh"
import uvm_pkg::*;

// ---------------------------------------------------------------------------
// AXI4 interface
// ---------------------------------------------------------------------------
interface axi4_if #(
    parameter AW = 32,
    parameter DW = 32
) (input logic clk, input logic rst_n);

    logic [AW-1:0]    awaddr;
    logic [7:0]       awlen;
    logic [2:0]       awsize;
    logic [1:0]       awburst;
    logic             awvalid;
    logic             awready;

    logic [DW-1:0]    wdata;
    logic [DW/8-1:0]  wstrb;
    logic             wlast;
    logic             wvalid;
    logic             wready;

    logic [1:0]       bresp;
    logic             bvalid;
    logic             bready;

    logic [AW-1:0]    araddr;
    logic [7:0]       arlen;
    logic [2:0]       arsize;
    logic [1:0]       arburst;
    logic             arvalid;
    logic             arready;

    logic [DW-1:0]    rdata;
    logic [1:0]       rresp;
    logic             rlast;
    logic             rvalid;
    logic             rready;

    clocking mst_cb @(posedge clk);
        output awaddr, awlen, awsize, awburst, awvalid;
        input  awready;
        output wdata, wstrb, wlast, wvalid;
        input  wready;
        output bready;
        input  bresp, bvalid;
        output araddr, arlen, arsize, arburst, arvalid;
        input  arready;
        output rready;
        input  rdata, rresp, rlast, rvalid;
    endclocking

    modport master (clocking mst_cb, input clk, rst_n);

endinterface

// ---------------------------------------------------------------------------
// AXI4 Write Sequence Item
// ---------------------------------------------------------------------------
class axi4_write_seq_item extends uvm_sequence_item;
    `uvm_object_utils(axi4_write_seq_item)

    rand logic [31:0] addr;
    rand logic [31:0] data;
    rand logic [3:0]  strb;
    rand logic [7:0]  len;
    rand logic [1:0]  burst;
    rand logic [2:0]  size;
    logic [1:0]       resp;

    constraint c_addr   { addr[1:0] == 2'b00; addr < 32'h0000_0400; }
    constraint c_strb   { strb != 4'b0000; }
    constraint c_size   { size inside {3'b000, 3'b001, 3'b010}; }
    constraint c_burst  { burst inside {2'b00, 2'b01}; }
    constraint c_len    { len inside {0, 1, 3, 7, 15}; }

    function new(string name = "axi4_write_seq_item");
        super.new(name);
    endfunction
endclass

// ---------------------------------------------------------------------------
// AXI4 Read Sequence Item
// ---------------------------------------------------------------------------
class axi4_read_seq_item extends uvm_sequence_item;
    `uvm_object_utils(axi4_read_seq_item)

    rand logic [31:0] addr;
    rand logic [7:0]  len;
    rand logic [1:0]  burst;
    rand logic [2:0]  size;
    logic [31:0]      data [$];
    logic [1:0]       resp;

    constraint c_addr  { addr[1:0] == 2'b00; addr < 32'h0000_0400; }
    constraint c_size  { size inside {3'b000, 3'b001, 3'b010}; }
    constraint c_burst { burst inside {2'b00, 2'b01}; }
    constraint c_len   { len inside {0, 1, 3, 7, 15}; }

    function new(string name = "axi4_read_seq_item");
        super.new(name);
    endfunction
endclass

// ---------------------------------------------------------------------------
// AXI4 Driver
// ---------------------------------------------------------------------------
class axi4_driver extends uvm_driver #(uvm_sequence_item);
    `uvm_component_utils(axi4_driver)

    virtual axi4_if #(32,32) vif;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db #(virtual axi4_if #(32,32))::get(this, "", "vif", vif))
            `uvm_fatal("CFG", "axi4_if not found")
    endfunction

    task run_phase(uvm_phase phase);
        uvm_sequence_item item;
        forever begin
            seq_item_port.get_next_item(item);
            if ($cast(axi4_write_seq_item, item, axi4_write_seq_item_h)) begin
                drive_write(axi4_write_seq_item_h);
            end else if ($cast(axi4_read_seq_item, item, axi4_read_seq_item_h)) begin
                drive_read(axi4_read_seq_item_h);
            end
            seq_item_port.item_done();
        end
    endtask

    axi4_write_seq_item axi4_write_seq_item_h;
    axi4_read_seq_item  axi4_read_seq_item_h;

    task drive_write(axi4_write_seq_item item);
        @(vif.mst_cb);
        vif.mst_cb.awaddr  <= item.addr;
        vif.mst_cb.awlen   <= item.len;
        vif.mst_cb.awsize  <= item.size;
        vif.mst_cb.awburst <= item.burst;
        vif.mst_cb.awvalid <= 1;
        do @(vif.mst_cb); while (!vif.mst_cb.awready);
        vif.mst_cb.awvalid <= 0;

        repeat(item.len + 1) begin
            @(vif.mst_cb);
            vif.mst_cb.wdata  <= item.data;
            vif.mst_cb.wstrb  <= item.strb;
            vif.mst_cb.wlast  <= (item.len == 0);
            vif.mst_cb.wvalid <= 1;
            do @(vif.mst_cb); while (!vif.mst_cb.wready);
        end
        vif.mst_cb.wvalid <= 0;
        vif.mst_cb.wlast  <= 0;

        vif.mst_cb.bready <= 1;
        do @(vif.mst_cb); while (!vif.mst_cb.bvalid);
        item.resp = vif.mst_cb.bresp;
        vif.mst_cb.bready <= 0;
    endtask

    task drive_read(axi4_read_seq_item item);
        @(vif.mst_cb);
        vif.mst_cb.araddr  <= item.addr;
        vif.mst_cb.arlen   <= item.len;
        vif.mst_cb.arsize  <= item.size;
        vif.mst_cb.arburst <= item.burst;
        vif.mst_cb.arvalid <= 1;
        do @(vif.mst_cb); while (!vif.mst_cb.arready);
        vif.mst_cb.arvalid <= 0;

        vif.mst_cb.rready <= 1;
        do begin
            @(vif.mst_cb);
            if (vif.mst_cb.rvalid) item.data.push_back(vif.mst_cb.rdata);
        end while (!vif.mst_cb.rlast || !vif.mst_cb.rvalid);
        vif.mst_cb.rready <= 0;
    endtask
endclass

// ---------------------------------------------------------------------------
// Scoreboard: write-readback check
// ---------------------------------------------------------------------------
class axi4_scoreboard extends uvm_component;
    `uvm_component_utils(axi4_scoreboard)

    uvm_tlm_analysis_fifo #(axi4_write_seq_item) wr_fifo;
    uvm_tlm_analysis_fifo #(axi4_read_seq_item)  rd_fifo;

    int pass_cnt, fail_cnt;
    logic [31:0] shadow_mem [logic [31:0]];

    function new(string name, uvm_component parent);
        super.new(name, parent);
        pass_cnt = 0; fail_cnt = 0;
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        wr_fifo = new("wr_fifo", this);
        rd_fifo = new("rd_fifo", this);
    endfunction

    task run_phase(uvm_phase phase);
        axi4_write_seq_item wr;
        axi4_read_seq_item  rd;
        forever begin
            fork
                begin wr_fifo.get(wr); shadow_write(wr); end
                begin rd_fifo.get(rd); shadow_check(rd);  end
            join_none
            #1;
        end
    endtask

    task shadow_write(axi4_write_seq_item wr);
        if (wr.resp == 2'b00)
            shadow_mem[wr.addr] = wr.data;
    endtask

    task shadow_check(axi4_read_seq_item rd);
        if (rd.data.size() > 0 && rd.resp == 2'b00) begin
            if (shadow_mem.exists(rd.addr)) begin
                if (rd.data[0] === shadow_mem[rd.addr]) begin
                    `uvm_info("SCBD", $sformatf("PASS: addr=0x%08h exp=0x%08h got=0x%08h",
                        rd.addr, shadow_mem[rd.addr], rd.data[0]), UVM_LOW)
                    pass_cnt++;
                end else begin
                    `uvm_error("SCBD", $sformatf("FAIL: addr=0x%08h exp=0x%08h got=0x%08h",
                        rd.addr, shadow_mem[rd.addr], rd.data[0]))
                    fail_cnt++;
                end
            end
        end
    endtask

    function void report_phase(uvm_phase phase);
        `uvm_info("SCBD", $sformatf("Scoreboard: PASS=%0d FAIL=%0d", pass_cnt, fail_cnt), UVM_NONE)
        if (fail_cnt > 0)
            `uvm_error("SCBD", "SCOREBOARD MISMATCHES DETECTED")
    endfunction
endclass

// ---------------------------------------------------------------------------
// Base test sequences
// ---------------------------------------------------------------------------
class axi4_bk2bk_seq extends uvm_sequence #(uvm_sequence_item);
    `uvm_object_utils(axi4_bk2bk_seq)

    function new(string name = "axi4_bk2bk_seq");
        super.new(name);
    endfunction

    task body();
        axi4_write_seq_item wr;
        axi4_read_seq_item  rd;
        // 32 back-to-back write-read pairs
        repeat(32) begin
            wr = axi4_write_seq_item::type_id::create("wr");
            assert(wr.randomize());
            start_item(wr); finish_item(wr);

            rd = axi4_read_seq_item::type_id::create("rd");
            rd.addr  = wr.addr;
            rd.len   = wr.len;
            rd.burst = wr.burst;
            rd.size  = wr.size;
            start_item(rd); finish_item(rd);
        end
    endtask
endclass

class axi4_burst_seq extends uvm_sequence #(uvm_sequence_item);
    `uvm_object_utils(axi4_burst_seq)

    function new(string name = "axi4_burst_seq");
        super.new(name);
    endfunction

    task body();
        axi4_write_seq_item wr;
        // 16-beat INCR burst
        wr = axi4_write_seq_item::type_id::create("wr_burst");
        assert(wr.randomize() with {len == 15; burst == 2'b01; size == 3'b010;});
        start_item(wr); finish_item(wr);
    endtask
endclass

class axi4_error_seq extends uvm_sequence #(uvm_sequence_item);
    `uvm_object_utils(axi4_error_seq)

    function new(string name = "axi4_error_seq");
        super.new(name);
    endfunction

    task body();
        axi4_write_seq_item wr;
        // Write to out-of-range address to trigger DECERR
        wr = axi4_write_seq_item::type_id::create("wr_err");
        assert(wr.randomize() with {addr == 32'hDEAD_BEEF;});
        start_item(wr); finish_item(wr);
    endtask
endclass

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------
class axi4_env extends uvm_env;
    `uvm_component_utils(axi4_env)

    axi4_driver    drv;
    axi4_scoreboard scbd;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        drv  = axi4_driver::type_id::create("drv", this);
        scbd = axi4_scoreboard::type_id::create("scbd", this);
    endfunction
endclass

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
class axi4_bk2bk_test extends uvm_test;
    `uvm_component_utils(axi4_bk2bk_test)

    axi4_env env;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env = axi4_env::type_id::create("env", this);
    endfunction

    task run_phase(uvm_phase phase);
        axi4_bk2bk_seq seq;
        phase.raise_objection(this);
        seq = axi4_bk2bk_seq::type_id::create("seq");
        seq.start(env.drv.sequencer);
        phase.drop_objection(this);
    endtask
endclass

class axi4_burst_test extends uvm_test;
    `uvm_component_utils(axi4_burst_test)

    axi4_env env;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env = axi4_env::type_id::create("env", this);
    endfunction

    task run_phase(uvm_phase phase);
        axi4_burst_seq seq;
        phase.raise_objection(this);
        seq = axi4_burst_seq::type_id::create("seq");
        seq.start(env.drv.sequencer);
        phase.drop_objection(this);
    endtask
endclass

class axi4_error_test extends uvm_test;
    `uvm_component_utils(axi4_error_test)

    axi4_env env;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env = axi4_env::type_id::create("env", this);
    endfunction

    task run_phase(uvm_phase phase);
        axi4_error_seq seq;
        phase.raise_objection(this);
        seq = axi4_error_seq::type_id::create("seq");
        seq.start(env.drv.sequencer);
        phase.drop_objection(this);
    endtask
endclass

// ---------------------------------------------------------------------------
// Top module
// ---------------------------------------------------------------------------
module axi4_tb_top;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    logic clk = 0;
    logic rst_n = 0;

    always #5 clk = ~clk;

    axi4_if #(32,32) axi_if (.clk(clk), .rst_n(rst_n));

    axi4_slave #(.AXI_ADDR_WIDTH(32), .AXI_DATA_WIDTH(32), .MEM_DEPTH(256)) dut (
        .ACLK     (clk),
        .ARESETn  (rst_n),
        .AWADDR   (axi_if.awaddr),   .AWLEN  (axi_if.awlen),
        .AWSIZE   (axi_if.awsize),   .AWBURST(axi_if.awburst),
        .AWVALID  (axi_if.awvalid),  .AWREADY(axi_if.awready),
        .WDATA    (axi_if.wdata),    .WSTRB  (axi_if.wstrb),
        .WLAST    (axi_if.wlast),    .WVALID (axi_if.wvalid),
        .WREADY   (axi_if.wready),
        .BRESP    (axi_if.bresp),    .BVALID (axi_if.bvalid),
        .BREADY   (axi_if.bready),
        .ARADDR   (axi_if.araddr),   .ARLEN  (axi_if.arlen),
        .ARSIZE   (axi_if.arsize),   .ARBURST(axi_if.arburst),
        .ARVALID  (axi_if.arvalid),  .ARREADY(axi_if.arready),
        .RDATA    (axi_if.rdata),    .RRESP  (axi_if.rresp),
        .RLAST    (axi_if.rlast),    .RVALID (axi_if.rvalid),
        .RREADY   (axi_if.rready)
    );

    initial begin
        uvm_config_db #(virtual axi4_if #(32,32))::set(null, "uvm_test_top.*", "vif", axi_if);
        #20 rst_n = 1;
        run_test();
    end

    // Simulation timeout
    initial begin
        #500000;
        `uvm_fatal("TIMEOUT", "Simulation exceeded 500us")
    end

endmodule
