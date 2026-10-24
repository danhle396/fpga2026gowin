// fpga/sim/tb_proto.v — kiểm fpga_top_v3 qua chân SPI theo giao thức v3 (A.7), việc RA-03.
// Vector: tools/gen_tb_proto.py → tb/proto_frames.mem (772 byte/khung), tb/proto_exp.mem (20 byte/kết quả).
// Kịch bản: (0) đọc khi chưa có kết quả → toàn 0; (1) NG khung đúng, đọc 20 byte, so golden (CYCLES phải bằng nhau
// giữa các khung, CRC đuôi tự kiểm); (2) CRC sai; (3) khung thiếu byte; (4) hai khung sát nhau: khung sau đến khi đang
// bận; (5) byte đầu không phải 0xA5 → bỏ qua; (6) chế độ RUN đọc 7 byte, IRQ về 0, đọc lại → toàn 0;
// (7) RST_N khi đang có kết quả → IRQ về 0, MISO toàn 0. Icarus 0.9.7: -g2001, NG chỉnh bằng -DTB_NG=...
`timescale 1ns/1ps
`ifndef TB_NG
`define TB_NG 50
`endif
module tb_proto;
    localparam NG = `TB_NG;
    localparam NF = NG + 7;           // số khung trong proto_frames.mem
    localparam NE = NG + 5;           // số kết quả 20 byte trong proto_exp.mem
    localparam HALF = 125;            // SCK 4 MHz

    reg clk = 0, sclk = 0, cs_n = 1, mosi = 0, rst_n = 1;
    wire miso, irq;
    always #10 clk = ~clk;

    fpga_top_v3 dut (.clk(clk), .rst_n(rst_n), .spi_sclk(sclk), .spi_cs_n(cs_n), .spi_mosi(mosi),
                     .spi_miso(miso), .irq(irq));

    reg [7:0] frames [0:NF*772-1];
    reg [7:0] expv   [0:NE*20-1];
    reg [7:0] got    [0:19];
    reg [23:0] cyc0;
    integer fails, e, i, k, cyc, nbad;
    reg [7:0] rx;
    reg [15:0] c;

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

    task send;                        // gửi n byte đầu của khung f trong một lần CS
        input integer f;
        input integer n;
        integer j;
        begin
            cs_n = 0; #(4*HALF);
            for (j = 0; j < n; j = j + 1) xfer(frames[f*772 + j], rx);
            #(3*HALF); cs_n = 1; #(4*HALF);
        end
    endtask

    task readn;
        input integer n;
        integer j;
        begin
            cs_n = 0; #(4*HALF);
            for (j = 0; j < n; j = j + 1) begin xfer(8'h00, rx); got[j] = rx; end
            #(3*HALF); cs_n = 1; #(4*HALF);
        end
    endtask

    task wait_irq;
        input integer limit;
        begin
            cyc = 0;
            while (!irq && cyc < limit) begin @(posedge clk); cyc = cyc + 1; end
        end
    endtask

    function [15:0] crc16;            // CRC-16/CCITT-FALSE trên got[a..b]
        input integer a;
        input integer b;
        integer x, y;
        reg [15:0] r;
        begin
            r = 16'hFFFF;
            for (x = a; x <= b; x = x + 1) begin
                r = r ^ {got[x], 8'h00};
                for (y = 0; y < 8; y = y + 1) r = r[15] ? ((r << 1) ^ 16'h1021) : (r << 1);
            end
            crc16 = r;
        end
    endfunction

    task check;                       // so got[0..n-1] với kết quả e; good = 1: CYCLES và CRC đuôi kiểm riêng
        input integer e_idx;
        input integer n;
        input integer good;
        input [8*24-1:0] name;
        integer j;
        begin
            nbad = 0;
            for (j = 0; j < n; j = j + 1)
                if (!(good && j >= 15) && got[j] !== expv[e_idx*20 + j]) nbad = nbad + 1;
            if (good && n == 20) begin
                c = crc16(7, 17);
                if ({got[18], got[19]} !== c) nbad = nbad + 1;
                if (cyc0 === 24'hxxxxxx) cyc0 = {got[15], got[16], got[17]};
                if ({got[15], got[16], got[17]} !== cyc0) nbad = nbad + 1;
            end
            if (nbad != 0 || irq !== 1'b0) begin
                fails = fails + 1;
                $display("FAIL %0s: %0d byte sai, irq sau doc = %b; doc %h %h %h %h %h %h %h, mong doi %h %h %h %h %h %h %h",
                         name, nbad, irq, got[0], got[1], got[2], got[3], got[4], got[5], got[6],
                         expv[e_idx*20], expv[e_idx*20+1], expv[e_idx*20+2], expv[e_idx*20+3], expv[e_idx*20+4],
                         expv[e_idx*20+5], expv[e_idx*20+6]);
            end
        end
    endtask

    initial begin
        $readmemh("tb/proto_frames.mem", frames);
        $readmemh("tb/proto_exp.mem", expv);
        fails = 0; cyc0 = 24'hxxxxxx;
        #2000;

        // (0) chưa có kết quả
        readn(7);
        nbad = 0; for (i = 0; i < 7; i = i + 1) if (got[i] !== 8'h00) nbad = nbad + 1;
        if (nbad) begin fails = fails + 1; $display("FAIL doc khi chua co ket qua: MISO khac 0"); end
        else $display("(0) doc khi chua co ket qua: toan 0  PASS");

        // (1) NG khung đúng
        for (k = 0; k < NG; k = k + 1) begin
            send(k, 772);
            wait_irq(1000000);
            if (!irq) begin fails = fails + 1; $display("FAIL khung dung %0d: khong co IRQ", k); end
            else begin
                readn(20); repeat (10) @(posedge clk);
                check(k, 20, 1, "khung dung");
            end
        end
        $display("(1) %0d khung dung: xong, CYCLES = %0d, so loi den day = %0d", NG, cyc0, fails);

        // (2) CRC sai
        send(NG, 772); wait_irq(20000);
        if (!irq) begin fails = fails + 1; $display("FAIL CRC sai: khong co IRQ"); end
        else begin readn(20); repeat (10) @(posedge clk); check(NG, 20, 0, "CRC sai"); end
        $display("(2) CRC sai -> STATUS 0x00, CLASS 0xFF, IRQ sau %0d chu ky", cyc);

        // (3) khung thiếu byte: CS lên sau 302 byte
        send(NG + 1, 302); wait_irq(20000);
        if (!irq) begin fails = fails + 1; $display("FAIL khung thieu byte: khong co IRQ"); end
        else begin readn(20); repeat (10) @(posedge clk); check(NG + 1, 20, 0, "khung thieu byte"); end
        $display("(3) khung thieu byte -> STATUS 0x04");

        // (4) hai khung sát nhau
        send(NG + 2, 772);
        send(NG + 3, 772);
        wait_irq(20000);
        if (!irq) begin fails = fails + 1; $display("FAIL khung den khi ban: khong co IRQ"); end
        else begin readn(20); repeat (10) @(posedge clk); check(NG + 2, 20, 0, "khung den khi ban"); end
        // Engine nhanh hơn thời gian một khung (772 byte ở 4 MHz = 1,54 ms ≈ 77.000 chu kỳ): kết quả của khung trước xong
        // trong lúc khung sau còn đang truyền, rồi bị khung lỗi của khung sau thay thế (một bộ đệm kết quả, bản mới nhất
        // thắng — A.7). MCU không bao giờ gửi khung khi chưa nhận kết quả nên không gặp trường hợp này.
        if (cyc0 < 24'd77000) begin
            wait_irq(200000);
            if (irq) begin fails = fails + 1; $display("FAIL engine nhanh: khong mong doi them IRQ"); end
            $display("(4) hai khung sat nhau (engine %0d chu ky < 1 khung): khung sau STATUS 0x07; ket qua khung truoc bi thay the", cyc0);
        end else begin
            wait_irq(1000000);
            if (!irq) begin fails = fails + 1; $display("FAIL khung truoc do: khong co IRQ"); end
            else begin readn(20); repeat (10) @(posedge clk); check(NG + 3, 20, 1, "khung truoc khung ban"); end
            $display("(4) hai khung sat nhau: khung sau STATUS 0x07, khung truoc van ra ket qua dung");
        end

        // (5) byte đầu không phải 0xA5
        send(NG + 4, 772); wait_irq(50000);
        if (irq) begin fails = fails + 1; $display("FAIL byte dau 0x00: FPGA van tra ket qua"); end
        else $display("(5) byte dau khong phai 0xA5: bo qua, khong IRQ  PASS");

        // (6) chế độ RUN: đọc 7 byte
        send(NG + 5, 772); wait_irq(1000000);
        readn(6); repeat (10) @(posedge clk);          // mới 6 byte: IRQ phải còn cao (A.7: hạ sau byte thứ 7)
        if (irq !== 1'b1) begin fails = fails + 1; $display("FAIL IRQ ha truoc khi doc du 7 byte"); end
        readn(7); repeat (10) @(posedge clk);
        check(NG + 4, 7, 0, "doc 7 byte (RUN)");
        readn(20);
        nbad = 0; for (i = 0; i < 20; i = i + 1) if (got[i] !== 8'h00) nbad = nbad + 1;
        if (nbad) begin fails = fails + 1; $display("FAIL doc lai sau RUN: MISO khac 0"); end
        else $display("(6) RUN 7 byte: IRQ ve 0; doc lai -> toan 0  PASS");

        // (7) RST_N
        send(NG + 6, 772); wait_irq(1000000);
        rst_n = 0; #1000; rst_n = 1; #1000;
        if (irq) begin fails = fails + 1; $display("FAIL RST_N: IRQ khong ve 0"); end
        readn(7);
        nbad = 0; for (i = 0; i < 7; i = i + 1) if (got[i] !== 8'h00) nbad = nbad + 1;
        if (nbad) begin fails = fails + 1; $display("FAIL RST_N: MISO khac 0 sau reset"); end
        else $display("(7) RST_N: IRQ ve 0, MISO toan 0  PASS");

        $display("------------------------------------------------------------");
        if (fails == 0) $display("PASS");
        else            $display("FAIL: %0d loi", fails);
        $finish;
    end
endmodule
