#!/usr/bin/env bash
# rtl/gowin/tao_project.sh — tạo 4 project Gowin mở được bằng Gowin IDE (File → Open Project → *.gprj), đúng nguồn,
# đúng tham số và đúng chân (header J2) của các file trong bitstreams/ và rtl/pin_probe/:
#   bash rtl/gowin/tao_project.sh [thư mục đích, mặc định gowin_proj]
# Thư mục đích không đưa lên git (.gitignore). Mỗi project là bản sao nguồn: sửa RTL thì sửa trong rtl/ rồi chạy lại
# script này, đừng sửa trong gowin_proj/ (sẽ bị xóa ở lần tạo sau). Bấm Run All trong IDE ra .fs trùng bitstreams/ từng bit
# (trừ dòng giờ tạo), đã kiểm 24/10.
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
D="${1:-$ROOT/gowin_proj}"
mkdir -p "$D"
ONLY_PROJECT=1 bash "$ROOT/rtl/v3/pnr_v3.sh" "$D/1_e1_proto1_sisfall" p1
ONLY_PROJECT=1 bash "$ROOT/rtl/v3/pnr_v3.sh" "$D/2_v3_e1_sisfall" v3
ONLY_PROJECT=1 bash "$ROOT/rtl/v3/pnr_v3.sh" "$D/3_v3_e2_n2" e2 "$ROOT/ml/out/e2_matrix/n2_11_p1"
P="$D/pin_probe"
rm -rf "$P"; mkdir -p "$P/src"
cp "$ROOT/rtl/pin_probe/pin_probe_top.v" "$ROOT/rtl/pin_probe/pin_probe_top.cst" "$P/src/"
printf '%s\n' "set_device -name GW2A-18C GW2A-LV18PG256C8/I7" "add_file src/pin_probe_top.v" "add_file src/pin_probe_top.cst" \
    "set_option -top_module pin_probe_top" "set_option -output_base_name pin_probe" "run all" > "$P/build.tcl"
python -I "$ROOT/rtl/gowin/tao_gprj.py" "$P"
echo "Mở bằng Gowin IDE: File → Open Project → $D/<tên>/fpga_project.gprj (pin_probe: pin_probe.gprj)"
