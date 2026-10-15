module weight_rom (
    input  wire                   clk,
    input  wire [11:0]            addr,
    output reg signed [7:0]       data
);

    // Conv1 :    0 ... 479
    // Conv2 :  480 ... 3039
    // Dense : 3040 ... 3167
    //
    // Force this memory into Gowin BSRAM.
    reg signed [7:0] mem [0:3167]
        /* synthesis syn_ramstyle = "block_ram" */;

    initial begin
        $readmemh("src/weights.mem", mem);
    end

    // Synchronous read -> suitable for BSRAM inference
    always @(posedge clk) begin
        if (addr < 12'd3168)
            data <= mem[addr];
        else
            data <= 8'sd0;
    end

endmodule