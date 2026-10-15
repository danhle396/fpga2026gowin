// rtl/v3/tb_stream.v — đưa một chuỗi khung ghi (do firmware sinh) qua chân SPI của fpga_top_v3, ghi lại từng khung
// đọc 20 byte ra file. Dùng cho mô phỏng ghép firmware ↔ RTL (tools/cosim.py). Icarus 0.9.7: -g2001, -DTB_NF=...
`timescale 1ns/1ps
`ifndef TB_NF
`define TB_NF 10
`endif
module tb_stream;
    localparam NF = `TB_NF;
    localparam HALF = 125;            // SCK 4 MHz
    reg clk = 0, sclk = 0, cs_n = 1, mosi = 0, rst_n = 1;
    wire miso, irq;
    always #10 clk = ~clk;
    fpga_top_v3 dut (.clk(clk), .rst_n(rst_n), .spi_sclk(sclk), .spi_cs_n(cs_n), .spi_mosi(mosi),
                     .spi_miso(miso), .irq(irq));
    reg [7:0] frames [0:NF*772-1];
    reg [7:0] rx;
    integer f, i, cyc, fd;

    task xfer;
        input  [7:0] d;
        output [7:0] q;
        integer b;
        begin
            for (b = 7; b >= 0; b = b - 1) begin
                mosi = d[b];
                #(HALF) sclk = 1; q[b] = miso;
                #(HALF) sclk = 0;
            end
        end
    endtask

    initial begin
        $readmemh("tb/stream_frames.mem", frames);
        fd = $fopen("tb/stream_results.mem", "w");
        #2000;
        for (f = 0; f < NF; f = f + 1) begin
            cs_n = 0; #(4*HALF);
            for (i = 0; i < 772; i = i + 1) xfer(frames[f*772 + i], rx);
            #(3*HALF); cs_n = 1;
            cyc = 0;
            while (!irq && cyc < 1000000) begin @(posedge clk); cyc = cyc + 1; end
            #2000; cs_n = 0; #(4*HALF);
            for (i = 0; i < 20; i = i + 1) begin
                xfer(8'h00, rx);
                $fwrite(fd, "%h\n", rx);
            end
            #(3*HALF); cs_n = 1; #5000;
        end
        $fclose(fd);
        $display("tb_stream: %0d khung", NF);
        $finish;
    end
endmodule
