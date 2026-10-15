#!/usr/bin/env bash
# Phép âm cho tb_e2: sửa một chỗ trong bản sao cnn_e2.v, chạy N2-S P=1 (và N1 cho lỗi GAP) với 2 vector, phải FAIL.
ROOT=D:/hoctap/fpga/fpga2026gowin
S="C:/Users/ADMIN/AppData/Local/Temp/claude/d--hoctap-fpga-fpga2026gowin/4f873fbe-983f-43f7-9d9d-b0d332537d87/scratchpad"
export PATH="/c/iverilog/bin:$PATH"
mut() {   # mut <tên> <sed> <thư mục xuất> <hậu tố>
    local W="$S/me2_$4"; rm -rf "$W"; mkdir -p "$W"
    cp "$ROOT/rtl/e2/cnn_e2.v" "$ROOT/rtl/e2/tb_e2.v" "$W/"
    cp "$ROOT/$3/"{weights.mem,bias.mem,cnn_params.vh,vec_in.mem,vec_exp.mem,vec_trace.mem} "$W/"
    sed -i "$2" "$W/cnn_e2.v"
    if cmp -s "$ROOT/rtl/e2/cnn_e2.v" "$W/cnn_e2.v"; then echo "?? $1: sed không đổi gì"; return; fi
    (cd "$W" && iverilog -g2001 -I . -DTB_NV=2 -s tb_e2 -o t.vvp tb_e2.v cnn_e2.v && vvp t.vvp > t.log 2>&1) \
        || { echo "?? $1: biên dịch lỗi"; return; }
    if grep -q '^FAIL' "$W/t.log"; then echo "bắt được  $1: $(grep -m1 '^FAIL' "$W/t.log")"; else echo "LỌT      $1"; fi
}
E=ml/out/e2_matrix/tie_p1
G=ml/out/e2_matrix/n1team_p1
mut "requant làm tròn thay vì lấy sàn"   's/s = v >>> n;/s = (v + (1 <<< n) \/ 2) >>> n;/' $E a &
mut "đệm biên: bỏ kiểm pos >= L"          's/ || (pos >= $signed({2.d0, L}))//' $E b &
mut "max-pool lấy q = 1 thay vì max"      's/if (!q || acc\[p\] > best\[p\]) best\[p\] <= acc\[p\];/best[p] <= acc[p];/' $E c &
mut "drain 2 nhịp thay vì 3"              's/if (drain == 3.d3) begin/if (drain == 3'"'"'d2) begin/' $E d &
mut "GAP lấy sàn sai (>> 4)"              's/gapf\[gc\] <= gsum >> GAP_SH;/gapf[gc] <= gsum >> (GAP_SH - 1);/' $G e &
mut "argmax: bằng nhau chọn chỉ số lớn"   's/(lg\[1\] > lg\[0\])/(lg[1] >= lg[0])/g' $E f &
wait
