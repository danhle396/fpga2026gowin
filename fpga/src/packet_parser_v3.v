// fpga/src/packet_parser_v3.v — nhận khung GHI của giao thức v3 (A.7): [A5][SEQ][768 byte][CRC-16 hi][lo] trong MỘT
// lần CS thấp. Sửa R3, R4, R5 của bản PROTO 1:
//   R3: 0xA5 phải là byte đầu sau khi CS xuống; CS lên giữa khung = khung thiếu byte, quay về chờ đầu khung.
//   R4: khung đến khi CNN đang bận không được ghi vào bộ đệm (đang bị đọc); báo BUSY + ERR.
//   R5: mọi kết cục của một khung đều phát một xung: payload_done (CRC đúng, không bận) hoặc frame_err + status.
// STATUS (A.7): bit0 CRC_OK, bit1 BUSY, bit2 ERR. Hợp lệ = 0x01.
module packet_parser_v3 (
    input  wire       clk,
    input  wire       rst,
    input  wire       cs_n,          // chân CS (chưa đồng bộ)
    input  wire [7:0] rx_data,
    input  wire       rx_valid,
    input  wire       busy,          // CNN đang chạy
    output reg  [7:0] sequence,
    output reg  [9:0] data_addr,
    output reg  [7:0] data_out,
    output reg        data_we = 0,
    output reg        payload_done = 0,  // khung đúng: bắt đầu suy luận
    output reg        frame_err = 0,     // khung hỏng: dựng khung kết quả lỗi
    output reg  [2:0] err_status
);
    localparam S_FIRST = 3'd0, S_SEQ = 3'd1, S_DATA = 3'd2, S_CRC_HI = 3'd3, S_CRC_LO = 3'd4, S_IGNORE = 3'd5;

    reg [2:0]  state = S_IGNORE;
    reg [9:0]  count = 10'd0;
    reg [15:0] crc = 16'hFFFF;
    reg [7:0]  crc_hi = 8'h00;
    reg        was_busy = 1'b0;
    reg [2:0]  cs_sync = 3'b111;
    wire [15:0] crc_next;

    crc16_ccitt u_crc (.crc_in(crc), .data_in(rx_data), .crc_out(crc_next));

    wire cs_fall = (cs_sync[2:1] == 2'b10);
    wire cs_rise = (cs_sync[2:1] == 2'b01);

    always @(posedge clk) begin
        cs_sync      <= {cs_sync[1:0], cs_n};
        data_we      <= 1'b0;
        payload_done <= 1'b0;
        frame_err    <= 1'b0;
        if (rst) begin
            state <= S_IGNORE;
        end else if (cs_fall) begin
            state <= S_FIRST;
            crc   <= 16'hFFFF;
        end else if (cs_rise) begin
            if (state == S_SEQ || state == S_DATA || state == S_CRC_HI || state == S_CRC_LO) begin
                frame_err  <= 1'b1;                          // thiếu byte
                err_status <= 3'b100;
            end
            state <= S_IGNORE;
        end else if (rx_valid) begin
            case (state)
            S_FIRST: begin
                if (rx_data == 8'hA5) begin
                    crc      <= crc_next;                    // CRC tính cả 0xA5 (A.7: byte 0..769)
                    was_busy <= busy;
                    state    <= S_SEQ;
                end else begin
                    state <= S_IGNORE;                       // ví dụ giao dịch ĐỌC: MCU gửi 0x00
                end
            end
            S_SEQ: begin
                sequence <= rx_data;
                crc      <= crc_next;
                count    <= 10'd0;
                state    <= S_DATA;
            end
            S_DATA: begin
                crc <= crc_next;
                if (!was_busy && !busy) begin
                    data_addr <= count;
                    data_out  <= rx_data;
                    data_we   <= 1'b1;
                end
                if (busy) was_busy <= 1'b1;
                if (count == 10'd767) state <= S_CRC_HI;
                count <= count + 10'd1;
            end
            S_CRC_HI: begin
                crc_hi <= rx_data;
                state  <= S_CRC_LO;
            end
            S_CRC_LO: begin
                if (was_busy) begin
                    frame_err  <= 1'b1;
                    err_status <= {2'b11, ({crc_hi, rx_data} == crc)};
                end else if ({crc_hi, rx_data} == crc) begin
                    payload_done <= 1'b1;
                end else begin
                    frame_err  <= 1'b1;
                    err_status <= 3'b000;                    // CRC sai: CRC_OK = 0
                end
                state <= S_IGNORE;                           // byte thừa trong cùng lần CS bị bỏ qua
            end
            default: ;
            endcase
        end
    end
endmodule
