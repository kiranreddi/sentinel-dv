// axi4_slave.sv — AXI4-Lite Slave with functional coverage groups and SVA properties
// Designed for sentinel-dv MCP verification demo (all 26 tools)

`timescale 1ns/1ps

module axi4_slave #(
    parameter AXI_ADDR_WIDTH = 32,
    parameter AXI_DATA_WIDTH = 32,
    parameter MEM_DEPTH      = 256
) (
    input  logic                      ACLK,
    input  logic                      ARESETn,

    // Write Address Channel
    input  logic [AXI_ADDR_WIDTH-1:0] AWADDR,
    input  logic [7:0]                AWLEN,
    input  logic [2:0]                AWSIZE,
    input  logic [1:0]                AWBURST,
    input  logic                      AWVALID,
    output logic                      AWREADY,

    // Write Data Channel
    input  logic [AXI_DATA_WIDTH-1:0] WDATA,
    input  logic [AXI_DATA_WIDTH/8-1:0] WSTRB,
    input  logic                      WLAST,
    input  logic                      WVALID,
    output logic                      WREADY,

    // Write Response Channel
    output logic [1:0]                BRESP,
    output logic                      BVALID,
    input  logic                      BREADY,

    // Read Address Channel
    input  logic [AXI_ADDR_WIDTH-1:0] ARADDR,
    input  logic [7:0]                ARLEN,
    input  logic [2:0]                ARSIZE,
    input  logic [1:0]                ARBURST,
    input  logic                      ARVALID,
    output logic                      ARREADY,

    // Read Data Channel
    output logic [AXI_DATA_WIDTH-1:0] RDATA,
    output logic [1:0]                RRESP,
    output logic                      RLAST,
    output logic                      RVALID,
    input  logic                      RREADY
);

    // -------------------------------------------------------------------------
    // Internal memory
    // -------------------------------------------------------------------------
    logic [AXI_DATA_WIDTH-1:0] mem [0:MEM_DEPTH-1];

    // -------------------------------------------------------------------------
    // State machines
    // -------------------------------------------------------------------------
    typedef enum logic [1:0] { W_IDLE, W_ADDR, W_DATA, W_RESP } wstate_t;
    typedef enum logic [1:0] { R_IDLE, R_ADDR, R_DATA }         rstate_t;

    wstate_t wstate, wstate_next;
    rstate_t rstate, rstate_next;

    logic [AXI_ADDR_WIDTH-1:0] waddr_q, raddr_q;
    logic [7:0]                wlen_q,  rlen_q;
    logic [2:0]                wsize_q, rsize_q;
    logic [1:0]                wburst_q, rburst_q;
    logic [7:0]                wbeat_cnt, rbeat_cnt;
    logic [1:0]                bresp_q;

    // -------------------------------------------------------------------------
    // Write FSM
    // -------------------------------------------------------------------------
    always_ff @(posedge ACLK or negedge ARESETn) begin
        if (!ARESETn) wstate <= W_IDLE;
        else          wstate <= wstate_next;
    end

    always_comb begin
        wstate_next = wstate;
        case (wstate)
            W_IDLE: if (AWVALID && AWREADY) wstate_next = W_DATA;
            W_ADDR: if (AWVALID && AWREADY) wstate_next = W_DATA;
            W_DATA: if (WVALID && WREADY && WLAST) wstate_next = W_RESP;
            W_RESP: if (BVALID && BREADY)           wstate_next = W_IDLE;
        endcase
    end

    assign AWREADY = (wstate == W_IDLE);
    assign WREADY  = (wstate == W_DATA);
    assign BVALID  = (wstate == W_RESP);
    assign BRESP   = bresp_q;

    always_ff @(posedge ACLK or negedge ARESETn) begin
        if (!ARESETn) begin
            waddr_q    <= '0;
            wlen_q     <= '0;
            wsize_q    <= '0;
            wburst_q   <= '0;
            wbeat_cnt  <= '0;
            bresp_q    <= 2'b00;
        end else begin
            if (AWVALID && AWREADY) begin
                waddr_q  <= AWADDR;
                wlen_q   <= AWLEN;
                wsize_q  <= AWSIZE;
                wburst_q <= AWBURST;
                wbeat_cnt <= '0;
                // Decode-error: out-of-range address
                bresp_q <= (AWADDR[AXI_ADDR_WIDTH-1:2] >= MEM_DEPTH) ? 2'b11 : 2'b00;
            end
            if (WVALID && WREADY) begin
                if (bresp_q == 2'b00) begin
                    // Write with byte strobes
                    if (WSTRB[0]) mem[waddr_q[AXI_ADDR_WIDTH-1:2]][7:0]   <= WDATA[7:0];
                    if (WSTRB[1]) mem[waddr_q[AXI_ADDR_WIDTH-1:2]][15:8]  <= WDATA[15:8];
                    if (WSTRB[2]) mem[waddr_q[AXI_ADDR_WIDTH-1:2]][23:16] <= WDATA[23:16];
                    if (WSTRB[3]) mem[waddr_q[AXI_ADDR_WIDTH-1:2]][31:24] <= WDATA[31:24];
                end
                wbeat_cnt <= wbeat_cnt + 1;
                // Burst address increment
                if (wburst_q == 2'b01) // INCR
                    waddr_q <= waddr_q + (1 << wsize_q);
            end
        end
    end

    // -------------------------------------------------------------------------
    // Read FSM
    // -------------------------------------------------------------------------
    always_ff @(posedge ACLK or negedge ARESETn) begin
        if (!ARESETn) rstate <= R_IDLE;
        else          rstate <= rstate_next;
    end

    always_comb begin
        rstate_next = rstate;
        case (rstate)
            R_IDLE: if (ARVALID && ARREADY) rstate_next = R_DATA;
            R_ADDR: if (ARVALID && ARREADY) rstate_next = R_DATA;
            R_DATA: if (RVALID && RREADY && RLAST) rstate_next = R_IDLE;
        endcase
    end

    assign ARREADY = (rstate == R_IDLE);
    assign RVALID  = (rstate == R_DATA);
    assign RRESP   = (raddr_q[AXI_ADDR_WIDTH-1:2] >= MEM_DEPTH) ? 2'b11 : 2'b00;
    assign RDATA   = (raddr_q[AXI_ADDR_WIDTH-1:2] < MEM_DEPTH)
                     ? mem[raddr_q[AXI_ADDR_WIDTH-1:2]] : '0;
    assign RLAST   = (rbeat_cnt == rlen_q);

    always_ff @(posedge ACLK or negedge ARESETn) begin
        if (!ARESETn) begin
            raddr_q   <= '0;
            rlen_q    <= '0;
            rsize_q   <= '0;
            rburst_q  <= '0;
            rbeat_cnt <= '0;
        end else begin
            if (ARVALID && ARREADY) begin
                raddr_q   <= ARADDR;
                rlen_q    <= ARLEN;
                rsize_q   <= ARSIZE;
                rburst_q  <= ARBURST;
                rbeat_cnt <= '0;
            end
            if (RVALID && RREADY) begin
                rbeat_cnt <= rbeat_cnt + 1;
                if (rburst_q == 2'b01) // INCR
                    raddr_q <= raddr_q + (1 << rsize_q);
            end
        end
    end

    // =========================================================================
    // SVA Properties — protocol correctness checks
    // =========================================================================

    // P1: AWVALID must not drop without handshake
    property awvalid_stable;
        @(posedge ACLK) disable iff (!ARESETn)
        (AWVALID && !AWREADY) |=> AWVALID;
    endproperty
    CHK_AWVALID_STABLE: assert property (awvalid_stable)
        else $error("[AXI4_SVA] AWVALID dropped before AWREADY");

    // P2: ARVALID must not drop without handshake
    property arvalid_stable;
        @(posedge ACLK) disable iff (!ARESETn)
        (ARVALID && !ARREADY) |=> ARVALID;
    endproperty
    CHK_ARVALID_STABLE: assert property (arvalid_stable)
        else $error("[AXI4_SVA] ARVALID dropped before ARREADY");

    // P3: WVALID must not drop mid-burst without handshake
    property wvalid_stable;
        @(posedge ACLK) disable iff (!ARESETn)
        (WVALID && !WREADY) |=> WVALID;
    endproperty
    CHK_WVALID_STABLE: assert property (wvalid_stable)
        else $error("[AXI4_SVA] WVALID dropped before WREADY");

    // P4: BREADY must be asserted within 16 cycles after BVALID
    property bresp_accepted;
        @(posedge ACLK) disable iff (!ARESETn)
        BVALID |-> ##[0:16] BREADY;
    endproperty
    CHK_BRESP_ACCEPTED: assert property (bresp_accepted)
        else $error("[AXI4_SVA] BVALID not accepted within 16 cycles");

    // P5: RLAST must be set on final beat
    property rlast_on_final;
        @(posedge ACLK) disable iff (!ARESETn)
        (RVALID && RREADY && (rbeat_cnt == rlen_q)) |-> RLAST;
    endproperty
    CHK_RLAST_ON_FINAL: assert property (rlast_on_final)
        else $error("[AXI4_SVA] RLAST not set on final read beat");

    // P6: No write to RESP state without prior write data
    property resp_after_data;
        @(posedge ACLK) disable iff (!ARESETn)
        (wstate == W_RESP) |-> (wbeat_cnt > 0);
    endproperty
    CHK_RESP_AFTER_DATA: assert property (resp_after_data)
        else $error("[AXI4_SVA] Write response issued without any data beats");

    // =========================================================================
    // Functional Coverage Groups
    // =========================================================================
    covergroup axi4_burst_cg @(posedge ACLK);
        cp_awburst: coverpoint AWBURST iff (AWVALID && AWREADY) {
            bins fixed = {2'b00};
            bins incr  = {2'b01};
            bins wrap  = {2'b10};
        }
        cp_arburst: coverpoint ARBURST iff (ARVALID && ARREADY) {
            bins fixed = {2'b00};
            bins incr  = {2'b01};
            bins wrap  = {2'b10};
        }
        cp_awlen: coverpoint AWLEN iff (AWVALID && AWREADY) {
            bins single = {0};
            bins short  = {[1:3]};
            bins medium = {[4:15]};
            bins long   = {[16:255]};
        }
        cp_awsize: coverpoint AWSIZE iff (AWVALID && AWREADY) {
            bins byte1 = {3'b000};
            bins byte2 = {3'b001};
            bins byte4 = {3'b010};
        }
        cp_bresp: coverpoint BRESP iff (BVALID && BREADY) {
            bins okay   = {2'b00};
            bins exokay = {2'b01};
            bins slverr = {2'b10};
            bins decerr = {2'b11};
        }
        cx_burst_size: cross cp_awburst, cp_awsize;
    endgroup

    covergroup axi4_backpressure_cg @(posedge ACLK);
        cp_aw_bp: coverpoint (AWVALID && !AWREADY) { bins high = {1}; bins low = {0}; }
        cp_w_bp:  coverpoint (WVALID && !WREADY)  { bins high = {1}; bins low = {0}; }
        cp_r_bp:  coverpoint (RVALID && !RREADY)  { bins high = {1}; bins low = {0}; }
        cp_b_bp:  coverpoint (BVALID && !BREADY)  { bins high = {1}; bins low = {0}; }
    endgroup

    covergroup axi4_error_cg @(posedge ACLK);
        cp_write_error: coverpoint bresp_q iff (wstate == W_RESP) {
            bins okay   = {2'b00};
            bins decerr = {2'b11};
        }
        cp_read_error: coverpoint RRESP iff (RVALID && RREADY) {
            bins okay   = {2'b00};
            bins decerr = {2'b11};
        }
    endgroup

    axi4_burst_cg       burst_cg_inst       = new();
    axi4_backpressure_cg backpressure_cg_inst = new();
    axi4_error_cg        error_cg_inst       = new();

endmodule
