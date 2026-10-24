#!/usr/bin/env python
# tools/gen_tb_proto.py — vector cho fpga/sim/tb_proto.v (RA-03), sinh từ golden model và thư mục xuất INT8 (export_mem.py --engine e2).
#   python -I tools/gen_tb_proto.py --export <fpga_export> --out <thư mục>/tb [--ng 50]
# Khung đúng gồm: 20 cửa sổ của golden_vectors.npz, khung tự kiểm LFSR (A.10), các mẫu cực trị (toàn +127, toàn −128,
# toàn 0, xen kẽ ±127, bậc thang) và cửa sổ ngẫu nhiên — phủ cả bão hòa (R9). SEQ chạy 0x40, 0x41, ...
import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
from golden_model import forward, result_frame, selftest_payload, write_frame  # noqa: E402

sys.stdout.reconfigure(encoding="utf8")
ap = argparse.ArgumentParser()
ap.add_argument("--export", type=pathlib.Path, required=True, help="thư mục có golden_vectors.npz (E1) "
                "hoặc thư mục xuất của export_mem.py")
ap.add_argument("--params", type=pathlib.Path, help="params_int8.npz (N2...), thay cho weights.mem E1")
ap.add_argument("--out", type=pathlib.Path, required=True)
ap.add_argument("--ng", type=int, default=50)
a = ap.parse_args()
if a.params and not a.params.exists() and (ROOT / a.params).exists():
    a.params = ROOT / a.params                         # params_src.txt ghi đường dẫn tương đối với gốc dự án

if a.params:
    z = np.load(a.params)
    P = {k: z[k] for k in z.files}
    P["n"], P["head"], P["score_shift"] = [int(v) for v in P["n"]], str(P["head"]), int(P["score_shift"])
else:
    q = json.loads((a.export / "quant_params.json").read_text(encoding="utf8"))
    W = np.array([int(v, 16) for v in (a.export / "weights.mem").read_text().split()], np.int64)
    B = np.array([int(v, 16) for v in (a.export / "bias.mem").read_text().split()], np.int64)
    W = np.where(W > 127, W - 256, W)
    B = np.where(B >= 2**31, B - 2**32, B)
    P = dict(w1=W[:480].reshape(16, 6, 5), b1=B[:16], w2=W[480:3040].reshape(32, 16, 5), b2=B[16:48],
             wd=W[3040:].reshape(4, 32), bd=B[48:], n=[int(q["conv1_shift"]), int(q["conv2_shift"])], head="gap",
             score_shift=int(q.get("score_shift", 0)))

rng = np.random.default_rng(42)
gv = a.export / "golden_vectors.npz"
X = list(np.load(gv)["input_windows"]) if gv.exists() else []
if not X:                                                            # thư mục export_mem: lấy vec_in.mem
    v = np.array([int(s, 16) for s in (a.export / "vec_in.mem").read_text().split()], np.int64)
    X = list(np.where(v > 127, v - 256, v).astype(np.int8).reshape(-1, 128, 6)[:20])
X.append(selftest_payload())
X += [np.full((128, 6), 127, np.int8), np.full((128, 6), -128, np.int8), np.zeros((128, 6), np.int8),
      np.tile(np.array([127, -128], np.int8), 384).reshape(128, 6),
      (np.arange(768) % 256 - 128).astype(np.int8).reshape(128, 6)]
while len(X) < a.ng + 7:
    X.append(rng.integers(-128, 128, (128, 6)).astype(np.int8))
X = X[:a.ng + 7]

frames, exp = [], []


def good(seq, x):
    cls, sc, lg = forward(x, P)
    return result_frame(seq, 0x01, cls, sc, lg, 0)


def err(seq, status):
    return result_frame(seq, status, 0xFF, 0, [0, 0, 0, 0], 0)


seq = 0x40
for k in range(a.ng):
    frames.append(write_frame(seq, X[k])); exp.append(good(seq, X[k])); seq += 1
f = bytearray(write_frame(seq, X[a.ng])); f[300] ^= 0x10                 # (2) CRC sai
frames.append(bytes(f)); exp.append(err(seq, 0x00)); seq += 1
frames.append(write_frame(seq, X[a.ng + 1])); exp.append(err(seq, 0x04)); seq += 1   # (3) thiếu byte
sa, sb = seq, seq + 1                                                    # (4) A rồi B khi đang bận
frames.append(write_frame(sa, X[a.ng + 2])); frames.append(write_frame(sb, X[a.ng + 3]))
exp.append(err(sb, 0x07)); exp.append(good(sa, X[a.ng + 2])); seq += 2
f = bytearray(write_frame(seq, X[a.ng + 4])); f[0] = 0x00                # (5) byte đầu sai
frames.append(bytes(f)); seq += 1
frames.append(write_frame(seq, X[a.ng + 5])); exp.append(good(seq, X[a.ng + 5])); seq += 1   # (6) RUN
frames.append(write_frame(seq, X[a.ng + 6]))                              # (7) RST_N
assert len(frames) == a.ng + 7 and len(exp) == a.ng + 5 and all(len(x) == 772 for x in frames)

a.out.mkdir(parents=True, exist_ok=True)
(a.out / "proto_frames.mem").write_text("".join(f"{b:02X}\n" for x in frames for b in x), newline="\n")
(a.out / "proto_exp.mem").write_text("".join(f"{b:02X}\n" for x in exp for b in x), newline="\n")
cls = [forward(x, P)[0] for x in X[:a.ng]]
print(f"tb_proto: {a.ng} khung đúng (lớp golden { {int(k): int(v) for k, v in zip(*np.unique(cls, return_counts=True))} }) + 7 khung kịch bản; "
      f"score_shift {P['score_shift']}")
