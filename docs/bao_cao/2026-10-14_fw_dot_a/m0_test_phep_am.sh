#!/usr/bin/env bash
# Phép âm cho tools/m0_test.py: mỗi lần làm hỏng một chỗ trong bản sao firmware, build ảnh test, chạy, phải ra FAIL.
set -u
ROOT=D:/hoctap/fpga/fpga2026gowin
PY="C:/Users/ADMIN/AppData/Local/Temp/claude/d--hoctap-fpga-fpga2026gowin/4f873fbe-983f-43f7-9d9d-b0d332537d87/scratchpad/venv/Scripts/python.exe"
W="C:/Users/ADMIN/AppData/Local/Temp/claude/d--hoctap-fpga-fpga2026gowin/4f873fbe-983f-43f7-9d9d-b0d332537d87/scratchpad/mut"

mutate() {   # mutate <tên> <file> <sed-expr>
    rm -rf "$W"; mkdir -p "$W/tools" "$W/ml"
    cp -r "$ROOT/firmware" "$W/"; cp -r "$ROOT/ml/src" "$W/ml/"
    cp "$ROOT/tools/m0_test.py" "$ROOT/tools/gen_tv_pre.py" "$W/tools/"
    rm -rf "$W/firmware/build"
    sed -i "$3" "$W/firmware/src/$2"
    if cmp -s "$ROOT/firmware/src/$2" "$W/firmware/src/$2"; then echo "?? $1: sed không đổi gì"; return; fi
    bash "$W/firmware/build.sh" test >/dev/null 2>&1 || { echo "?? $1: build lỗi"; return; }
    out=$("$PY" "$W/tools/m0_test.py" 2>&1)
    n=$(echo "$out" | grep -c '^ *FAIL')
    if echo "$out" | grep -q "CÓ FAIL"; then echo "bắt được  $1  ($n dòng FAIL)"; else echo "LỌT      $1"; fi
}

mutate "làm tròn y: +4 -> +3"            preprocess.c 's/(int32_t)r\[c\] + 4) >> 3/(int32_t)r[c] + 3) >> 3/'
mutate "hệ số lọc 3 -> 2 ở r[2n]"         preprocess.c 's/3 \* (int32_t)s->ev\[c\]/2 * (int32_t)s->ev[c]/'
mutate "kẹp 127 -> 126"                   preprocess.c 's/if (q > 127)  q = 127;/if (q > 126)  q = 126;/'
mutate "bước cửa sổ 16 -> 15"             preprocess.c 's/(s->n_out % PRE_HOP) == 0/(s->n_out % 15) == 0/'
mutate "CRC-16 đa thức 0x1021 -> 0x1022"  crc.c        's/0x1021u/0x1022u/'
mutate "CRC-8 PROTO 1 tính cả 0xA5"       spi_frame.c  's/tx(SPI_HDR_WRITE, ctx);             \/\* CRC-8/c8 = crc8_update(c8, SPI_HDR_WRITE); tx(SPI_HDR_WRITE, ctx); \/\* CRC-8/'
mutate "bỏ kiểm SEQ"                      spi_frame.c  's/if (b\[1\] != seq_expect)                         return SPI_E_SEQ;//'
mutate "SOS 3 s dùng >"                   safety.c     's/held >= c->sos_hold_ms/held > c->sos_hold_ms/'
mutate "không đánh dấu nút đã dùng khi hủy PRE_ALARM" safety.c 's/if (press) { s->btn_used = 1; go(s, ST_MONITOR/if (press) { go(s, ST_MONITOR/'
mutate "WEAR không bị bỏ qua ở SUSPECT"   safety.c     's/    case ST_SUSPECT:\r\?$/    case ST_SUSPECT: if (!wear) { go(s, ST_STANDBY, WHY_WEAR_OFF, now); return; }/'
mutate "T_TILT dùng <="                   safety.c     's/s->az_tb < c->t_tilt/s->az_tb <= c->t_tilt + 600/'
mutate "khối: span dùng >"                blocks.c     's/if (span >= /if (span > /'
