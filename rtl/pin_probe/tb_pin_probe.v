// rtl/pin_probe/tb_pin_probe.v — mỗi chân probe[k] phải có đúng k+1 xung trong một khung 16 nửa chu kỳ.
`timescale 1ns/1ps
module tb_pin_probe;
    reg clk = 0;
    wire [5:0] probe;
    wire led_n;
    always #5 clk = ~clk;

    pin_probe_top dut (.clk(clk), .probe(probe), .led_n(led_n));
    defparam dut.HALF = 5;

    integer cnt [0:5];
    integer hi  [0:5];
    integer k, n, fail;
    reg [5:0] prev;

    initial begin
        fail = 0;
        prev = 0;
        repeat (5 * 16 + 3) @(posedge clk);           // bỏ khung đầu
        for (k = 0; k < 6; k = k + 1) begin cnt[k] = 0; hi[k] = 0; end
        for (n = 0; n < 5 * 16; n = n + 1) begin      // đúng một khung
            @(posedge clk); #1;
            for (k = 0; k < 6; k = k + 1) begin
                if (probe[k] && !prev[k]) cnt[k] = cnt[k] + 1;
                if (probe[k]) hi[k] = hi[k] + 1;
            end
            prev = probe;
        end
        for (k = 0; k < 6; k = k + 1) begin
            $display("probe[%0d]: %0d xung, muc cao %0d/80 chu ky", k, cnt[k], hi[k]);
            if (cnt[k] != k + 1 || hi[k] != 5 * (k + 1)) fail = fail + 1;
        end
        if (fail == 0) $display("PASS");
        else           $display("FAIL: %0d chan sai", fail);
        $finish;
    end
endmodule
