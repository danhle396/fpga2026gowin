module input_buffer (
    input  wire       clk,

    input  wire       we,
    input  wire [9:0] write_addr,
    input  wire [7:0] write_data,

    input  wire [9:0] read_addr,
    output reg  [7:0] read_data
);

    // 768 bytes = 6 channels x 128 samples
    reg [7:0] mem [0:767];

    always @(posedge clk) begin

        if (we)
            mem[write_addr] <= write_data;

        read_data <= mem[read_addr];

    end

endmodule