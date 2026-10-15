# mk_trc.py — dựng file TRC (như firmware in ở chế độ TRC) từ khung ghi v3 do MÃ MÁY firmware sinh trong Unicorn
# (tools/m0_test.py chế độ 1), để chạy thử tools/check_frames.py --file khi chưa có board.
#   python mk_trc.py <file ra> ok|badcrc|lost [số lần lặp luồng]     (cần pip install unicorn)
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "ml" / "src"))
import numpy as np, cosim, m0_test as mt
out_path, mode = sys.argv[1], sys.argv[2]          # mode: ok | badcrc | lost
raw, _ = cosim.stream(6)
raw = np.concatenate([raw] * int(sys.argv[3] if len(sys.argv) > 3 else 1))
_, out = mt.run(1, len(raw), raw.astype("<i2").tobytes())
frames, i = [], 0
while i < len(out):
    if out[i] == ord("S"): i += 7
    else: frames.append(bytes(out[i + 2:i + 774])); i += 1545
# cửa sổ k kết thúc ở mẫu 50 Hz 128+16k, tức mẫu thô thứ 2*(128+16k)
at = {2 * (128 + 16 * k): f for k, f in enumerate(frames)}
L = ["# start"]
for n in range(len(raw)):
    if mode == "lost" and n == 5000: continue
    L.append("%d,%s,0,1" % (10 * n, ",".join(str(int(v)) for v in raw[n])))
    f = at.get(n + 1)
    if f is not None:
        crc = f[-2] << 8 | f[-1]
        if mode == "badcrc" and f[1] == 37: crc ^= 1
        L.append("F,%d,%04X" % (f[1], crc))
pathlib.Path(out_path).write_text("\n".join(L) + "\n", encoding="ascii")
print(len(frames), "khung,", len(raw), "mau ->", out_path)
