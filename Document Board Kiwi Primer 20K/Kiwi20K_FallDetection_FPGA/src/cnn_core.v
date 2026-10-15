module cnn_core (
    input  wire                   clk,
    input  wire                   start,

    // Input buffer containing 6 x 128 INT8
    output wire [9:0]             input_read_addr,
    input  wire signed [7:0]      input_read_data,

    // Requantization parameters
    // Will be replaced by actual values from trained model
    input  wire [4:0]             conv1_shift,
    input  wire [4:0]             conv2_shift,

    output wire                   busy,
    output wire                   inference_done,

    output wire [1:0]             class_id,
    output wire signed [31:0]     score,
    // 4 logit for protocol v3 (HIL tail, SCORE = top1 - top2); valid from inference_done until next start.
    // fpga_top (PROTO 1) leaves these unconnected.
    output wire signed [31:0]     logit0_out,
    output wire signed [31:0]     logit1_out,
    output wire signed [31:0]     logit2_out,
    output wire signed [31:0]     logit3_out
);

    // ============================================================
    // CNN stage definitions
    // ============================================================

    localparam ST_IDLE  = 4'd0;
    localparam ST_CONV1 = 4'd1;
    localparam ST_POOL1 = 4'd2;
    localparam ST_CONV2 = 4'd3;
    localparam ST_POOL2 = 4'd4;
    localparam ST_GAP   = 4'd5;
    localparam ST_DENSE = 4'd6;
    localparam ST_DONE  = 4'd7;


    // ============================================================
    // CNN controller
    // ============================================================

    wire conv_start;
    wire pool_start;
    wire gap_start;
    wire dense_start;

    wire conv_layer_sel;
    wire pool_layer_sel;

    wire conv_done;
    wire pool_done;
    wire gap_done;
    wire dense_done;

    wire [3:0] stage;

    // argmax4 has 2 register stages: hold back inference_done by 2 clocks
    wire done_raw;
    reg [1:0] done_dly = 2'b00;

    always @(posedge clk)
        done_dly <= {done_dly[0], done_raw};

    assign inference_done = done_dly[1];

    cnn_controller u_controller (
        .clk            (clk),
        .start          (start),

        .conv_done      (conv_done),
        .pool_done      (pool_done),
        .gap_done       (gap_done),
        .dense_done     (dense_done),

        .conv_start     (conv_start),
        .pool_start     (pool_start),
        .gap_start      (gap_start),
        .dense_start    (dense_start),

        .conv_layer_sel (conv_layer_sel),
        .pool_layer_sel (pool_layer_sel),

        .busy           (busy),
        .inference_done (done_raw),

        .stage          (stage)
    );


    // ============================================================
    // Shared Weight ROM / Bias ROM
    // ============================================================

    wire [11:0] conv_weight_addr;
    wire [11:0] dense_weight_addr;

    wire [5:0] conv_bias_addr;
    wire [5:0] dense_bias_addr;

    wire [11:0] shared_weight_addr;
    wire [5:0]  shared_bias_addr;

    wire signed [7:0]  shared_weight_data;
    wire signed [31:0] shared_bias_data;

    assign shared_weight_addr =
        (stage == ST_DENSE)
        ? dense_weight_addr
        : conv_weight_addr;

    assign shared_bias_addr =
        (stage == ST_DENSE)
        ? dense_bias_addr
        : conv_bias_addr;


    weight_rom u_weight_rom (
        .clk  (clk),
        .addr (shared_weight_addr),
        .data (shared_weight_data)
    );


    bias_rom u_bias_rom (
        .clk  (clk),
        .addr (shared_bias_addr),
        .data (shared_bias_data)
    );


    // ============================================================
    // Shared MAC P = 1
    // ============================================================

    wire conv_mac_clear;
    wire conv_mac_enable;

    wire signed [7:0] conv_mac_a;
    wire signed [7:0] conv_mac_b;


    wire dense_mac_clear;
    wire dense_mac_enable;

    wire signed [7:0] dense_mac_a;
    wire signed [7:0] dense_mac_b;


    wire shared_mac_clear;
    wire shared_mac_enable;

    wire signed [7:0] shared_mac_a;
    wire signed [7:0] shared_mac_b;

    wire signed [31:0] shared_mac_accumulator;


    assign shared_mac_clear =
        (stage == ST_DENSE)
        ? dense_mac_clear
        : conv_mac_clear;

    assign shared_mac_enable =
        (stage == ST_DENSE)
        ? dense_mac_enable
        : conv_mac_enable;

    assign shared_mac_a =
        (stage == ST_DENSE)
        ? dense_mac_a
        : conv_mac_a;

    assign shared_mac_b =
        (stage == ST_DENSE)
        ? dense_mac_b
        : conv_mac_b;


    mac_unit u_shared_mac (
        .clk         (clk),
        .clear       (shared_mac_clear),
        .enable      (shared_mac_enable),

        .data_a      (shared_mac_a),
        .data_b      (shared_mac_b),

        .accumulator (shared_mac_accumulator)
    );


    // ============================================================
    // Conv1D Engine
    // ============================================================

    wire [9:0] conv_input_addr;
    wire signed [7:0] conv_input_data;

    wire [10:0] conv_output_addr;
    wire signed [31:0] conv_output_data;
    wire conv_output_valid;

    wire conv_busy;


    // Conv1 reads raw input buffer.
    // Conv2 reads Feature RAM B.
    assign input_read_addr = conv_input_addr;


    conv1d_engine u_conv (
        .clk             (clk),
        .start           (conv_start),

        .layer_sel       (conv_layer_sel),

        .busy            (conv_busy),
        .done            (conv_done),

        .input_addr      (conv_input_addr),
        .input_data      (conv_input_data),

        .weight_addr     (conv_weight_addr),
        .weight_data     (shared_weight_data),

        .bias_addr       (conv_bias_addr),
        .bias_data       (shared_bias_data),

        .mac_clear       (conv_mac_clear),
        .mac_enable      (conv_mac_enable),

        .mac_a           (conv_mac_a),
        .mac_b           (conv_mac_b),

        .mac_accumulator (shared_mac_accumulator),

        .output_addr     (conv_output_addr),
        .output_data     (conv_output_data),
        .output_valid    (conv_output_valid)
    );


    // ============================================================
    // ReLU + Requantization
    // ============================================================

    wire signed [7:0] requant_data;

    wire [4:0] active_shift;

    assign active_shift =
        (stage == ST_CONV2)
        ? conv2_shift
        : conv1_shift;


    requantize_relu u_requant (
        .data_in      (conv_output_data),
        .shift_amount (active_shift),
        .data_out     (requant_data)
    );


    // ============================================================
    // Feature RAM A
    //
    // Conv1 output -> RAM A
    // Conv2 output -> RAM A
    // Pool reads from RAM A
    // ============================================================

    wire [10:0] feature_a_read_addr;
    wire signed [7:0] feature_a_read_data;


    feature_ram u_feature_ram_a (
        .clk        (clk),

        .we         (conv_output_valid),
        .write_addr (conv_output_addr),
        .write_data (requant_data),

        .read_addr  (feature_a_read_addr),
        .read_data  (feature_a_read_data)
    );


    // ============================================================
    // Feature RAM B
    //
    // Pool1 output -> RAM B
    // Pool2 output -> RAM B
    //
    // Conv2 reads RAM B
    // GAP reads RAM B
    // ============================================================

    wire [10:0] feature_b_read_addr;
    wire signed [7:0] feature_b_read_data;

    wire [9:0] pool_output_addr;
    wire signed [7:0] pool_output_data;
    wire pool_output_valid;


    feature_ram u_feature_ram_b (
        .clk        (clk),

        .we         (pool_output_valid),
        .write_addr ({1'b0, pool_output_addr}),
        .write_data (pool_output_data),

        .read_addr  (feature_b_read_addr),
        .read_data  (feature_b_read_data)
    );


    // Conv input selection
    assign conv_input_data =
        (stage == ST_CONV1)
        ? input_read_data
        : feature_b_read_data;


    // ============================================================
    // Max Pooling Engine
    // ============================================================

    wire pool_busy;

    wire [10:0] pool_input_addr;


    maxpool1d_engine u_pool (
        .clk          (clk),
        .start        (pool_start),

        .layer_sel    (pool_layer_sel),

        .busy         (pool_busy),
        .done         (pool_done),

        .input_addr   (pool_input_addr),
        .input_data   (feature_a_read_data),

        .output_addr  (pool_output_addr),
        .output_data  (pool_output_data),
        .output_valid (pool_output_valid)
    );


    assign feature_a_read_addr = pool_input_addr;


    // ============================================================
    // Global Average Pooling
    // ============================================================

    wire gap_busy;

    wire [9:0] gap_input_addr;

    wire [4:0] gap_output_addr;
    wire signed [7:0] gap_output_data;
    wire gap_output_valid;


    gap_engine u_gap (
        .clk          (clk),
        .start        (gap_start),

        .busy         (gap_busy),
        .done         (gap_done),

        .input_addr   (gap_input_addr),
        .input_data   (feature_b_read_data),

        .output_addr  (gap_output_addr),
        .output_data  (gap_output_data),
        .output_valid (gap_output_valid)
    );


    // RAM B read routing:
    //
    // Conv2 -> RAM B
    // GAP   -> RAM B

    assign feature_b_read_addr =
        (stage == ST_GAP)
        ? {1'b0, gap_input_addr}
        : {1'b0, conv_input_addr};


    // ============================================================
    // GAP Buffer
    // ============================================================

    wire [4:0] dense_input_addr;
    wire signed [7:0] dense_input_data;


    gap_buffer u_gap_buffer (
        .clk        (clk),

        .we         (gap_output_valid),
        .write_addr (gap_output_addr),
        .write_data (gap_output_data),

        .read_addr  (dense_input_addr),
        .read_data  (dense_input_data)
    );


    // ============================================================
    // Dense 32 -> 4
    // ============================================================

    wire dense_busy;

    wire signed [31:0] logit0;
    wire signed [31:0] logit1;
    wire signed [31:0] logit2;
    wire signed [31:0] logit3;


    dense_engine u_dense (
        .clk             (clk),
        .start           (dense_start),

        .busy            (dense_busy),
        .done            (dense_done),

        .input_addr      (dense_input_addr),
        .input_data      (dense_input_data),

        .weight_addr     (dense_weight_addr),
        .weight_data     (shared_weight_data),

        .bias_addr       (dense_bias_addr),
        .bias_data       (shared_bias_data),

        .mac_clear       (dense_mac_clear),
        .mac_enable      (dense_mac_enable),

        .mac_a           (dense_mac_a),
        .mac_b           (dense_mac_b),

        .mac_accumulator (shared_mac_accumulator),

        .logit0          (logit0),
        .logit1          (logit1),
        .logit2          (logit2),
        .logit3          (logit3)
    );


    // ============================================================
    // Argmax
    // ============================================================

    argmax4 u_argmax (
        .clk      (clk),

        .logit0   (logit0),
        .logit1   (logit1),
        .logit2   (logit2),
        .logit3   (logit3),

        .class_id (class_id),
        .score    (score)
    );

    assign logit0_out = logit0;
    assign logit1_out = logit1;
    assign logit2_out = logit2;
    assign logit3_out = logit3;

endmodule