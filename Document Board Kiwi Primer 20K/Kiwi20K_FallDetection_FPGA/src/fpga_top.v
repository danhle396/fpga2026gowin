`include "cnn_params.vh"   // generated from quant_params.json by tools/gen_cnn_params.py

module fpga_top (
    input  wire clk,

    input  wire spi_sclk,
    input  wire spi_cs_n,
    input  wire spi_mosi,
    output wire spi_miso,
    output wire irq
);

    // Clock ~50 MHz generated from 27 MHz board clock
    wire clk_50m;

    pll_50m u_pll (
        .clkout(clk_50m),
        .clkin (clk)
    );

    // SPI signals
    wire [7:0] spi_rx_data;
    wire       spi_rx_valid;

    spi_slave u_spi_slave (
        .sys_clk  (clk_50m),
        .spi_sclk (spi_sclk),
        .spi_cs_n (spi_cs_n),
        .spi_mosi (spi_mosi),

        .rx_data  (spi_rx_data),
        .rx_valid (spi_rx_valid)
    );


    // Packet_parser
    wire [7:0] sequence;

    wire [9:0] payload_addr;
    wire [7:0] payload_data;
    wire       payload_we;
    wire       payload_done;
    wire       crc_error;

    packet_parser u_packet_parser (
        .clk          (clk_50m),

        .rx_data      (spi_rx_data),
        .rx_valid     (spi_rx_valid),

        .sequence     (sequence),

        .data_addr    (payload_addr),
        .data_out     (payload_data),
        .data_we      (payload_we),

        .payload_done (payload_done),
        .crc_error    (crc_error)
    );


    // Input_buffer
    wire [9:0] cnn_read_addr;
    wire signed [7:0] cnn_read_data;

    input_buffer u_input_buffer (
        .clk        (clk_50m),

        .we         (payload_we),
        .write_addr (payload_addr),
        .write_data (payload_data),

        .read_addr  (cnn_read_addr),
        .read_data  (cnn_read_data)
    );


    // CNN Core
    wire        cnn_busy;
    wire        cnn_done;

    wire [1:0]  cnn_class;
    wire signed [31:0] cnn_score;

    cnn_core u_cnn_core (
        .clk             (clk_50m),

        // Start inference only after a valid packet + CRC
        .start           (payload_done),

        .input_read_addr (cnn_read_addr),
        .input_read_data (cnn_read_data),

        // Quantization shifts: single source = quant_params.json (RA-01).
        .conv1_shift     (`CNN_CONV1_SHIFT),
        .conv2_shift     (`CNN_CONV2_SHIFT),

        .busy            (cnn_busy),
        .inference_done  (cnn_done),

        .class_id        (cnn_class),
        .score           (cnn_score),

        // 4 logit are only used by the protocol v3 top (rtl/v3/fpga_top_v3.v); unused in PROTO 1
        .logit0_out      (),
        .logit1_out      (),
        .logit2_out      (),
        .logit3_out      ()
    );


    // CNN Result Register + IRQ
    wire [1:0] result_class;
    wire signed [31:0] result_score;
    wire result_valid;

    // SPI transmit block will generate this later
    wire result_read_done;

    result_register u_result_register (
        .clk             (clk_50m),

        .inference_done  (cnn_done),
        .class_in        (cnn_class),
        .score_in        (cnn_score),

        .read_done       (result_read_done),

        .class_out       (result_class),
        .score_out       (result_score),
        .valid           (result_valid),
        .irq             (irq)
    );


    // SPI Result Transmitter
    spi_result_tx u_spi_result_tx (
        .sys_clk      (clk_50m),

        .spi_sclk     (spi_sclk),
        .spi_cs_n     (spi_cs_n),

        .result_valid (result_valid),
        .class_id     (result_class),
        .score        (result_score),

        .spi_miso     (spi_miso),
        .read_done    (result_read_done)
    );
endmodule