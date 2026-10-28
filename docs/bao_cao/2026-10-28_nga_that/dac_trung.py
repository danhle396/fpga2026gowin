import sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")


def doc(path):
    rows, marks, ns = [], [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line.startswith("# >>> TU THE"):
            _, _, _, _, m, ph = line.split()
            marks.append((len(rows), m, ph))
            continue
        if line.startswith("N,"):
            ns.append((len(rows), line))
            continue
        p = line.split(",")
        if len(p) == 9 and p[0].isdigit():
            try:
                rows.append([int(x) for x in p[1:7]])
            except ValueError:
                pass
    return np.array(rows, np.int64), marks, ns


def tilt(a):
    k = 50
    c = np.cumsum(np.vstack([np.zeros((1, 3)), a[:, :3].astype(float)]), 0)
    lp = (c[k:] - c[:-k]) / k
    lp = np.vstack([np.repeat(lp[:1], k // 2, 0), lp, np.repeat(lp[-1:], k - k // 2 - 1, 0)])
    return np.degrees(np.arccos(np.clip(lp[:, 2] / np.linalg.norm(lp, axis=1), -1, 1)))


for path in sys.argv[1:]:
    b, marks, ns = doc(path)
    mag = np.linalg.norm(b[:, :3], axis=1) / 2048
    w = np.linalg.norm(b[:, 3:], axis=1) / 16.4
    tl = tilt(b)
    print(f"== {path.split('/')[-1]}: {len(b)} mẫu")
    print(f"{'lần':14s} {'đỉnh g':>6s} {'nghiêng trước':>13s} {'max sau':>7s} {'cuối':>5s} {'quay ±1.5s':>10s} {'ω max':>6s}  nga.c")
    starts = [(k, m) for k, m, ph in marks if ph == "doi"]
    for i, (k0, m) in enumerate(starts):
        k1 = starts[i + 1][0] if i + 1 < len(starts) else len(b)
        if m == "dung":
            continue
        seg = slice(k0, k1)
        p = k0 + int(np.argmax(mag[seg]))
        pre = tl[max(0, p - 150):max(1, p - 50)].mean()
        post = tl[p:min(len(b), p + 400)].max()
        end = tl[max(p, k1 - 150):k1].mean()
        rot = w[max(0, p - 150):p + 150].sum() / 100
        ev = [l.split(",")[2] + "/" + l.split(",")[3].split("=")[1] + "/" + str(int(l.split(",")[4].split("=")[1]) / 100) + "g"
              for r, l in ns if k0 <= r < k1]
        print(f"{m:14s} {mag[p]:6.2f} {pre:13.0f} {post:7.0f} {end:5.0f} {rot:10.0f} {w[p-150:p+150].max():6.0f}  {' '.join(ev)}")
