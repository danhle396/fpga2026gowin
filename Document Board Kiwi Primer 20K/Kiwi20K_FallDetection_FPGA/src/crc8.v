module crc8 (
    input  wire [7:0] crc_in,
    input  wire [7:0] data_in,
    output reg  [7:0] crc_out
);

    integer i;
    reg [7:0] crc;

    always @(*) begin
        crc = crc_in ^ data_in;

        for (i = 0; i < 8; i = i + 1) begin
            if (crc[7])
                crc = (crc << 1) ^ 8'h07;
            else
                crc = crc << 1;
        end

        crc_out = crc;
    end

endmodule