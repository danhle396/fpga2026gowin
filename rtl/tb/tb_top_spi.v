// rtl/tb/tb_top_spi.v — kiểm fpga_top QUA CHÂN SPI bằng đúng khung PROTO = 1 mà firmware sinh ra (A.7, FW-08):
//   ghi [A5][SEQ][768][CRC-8] ở SCK 4 MHz mode 0 → chờ IRQ → kéo CS, đọc 7 byte → so với golden
//   [5A][CLASS][logit lớn nhất 32 bit][CRC-8]; IRQ phải về 0 sau khi đọc.
// Thêm một khung sai CRC: FPGA không được bật IRQ, và khung đúng ngay sau đó vẫn chạy.
// Vector do tools/gen_tb_top.py sinh: tb/spi_frames.mem (771 byte/khung), tb/spi_exp.mem (7 byte/khung, khung sai CRC
// có kỳ vọng toàn 0xEE = "không được có kết quả"). Icarus 0.9.7: -g2001.
`timescale 1ns/1ps
module tb_top_spi;
    parameter NF      = 5;            // số khung trong spi_frames.mem
    parameter HALF    = 125;          // nửa chu kỳ SCK (ns): 4 MHz
    parameter TIMEOUT = 1000000;      // chu kỳ 50 MHz chờ IRQ (≈ 20 ms > 13,96 ms suy luận)

    reg clk = 0, sclk = 0, cs_n = 1, mosi = 0;
    wire miso, irq;
    always #10 clk = ~clk;            // 50 MHz

    fpga_top dut (.clk(clk), .spi_sclk(sclk), .spi_cs_n(cs_n), .spi_mosi(mosi), .spi_miso(miso), .irq(irq));

    reg [7:0] frames [0:NF*771-1];
    reg [7:0] expv   [0:NF*7-1];
    reg [7:0] got    [0:6];
    integer f, i, b, n, cyc, fails;
    reg [7:0] tx, rx;

    task xfer;                        // một byte mode 0, MSB trước
        input  [7:0] d;
        output [7:0] q;
        integer k;
        begin
            for (k = 7; k >= 0; k = k - 1) begin
                mosi = d[k];
                #(HALF) sclk = 1; q[k] = miso;
                #(HALF) sclk = 0;
            end
        end
    endtask

    initial begin
        $readmemh("tb/spi_frames.mem", frames);
        $readmemh("tb/spi_exp.mem", expv);
        fails = 0;
        #1000;
        for (f = 0; f < NF; f = f + 1) begin
            cs_n = 0; #(4*HALF);
            for (i = 0; i < 771; i = i + 1) xfer(frames[f*771 + i], rx);
            #(3*HALF); cs_n = 1;
            cyc = 0;
            n = (expv[f*7] == 8'hEE) ? 100000 : TIMEOUT;     // khung sai CRC: 2 ms là đủ thấy không có IRQ
            while (!irq && cyc < n) begin @(posedge clk); cyc = cyc + 1; end
            if (expv[f*7] == 8'hEE) begin
                if (irq) begin
                    $display("FAIL khung %0d: CRC sai nhung FPGA van bat IRQ", f); fails = fails + 1;
                end else
                    $display("khung %0d: CRC-8 sai -> khong co IRQ sau %0d chu ky  PASS", f, cyc);
            end else if (!irq) begin
                $display("FAIL khung %0d: khong thay IRQ sau %0d chu ky", f, cyc); fails = fails + 1;
            end else begin
                #2000; cs_n = 0; #(4*HALF);
                for (i = 0; i < 7; i = i + 1) begin xfer(8'h00, rx); got[i] = rx; end
                #(3*HALF); cs_n = 1;
                n = 0;
                for (i = 0; i < 7; i = i + 1) if (got[i] !== expv[f*7 + i]) n = n + 1;
                repeat (10) @(posedge clk);
                $display("khung %0d: IRQ sau %0d chu ky; doc %h %h %h %h %h %h %h; mong doi %h %h %h %h %h %h %h; IRQ sau doc = %b  %s",
                         f, cyc, got[0], got[1], got[2], got[3], got[4], got[5], got[6],
                         expv[f*7], expv[f*7+1], expv[f*7+2], expv[f*7+3], expv[f*7+4], expv[f*7+5], expv[f*7+6],
                         irq, (n == 0 && irq == 0) ? "PASS" : "FAIL");
                if (n != 0 || irq != 0) fails = fails + 1;
            end
            #5000;
        end
        $display("------------------------------------------------------------");
        if (fails == 0) $display("PASS");
        else            $display("FAIL: %0d khung sai", fails);
        $finish;
    end
endmodule
