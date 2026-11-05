#!/usr/bin/env bash
# Dựng chương trình đo CNN cho SN32F407 ngoài repo, cờ giống firmware/build.sh, tối ưu -O3 như dự toán FW-15.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO=/d/hoctap/fpga/fpga2026gowin/firmware
KEIL="$LOCALAPPDATA/Keil_v5"
PACKS="$LOCALAPPDATA/Arm/Packs"
BIN="$KEIL/ARM/ARMCLANG/bin"
DFP="$(ls -d "$PACKS"/SONiX/SN32F4_DFP/*/ | sort -V | tail -1)Device"
CMSIS="$(ls -d "$PACKS"/ARM/CMSIS/*/ | sort -V | tail -1)CMSIS/Core/Include"
OUT="$HERE/build"
mkdir -p "$OUT"
CFLAGS="--target=arm-arm-none-eabi -mcpu=cortex-m0 -mthumb -O3 -std=c99 -Wall -Wextra -Wno-unused-parameter
        -D__MICROLIB -ffunction-sections -fdata-sections"
OBJS=""
for f in "$HERE/test/do_cnn_main.c" "$HERE/test/so_lieu.c" "$REPO/test/cnn_mcu.c" "$REPO/src/board.c" "$DFP/Source/system_SN32F400.c"; do
    o="$OUT/$(basename "${f%.c}").o"
    "$BIN/armclang.exe" $CFLAGS -I "$(cygpath -w "$HERE/test")" -I "$(cygpath -w "$REPO/test")" -I "$(cygpath -w "$REPO/src")" \
        -I "$(cygpath -w "$DFP/Include")" -I "$(cygpath -w "$CMSIS")" -c "$(cygpath -w "$f")" -o "$(cygpath -w "$o")"
    OBJS="$OBJS $(cygpath -w "$o")"
done
cat > "$OUT/sn32f407.sct" <<'EOF'
LR_IROM1 0x00000000 0x00007FFC {
  ER_IROM1 0x00000000 0x00007FFC {
    *.o (RESET, +First)
    *(InRoot$$Sections)
    .ANY (+RO)
  }
  RW_IRAM1 0x20000000 0x00002000 {
    .ANY (+RW +ZI)
  }
}
LR_FLAG 0x00007FFC 0x00000004 {
  ER_FLAG 0x00007FFC 0x00000004 {
    *(.ARM.__at_0x00007FFC)
  }
}
EOF
"$BIN/armasm.exe" --cpu Cortex-M0 --pd "__MICROLIB SETA 1" "$(cygpath -w "$DFP/Source/ARM/startup_SN32F400.s")" \
    -o "$(cygpath -w "$OUT/startup.o")" 2>/dev/null
"$BIN/armlink.exe" --cpu Cortex-M0 --scatter "$(cygpath -w "$OUT/sn32f407.sct")" --entry Reset_Handler --remove \
    --library_type=microlib --map --list "$(cygpath -w "$OUT/fw.map")" --info totals -o "$(cygpath -w "$OUT/fw.axf")" $OBJS "$(cygpath -w "$OUT/startup.o")"
grep -E "Total (RO|RW)|Grand Totals" "$OUT/fw.map" | tail -4
ls -l "$OUT/fw.axf"
