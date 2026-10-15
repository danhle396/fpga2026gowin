// rtl/pin_probe/pin_probe_top.v — dò vị trí 6 chân J1-3 .. J1-8 của Kiwi Primer 20K trước khi nối dây
// (PROJECT_MASTER.md, Phụ lục E.4). Chân probe[k] phát k+1 xung 1 kHz trong mỗi khung 8 ms:
// đo bằng logic analyzer thì đếm xung, đo bằng đồng hồ DC thì thấy khoảng (k+1) x 0,21 V.
// LED1 trên board nháy khoảng 0,8 Hz để biết bitstream đang chạy.
module pin_probe_top (
    input  wire       clk,      // 27 MHz
    output reg  [5:0] probe,
    output wire       led_n     // mức thấp = sáng
);
    parameter HALF = 13500;     // 0,5 ms ở 27 MHz

    reg [13:0] div  = 0;
    reg [3:0]  slot = 0;        // 16 nửa chu kỳ = 8 ms
    reg [24:0] beat = 0;

    wire tick = (div == HALF - 1);
    integer k;

    always @(posedge clk) begin
        div  <= tick ? 14'd0 : div + 14'd1;
        beat <= beat + 25'd1;
        if (tick) begin
            slot <= slot + 4'd1;
            for (k = 0; k < 6; k = k + 1)
                probe[k] <= slot[0] && (slot[3:1] <= k);
        end
    end

    assign led_n = beat[24];
endmodule
