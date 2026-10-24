#!/usr/bin/env bash
# fpga/scripts/build.sh — tổng hợp + P&R project fpga/fpga_project.gprj bằng Gowin, đúng như bấm Run All trong IDE,
# trên BẢN SAO ở thư mục tạm (không ghi impl/ vào repo).
#   bash fpga/scripts/build.sh [thư mục làm việc]              # in tài nguyên, Fmax, đường dẫn .fs
#   bash fpga/scripts/build.sh --release [thư mục làm việc]    # chép .fs + báo cáo vào fpga/bitstream/, ghi SHA256
#   SIM_NETLIST=1 bash fpga/scripts/build.sh ...                # thêm netlist mô phỏng sau P&R (.vo) cho gl.sh
# Kiểm 24/10: .fs dựng ra trùng từng bit fpga/bitstream/fpga_project.fs (trừ dòng giờ tạo).
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GW="${GW_SH:-/c/Gowin/Gowin_V1.9.11.03_Education_x64/IDE/bin/gw_sh.exe}"
REL=0; [ "${1:-}" = "--release" ] && { REL=1; shift; }
W="${1:-${TMPDIR:-${TEMP:-/tmp}}/fpga_build}"
rm -rf "$W"; mkdir -p "$W/impl"
cp -r "$ROOT/fpga/fpga_project.gprj" "$ROOT/fpga/src" "$W/"
cp "$ROOT/fpga/impl/fpga_project_process_config.json" "$W/impl/"
{
    echo "open_project fpga_project.gprj"
    [ "${SIM_NETLIST:-0}" = "1" ] && echo "set_option -gen_verilog_sim_netlist 1"
    echo "run all"
} > "$W/build.tcl"
(cd "$W" && "$GW" build.tcl > pnr.log 2>&1) || { tail -20 "$W/pnr.log"; exit 1; }
R="$W/impl/pnr/fpga_project.rpt.txt"
grep -E "ERROR" "$W/pnr.log" && exit 1 || true
grep -E "^\s+(Logic|Register|BSRAM|DSP|I/O Port)\s+\|" "$R" || true
sed 's/<[^>]*>/ /g' "$W/impl/pnr/fpga_project_tr_content.html" | tr -d '\r' | tr '\n' ' ' | tr -s ' ' |
    grep -oE 'Max Frequency Summary.{0,160}' || true
ls -l "$W/impl/pnr/fpga_project.fs"
if [ $REL -eq 1 ]; then
    B="$ROOT/fpga/bitstream"
    chmod u+w "$B"/* 2>/dev/null || true
    cp "$W/impl/pnr/fpga_project.fs" "$B/"
    tr -d '\r' < "$R" > "$B/fpga_project.rpt.txt"
    (cd "$B" && sha256sum fpga_project.fs > SHA256.txt && cat SHA256.txt)
fi
