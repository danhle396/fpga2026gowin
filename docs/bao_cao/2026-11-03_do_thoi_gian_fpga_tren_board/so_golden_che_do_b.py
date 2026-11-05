"""So lớp và SCORE FPGA trả về ở chế độ B (2.000 cửa sổ giả ngẫu nhiên, mỗi khung một mầm) với golden_model.forward.
  python -I -X utf8 so_golden_che_do_b.py do_lan1.log do_lan2.log
Chạy từ thư mục này. Log chỉ ghi lớp và SCORE từng khung, không ghi logit, nên phép so này không bao gồm logit."""
import pathlib, sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ml" / "src"))
from golden_model import forward  # noqa: E402

z = np.load(ROOT / "ml" / "out" / "n2_11_d1" / "params_int8.npz")
P = {k: z[k] for k in z.files}
P["n"], P["head"], P["score_shift"] = [int(v) for v in P["n"]], str(P["head"]), int(P["score_shift"])


def cua_so(mam):
    s, ra = mam, []
    for _ in range(768):
        lsb = s & 1
        s >>= 1
        if lsb:
            s ^= 0xB400
        ra.append(s & 0xFF)
    return np.array(ra, np.uint8).astype(np.int8).reshape(128, 6)


def doc_b(path):
    """Chế độ thứ hai trong log: chỉ số khung về 0 lần thứ hai."""
    khoi, r = 0, []
    for l in open(path, encoding="utf8", errors="replace"):
        p = l.strip().split(",")
        if p[0] != "F" or len(p) != 10 or not all(x.isdigit() for x in p[1:]):
            continue
        if p[1] == "0":
            khoi += 1
        if khoi == 2:
            r.append((int(p[1]), int(p[8]), int(p[9])))
    return r


gold = {}
for i in range(2000):
    mam = (0xACE1 ^ (((i + 1) * 0x9E37) & 0xFFFFFFFF)) & 0xFFFF
    c, sc, _ = forward(cua_so(mam or 1), P)
    gold[i] = (int(c), int(sc))
print("golden: lop", {k: sum(1 for v in gold.values() if v[0] == k) for k in sorted({v[0] for v in gold.values()})},
      "; so gia tri SCORE khac nhau:", len({v[1] for v in gold.values()}))
for f in sys.argv[1:]:
    r = doc_b(f)
    sai = [x for x in r if gold[x[0]] != (x[1], x[2])]
    print(f, ":", len(r) - len(sai), "/", len(r), "khung trung lop va SCORE; sai dau:", sai[:5])
