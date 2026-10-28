import sys, numpy as np
sys.path.insert(0, r"d:\hoctap\fpga\fpga2026gowin\ml\src"); sys.path.insert(0, r"d:\hoctap\fpga\fpga2026gowin\tools")
import posture_model as pm, truc_cam_bien as tc
sys.stdout.reconfigure(encoding="utf-8")
_, marks = tc.doc(sys.argv[1]); b = np.load(sys.argv[2]); seg = tc.doan_giu(marks, len(b))
K = 9.80665 / 2048 / 1e4
mk = {k: m + "/" + ph for k, m, ph in marks}; cur = "-"; lab = []
for i in range(len(b)):
    cur = mk.get(i, cur); lab.append(cur)
p = pm.Posture(nguc=1); was = 0; tt = []
for i, r in enumerate(b):
    hb = p.huong; p.push(r); tt.append(pm.TEN[p.tt])
    if p.moving and not was: i0, hb0 = i, hb
    if was and not p.moving and abs(p.dh_cuoi * K) > 0.05:
        print(f"  đợt {i0/100:6.1f}–{i/100:6.1f}s  Δh {p.dh_cuoi*K:+.2f} m  hướng {hb0}→{p.huong}  ra {pm.TEN[p.tt]:12s} ({lab[i0]})")
    was = p.moving
n = 0
for m, (i0, i1) in seg.items():
    kv = tc.KY_VONG[m]; ok = tt[i1 - 1] == kv; n += ok
    print(f"{m:13s} → {tt[i1-1]:13s} {'✓' if ok else '✗ ' + kv}")
print("đúng", n, "/", len(seg))
