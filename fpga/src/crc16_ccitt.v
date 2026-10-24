// fpga/src/crc16_ccitt.v — một byte của CRC-16/CCITT-FALSE (A.7): đa thức 0x1021, MSB trước.
// Khởi tạo 0xFFFF ở module gọi. "123456789" -> 0x29B1. Tổ hợp thuần, giống crc16() của golden_model.py.
module crc16_ccitt (
    input  wire [15:0] crc_in,
    input  wire [7:0]  data_in,
    output reg  [15:0] crc_out
);
    integer i;
    reg [15:0] c;
    always @(*) begin
        c = crc_in ^ {data_in, 8'h00};
        for (i = 0; i < 8; i = i + 1)
            c = c[15] ? ((c << 1) ^ 16'h1021) : (c << 1);
        crc_out = c;
    end
endmodule
