#!/usr/bin/env python
# tools/spectrum_check.py — so phổ của tín hiệu đi vào mạng giữa D1 và dữ liệu trên mũ (việc AI-14, bước 1).
# D1 vốn 25 Hz nội suy lên 50 Hz, nên băng 12,5–25 Hz gần như trống; dữ liệu mũ (100 Hz → lọc [1,3,3,1]/8 → 50 Hz)
# thì có. Công cụ đo tỉ lệ công suất trong băng 12,5–25 Hz so với 0,5–25 Hz, theo trục, lúc đi bộ.
#
#   python -I tools/spectrum_check.py                                   # chỉ D1 (act 801, đi bộ)
#   python -I tools/spectrum_check.py --log ml/data/raw/s01_di_bo_01.csv ...   # thêm file LOG đi bộ trên mũ
import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
from golden_model import decimate  # noqa: E402

FS = 50.0
NSEG = 128
CH = ["ax", "ay", "az", "gx", "gy", "gz"]


def welch(x):
    """x: (N, C) ở 50 Hz → (f, P[C]) trung bình các đoạn 128 mẫu, cửa sổ Hann, chồng 50 %."""
    w = np.hanning(NSEG)
    segs = [x[s:s + NSEG] for s in range(0, len(x) - NSEG + 1, NSEG // 2)]
    if not segs:
        return None, None
    P = np.zeros((NSEG // 2 + 1, x.shape[1]))
    for s in segs:
        s = (s - s.mean(0)) * w[:, None]
        P += np.abs(np.fft.rfft(s, axis=0)) ** 2
    return np.fft.rfftfreq(NSEG, 1 / FS), P / len(segs)


def band_frac(f, P):
    hi = (f >= 12.5) & (f <= 25)
    all_ = (f >= 0.5) & (f <= 25)
    return P[hi].sum(0) / np.maximum(P[all_].sum(0), 1e-12)


def report(name, xs):
    acc = None
    for x in xs:
        f, P = welch(x.astype(np.float64))
        if f is None:
            continue
        acc = P if acc is None else acc + P
    if acc is None:
        print(f"{name}: không đủ dữ liệu")
        return None
    fr = band_frac(f, acc)
    print(f"{name}: tỉ lệ công suất 12,5–25 Hz / 0,5–25 Hz: " + ", ".join(f"{c} {v:.4f}" for c, v in zip(CH, fr)))
    return fr


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", nargs="*", default=[], type=pathlib.Path, help="file LOG 100 Hz đi bộ trên mũ")
    ap.add_argument("--act", type=int, default=801)
    a = ap.parse_args()
    D = np.load(ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz")
    xs = [D["data"][D["start"][i]:D["start"][i] + D["length"][i]] for i in np.flatnonzero(D["act"] == a.act)]
    f1 = report(f"D1 act {a.act} ({len(xs)} bản ghi, 50 Hz nội suy từ 25 Hz)", xs)
    # đối chứng tổng hợp: cùng D1 nhưng thêm thành phần 15 Hz nhỏ → công cụ phải thấy băng cao tăng
    rng = np.random.default_rng(0)
    xt = [x + (60 * np.sin(2 * np.pi * 15 * np.arange(len(x)) / FS)[:, None] * rng.uniform(0.5, 1.5, 6)).astype(np.int64)
          for x in xs]
    report("đối chứng: D1 + sóng 15 Hz biên độ 60 LSB", xt)
    if a.log:
        ys = []
        for p in a.log:
            raw = np.loadtxt(p, delimiter=",", skiprows=1, dtype=np.int64, ndmin=2)[:, 1:7]
            ys.append(decimate(raw))
        f2 = report(f"mũ ({len(ys)} file LOG, 100 Hz → [1,3,3,1]/8 → 50 Hz)", ys)
        if f1 is not None and f2 is not None:
            print("tỉ số mũ / D1 theo trục: " + ", ".join(f"{c} {b / max(a_, 1e-9):.1f}×" for c, a_, b in zip(CH, f1, f2)))
            print("AI-14 bước 1: nếu tỉ số ≫ 1 ở các trục gia tốc thì cân nhắc lọc thêm [1,2,1]/4 (phương án a của AI-14)")


if __name__ == "__main__":
    main()
