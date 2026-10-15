module feature_ram (
    input  wire                   clk,

    // Write port
    input  wire                   we,
    input  wire [10:0]            write_addr,
    input  wire signed [7:0]      write_data,

    // Read port
    input  wire [10:0]            read_addr,
    output reg  signed [7:0]      read_data
);

    // Maximum feature-map size:
    // 128 x 16 = 2048 INT8 values
    reg signed [7:0] mem [0:2047];

    always @(posedge clk) begin

        if (we)
            mem[write_addr] <= write_data;

        read_data <= mem[read_addr];

    end

endmodule