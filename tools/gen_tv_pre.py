#!/usr/bin/env python
# tools/gen_tv_pre.py — sinh vector cho FW-07/FW-08 từ golden model (A.2, A.3, A.7). Chỉ cần numpy.
#   python -I tools/gen_tv_pre.py            → firmware/tv/pre_in.csv, pre_out.csv, pre_frames.csv
# pre_in.csv     : 10.000 mẫu thô 100 Hz, 6 cột INT16 (ax, ay, az, gx, gy, gz), gyro coi như đã trừ offset
# pre_out.csv    : 5.000 mẫu 50 Hz INT8 sau decimate() + q8()
# pre_frames.csv : mỗi cửa sổ (128 mẫu, bước 16): seq, crc16 của khung v3 (772 byte), crc8 của khung PROTO 1
# Tín hiệu có chủ đích: đứng yên, đi bộ, va chạm bão hòa ±32768, ngẫu nhiên toàn dải, và các hằng số nằm đúng
# biên làm tròn của A.2 (63/64, 31/32, ±2048, ±16384, ...). Hạt giống cố định nên chạy lại ra đúng từng byte.
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
from golden_model import crc16, decimate, q8, write_frame  # noqa: E402

N_RAW, WIN, HOP = 10_000, 128, 16


def crc8(data, c=0):
    """Giống crc8.v của RTL: đa thức 0x07, khởi tạo 0."""
    for b in data:
        c ^= b
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


def frame_v1(seq, x):
    body = bytes([seq & 0xFF]) + x.astype(np.int8).tobytes()
    return bytes([0xA5]) + body + bytes([crc8(body)])


def make_raw(rng):
    t = np.arange(N_RAW) / 100.0
    r = np.zeros((N_RAW, 6), np.float64)
    seg = np.array_split(np.arange(N_RAW), 6)
    # 0: đứng yên, đầu thẳng (AZ ≈ +2048)
    i = seg[0]
    r[i] = [0, 0, 2048, 0, 0, 0] + rng.normal(0, [12, 12, 12, 6, 6, 6], (len(i), 6))
    # 1: đi bộ ~2 Hz
    i = seg[1]
    w = 2 * np.pi * 2.0 * t[i]
    r[i, 0] = 300 * np.sin(w) + 80 * np.sin(2 * w)
    r[i, 1] = 150 * np.sin(w / 2)
    r[i, 2] = 2048 + 400 * np.sin(2 * w)
    r[i, 3:] = np.stack([900 * np.sin(w), 600 * np.cos(w), 300 * np.sin(w / 2)], 1)
    r[i] += rng.normal(0, 20, (len(i), 6))
    # 2: các cú va chạm: xung bão hòa rồi nằm nghiêng
    i = seg[2]
    r[i] = [0, 1400, 1400, 0, 0, 0] + rng.normal(0, 10, (len(i), 6))
    for k in range(i[0] + 50, i[-1] - 40, 300):
        n = rng.integers(5, 20)
        r[k:k + n] = rng.choice([-1, 1], (n, 6)) * rng.uniform(20000, 40000, (n, 6))
    # 3: ngẫu nhiên toàn dải INT16
    i = seg[3]
    r[i] = rng.integers(-32768, 32768, (len(i), 6))
    # 4: hằng số ở biên làm tròn, mỗi giá trị giữ 24 mẫu (đủ để y = hằng số)
    i = seg[4]
    consts = [63, 64, -64, -65, 31, 32, -32, -33, 2048, -2048, 16384, -16384, 8192, -8192, 1640, -1640,
              16320, 16319, -16448, -16449, 8128, 8127, -8224, -8225, 0, 1, -1, 32767, -32768]
    for k, v in enumerate(consts):
        a = i[0] + 24 * k
        r[a:a + 24] = v
    r[i[0] + 24 * len(consts):i[-1] + 1] = rng.integers(-300, 300, (i[-1] + 1 - i[0] - 24 * len(consts), 6))
    # 5: sườn dốc và nhảy bậc từng mẫu (kiểm hệ số 1-3-3-1 và trạng thái lọc)
    i = seg[5]
    ramp = np.linspace(-32768, 32767, len(i))
    r[i] = np.stack([ramp, -ramp, ramp[::-1], (np.arange(len(i)) % 2) * 2000 - 1000,
                     (np.arange(len(i)) % 3) * 9000 - 9000, rng.integers(-5, 5, len(i))], 1)
    return np.clip(np.round(r), -32768, 32767).astype(np.int16)


def main():
    sys.stdout.reconfigure(encoding="utf8")
    out = ROOT / "firmware" / "tv"
    out.mkdir(parents=True, exist_ok=True)
    raw = make_raw(np.random.default_rng(20261014))
    q = q8(decimate(raw))                                    # (5000, 6) int8
    np.savetxt(out / "pre_in.csv", raw, fmt="%d", delimiter=",", header="ax,ay,az,gx,gy,gz", comments="")
    np.savetxt(out / "pre_out.csv", q, fmt="%d", delimiter=",", header="ax,ay,az,gx,gy,gz", comments="")
    rows = []
    seq = 0
    for n in range(WIN, len(q) + 1, HOP):
        x = q[n - WIN:n]
        f3, f1 = write_frame(seq, x), frame_v1(seq, x)
        assert len(f3) == 772 and len(f1) == 771 and crc16(f3) == 0
        rows.append(f"{seq},{f3[-2] << 8 | f3[-1]:04X},{f1[-1]:02X}")
        seq = (seq + 1) & 0xFF
    (out / "pre_frames.csv").write_text("seq,crc16_v3,crc8_v1\n" + "\n".join(rows) + "\n")
    sat = np.mean((q == 127) | (q == -128))
    print(f"pre_in {raw.shape} → pre_out {q.shape}, {len(rows)} cửa sổ; tỉ lệ mẫu bão hòa INT8 {sat:.1%}")
    print(f"ghi {out}")


if __name__ == "__main__":
    main()
