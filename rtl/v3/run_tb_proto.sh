#!/usr/bin/env bash
# rtl/v3/run_tb_proto.sh — chạy tb_proto (RA-03, RA-07) trên bản sao project Gowin.
#   bash rtl/v3/run_tb_proto.sh [--ng 50] [--export <fpga_export>] [--work <thư mục>]      # engine E1 (cnn_core)
#   bash rtl/v3/run_tb_proto.sh --e2 <thư mục export_mem.py --engine e2 --params ...> [--ng 50]   # engine E2
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJ="$ROOT/Document Board Kiwi Primer 20K/Kiwi20K_FallDetection_FPGA"
EXPORT="$ROOT/FPGA_Fall_Detection_AI-20261012T141515Z-1-001/FPGA_Fall_Detection_AI/fpga_export"
NG=50; WORK=""; E2=""
while [ $# -gt 0 ]; do
    case "$1" in
        --ng) NG="$2"; shift 2 ;;
        --export) EXPORT="$(cd "$2" && pwd)"; shift 2 ;;
        --work) WORK="$2"; shift 2 ;;
        --e2) E2="$(cd "$2" && pwd)"; shift 2 ;;
        *) echo "tham số lạ: $1"; exit 2 ;;
    esac
done
[ -n "$WORK" ] || WORK="$(mktemp -d)"
command -v iverilog >/dev/null || export PATH="/c/iverilog/bin:$PATH"
PY="$(command -v python3 || command -v python)"
rm -rf "$WORK"; mkdir -p "$WORK/tb"
cp -r "$PROJ/src" "$WORK/"
if [ -n "$E2" ]; then
    cp "$E2/cnn_params.vh" "$WORK/src/cnn_params.vh"
    cp "$E2/weights.mem" "$WORK/src/weights_e2.mem"
    cp "$E2/bias.mem" "$WORK/src/bias_e2.mem"
    "$PY" -I "$ROOT/tools/gen_tb_proto.py" --export "$E2" --params "$(cat "$E2/params_src.txt")" \
        --out "$WORK/tb" --ng "$NG" || exit 1
    CORE_SRC="$ROOT/rtl/e2/cnn_e2.v"
else
    "$PY" -I "$ROOT/tools/gen_cnn_params.py" --export "$EXPORT" --project "$WORK" >/dev/null || exit 1
    "$PY" -I "$ROOT/tools/gen_tb_proto.py" --export "$EXPORT" --out "$WORK/tb" --ng "$NG" || exit 1
    CORE_SRC="src/cnn_core.v src/cnn_controller.v src/conv1d_engine.v src/requantize_relu.v src/maxpool1d_engine.v
              src/feature_ram.v src/gap_engine.v src/gap_buffer.v src/dense_engine.v src/argmax4.v src/mac_unit.v
              src/weight_rom.v src/bias_rom.v"
fi
V3="$ROOT/rtl/v3"
cd "$WORK"
iverilog -g2001 -I src -DTB_NG="$NG" -s tb_proto -o tb_proto.vvp "$V3/tb_proto.v" "$V3/fpga_top_v3.v" \
    "$V3/packet_parser_v3.v" "$V3/result_frame_v3.v" "$V3/spi_result_tx_v3.v" "$V3/crc16_ccitt.v" \
    "$ROOT/rtl/tb/pll_50m_sim.v" src/spi_slave.v src/input_buffer.v $CORE_SRC || exit 1
vvp tb_proto.vvp | tee tb_proto.log
[ "$(grep -E '^(PASS|FAIL)' tb_proto.log | tail -1)" = "PASS" ]
