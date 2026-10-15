module packet_parser (
    input  wire       clk,

    input  wire [7:0] rx_data,
    input  wire       rx_valid,

    output reg  [7:0] sequence,

    output reg  [9:0] data_addr,
    output reg  [7:0] data_out,
    output reg        data_we = 0,

    output reg        payload_done = 0,
    output reg        crc_error = 0
);

    localparam WAIT_HEADER = 2'd0;
    localparam GET_SEQ     = 2'd1;
    localparam GET_DATA    = 2'd2;
    localparam WAIT_CRC    = 2'd3;

    reg [1:0] state = WAIT_HEADER;

    reg [9:0] byte_count = 10'd0;

    // Current CRC value
    reg  [7:0] crc_reg = 8'h00;
    wire [7:0] crc_next;

    // CRC-8:
    // Polynomial = 0x07
    // Initial    = 0x00
    crc8 u_crc8 (
        .crc_in  (crc_reg),
        .data_in (rx_data),
        .crc_out (crc_next)
    );

    always @(posedge clk) begin

        // Default: pulse signals stay low
        data_we      <= 1'b0;
        payload_done <= 1'b0;
        crc_error    <= 1'b0;

        if (rx_valid) begin

            case (state)

                // ------------------------------------------------
                // Wait for packet header 0xA5
                // ------------------------------------------------
                WAIT_HEADER: begin

                    if (rx_data == 8'hA5) begin
                        byte_count <= 10'd0;
                        crc_reg    <= 8'h00;
                        state      <= GET_SEQ;
                    end

                end

                // ------------------------------------------------
                // Receive Sequence byte
                // CRC starts from Sequence
                // ------------------------------------------------
                GET_SEQ: begin

                    sequence   <= rx_data;
                    crc_reg    <= crc_next;
                    byte_count <= 10'd0;

                    state <= GET_DATA;

                end

                // ------------------------------------------------
                // Receive 768 payload bytes
                // ------------------------------------------------
                GET_DATA: begin

                    data_addr <= byte_count;
                    data_out  <= rx_data;
                    data_we   <= 1'b1;

                    // Update CRC with every payload byte
                    crc_reg <= crc_next;

                    if (byte_count == 10'd767) begin

                        // 768 bytes received.
                        // Next byte is CRC from MCU.
                        state <= WAIT_CRC;

                    end
                    else begin

                        byte_count <= byte_count + 1'b1;

                    end

                end

                // ------------------------------------------------
                // Compare received CRC with calculated CRC
                // ------------------------------------------------
                WAIT_CRC: begin

                    if (rx_data == crc_reg) begin

                        // Packet is valid
                        payload_done <= 1'b1;

                    end
                    else begin

                        // CRC mismatch
                        crc_error <= 1'b1;

                    end

                    state <= WAIT_HEADER;

                end

                default: begin
                    state <= WAIT_HEADER;
                end

            endcase

        end
    end

endmodule