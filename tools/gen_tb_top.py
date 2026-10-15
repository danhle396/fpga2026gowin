#!/usr/bin/env python
# tools/gen_tb_top.py — sinh vector cho rtl/tb/tb_top_spi.v từ thư mục xuất INT8 (cùng nguồn với gen_cnn_params.py).
#   python -I tools/gen_tb_top.py --export <thư mục fpga_export> --out <project>/tb
# Ghi spi_frames.mem (5 khung PROTO 1 × 771 byte) và spi_exp.mem (5 × 7 byte). Khung số 2 bị đảo 1 bit CRC-8:
# kỳ vọng ghi toàn 0xEE nghĩa là FPGA không được trả kết quả. Khung và CRC dùng đúng hàm frame_v1() mà bộ test
# firmware (tools/m0_test.py) đã chứng minh trùng từng byte với firmware/src/spi_frame.c.
import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from golden_model import forward  # noqa: E402
from gen_tv_pre import crc8, frame_v1  # noqa: E402

sys.stdout.reconfigure(encoding="utf8")
ap = argparse.ArgumentParser()
ap.add_argument("--export", type=pathlib.Path, required=True)
ap.add_argument("--out", type=pathlib.Path, required=True)
a = ap.parse_args()

q = json.loads((a.export / "quant_params.json").read_text(encoding="utf8"))
W = np.array([int(v, 16) for v in (a.export / "weights.mem").read_text().split()], np.int64)
B = np.array([int(v, 16) for v in (a.export / "bias.mem").read_text().split()], np.int64)
W = np.where(W > 127, W - 256, W)
B = np.where(B >= 2**31, B - 2**32, B)
P = dict(w1=W[:480].reshape(16, 6, 5), b1=B[:16], w2=W[480:3040].reshape(32, 16, 5), b2=B[16:48],
         wd=W[3040:].reshape(4, 32), bd=B[48:], n=[int(q["conv1_shift"]), int(q["conv2_shift"])], head="gap",
         score_shift=0)
X = np.load(a.export / "golden_vectors.npz")["input_windows"]
# chọn 4 cửa sổ có lớp golden khác nhau nếu được
picks, seen = [], set()
for i, x in enumerate(X):
    c = forward(x, P)[0]
    if c not in seen:
        picks.append(i); seen.add(c)
picks = (picks + [i for i in range(len(X)) if i not in picks])[:4]

frames, exp = [], []
for k, i in enumerate([picks[0], picks[1], picks[1], picks[2], picks[3]]):
    seq = 0x10 + k
    f = bytearray(frame_v1(seq, X[i]))
    if k == 2:
        f[-1] ^= 0x01                                   # CRC-8 sai
        e = bytes([0xEE] * 7)
    else:
        cls, _, lg = forward(X[i], P)
        body = bytes([cls]) + (int(lg[cls]) & 0xFFFFFFFF).to_bytes(4, "big")
        e = bytes([0x5A]) + body + bytes([crc8(body)])
    frames.append(bytes(f))
    exp.append(e)
a.out.mkdir(parents=True, exist_ok=True)
(a.out / "spi_frames.mem").write_text("".join(f"{b:02X}\n" for f in frames for b in f), newline="\n")
(a.out / "spi_exp.mem").write_text("".join(f"{b:02X}\n" for e in exp for b in e), newline="\n")
print(f"tb_top_spi: 5 khung (cửa sổ {[int(p) for p in picks]}, khung 2 sai CRC), shift {P['n']}")
