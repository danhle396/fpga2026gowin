"""Hiệu chuẩn gia tốc từ các đoạn giữ yên: tìm offset o (và tùy chọn hệ số k) sao cho |(v - o) / k| = 2048."""
import sys, numpy as np
sys.path.insert(0, r"d:\hoctap\fpga\fpga2026gowin\ml\src"); sys.path.insert(0, r"d:\hoctap\fpga\fpga2026gowin\tools")
import posture_model as pm, truc_cam_bien as tc
sys.stdout.reconfigure(encoding="utf-8")
s, marks = tc.doc(sys.argv[1]); seg = tc.doan_giu(marks, len(s))
V = np.array([s[i0:i1, :3].mean(0) for i0, i1 in seg.values()])
def fit(scale):
    p = np.zeros(6); p[3:] = 1
    for _ in range(50):                      # Gauss-Newton
        o, k = p[:3], p[3:] if scale else np.ones(3)
        u = (V - o) / k; n = np.linalg.norm(u, axis=1); r = n - 2048
        J = np.zeros((len(V), 6))
        J[:, :3] = -(u / n[:, None]) / k
        J[:, 3:] = -(u / n[:, None]) * u / k
        if not scale: J = J[:, :3]
        d = np.linalg.lstsq(J, -r, rcond=None)[0]
        p[:len(d)] += d
    o, k = p[:3], (p[3:] if scale else np.ones(3))
    return o, k, np.linalg.norm((V - o) / k, axis=1)
for sc in (False, True):
    o, k, n = fit(sc)
    print(("offset + hệ số" if sc else "chỉ offset    "), "o =", np.round(o).astype(int), "k =", np.round(k, 3), "|g| sau:", np.round(n).astype(int))
o, _, _ = fit(False)
b = np.clip(s.astype(np.int64) - np.r_[np.round(o).astype(int), 0, 0, 0], -32767, 32767)
np.save(sys.argv[2], b); print("đã lưu log đã trừ offset")
