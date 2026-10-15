module argmax4 (
    input  wire               clk,

    input  wire signed [31:0] logit0,
    input  wire signed [31:0] logit1,
    input  wire signed [31:0] logit2,
    input  wire signed [31:0] logit3,

    output reg  [1:0]         class_id,
    output reg  signed [31:0] score
);

    // Two registered stages (pairwise, then final). Ties keep the lower index,
    // same result as the former combinational chain. Result is valid 2 clocks
    // after the logits settle; cnn_core delays inference_done accordingly.
    reg               a_sel, b_sel;
    reg signed [31:0] a_val, b_val;

    always @(posedge clk) begin

        a_sel <= (logit1 > logit0);
        a_val <= (logit1 > logit0) ? logit1 : logit0;

        b_sel <= (logit3 > logit2);
        b_val <= (logit3 > logit2) ? logit3 : logit2;

        if (b_val > a_val) begin
            class_id <= {1'b1, b_sel};
            score    <= b_val;
        end else begin
            class_id <= {1'b0, a_sel};
            score    <= a_val;
        end

    end

endmodule
