#!/usr/bin/env python
# tools/plot_d1.py — vẽ tín hiệu ở đầu của 20 kiểu ngã trong D1, canh theo điểm va chạm (bằng chứng cho AI-13).
#   python tools/plot_d1.py ml/data/public/d1_trials_50hz.npz docs/bao_cao/<thư mục>
import argparse
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ACC_LSB_PER_G = 2048.0
PRE, POST = 150, 250          # mẫu 50 Hz: 3 s trước, 5 s sau điểm va chạm


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="vẽ 20 kiểu ngã D1 canh theo điểm va chạm (AI-13)")
    ap.add_argument("npz", help="ml/data/public/d1_trials_50hz.npz")
    ap.add_argument("out", help="thư mục ghi hình")
    a = ap.parse_args()
    d = np.load(a.npz)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    codes = sorted(set(int(c) for c in d["act"] if c >= 900))
    t = np.arange(-PRE, POST) / 50.0
    rows = []
    for name, ylab, ylim in (("d1_nga_do_lon_gia_toc.png", "|a| (g)", (0, 6)),
                             ("d1_nga_goc_nghieng.png", "góc nghiêng so với phương đứng (độ)", (0, 180))):
        fig, axs = plt.subplots(4, 5, figsize=(20, 12), sharex=True, sharey=True)
        for ax, code in zip(axs.ravel(), codes):
            seg = []
            for i in np.flatnonzero(d["act"] == code):
                s, n, e = int(d["start"][i]), int(d["length"][i]), int(d["event"][i])
                if e - PRE < 0 or e + POST > n:
                    continue
                a = d["data"][s + e - PRE:s + e + POST, :3] / ACC_LSB_PER_G
                mag = np.linalg.norm(a, axis=1)
                seg.append(mag if ylim[1] == 6 else np.degrees(np.arccos(np.clip(a[:, 2] / np.maximum(mag, 1e-6), -1, 1))))
            seg = np.array(seg)
            if len(seg):
                lo, med, hi = np.percentile(seg, [10, 50, 90], axis=0)
                ax.fill_between(t, lo, hi, alpha=0.3)
                ax.plot(t, med)
                if ylim[1] == 180:
                    rows.append((code, len(seg), np.median(seg[:, -50:]), (np.median(seg[:, -50:], axis=1) > 45).mean() * 100))
            ax.axvline(0, color="k", lw=0.5)
            ax.set_title(f"{code}  (n = {len(seg)})")
            ax.set_ylim(*ylim)
        for ax in axs[-1]:
            ax.set_xlabel("thời gian quanh điểm va chạm (s)")
        for ax in axs[:, 0]:
            ax.set_ylabel(ylab)
        fig.suptitle("D1, cảm biến ở đầu: trung vị và dải 10–90 % của mọi lần ngã, theo từng kiểu")
        fig.tight_layout()
        fig.savefig(out / name, dpi=80)
        plt.close(fig)
    lines = ["kiểu ngã | số lần vẽ được | góc nghiêng trung vị ở giây 4–5 sau va chạm (độ) | % số lần có góc đó > 45°"]
    lines += ["%d | %d | %.0f | %.0f" % r for r in rows]
    (out / "d1_goc_nghieng_sau_nga.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
