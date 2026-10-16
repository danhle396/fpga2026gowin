#!/usr/bin/env python
# tools/gyro_residual.py — kiểm Pass của FW-05 trên file LOG của tools/logger.py (bước B5 trong docs/huong_dan_dot_B.md):
# ở chế độ LOG gyro đã trừ offset hiệu chuẩn lúc khởi động, nên khi board/mũ đặt yên, trung bình 500 mẫu của mỗi trục
# gyro phải trong ±2 LSB. In trung bình của 500 mẫu đầu (Pass) và trung bình 500 mẫu lệch nhất trên cả file (theo dõi trôi).
#
#   python -I tools/gyro_residual.py ml/data/raw/s00_bench_01.csv
import argparse
import sys

import numpy as np

N = 500
LIMIT = 2.0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--skip", type=int, default=0, help="bỏ số mẫu đầu (vd. lúc vừa đặt board xuống)")
    a = ap.parse_args()
    x = np.loadtxt(a.csv, delimiter=",", skiprows=1, ndmin=2)
    g = x[a.skip:, 4:7]                       # t_ms,ax,ay,az,gx,gy,gz,...
    if len(g) < N:
        print(f"FAIL  chỉ có {len(g)} mẫu, cần ≥ {N}")
        return 1
    m0 = g[:N].mean(axis=0)
    c = np.vstack([np.zeros((1, 3)), np.cumsum(g, axis=0)])
    w = (c[N:] - c[:-N]) / N                  # trung bình trượt 500 mẫu
    worst = w[np.abs(w).max(axis=1).argmax()]
    ok = bool(np.all(np.abs(m0) <= LIMIT))
    print(f"500 mẫu đầu: gx {m0[0]:+.2f}  gy {m0[1]:+.2f}  gz {m0[2]:+.2f} LSB  (giới hạn ±{LIMIT:g})")
    print(f"500 mẫu lệch nhất trong {len(g)} mẫu: gx {worst[0]:+.2f}  gy {worst[1]:+.2f}  gz {worst[2]:+.2f} LSB")
    print(("PASS" if ok else "FAIL") + "  FW-05: offset gyro dư của 500 mẫu đầu")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
