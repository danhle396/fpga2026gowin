#!/usr/bin/env bash
# Phép âm cho tb_proto: làm hỏng một chỗ trong bản sao rtl/v3, chạy với NG = 2, phải ra FAIL.
ROOT=D:/hoctap/fpga/fpga2026gowin
S="C:/Users/ADMIN/AppData/Local/Temp/claude/d--hoctap-fpga-fpga2026gowin/4f873fbe-983f-43f7-9d9d-b0d332537d87/scratchpad"
mut() {   # mut <tên> <file> <sed>
    local W="$S/mv3_$4"; rm -rf "$W"; mkdir -p "$W/rtl" "$W/tools" "$W/ml"
    cp -r "$ROOT/rtl/v3" "$ROOT/rtl/tb" "$W/rtl/"; cp -r "$ROOT/tools/"*.py "$W/tools/"; cp -r "$ROOT/ml/src" "$W/ml/"
    cp -r "$ROOT/Document Board Kiwi Primer 20K" "$W/" 2>/dev/null
    cp -r "$ROOT/FPGA_Fall_Detection_AI-20261012T141515Z-1-001" "$W/"
    sed -i "$3" "$W/rtl/v3/$2"
    if cmp -s "$ROOT/rtl/v3/$2" "$W/rtl/v3/$2"; then echo "?? $1: sed không đổi gì"; return; fi
    out=$(bash "$W/rtl/v3/run_tb_proto.sh" --ng 2 --work "$W/work" 2>&1)
    if echo "$out" | grep -qE '^FAIL'; then echo "bắt được  $1: $(echo "$out" | grep -E '^FAIL' | head -1)"; else echo "LỌT      $1"; fi
}
mut "CRC khung ghi không tính 0xA5"     packet_parser_v3.v 's|crc      <= crc_next;                    // CRC|crc      <= crc;                         // CRC|' a &
wait
