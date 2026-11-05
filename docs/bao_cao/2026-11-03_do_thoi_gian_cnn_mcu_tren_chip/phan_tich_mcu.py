"""Tổng hợp log đo CNN trên MCU: chu kỳ theo từng cửa sổ, đổi ra ms theo 48 MHz và theo clock đối chiếu đồng hồ máy tính."""
import sys

F = 48e6
cnn, cal, mul, khac = {}, {}, None, []
for l in open(sys.argv[1], encoding="utf8", errors="replace"):
    p = l.strip().split(" ", 1)
    if len(p) < 2:
        continue
    t, s = float(p[0]), p[1]
    q = s.split(",")
    if q[0] == "CNN" and len(q) == 5:
        cnn.setdefault(q[1], []).append((int(q[3]), int(q[4])))
    elif q[0] == "MUL":
        mul = (int(q[1]), int(q[2]))
    elif q[0] == "CAL":
        cal[q[1]] = t
    else:
        khac.append(s)
print("\n".join(khac))
if mul:
    print(f"vong MOVS {mul[0]}, vong MULS {mul[1]} chu ky / 1000 lan -> MULS = {(mul[1] - mul[0]) / 1000 + 1:.2f} chu ky")
f_thuc = None
if {"0", "1"} <= cal.keys():
    dt = cal["1"] - cal["0"]
    f_thuc = F * 20.0 / dt
    print(f"20.000 ms clock MCU = {dt:.3f} s dong ho may tinh -> HCLK that ~ {f_thuc / 1e6:.3f} MHz ({(f_thuc / F - 1) * 100:+.2f} %)")
tong = 0
for ten, r in cnn.items():
    c = [x[0] for x in r]
    d = sum(x[1] for x in r)
    tong += d == len(r)
    print(f"{ten:10} {d}/{len(r)} dung golden; chu ky min {min(c)} max {max(c)}; {min(c) / F * 1e3:.2f}-{max(c) / F * 1e3:.2f} ms @48 MHz"
          + (f"; {max(c) / f_thuc * 1e3:.2f} ms @clock doi chieu" if f_thuc else ""))
print("so cua so dung het:", tong, "/", len(cnn))
