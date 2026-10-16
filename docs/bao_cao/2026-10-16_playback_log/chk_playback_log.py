# so playback_log.run_file với mã máy app_core.c (m0_test chế độ 8) trên cùng luồng 100 Hz, mô hình N2 11 người
import pathlib, struct, sys
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, m0_test as mt, playback_log as pl, safety_model as sm
D = np.load(ROOT / "ml/data/public/d1_trials_50hz.npz")
parts = []
for act in (901, 815, 910, 806, 905, 815):
    i = np.flatnonzero((D["act"] == act) & (D["subject"] == 109))[0]
    x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]].astype(np.int64)
    up = np.empty((2 * len(x) - 1, 6), np.int64); up[0::2] = x; up[1::2] = (x[:-1] + x[1:]) // 2
    parts += [up, np.repeat(up[-1:], 400, 0)]
raw = np.concatenate(parts).astype(np.int16)
Q, ss = pl.load_params(ROOT / "ml/out/n2_11_d1/params_int8.npz")
t_score, tilt, lat = 8, 1, 3
blob = mt.cnn_blob(Q, []) + struct.pack("<IBBBx3hxx", len(raw), t_score, tilt, lat, 0, 0, 0)
exp, cancel = pl.run_file(raw, Q, ss, dict(t_score=t_score), lat, 2000)
blob += raw.astype("<i2").tobytes() + cancel.tobytes()
_, out = mt.run(8, 0, blob, max_insn=8_000_000_000)
got, i = [], 0
while i < len(out):
    if out[i] == ord("R"): i += 4
    else: got.append((struct.unpack("<I", out[i + 1:i + 5])[0], out[i + 5], out[i + 6])); i += 7
print(f"{len(raw)/100:.0f} s; firmware {len(got)} lần đổi trạng thái, playback_log {len(exp)}; TRÙNG: {got == exp}")
print("chuỗi:", [ (t, sm.NAMES[s]) for t, s, _ in exp][:20]); print("số lần nhấn hủy:", int((np.diff(np.r_[0, cancel]) == 1).sum()))
