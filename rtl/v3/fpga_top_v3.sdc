# rtl/v3/fpga_top_v3.sdc - timing constraints for fpga_top_v3 (protocol v3). R10, RA-02.
# 27 MHz input clock on H11; the rPLL 50.143 MHz clock is derived by the tool.
# SCK, CS, MOSI are asynchronous and pass a 3-FF synchronizer; MISO and IRQ are slow relative to SCK <= 4 MHz.
create_clock -name clk27 -period 37.037 -waveform {0 18.518} [get_ports {clk}]
set_false_path -from [get_ports {spi_sclk spi_cs_n spi_mosi}]
set_false_path -to [get_ports {spi_miso irq}]
set_false_path -from [get_ports {rst_n}]
