"""Sinh so_lieu.c: mô hình N2 đang chạy trên FPGA (ml/out/n2_11_d1), 6 cửa sổ thử và đáp án golden.
  sinh_so_lieu.py <file ra>"""
import pathlib, sys
import numpy as np

ROOT = pathlib.Path(r"D:\hoctap\fpga\fpga2026gowin")
sys.path.insert(0, str(ROOT / "ml" / "src"))
from golden_model import forward  # noqa: E402

z = np.load(ROOT / "ml" / "out" / "n2_11_d1" / "params_int8.npz")
P = {k: z[k] for k in z.files}
P["n"], P["head"], P["score_shift"] = [int(v) for v in P["n"]], str(P["head"]), int(P["score_shift"])


def lfsr():
    s, out = 0xACE1, []
    for _ in range(768):
        lsb = s & 1
        s >>= 1
        if lsb:
            s ^= 0xB400
        out.append(s & 0xFF)
    return np.array(out, np.uint8).astype(np.int8).reshape(128, 6)


d = np.load(ROOT / "ml" / "data" / "public" / "d1_windows.npz")
rng = np.random.default_rng(9)                     # cùng mầm với tools/m0_test.py
i_fall = rng.choice(np.flatnonzero(d["y"] == 3), 1)[0]
i_norm = rng.choice(np.flatnonzero(d["y"] == 0), 1)[0]
VAO = [("LFSR", lfsr()), ("toan_0", np.zeros((128, 6), np.int8)), ("toan_+127", np.full((128, 6), 127, np.int8)),
       ("toan_-128", np.full((128, 6), -128, np.int8)), ("D1_FALL", d["X"][i_fall]), ("D1_NORMAL", d["X"][i_norm])]


def mang(ten, kieu, v):
    v = [int(x) for x in np.asarray(v).ravel()]
    dong = [", ".join(map(str, v[i:i + 24])) for i in range(0, len(v), 24)]
    return f"static const {kieu} {ten}[{len(v)}] = {{\n" + ",\n".join(dong) + "\n};\n"


s = ['#include "so_lieu.h"\n']
nl = len(P["n"])
for i in range(1, nl + 1):
    s.append(mang(f"w{i}", "int8_t", P[f"w{i}"]))
    s.append(mang(f"b{i}", "int32_t", P[f"b{i}"]))
s.append(mang("wd", "int8_t", P["wd"]))
s.append(mang("bd", "int32_t", P["bd"]))
lop = ", ".join(f"{{ {P[f'w{i}'].shape[0]}, {P[f'w{i}'].shape[1]}, {P['n'][i - 1]}, w{i}, b{i} }}" for i in range(1, nl + 1))
s.append(f"const cnn_model_t MO_HINH = {{ {nl}, {1 if P['head'] == 'gap' else 0}, {P['score_shift']}, {{ {lop} }}, "
         f"{P['wd'].shape[1]}, wd, bd }};\n")
s.append(f"const int8_t VAO[{len(VAO)}][768] = {{\n")
for ten, x in VAO:
    v = np.asarray(x, np.int8).ravel().tolist()
    s.append("{" + ",".join(map(str, v)) + "},\n")
s.append("};\n")
kq = []
for ten, x in VAO:
    c, sc, lg = forward(x, P)
    kq.append((ten, int(c), int(sc), [int(v) for v in lg]))
    print(ten, "lop", int(c), "score", int(sc), "logit", [int(v) for v in lg])
assert kq[0][3] == [63183, -158442, -1073741824, 63644], "LFSR phai trung selftest_expect_v3_e2_n2.h"
s.append("const dap_an_t DAP_AN[%d] = {\n" % len(VAO))
for ten, c, sc, lg in kq:
    logit = ", ".join(("(-2147483647 - 1)" if v == -2147483648 else str(v)) for v in lg)
    s.append(f'  {{ "{ten}", {{ {logit} }}, {c}, {sc} }},\n')
s.append("};\n")
pathlib.Path(sys.argv[1]).write_text("".join(s), encoding="utf8")
print("OK", len(VAO), "cua so; tong weight", sum(P[f"w{i}"].size for i in range(1, nl + 1)) + P["wd"].size, "byte")
