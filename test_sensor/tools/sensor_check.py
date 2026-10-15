#!/usr/bin/env python3
"""
sensor_check.py — kiểm tra MPU6050 từ phía PC, đọc UART của firmware test.

Cách dùng:
    python sensor_check.py check  --port COM5              # đọc báo cáo T1..T7 + phân tích 10 s dữ liệu tĩnh
    python sensor_check.py check  --port COM5 --seconds 600 --save log_10phut.csv
    python sensor_check.py orient --port COM5              # kiểm tra 6 tư thế, đo AY_dung_yen
    python sensor_check.py plot   --port COM5              # vẽ realtime 6 trục
    python sensor_check.py analyze log_10phut.csv          # phân tích file CSV có sẵn
Thêm --sim thay cho --port để chạy thử với dữ liệu giả (không cần board).
Arduino (mpu6050_quick.ino) dùng --baud 115200.

Mã thoát: 0 = PASS, 1 = FAIL.
"""
import argparse
import collections
import csv
import math
import random
import re
import sys
import threading
import time

BAUD = 460800
FS_HZ = 100
ACC_LSB_PER_G = 2048.0
GYR_LSB_PER_DPS = 16.4

HDR_RE = re.compile(r"^#\s*(T\d+\w*)\s+(\S+)\s*:\s*(.*?)\s*->\s*(PASS|WARN|FAIL)\s*$")
CSV_RE = re.compile(r"^-?\d+(?:,-?\d+){7}$")

for _s in (sys.stdout, sys.stderr):        # console Windows (cp1252) không in được tiếng Việt
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


# --------------------------------------------------------------------------- nguồn dữ liệu

class SerialSource:
    def __init__(self, port, baud):
        try:
            import serial
        except ImportError:
            sys.exit("Thiếu pyserial: pip install pyserial")
        self.ser = serial.Serial()
        self.ser.port, self.ser.baudrate, self.ser.timeout = port, baud, 0.2
        self.ser.dtr = self.ser.rts = False     # không giữ EN/BOOT của ESP32 (mạch auto-reset)
        self.ser.open()
        self.ser.reset_input_buffer()

    def readline(self):
        raw = self.ser.readline()
        if not raw:
            return None
        return raw.decode("ascii", errors="replace").strip()

    def flush(self):
        """Bỏ dữ liệu cũ tích lại trong buffer (vd. khi đang chờ người dùng nhấn Enter)."""
        self.ser.reset_input_buffer()
        self.ser.readline()                  # bỏ nửa dòng còn sót

    def close(self):
        self.ser.close()


class SimSource:
    """Giả lập firmware: in header rồi stream 100 Hz, cảm biến nằm yên (Z hướng lên)."""

    HEADER = [
        "# ===== MPU6050 TEST (VKU-NewBie) =====",
        "# T1 BUS_IDLE      : SDA=1 SCL=1 -> PASS",
        "# T2 I2C_SCAN      : 1 thiet bi: 0x68 -> PASS",
        "# T3 WHO_AM_I      : 0x68 -> PASS",
        "# T4 CONFIG        : 7 thanh ghi doc lai dung -> PASS",
        "# T5 SELF_TEST     : AX+2.1% AY-1.3% AZ+0.8% GX+3.0% GY-2.2% GZ+1.1% (dat: |x|<=14%) -> PASS",
        "# T6 SAMPLE_RATE   : INT: 200 xung/2s = 100.0 Hz -> PASS",
        "# T7a GYRO_OFFSET  : gx=-10 gy=4 gz=-2 LSB (se tru o moi mau) -> PASS",
        "# T7b ACCEL_1G     : |a|=2051 LSB = 1.00 g -> PASS",
        "# T7c NOISE        : std|a|=5 std g=1/1/1 LSB -> PASS",
        "# T7d TEMP         : 29.4 C -> PASS",
        "# SUMMARY pass=10 warn=0 fail=0",
        "# STREAM START (gyro da tru offset, int=pin)",
        "# t_ms,ax,ay,az,gx,gy,gz,btn",
    ]

    def __init__(self):
        self.lines = list(self.HEADER)
        self.gravity = (0.0, 0.0, 1.0)
        self.n = 0
        self.t_start = time.monotonic()

    def set_gravity(self, g):
        self.gravity = g

    def readline(self):
        if self.lines:
            return self.lines.pop(0)
        wait = self.t_start + self.n / FS_HZ - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        t_ms = 1234 + self.n * 10
        self.n += 1
        a = [int(ACC_LSB_PER_G * g + 15 + random.gauss(0, 5)) for g in self.gravity]
        gy = [int(random.gauss(0, 1.5)) for _ in range(3)]
        return f"{t_ms},{a[0]},{a[1]},{a[2]},{gy[0]},{gy[1]},{gy[2]},0"

    def flush(self):
        pass

    def close(self):
        pass


def open_source(args):
    if args.sim:
        return SimSource()
    if not args.port:
        sys.exit("Cần --port COMx (hoặc --sim để chạy thử)")
    return SerialSource(args.port, args.baud)


def parse_sample(line):
    if line and CSV_RE.match(line):
        return tuple(int(x) for x in line.split(","))
    return None


def collect(src, seconds, echo_comments=True):
    """Đọc mẫu trong `seconds` giây (thời gian thực). Trả về list tuple 8 số."""
    samples = []
    t_end = time.monotonic() + seconds
    last_print = 0
    while time.monotonic() < t_end:
        line = src.readline()
        s = parse_sample(line)
        if s:
            samples.append(s)
        elif line and line.startswith("#") and echo_comments:
            print("   [board] " + line)
        now = time.monotonic()
        if seconds >= 20 and now - last_print >= 5:
            last_print = now
            print(f"   ... {len(samples)} mẫu, còn {t_end - now:.0f} s", flush=True)
    return samples


# --------------------------------------------------------------------------- báo cáo của firmware

def read_header(src, timeout):
    """Chờ báo cáo T1..T7 đến dòng '# STREAM START'. Trả về (danh sách kết quả, đã thấy stream?)."""
    results = []
    csv_seen = 0
    t_end = time.monotonic() + timeout
    hinted = False
    while time.monotonic() < t_end:
        line = src.readline()
        if line is None:
            continue
        if line.startswith("#"):
            print("   " + line)
            m = HDR_RE.match(line)
            if m:
                results.append((m.group(1), m.group(2), m.group(3), m.group(4)))
            if "FATAL" in line:
                results = []              # firmware sẽ tự chạy lại, bỏ kết quả lượt cũ
            if "STREAM START" in line:
                return results, True
        elif parse_sample(line):
            csv_seen += 1
            if csv_seen == 300 and not hinted:
                print("   (board đang stream — nhấn RESET trên board MCU để xem báo cáo T1..T7)")
                hinted = True
    return results, False


# --------------------------------------------------------------------------- phân tích

def mean(xs):
    return sum(xs) / len(xs)


def std(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def analyze(samples, static=True):
    """In bảng phân tích; trả về danh sách (tên, kết quả, chi tiết)."""
    out = []
    n = len(samples)
    if n < 20:
        out.append(("STREAM", "FAIL", f"chỉ nhận {n} mẫu — kiểm tra COM/baud, board có stream không"))
        return out

    t = [s[0] for s in samples]
    cols = list(zip(*samples))
    ax, ay, az, gx, gy, gz = (cols[i] for i in range(1, 7))

    # --- thời gian / mất mẫu
    gaps = [b - a for a, b in zip(t, t[1:])]
    hist = collections.Counter(gaps)
    dur = (t[-1] - t[0]) / 1000.0
    rate = (n - 1) / dur if dur > 0 else 0.0
    lost = sum(round(g / 10) - 1 for g in gaps if g >= 15)
    backwards = sum(1 for g in gaps if g <= 0)
    odd = sum(c for g, c in hist.items() if g not in (9, 10, 11) and 0 < g < 15)
    top = ", ".join(f"{g}ms×{c}" for g, c in sorted(hist.items(), key=lambda kv: -kv[1])[:5])
    ok_rate = 98.0 <= rate <= 102.0
    out.append(("SAMPLE_RATE", "PASS" if ok_rate else "FAIL",
                f"{rate:.2f} Hz trong {dur:.1f} s ({n} mẫu)"))
    out.append(("GAPS", "PASS" if lost == 0 and backwards == 0 else "FAIL",
                f"mất ~{lost} mẫu, lùi thời gian {backwards}, khoảng lạ {odd}; phân bố: {top}"))

    # --- giá trị bất thường
    flat = ax + ay + az + gx + gy + gz
    sat = sum(1 for v in flat if v >= 32767 or v <= -32768)
    allzero = all(v == 0 for v in ax + ay + az)
    frozen = all(std(c) == 0 for c in (ax, ay, az))
    if allzero:
        out.append(("VALUES", "FAIL", "accel toàn 0 — chip còn sleep (PWR_MGMT_1 chưa = 0x01)"))
    elif frozen:
        out.append(("VALUES", "FAIL", "accel không đổi — đọc lặp lại cùng một giá trị / chip treo"))
    else:
        out.append(("VALUES", "PASS" if sat == 0 else ("WARN" if not static else "FAIL"),
                    f"{sat} giá trị bão hòa ±32767"))

    if not static:
        return out

    # --- tĩnh: gia tốc ~1 g, gyro ~0
    mag = [math.sqrt(a * a + b * b + c * c) for a, b, c in zip(ax, ay, az)]
    m_g = mean(mag) / ACC_LSB_PER_G
    sd_mg = std(mag) / ACC_LSB_PER_G * 1000
    print(f"\n   accel TB (LSB): ax={mean(ax):8.1f} ay={mean(ay):8.1f} az={mean(az):8.1f}   "
          f"(g: {mean(ax)/ACC_LSB_PER_G:+.3f} {mean(ay)/ACC_LSB_PER_G:+.3f} {mean(az)/ACC_LSB_PER_G:+.3f})")
    print(f"   gyro  TB (LSB): gx={mean(gx):8.2f} gy={mean(gy):8.2f} gz={mean(gz):8.2f}   "
          f"std: {std(gx):.2f} {std(gy):.2f} {std(gz):.2f}")
    out.append(("ACCEL_1G", "PASS" if 0.90 <= m_g <= 1.10 else "FAIL",
                f"|a| = {mean(mag):.0f} LSB = {m_g:.3f} g (mong đợi 2048 ±10%)"))
    out.append(("ACCEL_NOISE", "PASS" if sd_mg < 10 else "WARN",
                f"std|a| = {sd_mg:.1f} mg (mong đợi < 10 mg khi để yên)"))
    gbias = max(abs(mean(c)) for c in (gx, gy, gz))
    gstd = max(std(c) for c in (gx, gy, gz))
    out.append(("GYRO_BIAS", "PASS" if gbias <= 1 else "WARN",
                f"max |TB| = {gbias:.2f} LSB = {gbias/GYR_LSB_PER_DPS:.3f} °/s (mong đợi ≤ 1 sau hiệu chuẩn)"))
    out.append(("GYRO_NOISE", "PASS" if gstd < 3 else "WARN",
                f"max std = {gstd:.2f} LSB = {gstd/GYR_LSB_PER_DPS:.3f} °/s"))
    return out


def print_table(rows, title):
    print(f"\n=== {title} ===")
    for name, res, detail in rows:
        print(f"  [{res}] {name:<16} {detail}")


def verdict(rows):
    return "FAIL" if any(r[1] == "FAIL" for r in rows) else ("WARN" if any(r[1] == "WARN" for r in rows) else "PASS")


def save_csv(samples, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_ms", "ax", "ay", "az", "gx", "gy", "gz", "btn"])
        w.writerows(samples)
    print(f"   đã lưu {len(samples)} mẫu vào {path}")


# --------------------------------------------------------------------------- các lệnh

def cmd_check(args):
    src = open_source(args)
    rows = []
    try:
        if not args.no_header:
            print(f"--> Nhấn nút RESET trên board MCU (chờ tối đa {args.timeout} s)...")
            hdr, streaming = read_header(src, args.timeout)
            for tid, name, detail, res in hdr:
                rows.append((f"{tid} {name}", res, detail))
            if not hdr:
                rows.append(("FW_REPORT", "FAIL", "không nhận được báo cáo T1..T7 từ firmware"))
            if not streaming:
                print_table(rows, "BÁO CÁO FIRMWARE")
                print("\nKẾT LUẬN: FAIL — firmware không vào được chế độ stream (xem lỗi T1..T4 ở trên)")
                return 1
        print(f"--> Để cảm biến NẰM YÊN, thu {args.seconds} s dữ liệu...")
        samples = collect(src, args.seconds)
    finally:
        src.close()

    if args.save:
        save_csv(samples, args.save)
    rows += analyze(samples, static=not args.moving)
    print_table(rows, "KẾT QUẢ")
    v = verdict(rows)
    print(f"\nKẾT LUẬN: {v}")
    return 1 if v == "FAIL" else 0


POSES = [
    ("+X hướng LÊN trời", (1, 0, 0)),
    ("-X hướng LÊN trời (lật ngược)", (-1, 0, 0)),
    ("+Y hướng LÊN trời", (0, 1, 0)),
    ("-Y hướng LÊN trời", (0, -1, 0)),
    ("+Z hướng LÊN trời (đặt phẳng, mặt linh kiện lên)", (0, 0, 1)),
    ("-Z hướng LÊN trời (úp mặt linh kiện xuống)", (0, 0, -1)),
]


def average_pose(src, seconds=2.0):
    src.flush()
    s = collect(src, seconds, echo_comments=False)
    if len(s) < 50:
        return None
    return [mean([x[i] for x in s]) for i in (1, 2, 3)]


def cmd_orient(args):
    src = open_source(args)
    rows = []
    tol = 0.10 * ACC_LSB_PER_G           # ±0,1 g
    try:
        print("Kiểm tra chiều trục: trục được ghi trên module (mũi tên X, Y). Mỗi tư thế giữ yên 2 s.")
        print("Cảm biến đo +1 g (≈ +2048) trên trục đang hướng LÊN trời.\n")
        for name, g in POSES:
            input(f"--> Đặt {name} rồi nhấn Enter...")
            if isinstance(src, SimSource):
                src.set_gravity(g)
            a = average_pose(src)
            if a is None:
                rows.append((name, "FAIL", "không đủ dữ liệu"))
                continue
            exp = [ACC_LSB_PER_G * x for x in g]
            err = max(abs(ai - ei) for ai, ei in zip(a, exp))
            res = "PASS" if err <= tol else ("WARN" if err <= 2 * tol else "FAIL")
            rows.append((name, res, f"ax={a[0]:+6.0f} ay={a[1]:+6.0f} az={a[2]:+6.0f} "
                                     f"(sai lệch lớn nhất {err/ACC_LSB_PER_G*1000:.0f} mg)"))
            print(f"    {res}: {rows[-1][2]}")

        input("\n--> Gắn cảm biến lên mũ ĐÚNG như khi dùng (Phụ lục A.1: Z lên trời, X về trước), đội mũ đứng thẳng, nhấn Enter...")
        if isinstance(src, SimSource):
            src.set_gravity((0, 0, 1))
        a = average_pose(src, 3.0)
    finally:
        src.close()

    print_table(rows, "6 TƯ THẾ")
    if a:
        print(f"\nKhi đeo đứng thẳng: ax={a[0]:+.0f} ay={a[1]:+.0f} az={a[2]:+.0f}")
        ok = abs(a[2] - ACC_LSB_PER_G) <= 0.15 * ACC_LSB_PER_G
        print(f"--> Ghi vào Phụ lục A.1:  AZ_dung_yen = {a[2]:+.0f}"
              + ("" if ok else "   (!) AZ xa +2048 — trục Z chưa hướng lên trời, xem lại cách gắn"))
    v = verdict(rows)
    print(f"\nKẾT LUẬN: {v}")
    return 1 if v == "FAIL" else 0


def cmd_plot(args):
    try:
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation
    except ImportError:
        sys.exit("Thiếu matplotlib: pip install matplotlib")

    src = open_source(args)
    win = int(args.window * FS_HZ)
    buf = collections.deque(maxlen=win)
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            s = parse_sample(src.readline())
            if s:
                buf.append(s)

    th = threading.Thread(target=reader, daemon=True)
    th.start()

    fig, (pa, pg) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
    names_a, names_g = ("ax", "ay", "az"), ("gx", "gy", "gz")
    la = [pa.plot([], [], label=n)[0] for n in names_a]
    lg = [pg.plot([], [], label=n)[0] for n in names_g]
    pa.set_ylabel("accel (g)"); pa.set_ylim(-2.5, 2.5); pa.legend(loc="upper left"); pa.grid(True)
    pg.set_ylabel("gyro (°/s)"); pg.set_ylim(-300, 300); pg.legend(loc="upper left"); pg.grid(True)
    pg.set_xlabel("thời gian (s)")
    title = fig.suptitle("MPU6050")

    def update(_):
        data = list(buf)
        if len(data) < 2:
            return
        t0 = data[-1][0]
        ts = [(d[0] - t0) / 1000.0 for d in data]
        for i, line in enumerate(la):
            line.set_data(ts, [d[1 + i] / ACC_LSB_PER_G for d in data])
        for i, line in enumerate(lg):
            line.set_data(ts, [d[4 + i] / GYR_LSB_PER_DPS for d in data])
        pa.set_xlim(-args.window, 0)
        a = data[-1]
        mag = math.sqrt(a[1] ** 2 + a[2] ** 2 + a[3] ** 2) / ACC_LSB_PER_G
        title.set_text(f"MPU6050 — |a| = {mag:.2f} g   btn = {a[7]}")

    _anim = FuncAnimation(fig, update, interval=50, cache_frame_data=False)
    plt.show()
    stop.set()
    th.join(timeout=1)
    src.close()
    return 0


def cmd_analyze(args):
    samples = []
    with open(args.file, newline="") as f:
        for line in f:
            s = parse_sample(line.strip())
            if s:
                samples.append(s)
    rows = analyze(samples, static=not args.moving)
    print_table(rows, f"PHÂN TÍCH {args.file}")
    v = verdict(rows)
    print(f"\nKẾT LUẬN: {v}")
    return 1 if v == "FAIL" else 0


def main():
    p = argparse.ArgumentParser(description="Kiểm tra cảm biến MPU6050 qua UART của firmware test")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_src(sp):
        sp.add_argument("--port", help="cổng COM, vd. COM5")
        sp.add_argument("--baud", type=int, default=BAUD, help=f"mặc định {BAUD}")
        sp.add_argument("--sim", action="store_true", help="dùng dữ liệu giả, không cần board")

    sp = sub.add_parser("check", help="báo cáo T1..T7 + phân tích dữ liệu tĩnh")
    add_src(sp)
    sp.add_argument("--seconds", type=float, default=10, help="thời gian thu (mặc định 10 s)")
    sp.add_argument("--timeout", type=float, default=30, help="thời gian chờ báo cáo sau RESET")
    sp.add_argument("--no-header", action="store_true", help="không chờ báo cáo, phân tích stream ngay")
    sp.add_argument("--moving", action="store_true", help="dữ liệu có chuyển động: chỉ kiểm thời gian/giá trị")
    sp.add_argument("--save", help="lưu CSV đã thu")
    sp.set_defaults(fn=cmd_check)

    sp = sub.add_parser("orient", help="kiểm tra 6 tư thế + đo AY_dung_yen")
    add_src(sp)
    sp.set_defaults(fn=cmd_orient)

    sp = sub.add_parser("plot", help="vẽ realtime")
    add_src(sp)
    sp.add_argument("--window", type=float, default=5, help="độ dài cửa sổ vẽ (s)")
    sp.set_defaults(fn=cmd_plot)

    sp = sub.add_parser("analyze", help="phân tích file CSV đã lưu")
    sp.add_argument("file")
    sp.add_argument("--moving", action="store_true")
    sp.set_defaults(fn=cmd_analyze)

    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
