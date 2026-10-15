module bias_rom (
    input  wire                    clk,
    input  wire [5:0]              addr,
    output reg signed [31:0]       data
);

    // Conv1 :  0 ... 15
    // Conv2 : 16 ... 47
    // Dense : 48 ... 51

    reg signed [31:0] mem [0:51]
        /* synthesis syn_ramstyle = "block_ram" */;

    initial begin
        $readmemh("src/bias.mem", mem);
    end

    always @(posedge clk) begin
        if (addr < 6'd52)
            data <= mem[addr];
        else
            data <= 32'sd0;
    end

endmodule