#!/usr/bin/env bash
# rtl/e2/run_tb_e2.sh — chạy tb_e2 trên một thư mục xuất của tools/export_mem.py --engine e2.
#   bash rtl/e2/run_tb_e2.sh <thư mục xuất> [số vector]
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EX="$(cd "$1" && pwd)"; NV="${2:-50}"
command -v iverilog >/dev/null || export PATH="/c/iverilog/bin:$PATH"
cd "$EX"
iverilog -g2001 -I . -DTB_NV="$NV" -s tb_e2 -o tb_e2.vvp "$ROOT/rtl/e2/tb_e2.v" "$ROOT/rtl/e2/cnn_e2.v" || exit 1
vvp tb_e2.vvp | tee tb_e2.log
[ "$(grep -E '^(PASS|FAIL)' tb_e2.log | tail -1)" = "PASS" ]
