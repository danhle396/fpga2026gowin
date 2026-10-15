module requantize_relu (
    input  wire signed [31:0] data_in,
    input  wire [4:0]         shift_amount,

    output reg signed [7:0]    data_out
);

    wire signed [31:0] shifted_value;

    assign shifted_value = data_in >>> shift_amount;

    always @(*) begin

        // ReLU
        if (data_in <= 0) begin

            data_out = 8'sd0;

        end
        else if (shifted_value > 32'sd127) begin

            data_out = 8'sd127;

        end
        else begin

            data_out = shifted_value[7:0];

        end

    end

endmodule