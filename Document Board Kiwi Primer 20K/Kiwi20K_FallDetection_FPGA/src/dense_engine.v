module dense_engine (
    input  wire                   clk,
    input  wire                   start,

    output reg                    busy = 0,
    output reg                    done = 0,

    // GAP vector: 32 INT8 values
    output reg  [4:0]             input_addr,
    input  wire signed [7:0]      input_data,

    // Shared weight ROM
    output reg  [11:0]            weight_addr,
    input  wire signed [7:0]      weight_data,

    // Shared bias ROM
    output reg  [5:0]             bias_addr,
    input  wire signed [31:0]     bias_data,

    // Shared MAC interface
    output wire                   mac_clear,
    output wire                   mac_enable,
    output wire signed [7:0]      mac_a,
    output wire signed [7:0]      mac_b,
    input  wire signed [31:0]     mac_accumulator,

    // Four Dense logits
    output reg signed [31:0]       logit0,
    output reg signed [31:0]       logit1,
    output reg signed [31:0]       logit2,
    output reg signed [31:0]       logit3
);

    localparam ST_IDLE   = 3'd0;
    localparam ST_CLEAR  = 3'd1;
    localparam ST_ISSUE  = 3'd2;
    localparam ST_WAIT   = 3'd3;
    localparam ST_MAC    = 3'd4;
    localparam ST_FINISH = 3'd5;

    reg [2:0] state = ST_IDLE;

    reg [1:0] class_idx = 2'd0;
    reg [4:0] feature_idx = 5'd0;

    // ------------------------------------------------------------
    // Shared MAC control
    // ------------------------------------------------------------
    assign mac_clear  = (state == ST_CLEAR);
    assign mac_enable = (state == ST_MAC);

    assign mac_a = input_data;
    assign mac_b = weight_data;

    // ------------------------------------------------------------
    // Controller
    // ------------------------------------------------------------
    always @(posedge clk) begin

        done <= 1'b0;

        case (state)

            ST_IDLE: begin

                busy <= 1'b0;

                if (start) begin

                    busy        <= 1'b1;
                    class_idx   <= 2'd0;
                    feature_idx <= 5'd0;

                    state <= ST_CLEAR;

                end
            end

            // Clear accumulator before each class
            ST_CLEAR: begin

                feature_idx <= 5'd0;

                state <= ST_ISSUE;

            end

            // ----------------------------------------------------
            // Dense weight layout:
            //
            // 3040 ... 3071 = class 0
            // 3072 ... 3103 = class 1
            // 3104 ... 3135 = class 2
            // 3136 ... 3167 = class 3
            // ----------------------------------------------------
            ST_ISSUE: begin

                input_addr <= feature_idx;

                weight_addr <=
                    12'd3040 +
                    (class_idx * 12'd32) +
                    feature_idx;

                // Dense bias starts at 48
                bias_addr <=
                    6'd48 +
                    class_idx;

                // GAP buffer is synchronous,
                // so wait one clock
                state <= ST_WAIT;

            end

            ST_WAIT: begin

                state <= ST_MAC;

            end

            // ----------------------------------------------------
            // One MAC operation:
            // accumulator += input * weight
            // ----------------------------------------------------
            ST_MAC: begin

                if (feature_idx == 5'd31) begin

                    state <= ST_FINISH;

                end
                else begin

                    feature_idx <= feature_idx + 1'b1;

                    state <= ST_ISSUE;

                end
            end

            // ----------------------------------------------------
            // Save Dense result = accumulator + bias
            // ----------------------------------------------------
            ST_FINISH: begin

                case (class_idx)

                    2'd0:
                        logit0 <= mac_accumulator + bias_data;

                    2'd1:
                        logit1 <= mac_accumulator + bias_data;

                    2'd2:
                        logit2 <= mac_accumulator + bias_data;

                    2'd3:
                        logit3 <= mac_accumulator + bias_data;

                endcase

                if (class_idx == 2'd3) begin

                    busy <= 1'b0;
                    done <= 1'b1;

                    state <= ST_IDLE;

                end
                else begin

                    class_idx <= class_idx + 1'b1;

                    state <= ST_CLEAR;

                end

            end

            default: begin

                state <= ST_IDLE;

            end

        endcase
    end

endmodule