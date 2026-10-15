// rtl/tb/pll_50m_sim.v — thay rPLL của Gowin khi mô phỏng bằng Icarus: clkout = clkin.
// Testbench tự cấp clock 50 MHz vào cổng clk của fpga_top. Chỉ dùng trong mô phỏng, không đưa vào project Gowin.
module pll_50m (clkout, clkin);
    output clkout;
    input  clkin;
    assign clkout = clkin;
endmodule
