#!/usr/bin/env python
# tools/logger.py — ghi luồng LOG 100 Hz của MCU ra CSV và báo mất mẫu (SPEC v3, A.9).
# Đã kiểm cú pháp; chưa chạy với board vì firmware LOG chưa có (việc FW-06, AI-03).
import argparse
import pathlib
import sys
import time

import serial

HEADER = "t_ms,ax,ay,az,gx,gy,gz,btn,wear"
PERIOD_MS = 10      # cảm biến 100 Hz
LOST_GAP_MS = 15    # khoảng 9–11 ms là bình thường; từ 15 ms trở lên là mất mẫu


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=460800)
    ap.add_argument("--subject", required=True)                # vd: s01
    ap.add_argument("--activity", required=True)               # vd: fall_front
    ap.add_argument("--trial", type=int, required=True)
    ap.add_argument("--seconds", type=float, default=0, help="0 = chạy đến khi Ctrl+C")
    a = ap.parse_args()

    out = pathlib.Path("ml/data/raw") / f"{a.subject}_{a.activity}_{a.trial:02d}.csv"
    if out.exists():
        sys.exit(f"Đã có {out} — không ghi đè dữ liệu thô")
    out.parent.mkdir(parents=True, exist_ok=True)

    n = lost = 0
    prev = None
    ncol = None                                                # 9 cột, hoặc 8 nếu mạch ghi không có cột wear (A.9)
    t_end = time.time() + a.seconds if a.seconds else float("inf")
    with serial.Serial(a.port, a.baud, timeout=1) as ser, open(out, "w", newline="\n") as f:
        try:
            while time.time() < t_end:
                line = ser.readline().decode("ascii", "ignore").strip()
                parts = line.split(",")
                if line.startswith(("#", "F,")) or len(parts) not in (8, 9):   # bỏ chú thích và dòng khung của chế độ TRC
                    continue
                try:
                    t = int(parts[0])
                    [int(p) for p in parts[1:]]
                except ValueError:
                    continue
                if ncol is None:
                    ncol = len(parts)
                    f.write(",".join(HEADER.split(",")[:ncol]) + "\n")
                elif len(parts) != ncol:
                    continue
                if prev is not None and t - prev >= LOST_GAP_MS:
                    lost += round((t - prev) / PERIOD_MS) - 1
                    print(f"MẤT MẪU tại t={t} ms (hở {t - prev} ms)")
                prev = t
                f.write(line + "\n")
                n += 1
        except KeyboardInterrupt:
            pass
    print(f"{out}: {n} mẫu, mất {lost} mẫu -> {'PASS' if n and lost == 0 else 'FAIL'}")


if __name__ == "__main__":
    main()
