module cnn_controller (
    input  wire clk,
    input  wire start,

    // Done signals from processing engines
    input  wire conv_done,
    input  wire pool_done,
    input  wire gap_done,
    input  wire dense_done,

    // Start pulses to processing engines
    output reg  conv_start = 0,
    output reg  pool_start = 0,
    output reg  gap_start = 0,
    output reg  dense_start = 0,

    // Select which layer is being processed
    output reg  conv_layer_sel = 0,
    output reg  pool_layer_sel = 0,

    output reg  busy = 0,
    output reg  inference_done = 0,

    // Current CNN stage, useful for memory routing
    output reg [3:0] stage = 0
);

    localparam ST_IDLE  = 4'd0;
    localparam ST_CONV1 = 4'd1;
    localparam ST_POOL1 = 4'd2;
    localparam ST_CONV2 = 4'd3;
    localparam ST_POOL2 = 4'd4;
    localparam ST_GAP   = 4'd5;
    localparam ST_DENSE = 4'd6;
    localparam ST_DONE  = 4'd7;

    reg [3:0] state = ST_IDLE;

    always @(posedge clk) begin

        // Start signals are one-clock pulses
        conv_start     <= 1'b0;
        pool_start     <= 1'b0;
        gap_start      <= 1'b0;
        dense_start    <= 1'b0;
        inference_done <= 1'b0;

        stage <= state;

        case (state)

            // ----------------------------------------------------
            ST_IDLE: begin

                busy <= 1'b0;

                if (start) begin

                    busy <= 1'b1;

                    // Conv1: 6 -> 16
                    conv_layer_sel <= 1'b0;
                    conv_start     <= 1'b1;

                    state <= ST_CONV1;

                end
            end

            // ----------------------------------------------------
            ST_CONV1: begin

                if (conv_done) begin

                    // Pool1: 128x16 -> 64x16
                    pool_layer_sel <= 1'b0;
                    pool_start     <= 1'b1;

                    state <= ST_POOL1;

                end
            end

            // ----------------------------------------------------
            ST_POOL1: begin

                if (pool_done) begin

                    // Conv2: 16 -> 32
                    conv_layer_sel <= 1'b1;
                    conv_start     <= 1'b1;

                    state <= ST_CONV2;

                end
            end

            // ----------------------------------------------------
            ST_CONV2: begin

                if (conv_done) begin

                    // Pool2: 64x32 -> 32x32
                    pool_layer_sel <= 1'b1;
                    pool_start     <= 1'b1;

                    state <= ST_POOL2;

                end
            end

            // ----------------------------------------------------
            ST_POOL2: begin

                if (pool_done) begin

                    gap_start <= 1'b1;

                    state <= ST_GAP;

                end
            end

            // ----------------------------------------------------
            ST_GAP: begin

                if (gap_done) begin

                    dense_start <= 1'b1;

                    state <= ST_DENSE;

                end
            end

            // ----------------------------------------------------
            ST_DENSE: begin

                if (dense_done) begin

                    state <= ST_DONE;

                end
            end

            // ----------------------------------------------------
            ST_DONE: begin

                busy           <= 1'b0;
                inference_done <= 1'b1;

                state <= ST_IDLE;

            end

            // ----------------------------------------------------
            default: begin

                state <= ST_IDLE;

            end

        endcase
    end

endmodule