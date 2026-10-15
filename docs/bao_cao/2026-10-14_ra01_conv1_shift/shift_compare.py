"""So conv1_shift 7 với 8 bằng golden model trên tập validation và test của SisFall.
Chạy: python -I shift_compare.py <ml/src> <fpga_export> <sisfall npz>"""
import sys
import numpy as np

sys.stdout.reconfigure(encoding="utf8")
sys.path.insert(0, sys.argv[1])
from golden_model import forward  # noqa: E402

ex, npz = sys.argv[2], sys.argv[3]
W = np.array([int(v, 16) for v in open(ex + "/weights.mem").read().split()], dtype=np.int64)
W = np.where(W > 127, W - 256, W)
B = np.array([int(v, 16) for v in open(ex + "/bias.mem").read().split()], dtype=np.int64)
B = np.where(B >= 2**31, B - 2**32, B)
base = dict(w1=W[0:480].reshape(16, 6, 5), b1=B[0:16], w2=W[480:3040].reshape(32, 16, 5), b2=B[16:48],
            wd=W[3040:3168].reshape(4, 32), bd=B[48:52], head="gap", score_shift=0)
d = np.load(npz, allow_pickle=False)
NAMES = ["NORMAL", "SIT_LIE", "STUMBLE", "FALL"]


def metrics(y, p):
    cm = np.zeros((4, 4), int)
    for a, b in zip(y, p):
        cm[a, b] += 1
    f1 = []
    for c in range(4):
        tp = cm[c, c]
        pr = tp / max(cm[:, c].sum(), 1)
        rc = tp / max(cm[c, :].sum(), 1)
        f1.append(0 if pr + rc == 0 else 2 * pr * rc / (pr + rc))
    return cm, np.trace(cm) / cm.sum(), float(np.mean(f1)), f1, cm[3, 3] / cm[3].sum()


for split in ["validation", "test"]:
    X, y = d[f"{split}_features"], d[f"{split}_labels"].astype(int)
    preds = {}
    for n1 in (7, 8):
        P = dict(base, n=[n1, 8])
        pr, sat1, sat2, zero1, zero2, maxacc = [], 0, 0, 0, 0, 0
        for x in X:
            tr = {}
            c, _, lg = forward(x, P, tr)
            pr.append(c)
            sat1 += (tr["l1"] == 127).sum()
            sat2 += (tr["l2"] == 127).sum()
            zero1 += (tr["l1"] == 0).sum()
            zero2 += (tr["l2"] == 0).sum()
        pr = np.array(pr)
        preds[n1] = pr
        cm, acc, mf1, f1, rf = metrics(y, pr)
        n_l1, n_l2 = len(X) * 64 * 16, len(X) * 32 * 32
        print(f"[{split}, n={len(X)}] shift=({n1},8): acc={acc*100:.2f}%  macroF1={mf1:.4f}  "
              f"recallFALL={rf*100:.2f}%  F1/lớp=" + " ".join(f"{NAMES[i]}:{f1[i]:.3f}" for i in range(4)))
        print(f"    bão hòa 127 sau pool: l1 {sat1/n_l1*100:.3f}%  l2 {sat2/n_l2*100:.3f}%   "
              f"bằng 0: l1 {zero1/n_l1*100:.1f}%  l2 {zero2/n_l2*100:.1f}%")
        print("    confusion (hàng = thật):", cm.tolist())
    print(f"    hai shift cho cùng nhãn ở {np.mean(preds[7] == preds[8])*100:.2f}% cửa sổ\n")
