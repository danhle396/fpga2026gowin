# ml/src/rom_layout.py — bố trí ROM của E1 và E2 (A.6) và mô hình địa chỉ của engine E2. Một nguồn duy nhất cho
# tools/export_mem.py (sinh .mem cho engine E2).
import numpy as np


def n_layers(P):
    return len(P["n"])


def pack_e1(P):
    """E1 (RTL hiện có): W[oc][ic][k] của từng lớp Conv nối liền, rồi Dense [lớp][đặc trưng]. Trả về (list int8, bases)."""
    rom, bases = [], []
    for i in range(1, n_layers(P) + 1):
        bases.append(len(rom))
        rom += [int(v) for v in np.asarray(P[f"w{i}"]).reshape(-1)]
    bases.append(len(rom))
    rom += [int(v) for v in np.asarray(P["wd"]).reshape(-1)]
    return rom, bases


def pack_rom(P, lanes):
    """E2: mỗi từ = `lanes` weight, làn 0 ở byte thấp. Conv: BASE + (g*5 + k)*IC + ic. Dense: BASE + g*F + i."""
    rom, bases = [], []
    for i in range(1, n_layers(P) + 1):
        w = np.asarray(P[f"w{i}"])
        OC, IC, _ = w.shape
        bases.append(len(rom))
        for g in range(OC // lanes):
            for k in range(5):
                for ic in range(IC):
                    rom.append([int(w[g * lanes + p, ic, k]) for p in range(lanes)])
    wd = np.asarray(P["wd"])
    bases.append(len(rom))
    for g in range(4 // lanes):
        for i in range(wd.shape[1]):
            rom.append([int(wd[g * lanes + p, i]) for p in range(lanes)])
    return rom, bases


def unpack_rom(rom, bases, shapes, lanes):
    """Ngược của pack_rom: shapes = [(OC, IC), ...] của các lớp Conv, rồi F của Dense."""
    P = {}
    for i, (OC, IC) in enumerate(shapes[:-1], start=1):
        w = np.zeros((OC, IC, 5), np.int64)
        a = bases[i - 1]
        for g in range(OC // lanes):
            for k in range(5):
                for ic in range(IC):
                    for p in range(lanes):
                        w[g * lanes + p, ic, k] = rom[a][p]
                    a += 1
        P[f"w{i}"] = w
    F = shapes[-1]
    wd = np.zeros((4, F), np.int64)
    a = bases[-1]
    for g in range(4 // lanes):
        for i in range(F):
            for p in range(lanes):
                wd[g * lanes + p, i] = rom[a][p]
            a += 1
    P["wd"] = wd
    return P


def engine(x, P, lanes):
    """Mô hình địa chỉ của E2: mọi bộ nhớ là mảng 1 chiều, chỉ dùng bộ đếm tăng dần như RTL sẽ làm."""
    rom, bases = pack_rom(P, lanes)
    src = [int(v) for v in np.asarray(x).reshape(-1)]
    L, IC = 128, 6
    for li, n in enumerate(P["n"]):
        w, b = np.asarray(P[f"w{li + 1}"]), np.asarray(P[f"b{li + 1}"])
        OC = w.shape[0]
        dst = [0] * ((L // 2) * OC)
        wr = 0
        for j in range(L // 2):
            for g in range(OC // lanes):
                best = [None] * lanes
                for q in range(2):
                    t = 2 * j + q
                    acc = [int(b[g * lanes + p]) for p in range(lanes)]
                    sa = (t - 2) * IC
                    wa = bases[li] + g * 5 * IC
                    for run in range(5 * IC):                       # một dải liên tiếp, hai địa chỉ cùng +1
                        pos = t - 2 + run // IC
                        xv = src[sa + run] if 0 <= pos < L else 0   # padding = bỏ qua
                        for p in range(lanes):
                            acc[p] += rom[wa + run][p] * xv
                    for p in range(lanes):
                        best[p] = acc[p] if best[p] is None else max(best[p], acc[p])
                for p in range(lanes):                              # địa chỉ ghi cũng +1
                    v = best[p]
                    dst[wr] = 0 if v <= 0 else min(v >> n, 127)
                    wr += 1
        src, L, IC = dst, L // 2, OC
    feat = [sum(src[t * IC + c] for t in range(L)) >> 5 for c in range(IC)] if P["head"] == "gap" else src
    logits = []
    for g in range(4 // lanes):
        acc = [int(P["bd"][g * lanes + p]) for p in range(lanes)]
        for i, xv in enumerate(feat):
            for p in range(lanes):
                acc[p] += rom[bases[-1] + g * len(feat) + i][p] * xv
        logits += acc
    return np.array(logits, np.int64), bases, len(rom)


def acc_bound(P):
    """Biên |acc| xấu nhất cho từng kênh ra của từng lớp: Σ|w|·xmax + |b| (lớp đầu xmax = 128, sau đó 127)."""
    out, xmax = [], 128
    for i in range(1, n_layers(P) + 1):
        w, b = np.abs(np.asarray(P[f"w{i}"], np.int64)), np.abs(np.asarray(P[f"b{i}"], np.int64))
        out.append(int((w.reshape(w.shape[0], -1).sum(1) * xmax + b).max()))
        xmax = 127
    wd, bd = np.abs(np.asarray(P["wd"], np.int64)), np.abs(np.asarray(P["bd"], np.int64))
    out.append(int((wd.sum(1) * 127 + bd).max()))
    return out
