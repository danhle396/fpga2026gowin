module mac_unit (
    input  wire                   clk,
    input  wire                   clear,
    input  wire                   enable,

    input  wire signed [7:0]      data_a,
    input  wire signed [7:0]      data_b,

    output reg  signed [31:0]     accumulator
);

    wire signed [15:0] product;

    assign product = data_a * data_b;

    always @(posedge clk) begin

        if (clear) begin
            accumulator <= 32'sd0;
        end

        else if (enable) begin
            accumulator <= accumulator + product;
        end

    end

endmodule