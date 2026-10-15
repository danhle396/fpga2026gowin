# ml/src/cnn_numpy.py — họ mạng của A.4 bằng numpy thuần: N1 (GAP) và N2 / N2-S / N2-L (Flatten-Dense).
# Huấn luyện FP32, lượng tử INT8 theo A.5 (shift lũy thừa 2), suy luận số nguyên theo lô.
# Mỗi lớp Conv: k5 pad2 → ReLU → MaxPool2. Lớp 2 (dự trữ) bị che khi huấn luyện; khi xuất: weight 0, bias −2^30.
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

K, PAD, S_X, L0, C0 = 5, 2, 1.0 / 16, 128, 6
RESERVED = 2
ARCH = {                       # kênh ra của từng lớp Conv, đầu ra
    "n1":  ([16, 32], "gap"),
    "n2":  ([16, 16, 32], "flatten"),
    "n2s": ([8, 16, 16], "flatten"),
    "n2l": ([16, 24, 32], "flatten"),
}


def n_features(arch):
    chans, head = ARCH[arch]
    return chans[-1] if head == "gap" else chans[-1] * (L0 >> len(chans))


def init_params(arch, rng):
    chans, _ = ARCH[arch]
    P, ic = {"arch": arch}, C0
    for i, oc in enumerate(chans, 1):
        P[f"w{i}"] = (rng.standard_normal((oc, ic, K)) * np.sqrt(2.0 / (ic * K))).astype(np.float32)
        P[f"b{i}"] = np.zeros(oc, np.float32)
        ic = oc
    F = n_features(arch)
    P["wd"] = (rng.standard_normal((4, F)) * np.sqrt(1.0 / F)).astype(np.float32)
    P["bd"] = np.zeros(4, np.float32)
    return P


def weights(P):
    return [k for k in P if k != "arch"]


def _cols(x):
    xp = np.pad(x, ((0, 0), (PAD, PAD), (0, 0)))
    return sliding_window_view(xp, K, axis=1).reshape(x.shape[0], x.shape[1], -1)


def _pool(r):
    B, L, C = r.shape
    v = r.reshape(B, L // 2, 2, C)
    idx = v.argmax(2)
    return np.take_along_axis(v, idx[:, :, None, :], 2)[:, :, 0, :], idx


def _unpool(dm, idx):
    B, L2, C = dm.shape
    out = np.zeros((B, L2, 2, C), dm.dtype)
    np.put_along_axis(out, idx[:, :, None, :], dm[:, :, None, :], 2)
    return out.reshape(B, 2 * L2, C)


def forward(P, xq, cache=False):
    chans, head = ARCH[P["arch"]]
    a = xq.astype(np.float32) * S_X
    cs = []
    for i in range(1, len(chans) + 1):
        c = _cols(a)
        z = c @ P[f"w{i}"].reshape(P[f"w{i}"].shape[0], -1).T + P[f"b{i}"]
        a, idx = _pool(np.maximum(z, 0))
        cs.append((c, z, idx, a))
    f = a.mean(1) if head == "gap" else a.reshape(a.shape[0], -1)
    lg = f @ P["wd"].T + P["bd"]
    lg[:, RESERVED] = -1e9
    return (lg, cs, f) if cache else lg


def loss_grad(P, xq, y, w):
    chans, head = ARCH[P["arch"]]
    lg, cs, f = forward(P, xq, cache=True)
    B = len(y)
    z = lg - lg.max(1, keepdims=True)
    p = np.exp(z)
    p /= p.sum(1, keepdims=True)
    loss = float(-(w * np.log(p[np.arange(B), y] + 1e-12)).sum() / w.sum())
    d = p
    d[np.arange(B), y] -= 1
    d *= (w / w.sum())[:, None]
    d[:, RESERVED] = 0
    g = {"wd": d.T @ f, "bd": d.sum(0)}
    df = d @ P["wd"]
    a_last = cs[-1][3]
    if head == "gap":
        da = np.repeat(df[:, None, :] / a_last.shape[1], a_last.shape[1], 1)
    else:
        da = df.reshape(a_last.shape)
    for i in range(len(chans), 0, -1):
        c, zz, idx, _ = cs[i - 1]
        W = P[f"w{i}"]
        oc, ic = W.shape[0], W.shape[1]
        dz = _unpool(da, idx) * (zz > 0)
        g[f"w{i}"] = (dz.reshape(-1, oc).T @ c.reshape(-1, ic * K)).reshape(W.shape)
        g[f"b{i}"] = dz.sum((0, 1))
        if i > 1:
            dc = (dz @ W.reshape(oc, -1)).reshape(B, -1, ic, K)
            L = dc.shape[1]
            dxp = np.zeros((B, L + 2 * PAD, ic), np.float32)
            for k in range(K):
                dxp[:, k:k + L, :] += dc[:, :, :, k]
            da = dxp[:, PAD:-PAD, :]
    return loss, g


class Adam:
    def __init__(self, P, lr=2e-3, wd=1e-4):
        self.lr, self.wd, self.t = lr, wd, 0
        self.m = {k: np.zeros_like(P[k]) for k in weights(P)}
        self.v = {k: np.zeros_like(P[k]) for k in weights(P)}

    def step(self, P, g, lr):
        self.t += 1
        for k in weights(P):
            gk = g[k] + (self.wd * P[k] if k.startswith("w") else 0)
            self.m[k] = 0.9 * self.m[k] + 0.1 * gk
            self.v[k] = 0.999 * self.v[k] + 0.001 * gk * gk
            mh = self.m[k] / (1 - 0.9 ** self.t)
            vh = self.v[k] / (1 - 0.999 ** self.t)
            P[k] -= (lr * mh / (np.sqrt(vh) + 1e-8)).astype(np.float32)


def augment(xq, rng):
    """Gương trái–phải (AY, GX, GZ đổi dấu), lệch biên độ ±10 %, nhiễu ±1 mức."""
    x = xq.astype(np.float32)
    flip = rng.random(len(x)) < 0.5
    x[flip] = x[flip] * np.array([1, -1, 1, -1, 1, -1], np.float32)
    x *= rng.uniform(0.9, 1.1, (len(x), 1, 6)).astype(np.float32)
    x += rng.integers(-1, 2, x.shape)
    return np.clip(np.round(x), -128, 127).astype(np.int8)


def train(arch, X, y, rng, epochs=30, batch=256, per_epoch=16384, fall_frac=0.3, lr=2e-3, log=None, ema=0.0):
    """ema > 0: trả về trung bình trượt mũ của trọng số (hệ số ema mỗi bước), không đổi quỹ đạo huấn luyện hay rng."""
    P = init_params(arch, rng)
    opt = Adam(P, lr)
    E = {k: P[k].copy() for k in weights(P)} if ema else None
    pos, neg = np.flatnonzero(y != 0), np.flatnonzero(y == 0)
    steps = per_epoch // batch
    for ep in range(epochs):
        idx = np.concatenate([rng.choice(pos, int(per_epoch * fall_frac)),
                              rng.choice(neg, per_epoch - int(per_epoch * fall_frac), replace=False)])
        rng.shuffle(idx)
        lr_ep = lr * 0.5 * (1 + np.cos(np.pi * ep / epochs))
        tot = 0.0
        for s in range(steps):
            b = idx[s * batch:(s + 1) * batch]
            loss, g = loss_grad(P, augment(X[b], rng), y[b].astype(np.int64), np.ones(len(b), np.float32))
            opt.step(P, g, lr_ep)
            if E is not None:
                for k in E:
                    E[k] = (ema * E[k] + (1 - ema) * P[k]).astype(np.float32)
            tot += loss
        if log:
            log(f"    epoch {ep + 1:2d}/{epochs}  loss {tot / steps:.4f}")
    if E is not None:
        P.update(E)
    return P


# ------------------------------------------------------------------ INT8 (A.5)
def int_forward(X, Q, batch=2048):
    """Suy luận số nguyên theo lô, đúng từng bit với golden_model.forward."""
    nl = len(Q["n"])
    lg_all = []
    for s in range(0, len(X), batch):
        a = X[s:s + batch].astype(np.int64)
        for i in range(1, nl + 1):
            w, b, n = Q[f"w{i}"], Q[f"b{i}"], Q["n"][i - 1]
            acc = _cols(a) @ w.reshape(w.shape[0], -1).astype(np.int64).T + b.astype(np.int64)
            assert np.abs(acc).max() < 2**31
            r = np.where(acc <= 0, 0, np.minimum(acc >> n, 127))
            a = r.reshape(r.shape[0], r.shape[1] // 2, 2, r.shape[2]).max(2)
        if Q["head"] == "gap":
            f = a.sum(1) >> (a.shape[1].bit_length() - 1)
        else:
            f = a.reshape(a.shape[0], -1)
        lg_all.append(f @ Q["wd"].astype(np.int64).T + Q["bd"].astype(np.int64))
    lg = np.concatenate(lg_all)
    assert np.abs(lg).max() < 2**31
    srt = np.sort(lg, 1)
    return lg.argmax(1), lg, srt[:, -1] - srt[:, -2]


def score(margin, shift):
    return np.clip(margin >> shift, 0, 127)


def quantize(P, Xcal, pct=99.99):
    """PTQ: thang kích hoạt theo phân vị pct; n lớn nhất sao cho |W| ≤ 127; bias + 2^(n−1) để requant làm tròn."""
    chans, head = ARCH[P["arch"]]
    _, cs, _ = forward(P, Xcal, cache=True)
    s_in, Q, n = S_X, {"head": head, "arch": P["arch"]}, []
    for i in range(1, len(chans) + 1):
        act = cs[i - 1][3]
        w, b = P[f"w{i}"].astype(np.float64), P[f"b{i}"].astype(np.float64)
        pos = act[act > 0]
        s_a = (np.percentile(pos, pct) if pos.size else 1.0) / 127
        ni = int(np.floor(np.log2(127 * s_a / (s_in * np.abs(w).max()))))
        ni = min(max(ni, 0), 31)
        s_w = s_a / (s_in * 2.0 ** ni)
        Q[f"w{i}"] = np.clip(np.round(w / s_w), -127, 127).astype(np.int64)
        Q[f"b{i}"] = (np.round(b / (s_in * s_w)) + (1 << (ni - 1) if ni > 0 else 0)).astype(np.int64)
        n.append(ni)
        s_in = s_in * s_w * 2.0 ** ni
    wd, bd = P["wd"].astype(np.float64), P["bd"].astype(np.float64)
    s_wd = np.abs(np.delete(wd, RESERVED, 0)).max() / 127
    Q["wd"] = np.clip(np.round(wd / s_wd), -127, 127).astype(np.int64)
    floor_comp = 0.5 * Q["wd"].sum(1) if head == "gap" else 0.0      # bù phần lấy sàn của GAP
    Q["bd"] = np.round(bd / (s_in * s_wd) + floor_comp).astype(np.int64)
    Q["wd"][RESERVED] = 0
    Q["bd"][RESERVED] = -(1 << 30)
    Q["n"] = n
    return Q


def golden_params(Q, score_shift):
    G = {k: Q[k] for k in Q if k[0] in "wb"}
    G.update(n=list(Q["n"]), head=Q["head"], score_shift=score_shift)
    return G
