module conv1d_engine (
    input  wire                   clk,
    input  wire                   start,

    // 0 = Conv1: 6 -> 16, length 128
    // 1 = Conv2: 16 -> 32, length 64
    input  wire                   layer_sel,

    output reg                    busy = 0,
    output reg                    done = 0,

    // Input feature memory
    output reg  [9:0]             input_addr,
    input  wire signed [7:0]      input_data,

    // Weight ROM
    output reg  [11:0]            weight_addr,
    input  wire signed [7:0]      weight_data,

    // Bias ROM
    output reg  [5:0]             bias_addr,
    input  wire signed [31:0]     bias_data,

    // Shared MAC interface
    output wire                   mac_clear,
    output wire                   mac_enable,
    output wire signed [7:0]      mac_a,
    output wire signed [7:0]      mac_b,
    input  wire signed [31:0]     mac_accumulator,

    // Raw Conv output
    output reg  [10:0]            output_addr,
    output reg  signed [31:0]     output_data,
    output reg                    output_valid = 0
);

    localparam ST_IDLE   = 3'd0;
    localparam ST_CLEAR  = 3'd1;
    localparam ST_ISSUE  = 3'd2;
    localparam ST_WAIT   = 3'd3;
    localparam ST_MAC    = 3'd4;
    localparam ST_FINISH = 3'd5;

    reg [2:0] state = ST_IDLE;

    reg [7:0] pos_idx = 8'd0;
    reg [5:0] out_ch  = 6'd0;
    reg [5:0] in_ch   = 6'd0;
    reg [2:0] k_idx   = 3'd0;

    reg pad_zero = 1'b0;

    wire [7:0] active_length;
    wire [5:0] active_in_channels;
    wire [5:0] active_out_channels;

    assign active_length       = layer_sel ? 8'd64 : 8'd128;
    assign active_in_channels  = layer_sel ? 6'd16 : 6'd6;
    assign active_out_channels = layer_sel ? 6'd32 : 6'd16;

    wire [8:0] pos_plus_k;
    wire [8:0] sample_index;
    wire       sample_valid;

    assign pos_plus_k = {1'b0, pos_idx} + k_idx;

    assign sample_valid =
        (pos_plus_k >= 9'd2) &&
        (pos_plus_k < ({1'b0, active_length} + 9'd2));

    assign sample_index = pos_plus_k - 9'd2;

    // Shared MAC control
    assign mac_clear  = (state == ST_CLEAR);
    assign mac_enable = (state == ST_MAC);

    assign mac_a = pad_zero ? 8'sd0 : input_data;
    assign mac_b = weight_data;

    always @(posedge clk) begin

        done         <= 1'b0;
        output_valid <= 1'b0;

        case (state)

            ST_IDLE: begin
                busy <= 1'b0;

                if (start) begin
                    busy    <= 1'b1;

                    pos_idx <= 8'd0;
                    out_ch  <= 6'd0;
                    in_ch   <= 6'd0;
                    k_idx   <= 3'd0;

                    state <= ST_CLEAR;
                end
            end

            ST_CLEAR: begin
                in_ch <= 6'd0;
                k_idx <= 3'd0;

                state <= ST_ISSUE;
            end

            ST_ISSUE: begin

                if (!sample_valid) begin
                    pad_zero   <= 1'b1;
                    input_addr <= 10'd0;
                end
                else begin
                    pad_zero <= 1'b0;

                    if (!layer_sel) begin
                        // Conv1: sample * 6 + channel
                        input_addr <=
                            (sample_index * 10'd6) + in_ch;
                    end
                    else begin
                        // Conv2: sample * 16 + channel
                        input_addr <=
                            (sample_index * 10'd16) + in_ch;
                    end
                end

                if (!layer_sel) begin

                    // Conv1 weights: 0..479
                    weight_addr <=
                        (out_ch * 12'd30) +
                        (in_ch  * 12'd5) +
                        k_idx;

                    bias_addr <= out_ch;

                end
                else begin

                    // Conv2 weights: 480..3039
                    weight_addr <=
                        12'd480 +
                        (out_ch * 12'd80) +
                        (in_ch  * 12'd5) +
                        k_idx;

                    bias_addr <= 6'd16 + out_ch;

                end

                state <= ST_WAIT;
            end

            ST_WAIT: begin
                state <= ST_MAC;
            end

            ST_MAC: begin

                if (k_idx == 3'd4) begin

                    k_idx <= 3'd0;

                    if (in_ch == active_in_channels - 1'b1) begin
                        in_ch <= 6'd0;
                        state <= ST_FINISH;
                    end
                    else begin
                        in_ch <= in_ch + 1'b1;
                        state <= ST_ISSUE;
                    end

                end
                else begin

                    k_idx <= k_idx + 1'b1;
                    state <= ST_ISSUE;

                end
            end

            ST_FINISH: begin

                output_data <= mac_accumulator + bias_data;

                if (!layer_sel) begin
                    output_addr <=
                        (pos_idx * 11'd16) + out_ch;
                end
                else begin
                    output_addr <=
                        (pos_idx * 11'd32) + out_ch;
                end

                output_valid <= 1'b1;

                if (out_ch == active_out_channels - 1'b1) begin

                    out_ch <= 6'd0;

                    if (pos_idx == active_length - 1'b1) begin
                        pos_idx <= 8'd0;
                        busy    <= 1'b0;
                        done    <= 1'b1;
                        state   <= ST_IDLE;
                    end
                    else begin
                        pos_idx <= pos_idx + 1'b1;
                        state   <= ST_CLEAR;
                    end

                end
                else begin

                    out_ch <= out_ch + 1'b1;
                    state  <= ST_CLEAR;

                end
            end

            default: begin
                state <= ST_IDLE;
            end

        endcase
    end

endmodule