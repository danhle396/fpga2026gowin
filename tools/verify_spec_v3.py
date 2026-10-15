import json
import sys
import numpy as np

sys.stdout.reconfigure(encoding="utf8")
sys.path.insert(0, sys.argv[1])
from golden_model import *  # noqa: E402

ex = sys.argv[2]
ok = True


def check(name, cond):
    global ok
    ok &= bool(cond)
    print(("PASS  " if cond else "FAIL  ") + name)


# 1) N1 với weight hiện có của nhóm (bố trí ROM của E1: W[oc][ic][k]) so với golden_vectors.npz.
#    Shift đọc từ quant_params.json — cùng nguồn với src/cnn_params.vh của RTL (RA-01).
q = json.load(open(ex + "/quant_params.json", encoding="utf8"))
SH = [int(q["conv1_shift"]), int(q["conv2_shift"])]
W = np.array([int(v, 16) for v in open(ex + "/weights.mem").read().split()], dtype=np.int64)
W = np.where(W > 127, W - 256, W)
B = np.array([int(v, 16) for v in open(ex + "/bias.mem").read().split()], dtype=np.int64)
B = np.where(B >= 2**31, B - 2**32, B)
N1 = dict(w1=W[0:480].reshape(16, 6, 5), b1=B[0:16], w2=W[480:3040].reshape(32, 16, 5), b2=B[16:48],
          wd=W[3040:3168].reshape(4, 32), bd=B[48:52], n=SH, head="gap", score_shift=0)
d = np.load(ex + "/golden_vectors.npz")
m = 0
for x, e, c in zip(d["input_windows"], d["expected_logits"], d["expected_classes"]):
    cls, _, lg = forward(x, N1)
    m += np.array_equal(lg, e) and cls == c
check(f"golden_model (N1, shift {SH[0]}/{SH[1]} từ quant_params.json) khớp golden_vectors của nhóm AI: {m}/20", m == 20)

# 2) N2 chạy được + mô hình địa chỉ của engine E2 (ROM k-major, P làn) == golden, P = 1, 2, 4
r = np.random.default_rng(3)


def rnd_net(chs, head):
    P = {"n": [], "head": head, "score_shift": 4}
    ic, L = 6, 128
    for i, oc in enumerate(chs, start=1):
        P[f"w{i}"] = r.integers(-127, 128, (oc, ic, 5), dtype=np.int8)
        P[f"b{i}"] = r.integers(-4000, 4000, oc, dtype=np.int32)
        P["n"].append(int(r.integers(6, 10)))
        ic = oc
        L //= 2
    F = ic if head == "gap" else ic * L
    P["wd"] = r.integers(-127, 128, (4, F), dtype=np.int8)
    P["bd"] = r.integers(-4000, 4000, 4, dtype=np.int32)
    return P


from rom_layout import engine, pack_rom  # noqa: E402,F401  (một nguồn với tools/export_mem.py)


N2 = rnd_net([16, 16, 32], "flatten")
x = r.integers(-128, 128, (128, 6), dtype=np.int8)
tr = {}
c, s, lg = forward(x, N2, tr)
check(f"N2 chạy: l1{tr['l1'].shape} l2{tr['l2'].shape} l3{tr['l3'].shape} feat{tr['feat'].shape}",
      tr["l3"].shape == (16, 32) and tr["feat"].shape == (512,))
for lanes in (1, 2, 4):
    e, bases, words = engine(x, N2, lanes)
    check(f"engine E2 (P={lanes}) == golden cho N2; BASE={bases}, {words} từ", np.array_equal(e, lg))
for lanes in (1, 4):
    e, bases, words = engine(d["input_windows"][0], N1, lanes)
    check(f"engine E2 (P={lanes}) == golden cho N1 thật; BASE={bases}, {words} từ",
          np.array_equal(e, d["expected_logits"][0]))
xs = selftest_payload()
check(f"khung tự kiểm LFSR: min={xs.min()} max={xs.max()}, engine == golden",
      np.array_equal(engine(xs, N2, 4)[0], forward(xs, N2)[2]))

# 3) tiền xử lý
ex_a = {2048: 16, -2048: -16, 16384: 127, -16384: -128, 63: 0, 64: 1, 0: 0}
ex_g = {1640: 26, -1640: -26, 8192: 127, -8192: -128, 31: 0, 32: 1}
ga = {k: int(q8(np.array([[k] * 6]))[0, 0]) for k in ex_a}
gg = {k: int(q8(np.array([[k] * 6]))[0, 3]) for k in ex_g}
check(f"q8 gia tốc (shift 7): {ga}", ga == ex_a)
check(f"q8 gyro (shift 6): {gg}", gg == ex_g)
raw = np.tile(np.array([[1000, -1000, 2048, 5, -5, 0]]), (10, 1))
check("decimate: tín hiệu hằng giữ nguyên", np.array_equal(decimate(raw), raw[:5]))
alt = np.array([[(-1) ** i * 800] * 6 for i in range(40)])
check(f"decimate: thành phần 50 Hz bị triệt (|y| max = {np.abs(decimate(alt)[2:]).max()})",
      np.abs(decimate(alt)[2:]).max() <= 1)
f = np.array([10, 12.5, 25, 30, 40])
H = np.cos(np.pi * f / 100) ** 3
print("      đáp ứng [1,3,3,1]/8:", {float(a): f"{20 * np.log10(h):.1f} dB" for a, h in zip(f, H)})

# 4) CRC và khung
check("CRC-16/CCITT-FALSE('123456789') = 0x29B1", crc16(b"123456789") == 0x29B1)
fr = write_frame(7, x)
check(f"khung ghi {len(fr)} byte, CRC tự kiểm = 0", len(fr) == 772 and crc16(fr) == 0)
rf = result_frame(7, 0x01, c, s, lg, 243000)
check(f"khung đọc {len(rf)} byte: {rf[:7].hex()} | {rf[7:].hex()}",
      len(rf) == 20 and crc16(rf[:7]) == 0 and crc16(rf[7:]) == 0)


# 5) con số trong SPEC
def count(chs, head):
    ic, L, w, mac, bias = 6, 128, 0, 0, 0
    for oc in chs:
        w += oc * ic * 5
        mac += L * oc * ic * 5
        bias += oc
        ic = oc
        L //= 2
    F = ic if head == "gap" else ic * L
    return w + 4 * F, bias + 4, mac + 4 * F


print("      (W, bias, MAC)  N1:", count([16, 32], "gap"), "| N2:", count([16, 16, 32], "flatten"),
      "| N2-S:", count([8, 16, 16], "flatten"), "| N2-L:", count([16, 24, 32], "flatten"))
print("      biên |acc|: C1", 30 * 128 * 127, "| conv>=2", 80 * 127 * 127, "| dense32", 32 * 127 * 127,
      "| dense512", 512 * 127 * 127, "| 2^23 =", 2**23)
print("TẤT CẢ PASS" if ok else "CÓ LỖI")
