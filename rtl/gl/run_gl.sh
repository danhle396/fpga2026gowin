#!/usr/bin/env bash
# rtl/gl/run_gl.sh — mô phỏng NETLIST SAU P&R của Gowin (không phải RTL): kiểm rằng tổng hợp + P&R giữ đúng chức năng,
# kể cả nội dung ROM weight/bias (INIT_RAM của pROM), BSRAM, DSP. Mô phỏng chức năng, không có SDF.
#   bash rtl/gl/run_gl.sh <thư mục làm việc> p1                 # bitstream 1: fpga_top (PROTO 1) + E1, tb_top_spi
#   bash rtl/gl/run_gl.sh <thư mục làm việc> v3 [NG=1]          # bitstream 2: fpga_top_v3 + E1, tb_proto
#   bash rtl/gl/run_gl.sh <thư mục làm việc> <thư mục export_mem.py --engine e2> [NG=3]   # bitstream 3: v3 + E2
# Weight E1 lấy từ fpga_export của nhóm, đúng như pnr_v3.sh tổng hợp vào bitstream 1 và 2.
# Netlist .vg của bản Education bị mã hóa; .vo sinh bằng SIM_NETLIST=1 thì không. rPLL thay bằng rpll_stub.v.
# Icarus 0.9.7 chạy netlist ≈ 2.000–5.000 chu kỳ/s: E2 NG = 1 mất 562 s cả P&R khi máy rảnh; NG = 3 mất 1.815 s khi máy bận.
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
W="$1"
if [ -d "$2" ]; then MODE=e2; E2="$(cd "$2" && pwd)"; N="${3:-3}"; else MODE="$2"; N="${3:-}"; fi
EXPORT="$ROOT/FPGA_Fall_Detection_AI-20261012T141515Z-1-001/FPGA_Fall_Detection_AI/fpga_export"
LIB="${GW_SIMLIB:-/c/Gowin/Gowin_V1.9.11.03_Education_x64/IDE/simlib/gw2a/prim_sim.v}"
command -v iverilog >/dev/null || export PATH="/c/iverilog/bin:$PATH"
PY="$(command -v python3 || command -v python)"
mkdir -p "$W"
case "$MODE" in
    e2) SIM_NETLIST=1 bash "$ROOT/rtl/v3/pnr_v3.sh" "$W/pnr" e2 "$E2" ;;
    v3) SIM_NETLIST=1 bash "$ROOT/rtl/v3/pnr_v3.sh" "$W/pnr" v3; N="${N:-1}" ;;
    p1) SIM_NETLIST=1 bash "$ROOT/rtl/v3/pnr_v3.sh" "$W/pnr" p1; N="${N:-5}" ;;
    *) echo "chế độ lạ: $MODE (p1 | v3 | <thư mục e2>)"; exit 2 ;;
esac
VO="$W/pnr/impl/pnr/fpga_project.vo"
[ -f "$VO" ] || { echo "không có $VO"; exit 1; }
echo "pROM trong netlist: $(grep -c '^pROM ' "$VO"), dòng INIT_RAM: $(grep -c 'INIT_RAM_' "$VO")"
# FF lên nguồn ở mức 1 (GSR nạp INIT). Mỗi dòng phải ứng với một khởi tạo CỐ Ý trong RTL (cs_sync, crc = FFFF, rst_sync…);
# thanh ghi không khởi tạo thì Gowin tự chọn INIT — lỗi conv_start = 1 lúc bật nguồn ngày 15/10 là loại này.
echo "FF có INIT=1:"
grep -E "defparam .*[.]INIT=1'b1;" "$VO" | awk '{ n = $2; sub(/^[^a-zA-Z_]/, "", n); sub(/[.]INIT.*/, "", n);
    sub(/_s[0-9]+$/, "", n); sub(/_[0-9]+$/, "", n); print "  " n }' | sort | uniq -c
awk '/^module rPLL /{skip=1} !skip{print} skip && /^endmodule/{skip=0}' "$LIB" > "$W/prim_sim_norpll.v"
rm -rf "$W/tb"; mkdir -p "$W/tb"
case "$MODE" in
    e2) "$PY" -I "$ROOT/tools/gen_tb_proto.py" --export "$E2" --params "$(cat "$E2/params_src.txt")" --out "$W/tb" --ng "$N"
        TOP=tb_proto; TB="$ROOT/rtl/v3/tb_proto.v"; DEF="-DTB_NG=$N" ;;
    v3) "$PY" -I "$ROOT/tools/gen_tb_proto.py" --export "$EXPORT" --out "$W/tb" --ng "$N"
        TOP=tb_proto; TB="$ROOT/rtl/v3/tb_proto.v"; DEF="-DTB_NG=$N" ;;
    p1) "$PY" -I "$ROOT/tools/gen_tb_top.py" --export "$EXPORT" --out "$W/tb"
        TOP=tb_top_spi; TB="$ROOT/rtl/tb/tb_top_spi.v"; DEF=""     # NF = 5 cố định theo gen_tb_top.py
        [ "$N" = 5 ] || { echo "tb_top_spi: NF cố định 5"; exit 2; } ;;
esac
cd "$W"
iverilog -g2001 $DEF -s "$TOP" -o gl.vvp "$TB" "$VO" prim_sim_norpll.v "$ROOT/rtl/gl/rpll_stub.v" 2>&1 \
    | grep -v "warning: Part select" || true
vvp gl.vvp | tee gl.log
[ "$(grep -E '^(PASS|FAIL)' gl.log | tail -1)" = "PASS" ]
