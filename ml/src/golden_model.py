# ml/src/golden_model.py — SPEC v3. Chỉ dùng số nguyên. Mảng xếp "vị trí trước": (L, C).
import numpy as np

K, PAD, AMAX = 5, 2, 127


def conv1d(x, w, b):
    """x: (L, IC); w: (OC, IC, K) int8; b: (OC,) int32 -> acc (L, OC) int64."""
    L = x.shape[0]
    xp = np.pad(x.astype(np.int64), ((PAD, PAD), (0, 0)))
    acc = np.zeros((L, w.shape[0]), np.int64)
    for k in range(K):
        acc += xp[k:k + L] @ w[:, :, k].astype(np.int64).T
    return acc + b.astype(np.int64)


def requant_relu(acc, n):
    """A.5: acc <= 0 -> 0; ngược lại min(acc >> n, 127). Dịch số học, không làm tròn."""
    return np.where(acc <= 0, 0, np.minimum(acc >> n, AMAX))


def maxpool2(a):
    L, C = a.shape
    return a.reshape(L // 2, 2, C).max(axis=1)


def forward(x, P, trace=None):
    """x: (128, 6) int8, hàng = mẫu (đúng thứ tự byte trong khung SPI).
    P: w1,b1,w2,b2[,w3,b3], wd (4, F), bd (4,), n [n1, n2, ...], head "gap" hoặc "flatten", score_shift."""
    a = x.astype(np.int64)
    for i, n in enumerate(P["n"], start=1):
        acc = conv1d(a, P[f"w{i}"], P[f"b{i}"])
        assert np.abs(acc).max() < 2**31, f"tràn accumulator lớp C{i}"
        a = maxpool2(requant_relu(acc, n))
        if trace is not None:
            trace[f"l{i}"] = a.copy()
    if P["head"] == "gap":
        f = a.sum(axis=0) >> (a.shape[0].bit_length() - 1)      # chia 32 bằng dịch, lấy sàn
    else:
        f = a.reshape(-1)                                       # flatten: i = t*C + c
    logits = P["wd"].astype(np.int64) @ f + P["bd"].astype(np.int64)
    assert np.abs(logits).max() < 2**31
    cls = int(np.argmax(logits))                                # bằng nhau -> chỉ số nhỏ
    top2 = int(np.max(np.delete(logits, cls)))
    score = int(np.clip((int(logits[cls]) - top2) >> P["score_shift"], 0, 127))
    if trace is not None:
        trace["feat"], trace["logit"] = f, logits
    return cls, score, logits


# ---------- tiền xử lý trên MCU (A.2) ----------
def decimate(raw):
    """raw: (M, 6) int16 ở 100 Hz -> (M//2, 6) ở 50 Hz.
    y[n] = (r[2n-2] + 3*r[2n-1] + 3*r[2n] + r[2n+1] + 4) >> 3, với r[-2] = r[-1] = r[0]."""
    r = raw.astype(np.int64)
    r = np.vstack([r[:1], r[:1], r])
    i = 2 * np.arange(len(raw) // 2)
    return (r[i] + 3 * r[i + 1] + 3 * r[i + 2] + r[i + 3] + 4) >> 3


def q8(d, shifts=(7, 7, 7, 6, 6, 6)):
    s = np.array(shifts, np.int64)
    return np.clip((d + (1 << (s - 1))) >> s, -128, 127).astype(np.int8)


# ---------- khung SPI (A.7) ----------
def crc16(data, c=0xFFFF):
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c


def write_frame(seq, x):
    body = bytes([0xA5, seq & 0xFF]) + x.astype(np.int8).tobytes()
    c = crc16(body)
    return body + bytes([c >> 8, c & 0xFF])


def result_frame(seq, status, cls, score, logits, cycles, logit_shift=0):
    head = bytes([0x5A, seq & 0xFF, status, cls & 0xFF, score])
    c = crc16(head)
    head += bytes([c >> 8, c & 0xFF])
    tail = b"".join(int(np.clip(int(v) >> logit_shift, -32768, 32767)).to_bytes(2, "big", signed=True) for v in logits)
    tail += int(cycles).to_bytes(3, "big")
    c = crc16(tail)
    return head + tail + bytes([c >> 8, c & 0xFF])


def selftest_payload():
    """A.10: 768 byte từ LFSR Galois 16 bit, đa thức 0xB400, mầm 0xACE1."""
    s, out = 0xACE1, []
    for _ in range(768):
        lsb = s & 1
        s >>= 1
        if lsb:
            s ^= 0xB400
        out.append(s & 0xFF)
    return np.frombuffer(bytes(out), np.int8).reshape(128, 6)
