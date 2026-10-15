#!/usr/bin/env python
# tools/export_mem.py — xuất một mô hình INT8 thành mọi thứ RTL, firmware và HIL cần (việc AI-04).
#
#   python -I tools/export_mem.py --params ml/out/n2s_d1/params_int8.npz --engine e2 --lanes 1 --out <thư mục>
#   python -I tools/export_mem.py --export <fpga_export của nhóm AI> --engine e1 --out <thư mục>
#
# Ra:
#   weights.mem      E1: 1 weight/dòng (2 hex). E2: 1 từ = `lanes` weight/dòng, làn 0 ở byte thấp (A.6)
#   bias.mem         1 bias INT32/dòng (8 hex), thứ tự lớp 1, 2, (3), Dense
#   cnn_params.vh    shift, kích thước lớp, BASE của ROM, số làn, đầu ra, SCORE_SHIFT
#   vec_in.mem       N cửa sổ × 768 byte (i = t·6 + c);  vec_exp.mem  N × (4 logit, lớp);  vec_score.mem  N × SCORE
#   spi/spi_XX.bin   khung GHI v3 772 byte, SEQ = XX;  spi/res_XX.mem  khung ĐỌC 20 byte mong đợi (CYCLES = --cycles)
#   selftest_expect.h  kết quả mong đợi của khung tự kiểm LFSR (A.10, SEQ 0xEE) cho firmware (FW-14)
#   export_report.txt
# Kiểm (Pass của AI-04): đọc ngược weights.mem/bias.mem → golden ra đúng lớp và logit của mọi vector; biên |acc| < 2^31
# cho mọi kênh ra; với E2 còn chạy mô hình địa chỉ (rom_layout.engine) trên ROM đã xuất cho 3 vector.
import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
import rom_layout as rl  # noqa: E402
from golden_model import forward, result_frame, selftest_payload, write_frame  # noqa: E402


def load_params(a):
    if a.params:
        z = np.load(a.params)
        P = {k: z[k] for k in z.files}
        P["n"] = [int(v) for v in P["n"]]
        P["head"] = str(P["head"])
        P["score_shift"] = int(P["score_shift"])
        return P
    q = json.loads((a.export / "quant_params.json").read_text(encoding="utf8"))
    W = np.array([int(v, 16) for v in (a.export / "weights.mem").read_text().split()], np.int64)
    B = np.array([int(v, 16) for v in (a.export / "bias.mem").read_text().split()], np.int64)
    W = np.where(W > 127, W - 256, W)
    B = np.where(B >= 2**31, B - 2**32, B)
    return dict(w1=W[:480].reshape(16, 6, 5), b1=B[:16], w2=W[480:3040].reshape(32, 16, 5), b2=B[16:48],
                wd=W[3040:].reshape(4, 32), bd=B[48:], n=[int(q["conv1_shift"]), int(q["conv2_shift"])],
                head="gap", score_shift=int(q.get("score_shift", 0)))


def vectors(a, rng):
    X, tag = [], []
    if a.data and pathlib.Path(a.data).exists():
        d = np.load(a.data)
        for lab, name in ((3, "FALL"), (0, "NORMAL")):
            for i in rng.choice(np.flatnonzero(d["y"] == lab), 10, replace=False):
                X.append(d["X"][i]); tag.append(f"D1 {name} #{i}")
    X.append(selftest_payload()); tag.append("LFSR A.10")
    for v, t in ((127, "+127"), (-128, "-128"), (0, "0")):
        X.append(np.full((128, 6), v, np.int8)); tag.append(f"toàn {t}")
    X.append(np.tile(np.array([127, -128], np.int8), 384).reshape(128, 6)); tag.append("xen kẽ ±127")
    X.append((np.arange(768) % 256 - 128).astype(np.int8).reshape(128, 6)); tag.append("bậc thang")
    X.append(np.tile(np.array([[16, 0, 0, 127, 127, 127]], np.int8), (128, 1))); tag.append("gyro bão hòa")
    while len(X) < a.nvec:
        X.append(rng.integers(-128, 128, (128, 6)).astype(np.int8)); tag.append("ngẫu nhiên")
    return X[:a.nvec], tag[:a.nvec]


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--params", type=pathlib.Path)
    src.add_argument("--export", type=pathlib.Path)
    ap.add_argument("--engine", choices=["e1", "e2"], default="e2")
    ap.add_argument("--lanes", type=int, default=1, choices=[1, 2, 4])
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--data", default=str(ROOT / "ml" / "data" / "public" / "d1_windows.npz"))
    ap.add_argument("--nvec", type=int, default=50)
    ap.add_argument("--cycles", type=int, default=0, help="CYCLES ghi vào res_XX.mem (E1 đo được 699800)")
    ap.add_argument("--seed", type=int, default=4)
    a = ap.parse_args()
    P = load_params(a)
    nl = len(P["n"])
    if a.engine == "e1" and (nl != 2 or P["head"] != "gap"):
        raise SystemExit("E1 hiện có chỉ chạy N1 (2 Conv + GAP); dùng --engine e2 hoặc chờ RB-02b")
    out = a.out
    (out / "spi").mkdir(parents=True, exist_ok=True)
    rep = []

    def log(s):
        print(s)
        rep.append(s)

    # ---- ROM ----
    shapes = [tuple(np.asarray(P[f"w{i}"]).shape[:2]) for i in range(1, nl + 1)] + [np.asarray(P["wd"]).shape[1]]
    if a.engine == "e1":
        rom, bases = rl.pack_e1(P)
        lines = [f"{v & 0xFF:02X}" for v in rom]
        lanes = 1
    else:
        lanes = a.lanes
        rom, bases = rl.pack_rom(P, lanes)
        lines = ["".join(f"{w[p] & 0xFF:02X}" for p in reversed(range(lanes))) for w in rom]
    bias = np.concatenate([np.asarray(P[f"b{i}"]) for i in range(1, nl + 1)] + [np.asarray(P["bd"])]).astype(np.int64)
    (out / "weights.mem").write_text("\n".join(lines) + "\n", newline="\n")
    (out / "bias.mem").write_text("".join(f"{int(v) & 0xFFFFFFFF:08X}\n" for v in bias), newline="\n")
    log(f"{a.engine.upper()} P = {lanes}: {len(rom)} từ ROM weight, BASE {bases}, {len(bias)} bias, shift {P['n']}, "
        f"đầu ra {P['head']}, score_shift {P['score_shift']}")

    # ---- đọc ngược ----
    rb_w = [int(v, 16) for v in (out / "weights.mem").read_text().split()]
    rb_b = np.array([int(v, 16) for v in (out / "bias.mem").read_text().split()], np.int64)
    rb_b = np.where(rb_b >= 2**31, rb_b - 2**32, rb_b)
    if a.engine == "e1":
        w8 = [v - 256 if v > 127 else v for v in rb_w]
        R, pos = {}, 0
        for i, (oc, ic) in enumerate(shapes[:-1], 1):
            R[f"w{i}"] = np.array(w8[pos:pos + oc * ic * 5]).reshape(oc, ic, 5); pos += oc * ic * 5
        R["wd"] = np.array(w8[pos:pos + 4 * shapes[-1]]).reshape(4, shapes[-1])
    else:
        words = [[((w >> (8 * p)) & 0xFF) - 256 if ((w >> (8 * p)) & 0xFF) > 127 else (w >> (8 * p)) & 0xFF
                  for p in range(lanes)] for w in rb_w]
        R = rl.unpack_rom(words, bases, shapes, lanes)
    pos = 0
    for i, (oc, _) in enumerate(shapes[:-1], 1):
        R[f"b{i}"] = rb_b[pos:pos + oc]; pos += oc
    R["bd"] = rb_b[pos:pos + 4]
    R.update(n=P["n"], head=P["head"], score_shift=P["score_shift"])

    # ---- vector ----
    rng = np.random.default_rng(a.seed)
    X, tag = vectors(a, rng)
    vin, vexp, vsc, vtr, vft, bad = [], [], [], [], [], 0
    for k, x in enumerate(X):
        c0, s0, l0 = forward(x, P)
        tr = {}
        c1, s1, l1 = forward(x, R, tr)
        for i in range(1, nl + 1):                      # vết từng lớp cho testbench (RB-02, RB-04)
            vtr += [f"{int(v) & 0xFF:02X}" for v in tr[f"l{i}"].reshape(-1)]
        if P["head"] == "gap":                          # đặc trưng sau GAP (RB-02: so `feat`)
            vft += [f"{int(v) & 0xFF:02X}" for v in tr["feat"]]
        bad += not (c0 == c1 and s0 == s1 and np.array_equal(l0, l1))
        vin += [f"{int(v) & 0xFF:02X}" for v in x.reshape(-1)]
        vexp += [f"{int(v) & 0xFFFFFFFF:08X}" for v in l1] + [f"{c1:08X}"]
        vsc.append(f"{s1:02X}")
        seq = k & 0xFF
        (out / "spi" / f"spi_{seq:02X}.bin").write_bytes(write_frame(seq, x))
        (out / "spi" / f"res_{seq:02X}.mem").write_text(
            "".join(f"{b:02X}\n" for b in result_frame(seq, 0x01, c1, s1, l1, a.cycles)), newline="\n")
    (out / "vec_in.mem").write_text("\n".join(vin) + "\n", newline="\n")
    (out / "vec_exp.mem").write_text("\n".join(vexp) + "\n", newline="\n")
    (out / "vec_score.mem").write_text("\n".join(vsc) + "\n", newline="\n")
    (out / "vec_trace.mem").write_text("\n".join(vtr) + "\n", newline="\n")      # l1, l2, (l3) của mỗi vector
    if vft:
        (out / "vec_feat.mem").write_text("\n".join(vft) + "\n", newline="\n")    # 32 đặc trưng GAP mỗi vector
    cls = [forward(x, R)[0] for x in X]
    log(f"{len(X)} vector: {', '.join(sorted(set(t.split(' #')[0] for t in tag)))}; lớp golden "
        f"{dict(zip(*map(lambda v: v.tolist(), np.unique(cls, return_counts=True))))}")
    log(f"{'PASS' if bad == 0 else 'FAIL'}  đọc ngược .mem → golden trùng lớp, SCORE, 4 logit: {len(X) - bad}/{len(X)}")
    bound = rl.acc_bound(P)
    okb = max(bound) < 2**31
    log(f"{'PASS' if okb else 'FAIL'}  biên |acc| xấu nhất theo lớp {bound} < 2^31 = {2**31}")
    oke = True
    if a.engine == "e2":
        for k in (0, len(X) // 2, len(X) - 1):
            e, _, _ = rl.engine(X[k], R, lanes)
            oke &= np.array_equal(e, forward(X[k], R)[2])
        log(f"{'PASS' if oke else 'FAIL'}  mô hình địa chỉ E2 trên ROM đã xuất == golden (3 vector)")

    # ---- cnn_params.vh ----
    vh = ["// GENERATED by tools/export_mem.py - DO NOT EDIT.", "`ifndef CNN_PARAMS_VH", "`define CNN_PARAMS_VH",
          f"`define CNN_ENGINE_{a.engine.upper()}", f"`define CNN_LANES {lanes}", f"`define CNN_NLAYERS {nl}",
          f"`define CNN_HEAD_GAP {1 if P['head'] == 'gap' else 0}", f"`define CNN_SCORE_SHIFT {P['score_shift']}",
          f"`define CNN_ROM_WORDS {len(rom)}", f"`define CNN_BIAS_WORDS {len(bias)}"]
    toff = 0
    for i, ((oc, ic), n, b) in enumerate(zip(shapes[:-1], P["n"], bases), 1):
        vh += [f"`define CNN_CONV{i}_SHIFT 5'd{n}", f"`define CNN_L{i}_OC {oc}", f"`define CNN_L{i}_IC {ic}",
               f"`define CNN_L{i}_BASE {b}", f"`define CNN_L{i}_OUT {(128 >> i) * oc}", f"`define CNN_L{i}_TOFF {toff}"]
        toff += (128 >> i) * oc
    vh += [f"`define CNN_TRACE_BYTES {toff}"]
    vh += [f"`define CNN_DENSE_F {shapes[-1]}", f"`define CNN_DENSE_BASE {bases[-1]}", "`endif"]
    (out / "cnn_params.vh").write_text("\n".join(vh) + "\n", newline="\n")

    # ---- selftest_expect.h ----
    xs = selftest_payload()
    c, s, lg = forward(xs, R)
    fr = result_frame(0xEE, 0x01, c, s, lg, a.cycles)
    h = ["/* GENERATED by tools/export_mem.py - DO NOT EDIT. Kết quả mong đợi của khung tự kiểm A.10 (SEQ 0xEE). */",
         "#ifndef SELFTEST_EXPECT_H", "#define SELFTEST_EXPECT_H", "#include <stdint.h>",
         f"#define SELFTEST_CLASS  {c}u", f"#define SELFTEST_SCORE  {s}u",
         f"static const int32_t selftest_logits[4] = {{ {', '.join(str(int(v)) for v in lg)} }};",
         f"static const uint8_t selftest_frame7[7] = {{ {', '.join(f'0x{b:02X}' for b in fr[:7])} }};",
         "#endif"]
    (out / "selftest_expect.h").write_text("\n".join(h) + "\n", encoding="utf8", newline="\n")
    log(f"selftest_expect.h: lớp {c}, SCORE {s}, logit {lg.tolist()}")
    (out / "export_report.txt").write_text("\n".join(rep) + "\n", encoding="utf8")
    if a.params:
        src = a.params.resolve()                       # tương đối với gốc dự án để chạy được trên máy khác
        try:
            src = src.relative_to(ROOT).as_posix()
        except ValueError:
            src = str(src)
        (out / "params_src.txt").write_text(str(src), encoding="utf8")     # cho tb_proto, cosim với E2
    sys.exit(0 if bad == 0 and okb and oke else 1)


if __name__ == "__main__":
    main()
