# dựng "buổi thử giả" từ D1 (người 105 → s01, 109 → s02) dưới dạng file LOG 100 Hz đặt tên theo docs/data_protocol.md
import pathlib, sys
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[3]; out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
D = np.load(ROOT / "ml/data/public/d1_trials_50hz.npz")
def up(i):
    x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]].astype(np.int64)
    u = np.empty((2 * len(x) - 1, 6), np.int64); u[0::2] = x; u[1::2] = (x[:-1] + x[1:]) // 2
    return u
def write(name, u, btn=None):
    btn = np.zeros(len(u), int) if btn is None else btn
    with open(out / name, "w", newline="\n") as f:
        f.write("t_ms,ax,ay,az,gx,gy,gz,btn,wear\n")
        for k, r in enumerate(u):
            f.write(f"{10*k}," + ",".join(str(int(v)) for v in r) + f",{btn[k]},1\n")
plan = {"nga_truoc": 901, "nga_sau": 910, "nga_trai": 902, "nga_dung_day": 905, "nga_ngoi": 903}
for sid, subj in (("s01", 105), ("s02", 109)):
    for name, act in plan.items():
        idx = np.flatnonzero((D["act"] == act) & (D["subject"] == subj))
        for n, i in enumerate(idx[:4], 1):
            write(f"{sid}_{name}_{n:02d}.csv", up(i))
    for name, act in (("di_bo", 801), ("nam_xuong", 815), ("cui_nhat", 806)):
        idx = np.flatnonzero((D["act"] == act) & (D["subject"] == subj))
        u = np.concatenate([up(i) for i in idx])          # mọi lần của hoạt động đó nối thành một file dài
        write(f"{sid}_{name}_01.csv", u)
    # va mũ khi đang đội: đi bộ + 3 xung chèn vào, người phụ bấm SW6 quanh mỗi xung
    u = np.concatenate([up(i) for i in np.flatnonzero((D["act"] == 801) & (D["subject"] == subj))])[:6000].copy()
    btn = np.zeros(len(u), int)
    for c in (1500, 3000, 4500):
        u[c:c + 3, 0] += 8000; btn[c - 80:c + 80] = 1
    write(f"{sid}_va_mu_01.csv", u, btn)
print(len(list(out.glob("*.csv"))), "file ->", out)
