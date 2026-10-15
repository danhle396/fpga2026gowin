#!/usr/bin/env python
# tools/check_frames.py — kiểm tiền xử lý của MCU trên board (việc FW-10, tầng kiểm 6): dựng lại từng khung từ mẫu thô
# của chế độ TRC bằng golden model rồi so CRC với dòng "F,seq,crc" MCU in ra.
#
#   python tools/check_frames.py --port COM5 --seconds 60 --out trc.log    # gửi "TRC", ghi luồng, rồi kiểm
#   python tools/check_frames.py --file trc.log [--proto 1]               # kiểm file đã ghi
#
# Luồng TRC (firmware/src/app_main.c): "# start" rồi mỗi mẫu "t_ms,ax,ay,az,gx,gy,gz,btn,wear" (gyro đã trừ offset),
# "F,seq,crc" cho khung đã gửi, "X,seq" cho cửa sổ bị bỏ vì FPGA còn bận. Pass của FW-10: 1.000 khung, CRC trùng 100 %.
import argparse
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from golden_model import decimate, q8, write_frame  # noqa: E402
from gen_tv_pre import frame_v1  # noqa: E402


def capture(port, baud, seconds, out):
    import serial
    with serial.Serial(port, baud, timeout=0.5) as ser, open(out, "w", newline="\n") as f:
        ser.write(b"TRC\n")
        t_end = time.time() + seconds
        while time.time() < t_end:
            line = ser.readline().decode("ascii", "ignore").strip()
            if line:
                f.write(line + "\n")
        ser.write(b"RUN\n")


def parse(path):
    lines = pathlib.Path(path).read_text(encoding="ascii", errors="ignore").splitlines()
    if "# start" in lines:                       # mẫu tính từ lúc app_init (ring rỗng)
        lines = lines[lines.index("# start") + 1:]
    raw, t, frames, skipped = [], [], [], []
    for ln in lines:
        p = ln.strip().split(",")
        if p[0] == "F" and len(p) == 3:
            frames.append((int(p[1]), int(p[2], 16), len(raw)))
        elif p[0] == "X" and len(p) == 2:
            skipped.append(int(p[1]))
        elif len(p) in (8, 9):
            try:
                v = [int(x) for x in p]
            except ValueError:
                continue
            t.append(v[0])
            raw.append(v[1:7])
    return np.array(raw, np.int64).reshape(-1, 6), np.array(t), frames, skipped


def check(raw, t, frames, skipped, proto):
    q = q8(decimate(raw))
    ends = list(range(128, len(q) + 1, 16))                  # cửa sổ thứ k kết thúc ở mẫu 50 Hz ends[k]
    ok = bad = 0
    first_bad = None
    n_win = len(frames) + len(skipped)
    for seq, crc, nraw in frames:
        # SEQ quay vòng 8 bit: tìm cửa sổ có chỉ số ≡ seq (mod 256) gần nhất trước vị trí dòng F trong luồng
        cand = [k for k in range(len(ends)) if k % 256 == seq and 2 * ends[k] <= nraw]
        if not cand:                             # không có cửa sổ nào khớp SEQ trước dòng F: luồng lệch
            bad += 1
            first_bad = first_bad or (seq, crc, None)
            continue
        k = cand[-1]
        x = q[ends[k] - 128:ends[k]]
        f = write_frame(seq, x) if proto == 3 else frame_v1(seq, x)
        exp = (f[-2] << 8 | f[-1]) if proto == 3 else f[-1]
        if exp == crc:
            ok += 1
        else:
            bad += 1
            first_bad = first_bad or (seq, crc, exp)
    gaps = np.diff(t) if len(t) > 1 else np.array([])
    lost = int(np.sum(np.round(gaps[gaps >= 15] / 10) - 1)) if len(gaps) else 0
    return ok, bad, n_win, lost, first_bad, (gaps.min() if len(gaps) else 0, gaps.max() if len(gaps) else 0)


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=460800)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--out", default="trc.log")
    ap.add_argument("--proto", type=int, default=1, choices=[1, 3])
    a = ap.parse_args()
    path = a.file
    if a.port:
        capture(a.port, a.baud, a.seconds, a.out)
        path = a.out
    raw, t, frames, skipped = parse(path)
    ok, bad, n_win, lost, fb, (gmin, gmax) = check(raw, t, frames, skipped, a.proto)
    print(f"{len(raw)} mẫu thô, {len(frames)} khung có CRC, {len(skipped)} cửa sổ bị bỏ (FPGA bận)")
    print(f"CRC của MCU trùng Python: {ok}/{len(frames)}" + (f"; khung sai đầu tiên SEQ {fb[0]}: MCU {fb[1]:04X}, "
                                                             + (f"Python {fb[2]:04X}" if fb[2] is not None
                                                                else "không có cửa sổ tương ứng") if fb else ""))
    print(f"khoảng cách mẫu {gmin}–{gmax} ms, mất {lost} mẫu (A.9: ≥ 15 ms là mất)")
    good = bad == 0 and len(frames) >= 1000 and lost == 0
    print("KẾT LUẬN FW-10: " + ("PASS" if good else "FAIL" if bad or lost else "chưa đủ 1.000 khung"))
    sys.exit(0 if bad == 0 and lost == 0 else 1)


if __name__ == "__main__":
    main()
