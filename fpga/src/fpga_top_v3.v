// fpga/src/fpga_top_v3.v — top giao thức v3 (A.7, việc RA-03): CRC-16, SEQ, STATUS, đuôi 13 byte, RST_N, CYCLES.
// Dùng lại nguyên spi_slave, input_buffer, cnn_core của project Gowin. fpga_top (PROTO 1) giữ nguyên để thông mạch
// lần đầu (RA-04). Chân: header J2 (24/10), xem fpga/src/fpga_top_v3.cst.
`include "cnn_params.vh"
`ifndef CNN_SCORE_SHIFT
`define CNN_SCORE_SHIFT 0
`endif
module fpga_top_v3 (
    input  wire clk,
    input  wire rst_n,           // thấp tích cực, từ MCU P2.1; kéo lên trong chip
    input  wire spi_sclk,
    input  wire spi_cs_n,
    input  wire spi_mosi,
    output wire spi_miso,
    output wire irq
);
    wire clk_50m;
    pll_50m u_pll (.clkout(clk_50m), .clkin(clk));

    // RST_N: đồng bộ 3 tầng, xả ra đồng bộ
    reg [2:0] rst_sync = 3'b111;
    always @(posedge clk_50m) rst_sync <= {rst_sync[1:0], ~rst_n};
    wire rst = rst_sync[2];

    wire [7:0] rx_data;
    wire       rx_valid;
    spi_slave u_spi_slave (.sys_clk(clk_50m), .spi_sclk(spi_sclk), .spi_cs_n(spi_cs_n), .spi_mosi(spi_mosi),
                           .rx_data(rx_data), .rx_valid(rx_valid));

    wire [7:0] seq;
    wire [9:0] waddr;
    wire [7:0] wdata;
    wire       we, payload_done, frame_err;
    wire [2:0] err_status;
    wire       cnn_busy;
    packet_parser_v3 u_parser (.clk(clk_50m), .rst(rst), .cs_n(spi_cs_n), .rx_data(rx_data), .rx_valid(rx_valid),
                               .busy(cnn_busy), .sequence(seq), .data_addr(waddr), .data_out(wdata), .data_we(we),
                               .payload_done(payload_done), .frame_err(frame_err), .err_status(err_status));

    wire [9:0]        raddr;
    wire signed [7:0] rdata;
    input_buffer u_input_buffer (.clk(clk_50m), .we(we), .write_addr(waddr), .write_data(wdata),
                                 .read_addr(raddr), .read_data(rdata));

    wire               cnn_done;
    wire [1:0]         cnn_class;
    wire signed [31:0] cnn_top, lg0, lg1, lg2, lg3;
`ifdef CNN_ENGINE_E2
    // Engine E2 (fpga/src/cnn_e2.v, RB-04): bảng lớp và ROM do tools/export_mem.py --engine e2 sinh
`ifndef CNN_L3_OC
`define CNN_L3_OC 1
`define CNN_L3_IC 1
`define CNN_CONV3_SHIFT 0
`define CNN_L3_BASE 0
`endif
    wire [23:0] e2_cycles;
    cnn_e2 #(.LANES(`CNN_LANES), .NL(`CNN_NLAYERS), .HEAD_GAP(`CNN_HEAD_GAP),
             .L1_OC(`CNN_L1_OC), .L1_IC(`CNN_L1_IC), .L1_SH(`CNN_CONV1_SHIFT), .L1_BASE(`CNN_L1_BASE),
             .L2_OC(`CNN_L2_OC), .L2_IC(`CNN_L2_IC), .L2_SH(`CNN_CONV2_SHIFT), .L2_BASE(`CNN_L2_BASE),
             .L3_OC(`CNN_L3_OC), .L3_IC(`CNN_L3_IC), .L3_SH(`CNN_CONV3_SHIFT), .L3_BASE(`CNN_L3_BASE),
             .DENSE_F(`CNN_DENSE_F), .DENSE_BASE(`CNN_DENSE_BASE),
             .ROM_WORDS(`CNN_ROM_WORDS), .BIAS_WORDS(`CNN_BIAS_WORDS),
             .WFILE("src/weights_e2.mem"), .BFILE("src/bias_e2.mem"))
        u_cnn (.clk(clk_50m), .start(payload_done), .input_read_addr(raddr), .input_read_data(rdata),
               .busy(cnn_busy), .inference_done(cnn_done), .class_id(cnn_class), .score(cnn_top),
               .logit0_out(lg0), .logit1_out(lg1), .logit2_out(lg2), .logit3_out(lg3), .cycles(e2_cycles));
`else
    // Engine E1 (cnn_core của project, N1)
    cnn_core u_cnn_core (.clk(clk_50m), .start(payload_done), .input_read_addr(raddr), .input_read_data(rdata),
                         .conv1_shift(`CNN_CONV1_SHIFT), .conv2_shift(`CNN_CONV2_SHIFT),
                         .busy(cnn_busy), .inference_done(cnn_done), .class_id(cnn_class), .score(cnn_top),
                         .logit0_out(lg0), .logit1_out(lg1), .logit2_out(lg2), .logit3_out(lg3));
`endif

    // CYCLES: số chu kỳ từ khi khung ghi xong (payload_done) tới inference_done, bão hòa 24 bit
    reg [23:0] cyc = 24'd0, cyc_hold = 24'd0;
    reg [7:0]  seq_run = 8'd0;
    reg        counting = 1'b0;
    always @(posedge clk_50m) begin
        if (payload_done) begin
            cyc <= 24'd1; counting <= 1'b1; seq_run <= seq;
        end else if (counting) begin
            if (cnn_done) begin
                counting <= 1'b0; cyc_hold <= cyc;
            end else if (cyc != 24'hFFFFFF) begin
                cyc <= cyc + 24'd1;
            end
        end
    end

    wire [4:0] rd_index;
    wire [7:0] rd_byte;
    wire       valid, read_done;
    result_frame_v3 #(.SCORE_SHIFT(`CNN_SCORE_SHIFT), .LOGIT_SHIFT(0)) u_frame (
        .clk(clk_50m), .rst(rst), .done(cnn_done), .class_id(cnn_class),
        .logit0(lg0), .logit1(lg1), .logit2(lg2), .logit3(lg3),
        .cycles(cnn_done ? cyc : cyc_hold), .seq_ok(seq_run),
        .err(frame_err), .err_status(err_status), .seq_err(seq),
        .rd_index(rd_index), .rd_byte(rd_byte), .read_done(read_done), .valid(valid), .irq(irq));

    spi_result_tx_v3 u_tx (.sys_clk(clk_50m), .rst(rst), .spi_sclk(spi_sclk), .spi_cs_n(spi_cs_n),
                           .result_valid(valid), .rd_index(rd_index), .rd_byte(rd_byte),
                           .spi_miso(spi_miso), .read_done(read_done));
endmodule
