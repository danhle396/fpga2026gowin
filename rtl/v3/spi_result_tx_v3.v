// rtl/v3/spi_result_tx_v3.v — phát khung ĐỌC 20 byte (A.7) trên MISO, SPI mode 0, MSB trước.
// Bắt đầu khi CS xuống và có kết quả (valid); không có kết quả thì MISO = 0 suốt giao dịch.
// read_done phát khi byte thứ 7 (chỉ số 6) đã đẩy xong: IRQ về thấp (A.7); byte 7..19 vẫn tiếp tục nếu MCU còn clock (HIL).
// rd_index trỏ trước tới byte KẾ TIẾP, nên ở cạnh xuống SCK cuối của một byte, byte mới nạp ngay trong cùng chu kỳ:
// MISO đổi sau cạnh xuống ≈ 3 chu kỳ clock hệ thống như bản PROTO 1 (R11), vì vậy SCK ≤ 4 MHz.
module spi_result_tx_v3 (
    input  wire       sys_clk,
    input  wire       rst,
    input  wire       spi_sclk,
    input  wire       spi_cs_n,
    input  wire       result_valid,
    output reg  [4:0] rd_index = 5'd0,
    input  wire [7:0] rd_byte,
    output reg        spi_miso = 1'b0,
    output reg        read_done = 1'b0
);
    reg [2:0] sclk_sync = 3'b000;
    reg [2:0] cs_sync   = 3'b111;
    reg       active = 1'b0;
    reg       primed = 1'b0;
    reg [2:0] bit_index = 3'd0;
    reg [4:0] byte_cnt = 5'd0;
    reg [7:0] shift_reg = 8'd0;

    wire sclk_falling = (sclk_sync[2:1] == 2'b10);
    wire cs_falling   = (cs_sync[2:1] == 2'b10);

    always @(posedge sys_clk) begin
        sclk_sync <= {sclk_sync[1:0], spi_sclk};
        cs_sync   <= {cs_sync[1:0], spi_cs_n};
        read_done <= 1'b0;
        if (rst) begin
            active <= 1'b0; primed <= 1'b0; spi_miso <= 1'b0;
        end else if (cs_falling) begin
            active    <= result_valid;
            primed    <= result_valid;
            rd_index  <= 5'd0;
            byte_cnt  <= 5'd0;
            bit_index <= 3'd0;
            spi_miso  <= 1'b0;
        end else if (cs_sync[2]) begin
            active   <= 1'b0;
            primed   <= 1'b0;
            spi_miso <= 1'b0;
        end else if (primed) begin                      // chu kỳ ngay sau CS xuống: nạp byte 0
            shift_reg <= rd_byte;
            spi_miso  <= rd_byte[7];
            rd_index  <= 5'd1;
            primed    <= 1'b0;
        end else if (active && sclk_falling) begin
            if (bit_index == 3'd7) begin
                bit_index <= 3'd0;
                if (byte_cnt == 5'd6) read_done <= 1'b1;
                if (byte_cnt == 5'd19) begin
                    active   <= 1'b0;
                    spi_miso <= 1'b0;
                end else begin
                    byte_cnt  <= byte_cnt + 5'd1;
                    shift_reg <= rd_byte;               // rd_index đã trỏ sẵn byte kế
                    spi_miso  <= rd_byte[7];
                    rd_index  <= rd_index + 5'd1;
                end
            end else begin
                shift_reg <= {shift_reg[6:0], 1'b0};
                spi_miso  <= shift_reg[6];
                bit_index <= bit_index + 3'd1;
            end
        end
    end
endmodule
