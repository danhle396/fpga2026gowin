module maxpool1d_engine (
    input  wire                   clk,
    input  wire                   start,

    // 0 = Pool1: 128x16 -> 64x16
    // 1 = Pool2:  64x32 -> 32x32
    input  wire                   layer_sel,

    output reg                    busy = 0,
    output reg                    done = 0,

    // Input feature-map memory
    output reg  [10:0]            input_addr,
    input  wire signed [7:0]      input_data,

    // Output feature-map memory
    output reg  [9:0]             output_addr,
    output reg  signed [7:0]      output_data,
    output reg                    output_valid = 0
);

    localparam ST_IDLE     = 3'd0;
    localparam ST_ISSUE0   = 3'd1;
    localparam ST_WAIT0    = 3'd2;
    localparam ST_CAPTURE0 = 3'd3;
    localparam ST_ISSUE1   = 3'd4;
    localparam ST_WAIT1    = 3'd5;
    localparam ST_WRITE    = 3'd6;

    reg [2:0] state = ST_IDLE;

    reg [6:0] pool_pos = 7'd0;
    reg [5:0] channel  = 6'd0;

    reg signed [7:0] sample0;

    wire [6:0] output_length;
    wire [5:0] channels;

    assign output_length = layer_sel ? 7'd32 : 7'd64;
    assign channels      = layer_sel ? 6'd32 : 6'd16;

    always @(posedge clk) begin

        done         <= 1'b0;
        output_valid <= 1'b0;

        case (state)

            ST_IDLE: begin
                busy <= 1'b0;

                if (start) begin
                    busy     <= 1'b1;
                    pool_pos <= 7'd0;
                    channel  <= 6'd0;

                    state <= ST_ISSUE0;
                end
            end

            // Read first sample of pooling pair
            ST_ISSUE0: begin

                if (!layer_sel) begin
                    // Pool1 input layout:
                    // sample * 16 + channel
                    input_addr <=
                        ((pool_pos << 1) * 11'd16) +
                        channel;
                end
                else begin
                    // Pool2 input layout:
                    // sample * 32 + channel
                    input_addr <=
                        ((pool_pos << 1) * 11'd32) +
                        channel;
                end

                state <= ST_WAIT0;
            end

            // Wait for synchronous RAM
            ST_WAIT0: begin
                state <= ST_CAPTURE0;
            end

            ST_CAPTURE0: begin
                sample0 <= input_data;

                state <= ST_ISSUE1;
            end

            // Read second sample
            ST_ISSUE1: begin

                if (!layer_sel) begin

                    input_addr <=
                        (((pool_pos << 1) + 1'b1) * 11'd16) +
                        channel;

                end
                else begin

                    input_addr <=
                        (((pool_pos << 1) + 1'b1) * 11'd32) +
                        channel;

                end

                state <= ST_WAIT1;
            end

            ST_WAIT1: begin
                state <= ST_WRITE;
            end

            // Compare the two samples
            ST_WRITE: begin

                if (sample0 >= input_data)
                    output_data <= sample0;
                else
                    output_data <= input_data;

                // position-major output
                if (!layer_sel) begin
                    // 64 x 16
                    output_addr <=
                        (pool_pos * 10'd16) +
                        channel;
                end
                else begin
                    // 32 x 32
                    output_addr <=
                        (pool_pos * 10'd32) +
                        channel;
                end

                output_valid <= 1'b1;

                // Next channel / pooling position
                if (channel == channels - 1'b1) begin

                    channel <= 6'd0;

                    if (pool_pos == output_length - 1'b1) begin

                        pool_pos <= 7'd0;
                        busy     <= 1'b0;
                        done     <= 1'b1;
                        state    <= ST_IDLE;

                    end
                    else begin

                        pool_pos <= pool_pos + 1'b1;
                        state    <= ST_ISSUE0;

                    end

                end
                else begin

                    channel <= channel + 1'b1;
                    state   <= ST_ISSUE0;

                end
            end

            default: begin
                state <= ST_IDLE;
            end

        endcase
    end

endmodule