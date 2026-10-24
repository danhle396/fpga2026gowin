// fpga/src/result_frame_v3.v — dựng khung ĐỌC 20 byte của A.7 rồi bật IRQ:
//   0 0x5A | 1 SEQ | 2 STATUS | 3 CLASS | 4 SCORE | 5,6 CRC-16(0..4) | 7..14 4 logit INT16 BE | 15..17 CYCLES | 18,19 CRC-16(7..17)
// SCORE = clamp((top1 − top2) >> SCORE_SHIFT, 0, 127), top1 = logit của lớp argmax (bằng nhau → chỉ số nhỏ, đã có ở
// argmax4). Logit gỡ lỗi = clamp(logit >> LOGIT_SHIFT, −32768, 32767) (A.5). Khung lỗi: CLASS 0xFF, SCORE 0, đuôi 0.
// CRC tính tuần tự 1 byte/chu kỳ (16 chu kỳ) để khỏi có chuỗi XOR dài; IRQ lên khi khung xong.
module result_frame_v3 #(
    parameter SCORE_SHIFT = 0,
    parameter LOGIT_SHIFT = 0
) (
    input  wire               clk,
    input  wire               rst,
    input  wire               done,          // xung: suy luận xong
    input  wire [1:0]         class_id,
    input  wire signed [31:0] logit0, logit1, logit2, logit3,
    input  wire [23:0]        cycles,
    input  wire [7:0]         seq_ok,        // SEQ của khung đã suy luận
    input  wire               err,           // xung: khung ghi hỏng
    input  wire [2:0]         err_status,
    input  wire [7:0]         seq_err,
    input  wire [4:0]         rd_index,      // byte đang được spi_result_tx_v3 đọc
    output wire [7:0]         rd_byte,
    input  wire               read_done,     // MCU đã đọc xong byte thứ 7
    output reg                valid = 1'b0,
    output reg                irq = 1'b0
);
    reg [7:0] f [0:19];
    reg [4:0] step = 5'd0;
    reg       building = 1'b0;
    reg [15:0] crc = 16'hFFFF;
    reg signed [31:0] top2;
    reg [1:0]  cls;
    reg signed [31:0] lg [0:3];
    reg [2:0]  phase = 3'd0;
    reg        pend_done = 1'b0, pend_err = 1'b0;   // đến lúc đang dựng khung khác: làm sau
    wire [15:0] crc_next;
    wire       go_done = (done || pend_done) && !building;
    wire       go_err  = (err || pend_err) && !building && !go_done;
    integer i;

    assign rd_byte = (rd_index < 5'd20) ? f[rd_index] : 8'h00;

    // byte đang đưa vào CRC: 0..4 rồi 7..17
    wire [4:0] crc_idx = (step < 5'd5) ? step : step + 5'd2;
    crc16_ccitt u_crc (.crc_in(crc), .data_in(f[crc_idx]), .crc_out(crc_next));

    function [15:0] sat16;
        input signed [31:0] v;
        reg signed [31:0] s;
        begin
            s = v >>> LOGIT_SHIFT;
            if (s > 32767)        sat16 = 16'h7FFF;
            else if (s < -32768)  sat16 = 16'h8000;
            else                  sat16 = s[15:0];
        end
    endfunction

    function [7:0] score_of;
        input signed [31:0] top1;
        input signed [31:0] second;
        reg [32:0] d;
        begin
            d = ({top1[31], top1} - {second[31], second}) >> SCORE_SHIFT;   // top1 ≥ second nên d ≥ 0
            score_of = (d > 33'd127) ? 8'd127 : d[7:0];
        end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            valid <= 1'b0; irq <= 1'b0; building <= 1'b0; phase <= 3'd0; pend_done <= 1'b0; pend_err <= 1'b0;
        end else begin
            if (done && building) pend_done <= 1'b1;
            if (err && (building || go_done)) pend_err <= 1'b1;
            if (read_done) begin
                valid <= 1'b0;
                irq   <= 1'b0;
            end
            if (go_done) begin
                pend_done <= 1'b0;
                // pha 0: chốt đầu vào; pha 1..4: tìm top2; pha 5: điền byte; rồi 16 bước CRC
                lg[0] <= logit0; lg[1] <= logit1; lg[2] <= logit2; lg[3] <= logit3;
                cls   <= class_id;
                f[0] <= 8'h5A; f[1] <= seq_ok; f[2] <= 8'h01; f[3] <= {6'd0, class_id};
                f[15] <= cycles[23:16]; f[16] <= cycles[15:8]; f[17] <= cycles[7:0];
                top2  <= 32'sh80000000;
                building <= 1'b1; phase <= 3'd1; step <= 5'd0; valid <= 1'b0; irq <= 1'b0;
            end else if (go_err) begin
                pend_err <= 1'b0;
                f[0] <= 8'h5A; f[1] <= seq_err; f[2] <= {5'd0, err_status}; f[3] <= 8'hFF; f[4] <= 8'h00;
                for (i = 7; i < 18; i = i + 1) f[i] <= 8'h00;
                building <= 1'b1; phase <= 3'd6; step <= 5'd0; crc <= 16'hFFFF; valid <= 1'b0; irq <= 1'b0;
            end else if (building) begin
                if (phase >= 3'd1 && phase <= 3'd4) begin
                    if (phase - 3'd1 != {1'b0, cls} && lg[phase - 3'd1] > top2) top2 <= lg[phase - 3'd1];
                    phase <= phase + 3'd1;
                end else if (phase == 3'd5) begin
                    f[4]  <= score_of(lg[cls], top2);
                    {f[7],  f[8]}  <= sat16(lg[0]);
                    {f[9],  f[10]} <= sat16(lg[1]);
                    {f[11], f[12]} <= sat16(lg[2]);
                    {f[13], f[14]} <= sat16(lg[3]);
                    crc <= 16'hFFFF;
                    phase <= 3'd6;
                end else begin                                   // phase 6: CRC
                    if (step == 5'd4) begin
                        f[5] <= crc_next[15:8]; f[6] <= crc_next[7:0];
                        crc <= 16'hFFFF;
                    end else if (step == 5'd15) begin
                        f[18] <= crc_next[15:8]; f[19] <= crc_next[7:0];
                        building <= 1'b0; phase <= 3'd0;
                        valid <= 1'b1; irq <= 1'b1;
                    end else begin
                        crc <= crc_next;
                    end
                    step <= step + 5'd1;
                end
            end
        end
    end
endmodule
