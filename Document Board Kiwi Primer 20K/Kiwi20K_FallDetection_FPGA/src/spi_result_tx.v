module spi_result_tx (
    input  wire                   sys_clk,

    input  wire                   spi_sclk,
    input  wire                   spi_cs_n,

    input  wire                   result_valid,
    input  wire [1:0]             class_id,
    input  wire signed [31:0]     score,

    output reg                    spi_miso,
    output reg                    read_done = 0
);

    // Synchronize external SPI signals
    reg [2:0] sclk_sync = 3'b000;
    reg [2:0] cs_sync   = 3'b111;

    always @(posedge sys_clk) begin
        sclk_sync <= {sclk_sync[1:0], spi_sclk};
        cs_sync   <= {cs_sync[1:0], spi_cs_n};
    end

    wire sclk_falling;
    wire cs_falling;

    assign sclk_falling = (sclk_sync[2:1] == 2'b10);
    assign cs_falling   = (cs_sync[2:1]   == 2'b10);


    // ============================================================
    // CRC-8 function
    // Poly = 0x07, Init = 0x00
    // ============================================================

    function [7:0] crc8_update;

        input [7:0] crc_in;
        input [7:0] data_in;

        integer i;
        reg [7:0] crc;

        begin

            crc = crc_in ^ data_in;

            for (i = 0; i < 8; i = i + 1) begin

                if (crc[7])
                    crc = (crc << 1) ^ 8'h07;
                else
                    crc = crc << 1;

            end

            crc8_update = crc;

        end

    endfunction


    wire [7:0] class_byte;

    assign class_byte = {6'b000000, class_id};


    // CRC excludes header 0x5A.
    wire [7:0] crc1;
    wire [7:0] crc2;
    wire [7:0] crc3;
    wire [7:0] crc4;
    wire [7:0] result_crc;

    assign crc1 =
        crc8_update(8'h00, class_byte);

    assign crc2 =
        crc8_update(crc1, score[31:24]);

    assign crc3 =
        crc8_update(crc2, score[23:16]);

    assign crc4 =
        crc8_update(crc3, score[15:8]);

    assign result_crc =
        crc8_update(crc4, score[7:0]);


    // ============================================================
    // TX state
    //
    // Packet:
    //
    // byte 0 = 0x5A
    // byte 1 = Class
    // byte 2 = Score[31:24]
    // byte 3 = Score[23:16]
    // byte 4 = Score[15:8]
    // byte 5 = Score[7:0]
    // byte 6 = CRC8
    //
    // Total = 7 bytes
    // ============================================================

    reg       active = 1'b0;

    reg [2:0] byte_index = 3'd0;
    reg [2:0] bit_index  = 3'd0;

    reg [7:0] shift_reg = 8'd0;


    always @(posedge sys_clk) begin

        read_done <= 1'b0;


        // --------------------------------------------------------
        // MCU starts SPI transaction after IRQ
        // --------------------------------------------------------
        if (cs_falling && result_valid) begin

            active     <= 1'b1;

            byte_index <= 3'd0;
            bit_index  <= 3'd0;

            shift_reg  <= 8'h5A;

            // MSB of 0x5A
            spi_miso   <= 1'b0;

        end


        // --------------------------------------------------------
        // Shift data on falling edge.
        // MCU samples on rising edge (SPI Mode 0).
        // --------------------------------------------------------
        else if (active && sclk_falling) begin

            if (bit_index == 3'd7) begin

                bit_index <= 3'd0;

                // Last byte finished
                if (byte_index == 3'd6) begin

                    active    <= 1'b0;
                    read_done <= 1'b1;
                    spi_miso  <= 1'b0;

                end

                else begin

                    byte_index <= byte_index + 1'b1;

                    // Load next byte
                    case (byte_index)

                        // Header finished -> Class
                        3'd0: begin
                            shift_reg <= class_byte;
                            spi_miso  <= class_byte[7];
                        end

                        // Class finished -> Score[31:24]
                        3'd1: begin
                            shift_reg <= score[31:24];
                            spi_miso  <= score[31];
                        end

                        3'd2: begin
                            shift_reg <= score[23:16];
                            spi_miso  <= score[23];
                        end

                        3'd3: begin
                            shift_reg <= score[15:8];
                            spi_miso  <= score[15];
                        end

                        3'd4: begin
                            shift_reg <= score[7:0];
                            spi_miso  <= score[7];
                        end

                        // Score finished -> CRC
                        3'd5: begin
                            shift_reg <= result_crc;
                            spi_miso  <= result_crc[7];
                        end

                        default: begin
                            shift_reg <= 8'h00;
                            spi_miso  <= 1'b0;
                        end

                    endcase

                end

            end

            else begin

                shift_reg <= {shift_reg[6:0], 1'b0};

                spi_miso <= shift_reg[6];

                bit_index <= bit_index + 1'b1;

            end

        end


        // CS released early / idle
        if (cs_sync[2] && !cs_falling && !active)
            spi_miso <= 1'b0;

    end

endmodule