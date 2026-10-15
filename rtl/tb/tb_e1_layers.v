// rtl/tb/tb_e1_layers.v — testbench TỪNG TẦNG cho engine E1 (cnn_core của project), việc RB-02.
// So l1 (RAM B sau POOL1), l2 (RAM B sau POOL2), feat (gap_buffer sau GAP) và 4 logit + lớp với golden.
// Vector: tools/export_mem.py --engine e1 → tb/vec_in.mem, vec_exp.mem, vec_trace.mem, vec_feat.mem; weight ở
// src/weights.mem, src/bias.mem (đường dẫn cố định trong weight_rom.v, bias_rom.v). Icarus 0.9.7: -g2001, -DTB_NV=...
`timescale 1ns/1ps
`include "cnn_params.vh"
`ifndef TB_NV
`define TB_NV 50
`endif
module tb_e1_layers;
    localparam NV = `TB_NV;
    localparam ST_CONV2 = 4'd3, ST_GAP = 4'd5, ST_DENSE = 4'd6;
    reg clk = 1'b0;
    always #10 clk = ~clk;
    reg start = 1'b0;

    wire [9:0] iaddr;
    reg signed [7:0] idata = 8'sd0;
    wire busy, done;
    wire [1:0] cls;
    wire signed [31:0] top, l0, l1, l2, l3;

    reg [7:0]  vin  [0:NV*768-1];
    reg [31:0] vexp [0:NV*5-1];
    reg [7:0]  vtr  [0:NV*`CNN_TRACE_BYTES-1];
    reg [7:0]  vft  [0:NV*32-1];
    integer v, e, nbad, pass, err_l1, err_l2, err_f, err_lg, t;

    always @(posedge clk)                                // như input_buffer.v: đọc đồng bộ
        idata <= (iaddr < 10'd768) ? vin[v*768 + iaddr] : 8'sd0;

    cnn_core dut (.clk(clk), .start(start), .input_read_addr(iaddr), .input_read_data(idata),
                  .conv1_shift(`CNN_CONV1_SHIFT), .conv2_shift(`CNN_CONV2_SHIFT), .busy(busy),
                  .inference_done(done), .class_id(cls), .score(top),
                  .logit0_out(l0), .logit1_out(l1), .logit2_out(l2), .logit3_out(l3));

    initial begin
        $readmemh("tb/vec_in.mem", vin);
        $readmemh("tb/vec_exp.mem", vexp);
        $readmemh("tb/vec_trace.mem", vtr);
        $readmemh("tb/vec_feat.mem", vft);
        pass = 0; err_l1 = 0; err_l2 = 0; err_f = 0; err_lg = 0;
        for (v = 0; v < NV; v = v + 1) begin
            @(posedge clk); start <= 1'b1; @(posedge clk); start <= 1'b0;
            // l1: RAM B đầy khi POOL1 xong, tức lúc stage sang CONV2 (CONV2 chỉ đọc B)
            wait (dut.stage == ST_CONV2); repeat (3) @(posedge clk);
            nbad = 0;
            for (e = 0; e < `CNN_L1_OUT; e = e + 1)
                if (dut.u_feature_ram_b.mem[e] !== vtr[v*`CNN_TRACE_BYTES + `CNN_L1_TOFF + e]) nbad = nbad + 1;
            if (nbad) begin err_l1 = err_l1 + 1; $display("FAIL vector %0d: l1 sai %0d/%0d byte", v, nbad, `CNN_L1_OUT); end
            // l2: RAM B sau POOL2, lúc stage sang GAP
            wait (dut.stage == ST_GAP); repeat (3) @(posedge clk);
            nbad = 0;
            for (e = 0; e < `CNN_L2_OUT; e = e + 1)
                if (dut.u_feature_ram_b.mem[e] !== vtr[v*`CNN_TRACE_BYTES + `CNN_L2_TOFF + e]) nbad = nbad + 1;
            if (nbad) begin err_l2 = err_l2 + 1; $display("FAIL vector %0d: l2 sai %0d/%0d byte", v, nbad, `CNN_L2_OUT); end
            // feat: gap_buffer lúc stage sang DENSE
            wait (dut.stage == ST_DENSE); repeat (3) @(posedge clk);
            nbad = 0;
            for (e = 0; e < 32; e = e + 1)
                if (dut.u_gap_buffer.mem[e] !== vft[v*32 + e]) nbad = nbad + 1;
            if (nbad) begin err_f = err_f + 1; $display("FAIL vector %0d: feat sai %0d/32", v, nbad); end
            t = 0;
            while (!done && t < 1000000) begin @(posedge clk); t = t + 1; end
            if (l0 === vexp[v*5] && l1 === vexp[v*5+1] && l2 === vexp[v*5+2] && l3 === vexp[v*5+3] &&
                {30'd0, cls} === vexp[v*5+4]) pass = pass + 1;
            else begin
                err_lg = err_lg + 1;
                $display("FAIL vector %0d: logit %0d %0d %0d %0d lop %0d", v, l0, l1, l2, l3, cls);
            end
        end
        $display("TUNG TANG E1 (%0d vector): l1 %0d/%0d, l2 %0d/%0d, feat %0d/%0d, logit+lop %0d/%0d", NV,
                 NV - err_l1, NV, NV - err_l2, NV, NV - err_f, NV, pass, NV);
        if (err_l1 == 0 && err_l2 == 0 && err_f == 0 && pass == NV) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
