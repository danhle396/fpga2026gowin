// fpga/sim/tb_e2.v — kiểm engine E2 (RB-03, RB-04) với vector của tools/export_mem.py --engine e2.
// Chạy trong thư mục xuất (có weights.mem, bias.mem, cnn_params.vh, vec_in.mem, vec_exp.mem): fpga/scripts/test.sh.
// So 4 logit và lớp của từng vector với golden, in số chu kỳ mỗi lần. Icarus 0.9.7: -g2001; số vector: -DTB_NV=...
`timescale 1ns/1ps
`include "cnn_params.vh"
`ifndef TB_NV
`define TB_NV 50
`endif
`ifndef CNN_L3_OC
`define CNN_L3_OC 1
`define CNN_L3_IC 1
`define CNN_CONV3_SHIFT 0
`define CNN_L3_BASE 0
`define CNN_L3_OUT 0
`define CNN_L3_TOFF 0
`endif
module tb_e2;
    localparam NV = `TB_NV;
    reg clk = 0, start = 0;
    always #10 clk = ~clk;

    reg  [7:0] ibuf [0:767];
    reg  [7:0] vin  [0:NV*768-1];
    reg  [31:0] vexp [0:NV*5-1];
    reg  [7:0]  vtr  [0:NV*`CNN_TRACE_BYTES-1];          // l1, l2, (l3) của từng vector (export_mem.py)
    integer lerr [0:2];
    integer e, lbad;
    wire [9:0] iaddr;
    reg  [7:0] ird;
    always @(posedge clk) ird <= ibuf[iaddr];       // như input_buffer.v: đọc đồng bộ 1 chu kỳ

    wire busy, done;
    wire [1:0] cls;
    wire signed [31:0] top, l0, l1, l2, l3;
    wire [23:0] cyc;
    cnn_e2 #(.LANES(`CNN_LANES), .NL(`CNN_NLAYERS), .HEAD_GAP(`CNN_HEAD_GAP),
             .L1_OC(`CNN_L1_OC), .L1_IC(`CNN_L1_IC), .L1_SH(`CNN_CONV1_SHIFT), .L1_BASE(`CNN_L1_BASE),
             .L2_OC(`CNN_L2_OC), .L2_IC(`CNN_L2_IC), .L2_SH(`CNN_CONV2_SHIFT), .L2_BASE(`CNN_L2_BASE),
             .L3_OC(`CNN_L3_OC), .L3_IC(`CNN_L3_IC), .L3_SH(`CNN_CONV3_SHIFT), .L3_BASE(`CNN_L3_BASE),
             .DENSE_F(`CNN_DENSE_F), .DENSE_BASE(`CNN_DENSE_BASE),
             .ROM_WORDS(`CNN_ROM_WORDS), .BIAS_WORDS(`CNN_BIAS_WORDS),
             .WFILE("weights.mem"), .BFILE("bias.mem"))
        dut (.clk(clk), .start(start), .input_read_addr(iaddr), .input_read_data(ird), .busy(busy),
             .inference_done(done), .class_id(cls), .score(top), .logit0_out(l0), .logit1_out(l1),
             .logit2_out(l2), .logit3_out(l3), .cycles(cyc));

    integer v, i, pass, maxc, minc, t;
    initial begin
        $readmemh("vec_in.mem", vin);
        $readmemh("vec_exp.mem", vexp);
        $readmemh("vec_trace.mem", vtr);
        lerr[0] = 0; lerr[1] = 0; lerr[2] = 0;
        pass = 0; maxc = 0; minc = 32'h7FFFFFFF;
        $display("E2: LANES=%0d NL=%0d HEAD_GAP=%0d, %0d vector", `CNN_LANES, `CNN_NLAYERS, `CNN_HEAD_GAP, NV);
        for (v = 0; v < NV; v = v + 1) begin
            for (i = 0; i < 768; i = i + 1) ibuf[i] = vin[v * 768 + i];
            @(posedge clk); start <= 1; @(posedge clk); start <= 0;
            // vết từng lớp: ghi RAM trễ 1 nhịp sau khi layer đổi, nên chờ 3 nhịp rồi chụp
            lbad = 0;
            @(posedge clk);                                // để DUT kịp đặt lại layer = 0 (N1 kết thúc ở layer 1)
            wait (dut.layer == 2'd1); repeat (3) @(posedge clk);
            for (e = 0; e < `CNN_L1_OUT; e = e + 1)
                if (dut.ram_a[e] !== vtr[v*`CNN_TRACE_BYTES + `CNN_L1_TOFF + e]) lbad = lbad + 1;
            if (lbad) begin lerr[0] = lerr[0] + 1; $display("FAIL vector %0d: l1 sai %0d byte", v, lbad); end
            if (`CNN_NLAYERS == 3) begin
                lbad = 0;
                wait (dut.layer == 2'd2); repeat (3) @(posedge clk);
                for (e = 0; e < `CNN_L2_OUT; e = e + 1)
                    if (dut.ram_b[e] !== vtr[v*`CNN_TRACE_BYTES + `CNN_L2_TOFF + e]) lbad = lbad + 1;
                if (lbad) begin lerr[1] = lerr[1] + 1; $display("FAIL vector %0d: l2 sai %0d byte", v, lbad); end
            end
            t = 0;
            while (!done && t < 2000000) begin @(posedge clk); t = t + 1; end
            lbad = 0;
            if (`CNN_NLAYERS == 3) begin
                for (e = 0; e < `CNN_L3_OUT; e = e + 1)
                    if (dut.ram_a[e] !== vtr[v*`CNN_TRACE_BYTES + `CNN_L3_TOFF + e]) lbad = lbad + 1;
                if (lbad) begin lerr[2] = lerr[2] + 1; $display("FAIL vector %0d: l3 sai %0d byte", v, lbad); end
            end else begin
                for (e = 0; e < `CNN_L2_OUT; e = e + 1)
                    if (dut.ram_b[e] !== vtr[v*`CNN_TRACE_BYTES + `CNN_L2_TOFF + e]) lbad = lbad + 1;
                if (lbad) begin lerr[1] = lerr[1] + 1; $display("FAIL vector %0d: l2 sai %0d byte", v, lbad); end
            end
            if (l0 === vexp[v*5] && l1 === vexp[v*5+1] && l2 === vexp[v*5+2] && l3 === vexp[v*5+3] &&
                {30'd0, cls} === vexp[v*5+4]) pass = pass + 1;
            else
                $display("FAIL vector %0d: logit %0d %0d %0d %0d lop %0d; mong doi %0d %0d %0d %0d lop %0d", v,
                         l0, l1, l2, l3, cls, $signed(vexp[v*5]), $signed(vexp[v*5+1]), $signed(vexp[v*5+2]),
                         $signed(vexp[v*5+3]), vexp[v*5+4]);
            if (cyc > maxc) maxc = cyc;
            if (cyc < minc) minc = cyc;
        end
        $display("KET QUA: %0d/%0d vector khop golden (logit + lop), cycles/inference = %0d..%0d", pass, NV, minc, maxc);
        $display("TUNG TANG: l1 %0d/%0d, l2 %0d/%0d%s", NV - lerr[0], NV, NV - lerr[1], NV,
                 (`CNN_NLAYERS == 3) ? "" : " (N1: khong co l3)");
        if (`CNN_NLAYERS == 3) $display("           l3 %0d/%0d", NV - lerr[2], NV);
        if (pass == NV && lerr[0] == 0 && lerr[1] == 0 && lerr[2] == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
