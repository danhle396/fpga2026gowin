# Phân bố az_tb (độ nghiêng đầu, LSB, 2048 = thẳng) và still_run lúc vào PRE_ALARM: ngã nằm thật so với báo giả.
import sys
import numpy as np
sys.path.insert(0, r"D:\hoctap\fpga\fpga2026gowin\tools")
sys.path.insert(0, r"D:\hoctap\fpga\fpga2026gowin\ml\src")
sys.stdout.reconfigure(encoding="utf8")
import playback_d1 as pb   # noqa: E402
import cnn_numpy as cn     # noqa: E402
import safety_model as sm  # noqa: E402

D = np.load(r"D:\hoctap\fpga\fpga2026gowin\ml\data\public\d1_trials_50hz.npz")
M = r"D:\hoctap\fpga\fpga2026gowin\ml\out\n2_d1\loso_params.npz"


def play_detail(x, cls, sc, cfg):
    fsm = sm.Safety(cfg, 0)
    blk = sm.Blocks(300, 250, 16)
    ev = [((128 + 16 * k) * 20 + 40, 1, int(cls[k]), int(sc[k])) for k in range(len(cls))]
    for i in range(len(x)):
        if blk.push(x[i]):
            ev.append(((i + 1) * 20, 2, blk.still_run, blk.az_tb))
    ev.sort(key=lambda e: (e[0], e[1]))
    j = 0
    for t in range(0, len(x) * 20 + 2001, 10):
        while j < len(ev) and ev[j][0] <= t:
            _, typ, a, b = ev[j]
            fsm.on_result(a, b) if typ == 1 else fsm.on_block(a, b)
            j += 1
        fsm.tick(t, 1, 0)
        if fsm.events & sm.EV_STATE and fsm.st == sm.PRE_ALARM:
            return fsm.az_tb, fsm.still_run
    return None


true_az, false_az = [], []
for s in np.unique(D["subject"]):
    Q, ss = pb.load_fold(M, s)
    for i in np.flatnonzero(D["subject"] == s):
        act = int(D["act"][i])
        if not (act in pb.LYING or 800 <= act < 900):
            continue
        x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]]
        q = pb.q8(x)
        if len(q) < 128:
            continue
        W = np.stack([q[n - 128:n] for n in range(128, len(q) + 1, 16)])
        c, _, mg = cn.int_forward(W, Q)
        r = play_detail(x, c, cn.score(mg, ss), dict(t_score=8))
        if r:
            (true_az if act >= 900 else false_az).append((r[0], act))
ta = np.array([a for a, _ in true_az]); fa = np.array([a for a, _ in false_az])
print(f"ngã nằm tới PRE_ALARM: {len(ta)}; az_tb trung vị {np.median(ta):.0f}, p90 {np.percentile(ta, 90):.0f}, max {ta.max()}")
print(f"báo giả: {len(fa)}; az_tb: {sorted((int(a), act) for a, act in false_az)}")
for thr in (1450, 1200, 1024, 800, 600, 400):
    print(f"  T_TILT {thr:5d} ({np.degrees(np.arccos(min(thr / 2048, 1))):.0f}°): giữ {np.mean(ta < thr) * 100:.1f} % ngã nằm, "
          f"còn {int(np.sum(fa < thr))}/{len(fa)} báo giả")
print(f"ngã nằm: az_tb nhỏ nhất {ta.min()}, số cú có az_tb < -1450: {int(np.sum(ta < -1450))}, < -1024: {int(np.sum(ta < -1024))}")
for lo in (1450, 1600, 1800):
    keep = np.mean((ta < 1450) & (ta > -lo)) * 100
    left = int(np.sum((fa < 1450) & (fa > -lo)))
    print(f"  hai phía −{lo} < az_tb < 1450: giữ {keep:.1f} % ngã nằm, còn {left}/{len(fa)} báo giả")
