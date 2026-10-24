#!/usr/bin/env bash
# fpga/scripts/test.sh — kiểm RTL của project fpga/ bằng Icarus Verilog (-g2001), không cần Gowin, không ghi vào repo.
#   bash fpga/scripts/test.sh [--ng 10] [--work <thư mục>]
#   1. fpga/src mang đúng mô hình của bitstream (ml/out/e2_matrix/n2_11_p1)
#   2. tb_e2: engine E2 từng tầng với 10 vector, P = 1 (bản nạp) và P = 4 (làn song song)
#   3. tb_proto: cả top v3 qua chân SPI, NG khung đúng (so golden) + 7 kịch bản lỗi
#   4. sketch ESP32 mang đúng bản lõi C của firmware/src
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NG=10; WORK=""
while [ $# -gt 0 ]; do
    case "$1" in
        --ng) NG="$2"; shift 2 ;;
        --work) WORK="$2"; shift 2 ;;
        *) echo "tham số lạ: $1"; exit 2 ;;
    esac
done
[ -n "$WORK" ] || WORK="$(mktemp -d)"
command -v iverilog >/dev/null || export PATH="/c/iverilog/bin:$PATH"
command -v iverilog >/dev/null || { echo "không thấy iverilog"; exit 2; }
PY="$(command -v python3 || command -v python)"
M="$ROOT/ml/out/e2_matrix/n2_11_p1"
PARAMS="$ROOT/$(cat "$M/params_src.txt")"
SIM="$ROOT/fpga/sim"
rm -rf "$WORK"; mkdir -p "$WORK"
echo "thư mục làm việc: $WORK"
declare -a NAMES RESULTS TIMES
add() { NAMES+=("$1"); RESULTS+=("$2"); TIMES+=("$3 s"); echo "  $1: $2 ($3 s)"; }
passed() { [ "$(grep -E '^(PASS|FAIL)' "$1" | tail -1)" = "PASS" ]; }

# 1. mô hình trong fpga/src
S="$ROOT/fpga/src"
if cmp -s "$M/cnn_params.vh" "$S/cnn_params.vh" && cmp -s "$M/weights.mem" "$S/weights_e2.mem" && cmp -s "$M/bias.mem" "$S/bias_e2.mem"
then add "fpga/src = mô hình n2_11_p1" PASS 0; else add "fpga/src = mô hình n2_11_p1" FAIL 0; fi

# 2. tb_e2, P = 1 và 4
for P in 1 4; do
    D="$WORK/e2_p$P"; t0=$SECONDS
    if "$PY" -I "$ROOT/tools/export_mem.py" --params "$PARAMS" --engine e2 --lanes $P --out "$D" > /dev/null \
       && (cd "$D" && iverilog -g2001 -I . -DTB_NV=10 -s tb_e2 -o tb_e2.vvp "$SIM/tb_e2.v" "$S/cnn_e2.v" && vvp tb_e2.vvp) \
          > "$WORK/tb_e2_p$P.log" 2>&1 && passed "$WORK/tb_e2_p$P.log"
    then add "tb_e2 (P = $P, 10 vector, mọi tầng)" PASS $((SECONDS - t0))
    else add "tb_e2 (P = $P, 10 vector, mọi tầng)" FAIL $((SECONDS - t0)); fi
done

# 3. tb_proto trên fpga/src
D="$WORK/proto"; t0=$SECONDS
mkdir -p "$D/tb"; cp -r "$S" "$D/src"
if "$PY" -I "$ROOT/tools/gen_tb_proto.py" --export "$M" --params "$PARAMS" --out "$D/tb" --ng "$NG" > /dev/null \
   && (cd "$D" && iverilog -g2001 -I src -DTB_NG="$NG" -s tb_proto -o tb.vvp "$SIM/tb_proto.v" src/fpga_top_v3.v \
         src/packet_parser_v3.v src/result_frame_v3.v src/spi_result_tx_v3.v src/crc16_ccitt.v src/spi_slave.v \
         src/input_buffer.v src/cnn_e2.v "$SIM/pll_50m_sim.v" && vvp tb.vvp) > "$WORK/tb_proto.log" 2>&1 \
   && passed "$WORK/tb_proto.log"
then add "tb_proto (top v3 qua SPI: $NG khung + 7 kịch bản lỗi)" PASS $((SECONDS - t0))
else add "tb_proto (top v3 qua SPI: $NG khung + 7 kịch bản lỗi)" FAIL $((SECONDS - t0)); fi

# 4. lõi C trong sketch ESP32
if bash "$ROOT/esp32/dong_bo_core.sh" --check > "$WORK/esp32_sync.log" 2>&1
then add "esp32/mu_nga_hub trùng firmware/src" PASS 0; else add "esp32/mu_nga_hub trùng firmware/src" FAIL 0; fi

echo
echo "| Kiểm | Kết quả | Thời gian |"
echo "|---|---|---|"
fail=0
for i in "${!NAMES[@]}"; do
    echo "| ${NAMES[$i]} | ${RESULTS[$i]} | ${TIMES[$i]} |"
    [ "${RESULTS[$i]}" = "PASS" ] || fail=1
done
echo "Icarus: $(iverilog -V 2>&1 | head -1)"
[ $fail -eq 0 ] && echo "TẤT CẢ PASS" || echo "CÓ FAIL"
exit $fail
