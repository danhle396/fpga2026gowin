set_device -name GW2A-18C GW2A-LV18PG256C8/I7
add_file src/argmax4.v
add_file src/bias_rom.v
add_file src/cnn_controller.v
add_file src/cnn_core.v
add_file src/conv1d_engine.v
add_file src/crc8.v
add_file src/dense_engine.v
add_file src/feature_ram.v
add_file src/fpga_top.v
add_file src/gap_buffer.v
add_file src/gap_engine.v
add_file src/gowin_rpll/pll_50m.v
add_file src/input_buffer.v
add_file src/mac_unit.v
add_file src/maxpool1d_engine.v
add_file src/packet_parser.v
add_file src/requantize_relu.v
add_file src/result_register.v
add_file src/spi_result_tx.v
add_file src/spi_slave.v
add_file src/weight_rom.v
add_file src/fpga_top.cst
set_option -top_module fpga_top
set_option -output_base_name fpga_project
run all
