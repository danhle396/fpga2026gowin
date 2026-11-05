"""Tổng hợp log của do_thoi_gian_fpga: mỗi chế độ in số khung theo mã kết quả, CYCLES, thời gian ESP32 đo được."""
import sys, collections

TEN = ["OK", "TIMEOUT", "HDR", "CRC", "STATUS", "SEQ", "CLASS", "TAIL", "DAP_AN"]
F_DN = 50.143e6


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p / 100 * len(v)))]


cheo = {}
m = None
loi_dong = 0
for l in open(sys.argv[1], encoding="utf8", errors="replace"):
    l = l.strip()
    if l.startswith("F,"):
        p = l.split(",")
        if len(p) != 10 or not all(x.isdigit() for x in p[1:]):
            loi_dong += 1
            continue
        if p[1] == "0":          # chỉ số khung về 0 = chế độ mới; dòng MODE có thể hỏng trên đường truyền
            m = "ABC"[len(cheo)]
            cheo[m] = []
        cheo[m].append(tuple(int(x) for x in p[1:]))
    elif l and not l.startswith(("#", "MODE,", "F0", "END")):
        loi_dong += 1
print("dong log hong:", loi_dong)

for m, r in cheo.items():
    print(f"== che do {m}: {len(r)} khung")
    print("  ket qua:", {TEN[k]: v for k, v in sorted(collections.Counter(x[1] for x in r).items())})
    print("  CYCLES :", dict(collections.Counter(x[2] for x in r).most_common(6)))
    print("  lop    :", dict(sorted(collections.Counter(x[7] for x in r).items())))
    ok = [x for x in r if x[1] == 0]
    if not ok:
        continue
    tw = [x[3] for x in ok]
    print(f"  ghi 772 B: min {min(tw)} trung vi {pct(tw, 50)} max {max(tw)} us")
    if m == "C":
        continue
    lo, hi = [x[4] for x in ok], [x[5] for x in ok]
    giua = [(a + b) / 2 for a, b in zip(lo, hi)]
    rong = [b - a for a, b in zip(lo, hi)]
    print(f"  t_lo: min {min(lo)} trung vi {pct(lo, 50)} p99 {pct(lo, 99)} max {max(lo)} us")
    print(f"  t_hi: min {min(hi)} trung vi {pct(hi, 50)} p99 {pct(hi, 99)} max {max(hi)} us")
    print(f"  chu ky doc tham: trung vi {pct(rong, 50)} max {max(rong)} us, so lan doc tham trung vi {pct([x[6] for x in ok], 50)}")
    tb = sum(giua) / len(giua)
    print(f"  diem giua: trung binh {tb:.2f} trung vi {pct(giua, 50)} us; max(t_lo) {max(lo)} <= min(t_hi) {min(hi)}: {max(lo) <= min(hi)}")
    c = ok[0][2]
    print(f"  CYCLES/50,143 MHz = {c / F_DN * 1e6:.2f} us; clock suy ra tu dong ho ESP32 = {c / tb:.3f} MHz")
