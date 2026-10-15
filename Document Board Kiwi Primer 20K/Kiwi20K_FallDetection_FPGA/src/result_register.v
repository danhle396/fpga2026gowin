module result_register (
    input  wire                    clk,

    // CNN finished
    input  wire                    inference_done,
    input  wire [1:0]              class_in,
    input  wire signed [31:0]      score_in,

    // Will come from SPI TX after MCU reads result
    input  wire                    read_done,

    output reg  [1:0]              class_out = 2'd0,
    output reg  signed [31:0]      score_out = 32'sd0,
    output reg                     valid = 1'b0,
    output reg                     irq = 1'b0
);

    always @(posedge clk) begin

        // MCU has finished reading result
        if (read_done) begin
            valid <= 1'b0;
            irq   <= 1'b0;
        end

        // CNN has produced a new result
        if (inference_done) begin
            class_out <= class_in;
            score_out <= score_in;

            valid <= 1'b1;
            irq   <= 1'b1;
        end

    end

endmodule