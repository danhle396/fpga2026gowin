#!/usr/bin/env bash
# rtl/tb/run_all.sh — chạy mọi testbench RTL rồi in bảng PASS/FAIL (việc RB-01). Không ghi gì vào project Gowin:
# mọi thứ chạy trên bản sao trong thư mục làm việc.
#   bash rtl/tb/run_all.sh                         # weight của nhóm AI (fpga_export hiện hành)
#   bash rtl/tb/run_all.sh --export ml/out/n1_d1/fpga_export   # weight khác, ví dụ N1 huấn luyện trên D1
#   bash rtl/tb/run_all.sh --work <thư mục>        # giữ lại thư mục làm việc để xem log
# Cần: Icarus Verilog (-g2001, chạy được trên 0.9.7 và bản mới), Python 3 + numpy.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJ="$ROOT/Document Board Kiwi Primer 20K/Kiwi20K_FallDetection_FPGA"
EXPORT="$ROOT/FPGA_Fall_Detection_AI-20261012T141515Z-1-001/FPGA_Fall_Detection_AI/fpga_export"
WORK=""
while [ $# -gt 0 ]; do
    case "$1" in
        --export) EXPORT="$(cd "$2" && pwd)"; shift 2 ;;
        --work)   WORK="$2"; shift 2 ;;
        *) echo "tham số lạ: $1"; exit 2 ;;
    esac
done
[ -n "$WORK" ] || WORK="$(mktemp -d)"
command -v iverilog >/dev/null || export PATH="/c/iverilog/bin:$PATH"
command -v iverilog >/dev/null || { echo "không thấy iverilog"; exit 2; }
PY="$(command -v python3 || command -v python)"

rm -rf "$WORK"; mkdir -p "$WORK"
cp -r "$PROJ/src" "$PROJ/tb_cnn_core_golden.v" "$WORK/"
mkdir -p "$WORK/tb"
echo "thư mục làm việc: $WORK"
echo "weight: $EXPORT"
"$PY" -I "$ROOT/tools/gen_cnn_params.py" --export "$EXPORT" --project "$WORK" || { echo "FAIL gen_cnn_params"; exit 1; }
"$PY" -I "$ROOT/tools/gen_tb_top.py" --export "$EXPORT" --out "$WORK/tb" || { echo "FAIL gen_tb_top"; exit 1; }

CORE="src/cnn_core.v src/cnn_controller.v src/conv1d_engine.v src/requantize_relu.v src/maxpool1d_engine.v
      src/feature_ram.v src/gap_engine.v src/gap_buffer.v src/dense_engine.v src/argmax4.v src/mac_unit.v
      src/weight_rom.v src/bias_rom.v"
TOP="src/fpga_top.v src/spi_slave.v src/packet_parser.v src/crc8.v src/input_buffer.v src/result_register.v
     src/spi_result_tx.v $ROOT/rtl/tb/pll_50m_sim.v"

declare -a NAMES RESULTS TIMES
run_tb() {   # run_tb <tên> <top> <file...>
    local name="$1" top="$2"; shift 2
    local t0=$SECONDS log="$WORK/$name.log"
    if ! (cd "$WORK" && iverilog -g2001 -I src -s "$top" -o "$name.vvp" "$@") >"$log" 2>&1; then
        RESULTS+=("FAIL (biên dịch)")
    elif ! (cd "$WORK" && vvp "$name.vvp") >>"$log" 2>&1; then
        RESULTS+=("FAIL (vvp)")
    elif [ "$(grep -E '^(PASS|FAIL)' "$log" | tail -1)" = "PASS" ]; then
        RESULTS+=("PASS")
    else
        RESULTS+=("FAIL")
    fi
    NAMES+=("$name"); TIMES+=("$((SECONDS - t0)) s")
    echo "  $name: ${RESULTS[-1]}  ($((SECONDS - t0)) s) — log $log"
}

echo "chạy testbench:"
run_tb tb_pin_probe       tb_pin_probe       "$ROOT/rtl/pin_probe/tb_pin_probe.v" "$ROOT/rtl/pin_probe/pin_probe_top.v"
run_tb tb_top_spi         tb_top_spi         "$ROOT/rtl/tb/tb_top_spi.v" $TOP $CORE
run_tb tb_cnn_core_golden tb_cnn_core_golden tb_cnn_core_golden.v $CORE

# E1 từng tầng (RB-02): l1, l2, feat, logit với 10 vector của export_mem.py (có bão hòa, LFSR)
"$PY" -I "$ROOT/tools/export_mem.py" --export "$EXPORT" --engine e1 --out "$WORK/e1x" >/dev/null 2>&1     || "$PY" -I "$ROOT/tools/export_mem.py" --params "$EXPORT/../params_int8.npz" --engine e1 --out "$WORK/e1x" >/dev/null
for f in vec_in vec_exp vec_trace vec_feat; do cp "$WORK/e1x/$f.mem" "$WORK/tb/$f.mem"; done
cp "$WORK/e1x/cnn_params.vh" "$WORK/e1x/weights.mem" "$WORK/e1x/bias.mem" "$WORK/src/"
run_tb tb_e1_layers       tb_e1_layers -DTB_NV=10 "$ROOT/rtl/tb/tb_e1_layers.v" $CORE
# trả lại tham số, weight và 20 vector của gen_cnn_params cho các testbench sau
"$PY" -I "$ROOT/tools/gen_cnn_params.py" --export "$EXPORT" --project "$WORK" >/dev/null

# giao thức v3 (RA-03) với E1: 5 khung đúng + 7 kịch bản lỗi
"$PY" -I "$ROOT/tools/gen_tb_proto.py" --export "$EXPORT" --out "$WORK/tb" --ng 5 >/dev/null || { echo "FAIL gen_tb_proto"; exit 1; }
V3="$ROOT/rtl/v3"
run_tb tb_proto_v3_e1     tb_proto -DTB_NG=5 "$V3/tb_proto.v" "$V3/fpga_top_v3.v" "$V3/packet_parser_v3.v" \
    "$V3/result_frame_v3.v" "$V3/spi_result_tx_v3.v" "$V3/crc16_ccitt.v" "$ROOT/rtl/tb/pll_50m_sim.v" \
    src/spi_slave.v src/input_buffer.v $CORE

# engine E2 (RB-04) với cùng weight, bố trí E2, P = 1 và 4: 10 vector, so từng tầng
for P in 1 4; do
    D="$WORK/e2_p$P"
    if [ -f "$EXPORT/weights.mem" ] && [ "$(wc -l < "$EXPORT/weights.mem")" -eq 3168 ]; then
        "$PY" -I "$ROOT/tools/export_mem.py" --export "$EXPORT" --engine e2 --lanes $P --out "$D" >/dev/null
    else
        "$PY" -I "$ROOT/tools/export_mem.py" --params "$EXPORT/../params_int8.npz" --engine e2 --lanes $P --out "$D" >/dev/null
    fi || { echo "FAIL export_mem"; exit 1; }
    t0=$SECONDS
    if (cd "$D" && iverilog -g2001 -I . -DTB_NV=10 -s tb_e2 -o tb_e2.vvp "$ROOT/rtl/e2/tb_e2.v" "$ROOT/rtl/e2/cnn_e2.v" \
          && vvp tb_e2.vvp) > "$WORK/tb_e2_p$P.log" 2>&1 && [ "$(grep -E '^(PASS|FAIL)' "$WORK/tb_e2_p$P.log" | tail -1)" = "PASS" ]; then
        RESULTS+=("PASS")
    else
        RESULTS+=("FAIL")
    fi
    NAMES+=("tb_e2 (P = $P)"); TIMES+=("$((SECONDS - t0)) s")
    echo "  tb_e2 P=$P: ${RESULTS[-1]}  ($((SECONDS - t0)) s) — log $WORK/tb_e2_p$P.log"
done

echo
echo "| Testbench | Kết quả | Thời gian |"
echo "|---|---|---|"
fail=0
for i in "${!NAMES[@]}"; do
    echo "| ${NAMES[$i]} | ${RESULTS[$i]} | ${TIMES[$i]} |"
    [ "${RESULTS[$i]}" = "PASS" ] || fail=1
done
echo "Icarus: $(iverilog -V 2>&1 | head -1)"
[ $fail -eq 0 ] && echo "TẤT CẢ PASS" || echo "CÓ FAIL"
exit $fail
