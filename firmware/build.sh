#!/usr/bin/env bash
# firmware/build.sh — biên dịch firmware chính cho SN32F407 bằng Arm Compiler 6 của Keil MDK, không cần mở uVision.
#   bash firmware/build.sh        → build/fw.hex   (MCU nút cảm biến: MPU6050 → khung node_link → UART → ESP32)
#   bash firmware/build.sh test   → build/test.axf (lõi C dùng chung với ESP32 + bộ test, chạy trong trình giả lập: tools/m0_test.py)
# Project Keil tương đương: firmware/keil/fw.uvprojx (UV4 -b).
set -e
cd "$(dirname "$0")"

KEIL="${KEIL:-$LOCALAPPDATA/Keil_v5}"
PACKS="${PACKS:-$LOCALAPPDATA/Arm/Packs}"
BIN="$KEIL/ARM/ARMCLANG/bin"
DFP="$(ls -d "$PACKS"/SONiX/SN32F4_DFP/*/ | sort -V | tail -1)Device"
CMSIS="$(ls -d "$PACKS"/ARM/CMSIS/*/ | sort -V | tail -1)CMSIS/Core/Include"
[ -x "$BIN/armclang.exe" ] || { echo "Không thấy armclang ở $BIN — đặt biến KEIL"; exit 1; }

CORE="src/node_link.c src/hub.c src/crc.c src/preprocess.c src/spi_frame.c src/blocks.c src/safety.c src/app_core.c src/pwr_btn.c src/posture.c src/nga.c"   # C thuần, chạy trên ESP32
MCU="src/app_main.c src/board.c src/i2c0.c src/imu.c src/gyro_cal.c src/node_link.c src/crc.c"
OPT="${OPT:--Oz}"        # bản đo tốc độ FW-15: OPT=-O3
CFLAGS="--target=arm-arm-none-eabi -mcpu=cortex-m0 -mthumb $OPT -std=c99 -Wall -Wextra -Wno-unused-parameter
        -D__MICROLIB -ffunction-sections -fdata-sections -I src -I test"
mkdir -p build

compile() {     # compile <thư mục obj> <file .c>...
    local dir="$1"; shift
    OBJS=""
    for f in "$@"; do
        local o="$dir/$(basename "${f%.c}").o"
        "$BIN/armclang.exe" $CFLAGS -I "$(cygpath -w "$DFP/Include")" -I "$(cygpath -w "$CMSIS")" \
            -c "$(cygpath -w "$f")" -o "$o"
        OBJS="$OBJS $o"
    done
}

if [ "${1:-fw}" = "test" ]; then
    mkdir -p build/test
    compile build/test $CORE src/gyro_cal.c test/cnn_mcu.c test/host_main.c test/host_startup.c
    cat > build/test/host.sct <<'EOF'
LR 0x00000000 0x00100000 {
  ER_RO 0x00000000 0x00100000 { *(RESET, +First) *(InRoot$$Sections) .ANY (+RO) }
  RW 0x20000000 0x0003E000 { .ANY (+RW +ZI) }
  ARM_LIB_STACK 0x20040000 EMPTY -0x2000 { }
}
EOF
    "$BIN/armlink.exe" --cpu Cortex-M0 --scatter build/test/host.sct --entry Reset_Handler --remove \
        --library_type=microlib --map --list build/test/test.map --info totals -o build/test.axf $OBJS
    "$BIN/fromelf.exe" --bin -o build/test.bin build/test.axf
    ls -l build/test.axf build/test.bin
    exit 0
fi

mkdir -p build/fw
cat > build/fw/sn32f407.sct <<'EOF'
LR_IROM1 0x00000000 0x00007FFC {          ; Flash 32 KB, trừ 4 byte cuối
  ER_IROM1 0x00000000 0x00007FFC {
    *.o (RESET, +First)
    *(InRoot$$Sections)
    .ANY (+RO)
  }
  RW_IRAM1 0x20000000 0x00002000 {        ; RAM 8 KB
    .ANY (+RW +ZI)
  }
}
LR_FLAG 0x00007FFC 0x00000004 {           ; từ cờ ở cuối Flash do startup của SONiX khai báo
  ER_FLAG 0x00007FFC 0x00000004 {
    *(.ARM.__at_0x00007FFC)
  }
}
EOF
compile build/fw $MCU "$DFP/Source/system_SN32F400.c"
"$BIN/armasm.exe" --cpu Cortex-M0 --pd "__MICROLIB SETA 1" "$(cygpath -w "$DFP/Source/ARM/startup_SN32F400.s")" \
    -o build/fw/startup.o 2>/dev/null
"$BIN/armlink.exe" --cpu Cortex-M0 --scatter build/fw/sn32f407.sct --entry Reset_Handler --remove \
    --library_type=microlib --map --list build/fw/fw.map --info totals -o build/fw.axf $OBJS build/fw/startup.o
"$BIN/fromelf.exe" --i32combined -o build/fw.hex build/fw.axf
grep -E "Total (RO|RW)" build/fw/fw.map | tail -3
ls -l build/fw.hex
