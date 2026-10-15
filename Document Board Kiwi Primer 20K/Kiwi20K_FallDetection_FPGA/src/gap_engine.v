module gap_engine (
    input  wire                   clk,
    input  wire                   start,

    output reg                    busy = 0,
    output reg                    done = 0,

    // Pool2 feature RAM: 32 positions x 32 channels
    output reg  [9:0]             input_addr,
    input  wire signed [7:0]      input_data,

    // GAP output: 32 values, one per channel
    output reg  [4:0]             output_addr,
    output reg  signed [7:0]      output_data,
    output reg                    output_valid = 0
);

    localparam ST_IDLE   = 2'd0;
    localparam ST_ISSUE  = 2'd1;
    localparam ST_WAIT   = 2'd2;
    localparam ST_ACCUM  = 2'd3;

    reg [1:0] state = ST_IDLE;

    reg [4:0] channel = 5'd0;
    reg [4:0] pos     = 5'd0;

    reg signed [31:0] sum = 32'sd0;

    wire signed [31:0] sum_with_last;
    wire signed [31:0] average_value;

    assign sum_with_last =
        sum + {{24{input_data[7]}}, input_data};

    assign average_value =
        sum_with_last >>> 5;

    always @(posedge clk) begin

        done         <= 1'b0;
        output_valid <= 1'b0;

        case (state)

            ST_IDLE: begin
                busy <= 1'b0;

                if (start) begin
                    busy    <= 1'b1;
                    channel <= 5'd0;
                    pos     <= 5'd0;
                    sum     <= 32'sd0;

                    state <= ST_ISSUE;
                end
            end

            // Address layout:
            // address = position * 32 + channel
            ST_ISSUE: begin

                input_addr <=
                    (pos * 10'd32) + channel;

                state <= ST_WAIT;
            end

            // One clock wait for synchronous RAM
            ST_WAIT: begin
                state <= ST_ACCUM;
            end

            ST_ACCUM: begin

                if (pos == 5'd31) begin

                    // Include the last value then divide by 32.
                    // Division by 32 = arithmetic shift right 5.
                    output_data <= average_value[7:0];

                    output_addr  <= channel;
                    output_valid <= 1'b1;

                    sum <= 32'sd0;
                    pos <= 5'd0;

                    if (channel == 5'd31) begin

                        channel <= 5'd0;
                        busy    <= 1'b0;
                        done    <= 1'b1;

                        state <= ST_IDLE;

                    end
                    else begin

                        channel <= channel + 1'b1;
                        state   <= ST_ISSUE;

                    end

                end
                else begin

                    sum <= sum + input_data;
                    pos <= pos + 1'b1;

                    state <= ST_ISSUE;

                end
            end

            default: begin
                state <= ST_IDLE;
            end

        endcase
    end

endmodule