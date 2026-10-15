module spi_slave (
    input  wire       sys_clk,

    input  wire       spi_sclk,
    input  wire       spi_cs_n,
    input  wire       spi_mosi,


    output reg [7:0]  rx_data,
    output reg        rx_valid = 0
);

    reg [2:0] sclk_sync = 3'b000;
    reg [2:0] cs_sync   = 3'b111;
    reg [2:0] mosi_sync = 3'b000;

    reg [7:0] rx_shift = 8'd0;
    reg [2:0] bit_count = 3'd0;

    wire sclk_rising;

    // Synchronize SPI signals to FPGA system clock
    always @(posedge sys_clk) begin
        sclk_sync <= {sclk_sync[1:0], spi_sclk};
        cs_sync   <= {cs_sync[1:0], spi_cs_n};
        mosi_sync <= {mosi_sync[1:0], spi_mosi};
    end

    // Detect rising edge of SPI clock
    assign sclk_rising = (sclk_sync[2:1] == 2'b01);


    // SPI receive logic
    always @(posedge sys_clk) begin
        rx_valid <= 1'b0;

        if (cs_sync[2]) begin
            bit_count <= 3'd0;
        end
        else if (sclk_rising) begin
            rx_shift <= {rx_shift[6:0], mosi_sync[2]};

            if (bit_count == 3'd7) begin
                rx_data <= {rx_shift[6:0], mosi_sync[2]};
                rx_valid <= 1'b1;
                bit_count <= 3'd0;
            end
            else begin
                bit_count <= bit_count + 1'b1;
            end
        end
    end

endmodule