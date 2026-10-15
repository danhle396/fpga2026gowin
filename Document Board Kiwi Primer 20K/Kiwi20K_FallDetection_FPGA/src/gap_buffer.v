module gap_buffer (
    input  wire                  clk,

    input  wire                  we,
    input  wire [4:0]            write_addr,
    input  wire signed [7:0]     write_data,

    input  wire [4:0]            read_addr,
    output reg  signed [7:0]     read_data
);

    // 32 outputs from Global Average Pooling
    reg signed [7:0] mem [0:31];

    always @(posedge clk) begin

        if (we)
            mem[write_addr] <= write_data;

        read_data <= mem[read_addr];

    end

endmodule