#!/usr/bin/env bash
# build.sh — biên dịch firmware test MPU6050 cho SN32F407 bằng Arm Compiler 6 của Keil MDK, không cần mở uVision.
# Dùng MicroLIB (như tùy chọn "Use MicroLIB" trong uVision) để không kéo theo semihosting.
# Chạy trong Git Bash:  bash test_sensor/firmware/build.sh
# Ra: test_sensor/firmware/build/mpu6050_test.hex (nạp bằng công cụ nạp của SONiX hoặc qua Keil).
set -e
cd "$(dirname "$0")"

KEIL="${KEIL:-$LOCALAPPDATA/Keil_v5}"
PACKS="${PACKS:-$LOCALAPPDATA/Arm/Packs}"
BIN="$KEIL/ARM/ARMCLANG/bin"
DFP="$(ls -d "$PACKS"/SONiX/SN32F4_DFP/*/ | sort -V | tail -1)Device"
CMSIS="$(ls -d "$PACKS"/ARM/CMSIS/*/ | sort -V | tail -1)CMSIS/Core/Include"
[ -x "$BIN/armclang.exe" ] || { echo "Không thấy armclang ở $BIN — đặt biến KEIL"; exit 1; }

mkdir -p build
cat > build/sn32f407.sct <<'EOF'
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

OBJS=""
for f in test_main.c mpu6050.c i2c_soft.c board_sn32f407.c "$DFP/Source/system_SN32F400.c"; do
    o="build/$(basename "${f%.c}").o"
    "$BIN/armclang.exe" --target=arm-arm-none-eabi -mcpu=cortex-m0 -mthumb -Oz -std=c99 -Wall -D__MICROLIB \
        -ffunction-sections -fdata-sections \
        -I . -I "$(cygpath -w "$DFP/Include")" -I "$(cygpath -w "$CMSIS")" \
        -c "$(cygpath -w "$f")" -o "$o"
    OBJS="$OBJS $o"
done
"$BIN/armasm.exe" --cpu Cortex-M0 --pd "__MICROLIB SETA 1" "$(cygpath -w "$DFP/Source/ARM/startup_SN32F400.s")" -o build/startup.o 2>/dev/null
"$BIN/armlink.exe" --cpu Cortex-M0 --scatter build/sn32f407.sct --entry Reset_Handler --remove --library_type=microlib \
    --map --list build/mpu6050_test.map --info totals -o build/mpu6050_test.axf $OBJS build/startup.o
"$BIN/fromelf.exe" --i32combined -o build/mpu6050_test.hex build/mpu6050_test.axf
ls -l build/mpu6050_test.hex
