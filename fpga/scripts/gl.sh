#!/usr/bin/env bash
# fpga/scripts/gl.sh — mô phỏng NETLIST SAU P&R của Gowin (không phải RTL): dựng fpga/ kèm netlist .vo rồi chạy
# tb_proto trên chính netlist đó, kể cả nội dung ROM weight/bias (INIT_RAM của pROM), BSRAM, DSP. Không có SDF.
#   bash fpga/scripts/gl.sh [thư mục làm việc] [NG=1]
# Icarus 0.9.7 chạy netlist ≈ 2.000–5.000 chu kỳ/s: NG = 1 mất khoảng 10 phút. rPLL thay bằng fpga/sim/rpll_stub.v.
# In danh sách FF lên nguồn ở mức 1: mỗi dòng phải là khởi tạo CỐ Ý trong RTL (cs_sync, crc = FFFF…); thanh ghi không
# khởi tạo thì Gowin tự chọn INIT (lỗi conv_start ngày 15/10, docs/bao_cao/2026-10-15_loi_init_conv_start/).
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
W="${1:-${TMPDIR:-${TEMP:-/tmp}}/fpga_gl}"; N="${2:-1}"
M="$ROOT/ml/out/e2_matrix/n2_11_p1"
LIB="${GW_SIMLIB:-/c/Gowin/Gowin_V1.9.11.03_Education_x64/IDE/simlib/gw2a/prim_sim.v}"
command -v iverilog >/dev/null || export PATH="/c/iverilog/bin:$PATH"
PY="$(command -v python3 || command -v python)"
mkdir -p "$W"
SIM_NETLIST=1 bash "$ROOT/fpga/scripts/build.sh" "$W/pnr"
VO="$W/pnr/impl/pnr/fpga_project.vo"
[ -f "$VO" ] || { echo "không có $VO"; exit 1; }
echo "pROM trong netlist: $(grep -c '^pROM ' "$VO"), dòng INIT_RAM: $(grep -c 'INIT_RAM_' "$VO")"
echo "FF có INIT=1:"
grep -E "defparam .*[.]INIT=1'b1;" "$VO" | awk '{ n = $2; sub(/^[^a-zA-Z_]/, "", n); sub(/[.]INIT.*/, "", n);
    sub(/_s[0-9]+$/, "", n); sub(/_[0-9]+$/, "", n); print "  " n }' | sort | uniq -c
awk '/^module rPLL /{skip=1} !skip{print} skip && /^endmodule/{skip=0}' "$LIB" > "$W/prim_sim_norpll.v"
rm -rf "$W/tb"; mkdir -p "$W/tb"
"$PY" -I "$ROOT/tools/gen_tb_proto.py" --export "$M" --params "$ROOT/$(cat "$M/params_src.txt")" --out "$W/tb" --ng "$N"
cd "$W"
iverilog -g2001 -DTB_NG="$N" -s tb_proto -o gl.vvp "$ROOT/fpga/sim/tb_proto.v" "$VO" prim_sim_norpll.v \
    "$ROOT/fpga/sim/rpll_stub.v" 2>&1 | grep -v "warning: Part select" || true
vvp gl.vvp | tee gl.log
[ "$(grep -E '^(PASS|FAIL)' gl.log | tail -1)" = "PASS" ]
