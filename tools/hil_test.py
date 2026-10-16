#!/usr/bin/env python
# tools/hil_test.py — kiểm thử phần cứng trong vòng lặp PC → MCU → FPGA → PC (việc TH-07, FW-13; tầng kiểm 5).
# Firmware ở chế độ HIL (gửi "HIL"): nhận khung ghi 772 byte, chuyển sang FPGA, trả nguyên 20 byte khung đọc.
#
#   python tools/hil_test.py --port COM5 --n 500                        # weight SisFall của nhóm, PROTO 1
#   python tools/hil_test.py --port COM5 --n 2000 --proto 3 --params ml/out/n2_11_d1/params_int8.npz   # bitstream 3
#   python tools/hil_test.py --mock --n 200 [--mock-error 37]           # không cần board: thử chính công cụ
#
# Cửa sổ: D1 thật (FALL và NORMAL), khung tự kiểm LFSR, các mẫu cực trị, rồi ngẫu nhiên. Đáp án: golden_model.forward.
# Pass của TH-07: ≥ 500 cửa sổ, 0 sai lệch CLASS, SCORE, 4 LOGIT (PROTO 1 chỉ có CLASS và logit lớn nhất).
import argparse
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from golden_model import crc16, forward, result_frame, selftest_payload, write_frame  # noqa: E402
from gen_tv_pre import crc8  # noqa: E402

TEAM = ROOT / "FPGA_Fall_Detection_AI-20261012T141515Z-1-001" / "FPGA_Fall_Detection_AI" / "fpga_export"


def load(a):
    if a.params:
        z = np.load(a.params)
        P = {k: z[k] for k in z.files}
        P["n"], P["head"], P["score_shift"] = [int(v) for v in P["n"]], str(P["head"]), int(P["score_shift"])
        return P
    q = json.loads((TEAM / "quant_params.json").read_text(encoding="utf8"))
    W = np.array([int(v, 16) for v in (TEAM / "weights.mem").read_text().split()], np.int64)
    B = np.array([int(v, 16) for v in (TEAM / "bias.mem").read_text().split()], np.int64)
    W, B = np.where(W > 127, W - 256, W), np.where(B >= 2**31, B - 2**32, B)
    return dict(w1=W[:480].reshape(16, 6, 5), b1=B[:16], w2=W[480:3040].reshape(32, 16, 5), b2=B[16:48],
                wd=W[3040:].reshape(4, 32), bd=B[48:], n=[q["conv1_shift"], q["conv2_shift"]], head="gap",
                score_shift=int(q.get("score_shift", 0)))


def windows(n, rng):
    d = np.load(ROOT / "ml" / "data" / "public" / "d1_windows.npz")
    X = [selftest_payload(), np.full((128, 6), 127, np.int8), np.full((128, 6), -128, np.int8),
         np.zeros((128, 6), np.int8)]
    nf = min(n // 4, int(np.sum(d["y"] == 3)))
    X += list(d["X"][rng.choice(np.flatnonzero(d["y"] == 3), nf, replace=False)])
    X += list(d["X"][rng.choice(np.flatnonzero(d["y"] == 0), max(0, n - len(X) - n // 10), replace=False)])
    while len(X) < n:
        X.append(rng.integers(-128, 128, (128, 6)).astype(np.int8))
    return X[:n]


class Mock:
    """Đứng thay MCU + FPGA bằng golden model, để thử công cụ khi chưa có board."""
    def __init__(self, P, proto, err_at):
        self.P, self.proto, self.err_at, self.k, self.out = P, proto, err_at, 0, b""

    def write(self, b):
        if b.startswith(b"HIL") or b == b"Q":
            return
        x = np.frombuffer(b[2:770], np.int8).reshape(128, 6)
        c, s, lg = forward(x, self.P)
        if self.k == self.err_at:
            lg = lg.copy(); lg[c] += 1                   # lỗi ở logit thắng: thấy được ở cả PROTO 1
        self.k += 1
        if self.proto == 1:
            body = bytes([c]) + (int(lg[c]) & 0xFFFFFFFF).to_bytes(4, "big")
            self.out = (bytes([0x5A]) + body + bytes([crc8(body)])).ljust(20, b"\0")
        else:
            self.out = result_frame(b[1], 0x01, c, s, lg, 699800)

    def read(self, n):
        r, self.out = self.out[:n], self.out[n:]
        return r

    def reset_input_buffer(self):
        pass


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=460800)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--proto", type=int, default=1, choices=[1, 3])
    ap.add_argument("--params", type=pathlib.Path)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--mock-error", type=int, default=-1)
    ap.add_argument("--seed", type=int, default=12)
    a = ap.parse_args()
    P = load(a)
    X = windows(a.n, np.random.default_rng(a.seed))
    if a.mock:
        ser = Mock(P, a.proto, a.mock_error)
    else:
        import serial
        ser = serial.Serial(a.port, a.baud, timeout=0.5)
        ser.write(b"HIL\n")
        time.sleep(0.3)
        ser.reset_input_buffer()
    bad, cyc, t0 = [], set(), time.time()
    for k, x in enumerate(X):
        seq = k & 0xFF
        ser.write(write_frame(seq, x))
        r = ser.read(20)
        c, s, lg = forward(x, P)
        if len(r) < 20:
            bad.append((k, "thiếu byte trả về"))
            continue
        if r[0] == 0xEE:
            bad.append((k, "MCU báo khung UART hỏng"))
            continue
        if a.proto == 1:
            body = r[1:6]
            got = (r[0], r[1], int.from_bytes(r[2:6], "big", signed=True), r[6])
            exp = (0x5A, c, int(lg[c]), crc8(body))
            if got != exp:
                bad.append((k, f"nhận {got}, mong đợi {exp}"))
        else:
            e = result_frame(seq, 0x01, c, s, lg, 0)
            if r[:15] != e[:15] or crc16(r[7:18]) != (r[18] << 8 | r[19]):
                bad.append((k, f"nhận {r.hex()}, mong đợi {e[:15].hex()}…"))
            cyc.add(int.from_bytes(r[15:18], "big"))
    if not a.mock:
        ser.write(b"Q")
    dt = time.time() - t0
    print(f"{len(X)} cửa sổ qua {'MÔ PHỎNG' if a.mock else a.port} (PROTO {a.proto}) trong {dt:.1f} s: "
          f"{len(X) - len(bad)} khớp golden, {len(bad)} sai" + (f"; CYCLES {sorted(cyc)}" if cyc else ""))
    for k, msg in bad[:5]:
        print(f"  cửa sổ {k}: {msg}")
    print("KẾT LUẬN TH-07: " + ("PASS" if not bad and len(X) >= 500 else "FAIL" if bad else "chưa đủ 500 cửa sổ"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
