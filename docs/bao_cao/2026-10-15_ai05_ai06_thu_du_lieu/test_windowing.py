# Thử tools/windowing.py bằng file LOG giả dựng từ D1 (nội suy 50 → 100 Hz).
import pathlib
import subprocess
import sys

import numpy as np
sys.stdout.reconfigure(encoding="utf8")

ROOT = pathlib.Path(r"D:\hoctap\fpga\fpga2026gowin")
S = pathlib.Path(r"C:\Users\ADMIN\AppData\Local\Temp\claude\d--hoctap-fpga-fpga2026gowin\4f873fbe-983f-43f7-9d9d-b0d332537d87\scratchpad\win_test")
raw_dir = S / "raw"
if S.exists():
    import shutil
    shutil.rmtree(S)
raw_dir.mkdir(parents=True)
D = np.load(ROOT / "ml/data/public/d1_trials_50hz.npz")


def up(i):
    x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]].astype(np.int64)
    u = np.empty((2 * len(x) - 1, 6), np.int64)
    u[0::2] = x
    u[1::2] = (x[:-1] + x[1:]) // 2
    return u


def write(name, raw, btn=None, gap_at=None):
    t = np.arange(len(raw)) * 10
    if gap_at is not None:
        t[gap_at:] += 30
    btn = np.zeros(len(raw), np.int64) if btn is None else btn
    with open(raw_dir / name, "w", newline="\n") as f:
        f.write("t_ms,ax,ay,az,gx,gy,gz,btn,wear\n")
        for k in range(len(raw)):
            f.write(f"{t[k]}," + ",".join(str(int(v)) for v in raw[k]) + f",{btn[k]},1\n")


falls = [i for i in np.flatnonzero((D["subject"] == 101) & (D["act"] == 901))][:5]
exp_ev = {}
for n, i in enumerate(falls, 1):
    write(f"s01_nga_truoc_{n:02d}.csv", up(i))
    exp_ev[f"s01_nga_truoc_{n:02d}"] = [2 * int(D["event"][i])]
parts, btn, evs, pos = [], [], [], 0
for i in [j for j in np.flatnonzero((D["subject"] == 102) & (D["act"] == 910))][:5]:
    u = up(i)
    e = 2 * int(D["event"][i])
    b = np.zeros(len(u), np.int64)
    b[max(0, e - 80):e + 80] = 1
    parts += [u, np.repeat(u[-1:], 600, 0)]
    btn += [b, np.zeros(600, np.int64)]
    evs.append(pos + e)
    pos += len(u) + 600
write("s02_roi_mu_01.csv", np.concatenate(parts), np.concatenate(btn))
exp_ev["s02_roi_mu_01"] = evs
walk = np.flatnonzero((D["subject"] == 103) & (D["act"] == 801))[0]
write("s02_di_bo_01.csv", up(walk))
write("s03_di_bo_02.csv", up(walk), gap_at=500)              # mất mẫu → phải bị bỏ
write("s03_nhay_mua_01.csv", up(walk))                        # tên lạ → phải bị bỏ

for args, out in ((["--include-falls"], "all.npz"), (["--only-falls"], "d3.npz")):
    r = subprocess.run([sys.executable, "-I", str(ROOT / "tools/windowing.py"), str(raw_dir), "--out", str(S / out),
                        "--plot", str(S / "plot")] + args, capture_output=True, text=True, encoding="utf8")
    print(r.stdout, r.stderr[-500:])

# kiểm vị trí sự kiện: dựng lại sự kiện từ p của cửa sổ dương
z = np.load(S / "all.npz")
ok = True
for name, ev in exp_ev.items():
    subj, act_name, trial = name.split("_")[0], "_".join(name.split("_")[1:-1]), int(name.split("_")[-1])
    code = {"nga_truoc": 951, "roi_mu": 701}[act_name]
    m = (z["act"] == code) & (z["trial"] == trial) & (z["subject"] == 200 + int(subj[1:])) & (z["y"] != 0)
    n_pos = int(m.sum())
    ok &= n_pos == 3 * len(ev)
    print(f"{name}: {len(ev)} sự kiện, {n_pos} cửa sổ dương (mong đợi {3 * len(ev)})")
# so điểm sự kiện tìm được với điểm của D1 (x2, sai khác do nội suy ≤ 1 mẫu 100 Hz)
sys.path.insert(0, str(ROOT / "tools"))
import windowing as w  # noqa: E402
for name, ev in exp_ev.items():
    _, raw, btn, _ = w.read_log(raw_dir / f"{name}.csv")
    mode = w.ACTS["_".join(name.split("_")[1:-1])][2]
    got = w.find_events(raw, btn, mode)
    d = [abs(a - b) for a, b in zip(got, ev)]
    ok &= len(got) == len(ev) and max(d) <= 1
    print(f"{name}: điểm sự kiện tìm được {got} so với D1×2 {ev}, lệch lớn nhất {max(d)}")
print("TẤT CẢ PASS" if ok else "CÓ FAIL")
