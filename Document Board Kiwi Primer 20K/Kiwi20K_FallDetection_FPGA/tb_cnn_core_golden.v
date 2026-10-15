`timescale 1ns/1ps
`include "cnn_params.vh"

// 20-vector golden test for cnn_core (RA-01).
// Shifts come from src/cnn_params.vh, generated from quant_params.json by
// tools/gen_cnn_params.py, which also writes tb/vec_in.mem and tb/vec_exp.mem
// from ml/src/golden_model.py. Verilog-2001 (Icarus 0.9.7: -g2001 -I src).
// Run from the Gowin project root (ROMs read src/weights.mem, src/bias.mem).

`ifndef TB_NV
`define TB_NV 20   // số vector; tools/export_mem.py sinh 50: iverilog -DTB_NV=50
`endif

module tb_cnn_core_golden;

    localparam NV = `TB_NV;

    // 50 MHz clock
    reg clk = 1'b0;
    always #10 clk = ~clk;

    reg start = 1'b0;

    wire [9:0] input_read_addr;
    reg signed [7:0] input_read_data = 8'sd0;

    wire busy;
    wire inference_done;
    wire [1:0] class_id;
    wire signed [31:0] score;

    reg [7:0]  vin  [0:NV*768-1];
    reg [31:0] vexp [0:NV*5-1];

    integer v;
    integer cycle_count;
    integer max_cycles;
    integer mism;
    integer pass;

    // Match input_buffer.v synchronous read behavior.
    always @(posedge clk) begin
        if (input_read_addr < 10'd768)
            input_read_data <= vin[v*768 + input_read_addr];
        else
            input_read_data <= 8'sd0;
    end

    cnn_core dut (
        .clk             (clk),
        .start           (start),

        .input_read_addr (input_read_addr),
        .input_read_data (input_read_data),

        .conv1_shift     (`CNN_CONV1_SHIFT),
        .conv2_shift     (`CNN_CONV2_SHIFT),

        .busy            (busy),
        .inference_done  (inference_done),

        .class_id        (class_id),
        .score           (score)
    );

    task check;
        input integer idx;
        input [31:0] got;
        begin
            if (got !== vexp[v*5 + idx]) begin
                $display("FAIL tai vector %0d phan tu %0d: mong doi %0d, nhan %0d",
                         v, idx, $signed(vexp[v*5 + idx]), $signed(got));
                mism = mism + 1;
            end
        end
    endtask

    initial begin
        $readmemh("tb/vec_in.mem", vin);
        $readmemh("tb/vec_exp.mem", vexp);
        pass = 0;
        max_cycles = 0;
        v = 0;

        $display("cnn_core golden test: %0d vectors, conv1_shift=%0d conv2_shift=%0d",
                 NV, `CNN_CONV1_SHIFT, `CNN_CONV2_SHIFT);

        repeat (5) @(posedge clk);

        for (v = 0; v < NV; v = v + 1) begin
            start <= 1'b1;
            @(posedge clk);
            start <= 1'b0;

            cycle_count = 0;
            while (!inference_done && cycle_count < 1500000) begin
                @(posedge clk);
                cycle_count = cycle_count + 1;
            end
            #1;

            // inference_done is a 1-cycle pulse and may already be low after #1,
            // so judge the timeout by the counter, not by re-reading the pulse.
            mism = 0;
            if (cycle_count >= 1500000) begin
                $display("FAIL tai vector %0d: timeout sau %0d chu ky", v, cycle_count);
                mism = 1;
            end
            else begin
                check(0, dut.logit0);
                check(1, dut.logit1);
                check(2, dut.logit2);
                check(3, dut.logit3);
                check(4, {30'd0, class_id});
            end

            if (mism == 0) pass = pass + 1;
            if (cycle_count > max_cycles) max_cycles = cycle_count;
            $display("v%0d: cycles=%0d class=%0d logits=%0d %0d %0d %0d %s", v, cycle_count, class_id,
                     $signed(dut.logit0), $signed(dut.logit1), $signed(dut.logit2), $signed(dut.logit3),
                     (mism == 0) ? "PASS" : "FAIL");

            repeat (3) @(posedge clk);
        end

        $display("------------------------------------------------------------");
        $display("KET QUA: %0d/%0d vector khop golden, cycles/inference=%0d", pass, NV, max_cycles);
        if (pass == NV)
            $display("PASS");
        else
            $display("FAIL: KHONG nap bitstream nay len board");
        $finish;
    end

endmodule
