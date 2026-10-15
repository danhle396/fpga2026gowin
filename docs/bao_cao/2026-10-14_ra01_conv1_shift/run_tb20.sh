#!/bin/bash
# Chạy testbench 20 vector trên BẢN SAO project (không đụng impl/ của đồng đội).
set -e
SRC="D:/hoctap/fpga/fpga2026gowin/Document Board Kiwi Primer 20K/Kiwi20K_FallDetection_FPGA"
W="C:/Users/ADMIN/AppData/Local/Temp/claude/d--hoctap-fpga-fpga2026gowin/9b5f4884-f4b4-4be2-8b28-b5da3e3b0998/scratchpad/sim"
rm -rf "$W"; mkdir -p "$W"
cp -r "$SRC/src" "$SRC/tb" "$SRC/tb_cnn_core_golden.v" "$W/"
cd "$W"
export PATH="/c/iverilog/bin:$PATH"
iverilog -g2001 -I src -s tb_cnn_core_golden -o tb20.vvp tb_cnn_core_golden.v \
  src/cnn_core.v src/cnn_controller.v src/conv1d_engine.v src/requantize_relu.v src/maxpool1d_engine.v \
  src/feature_ram.v src/gap_engine.v src/gap_buffer.v src/dense_engine.v src/argmax4.v src/mac_unit.v \
  src/weight_rom.v src/bias_rom.v
vvp tb20.vvp
