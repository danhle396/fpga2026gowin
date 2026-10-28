#!/usr/bin/env bash
# esp32/dong_bo_core.sh — chép các file C thuần của firmware/src sang sketch ESP32 (Arduino chỉ biên dịch file nằm cạnh
# .ino). Nguồn duy nhất vẫn là firmware/src; chạy lại script này sau mỗi lần sửa ở đó.
#   bash esp32/dong_bo_core.sh            # chép
#   bash esp32/dong_bo_core.sh --check    # chỉ kiểm, khác thì thoát mã 1 (fpga/scripts/test.sh gọi)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
S="$ROOT/firmware/src"
D="$ROOT/esp32/mu_nga_hub"
FILES="app_core.c app_core.h preprocess.c preprocess.h blocks.c blocks.h safety.c safety.h pwr_btn.c pwr_btn.h
       spi_frame.c spi_frame.h crc.c crc.h fw_config.h node_link.c node_link.h hub.c hub.h posture.c posture.h nga.c nga.h selftest_expect_v3_e2_n2.h"
bad=0
for f in $FILES; do
    if [ "${1:-}" = "--check" ]; then
        cmp -s "$S/$f" "$D/$f" || { echo "lệch: esp32/mu_nga_hub/$f"; bad=1; }
    else
        cp "$S/$f" "$D/$f"
    fi
done
[ "${1:-}" = "--check" ] && { [ $bad -eq 0 ] && echo "esp32/mu_nga_hub trùng firmware/src"; exit $bad; }
echo "đã chép $(echo $FILES | wc -w) file sang esp32/mu_nga_hub/"
