# mpu6050_test.py — test MPU6050 bằng ESP32 + MicroPython.
#
# Chạy cùng các bài test T1..T7 với firmware SN32F407 (test_sensor/firmware),
# in cùng định dạng báo cáo, rồi stream CSV 100 Hz "t_ms,ax,ay,az,gx,gy,gz,btn"
# -> dùng chung tools/sensor_check.py (thêm --baud 115200).
# Được setup_esp32.py chép lên board thành main.py; nhấn EN/RESET để chạy lại.
import sys
import time
from machine import I2C, Pin

# ---------------------------------------------------------------- chân theo chip
_m = sys.implementation._machine.upper()
if "ESP32S3" in _m:
    SCL, SDA, INT = 9, 8, 7
elif "ESP32C3" in _m:
    SCL, SDA, INT = 5, 4, 6
else:                               # ESP32 thường (DevKit V1, WROOM-32)
    SCL, SDA, INT = 22, 21, 4

ADDR = 0x68
CFG = [                             # SPEC 2.1 (+0x37 chỉ ở bản test, xem README)
    (0x6B, 0x01), (0x19, 0x09), (0x1A, 0x03), (0x1B, 0x18),
    (0x1C, 0x18), (0x37, 0x30), (0x38, 0x01),
]
CALIB_SAMPLES = 200

n = {"PASS": 0, "WARN": 0, "FAIL": 0}
i2c = None
int_pin = None
int_ok = False
goff = [0, 0, 0]


def report(tid, name, res, detail):
    print("# %s %-14s: %s -> %s" % (tid, name, detail, res))
    n[res] += 1


def wr(reg, val):
    i2c.writeto_mem(ADDR, reg, bytes([val]))


def rd(reg, cnt=1):
    return i2c.readfrom_mem(ADDR, reg, cnt)


def s16(hi, lo):
    v = (hi << 8) | lo
    return v - 65536 if v & 0x8000 else v


def read7():
    b = rd(0x3B, 14)
    return [s16(b[2 * i], b[2 * i + 1]) for i in range(7)]


def data_ready():
    return rd(0x3A)[0] & 1


def wait_ready(timeout_ms=50):
    t0 = time.ticks_ms()
    while True:
        if int_ok:
            if int_pin.value():
                return
        elif data_ready():
            return
        if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
            raise OSError("het gio cho data-ready")


def configure():
    for i, (r, v) in enumerate(CFG):
        wr(r, v)
        if i == 0:
            time.sleep_ms(10)
    time.sleep_ms(50)


# ---------------------------------------------------------------- các bài test
def t1_bus():
    # gỡ bus treo: phát 9 xung SCL khi SDA bị giữ thấp
    scl = Pin(SCL, Pin.OPEN_DRAIN, value=1)
    sda = Pin(SDA, Pin.IN, Pin.PULL_UP)
    for _ in range(9):
        if sda.value():
            break
        scl.value(0); time.sleep_us(5); scl.value(1); time.sleep_us(5)
    s, c = sda.value(), Pin(SCL, Pin.IN, Pin.PULL_UP).value()
    if s and c:
        report("T1", "BUS_IDLE", "PASS", "SDA=1 SCL=1")
        return True
    report("T1", "BUS_IDLE", "FAIL", "SDA=%d SCL=%d (thieu pull-up / chap GND / sai chan)" % (s, c))
    return False


def t2_scan():
    found = i2c.scan()
    lst = " ".join("0x%02X" % a for a in found[:10]) or "-"
    if ADDR in found:
        report("T2", "I2C_SCAN", "PASS", "%d thiet bi: %s" % (len(found), lst))
        return True
    if 0x69 in found:
        report("T2", "I2C_SCAN", "FAIL", "thay 0x69 -> chan AD0 dang o muc 1, noi AD0 xuong GND")
    else:
        report("T2", "I2C_SCAN", "FAIL", "%d thiet bi: %s (khong co 0x68)" % (len(found), lst))
    return False


def t3_whoami():
    wid = rd(0x75)[0]
    if wid == 0x68:
        report("T3", "WHO_AM_I", "PASS", "0x%02X" % wid)
        return True
    if wid in (0x70, 0x71, 0x72, 0x73, 0x98, 0x19):
        report("T3", "WHO_AM_I", "WARN", "0x%02X: khong phai MPU6050 that (MPU6500/clone)" % wid)
        return True
    report("T3", "WHO_AM_I", "FAIL", "0x%02X (mong doi 0x68)" % wid)
    return False


def t4_config():
    wr(0x6B, 0x80)                  # DEVICE_RESET
    time.sleep_ms(100)
    wr(0x68, 0x07)                  # SIGNAL_PATH_RESET
    time.sleep_ms(100)
    configure()
    for r, v in CFG:
        got = rd(r)[0]
        if got != v:
            report("T4", "CONFIG", "FAIL", "doc lai 0x%02X = 0x%02X (khac gia tri da ghi)" % (r, got))
            return False
    report("T4", "CONFIG", "PASS", "%d thanh ghi doc lai dung" % len(CFG))
    return True


def _avg(cnt):
    s = [0] * 6
    for _ in range(cnt):
        t0 = time.ticks_ms()
        while not data_ready():
            if time.ticks_diff(time.ticks_ms(), t0) > 50:
                raise OSError("het gio cho data-ready")
        v = read7()
        for k, x in enumerate(v[0:3] + v[4:7]):
            s[k] += x
    return [x / cnt for x in s]


def t5_selftest():
    # Register Map rev 4.2 mục 4.1: accel ở ±8 g, gyro ở ±250 °/s, đạt khi |sai lệch| <= 14 %
    wr(0x1B, 0x00); wr(0x1C, 0x10); time.sleep_ms(100)
    base = _avg(50)
    wr(0x1B, 0xE0); wr(0x1C, 0xF0); time.sleep_ms(100)
    test = _avg(50)
    wr(0x1B, 0x18); wr(0x1C, 0x18); time.sleep_ms(100)
    t = rd(0x0D, 4)
    code = [((t[0] >> 3) & 0x1C) | ((t[3] >> 4) & 3),
            ((t[1] >> 3) & 0x1C) | ((t[3] >> 2) & 3),
            ((t[2] >> 3) & 0x1C) | (t[3] & 3),
            t[0] & 0x1F, t[1] & 0x1F, t[2] & 0x1F]
    ft = [4096 * 0.34 * (0.92 / 0.34) ** ((c - 1) / 30) if c else 0 for c in code[:3]]
    ft += [25 * 131 * 1.046 ** (c - 1) if c else 0 for c in code[3:]]
    ft[4] = -ft[4]
    parts, ok = [], True
    for i, nm in enumerate(("AX", "AY", "AZ", "GX", "GY", "GZ")):
        pct = 100 * ((test[i] - base[i]) - ft[i]) / ft[i] if ft[i] else 999
        ok = ok and ft[i] != 0 and abs(pct) <= 14
        parts.append("%s%+.1f%%" % (nm, pct))
    report("T5", "SELF_TEST", "PASS" if ok else "WARN", " ".join(parts) + " (dat: |x|<=14%)")


def t6_rate():
    global int_pin, int_ok
    configure()
    int_pin = Pin(INT, Pin.IN, Pin.PULL_DOWN)
    read7()                         # xóa chốt INT
    edges, prev = 0, int_pin.value()
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 2000:
        lv = int_pin.value()
        if lv and not prev:
            edges += 1
            read7()
        prev = lv
    if 194 <= edges <= 206:
        int_ok = True
        report("T6", "SAMPLE_RATE", "PASS", "INT: %d xung/2s = %.1f Hz" % (edges, edges / 2))
        return
    polls = 0
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 2000:
        if data_ready():
            polls += 1
            read7()
    report("T6", "SAMPLE_RATE", "FAIL",
           "INT(GPIO%d): %d xung/2s (mong doi 200); poll INT_STATUS: %d mau/2s" % (INT, edges, polls))
    if 194 <= polls <= 206:
        print("#    -> chip lay mau dung 100 Hz, loi o day/chan INT. Stream se dung che do poll.")


def t7_static():
    global goff
    sa, sg, ssg = [0] * 3, [0] * 3, [0] * 3
    sm = ssm = st = 0
    for _ in range(CALIB_SAMPLES):
        wait_ready()
        v = read7()
        for k in range(3):
            sa[k] += v[k]
            sg[k] += v[4 + k]
            ssg[k] += v[4 + k] ** 2
        m = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5
        sm += m
        ssm += m * m
        st += v[3]
    N = CALIB_SAMPLES
    goff = [int(x / N) for x in sg]
    sdg = [max(0, ssg[k] / N - (sg[k] / N) ** 2) ** 0.5 for k in range(3)]
    mm = sm / N
    sdm = max(0, ssm / N - mm * mm) ** 0.5
    temp = st / N / 340 + 36.53
    print("# T7 accel trung binh: ax=%d ay=%d az=%d (LSB, 2048 = 1 g)" % tuple(int(x / N) for x in sa))
    report("T7a", "GYRO_OFFSET", "WARN" if max(abs(x) for x in goff) > 328 else "PASS",
           "gx=%d gy=%d gz=%d LSB (se tru o moi mau)" % tuple(goff))
    report("T7b", "ACCEL_1G", "PASS" if 1843 <= mm <= 2253 else "FAIL",
           "|a|=%d LSB = %.2f g" % (mm, mm / 2048))
    noisy = sdm >= 40 or max(sdg) >= 10
    report("T7c", "NOISE", "WARN" if noisy else "PASS",
           "std|a|=%d std g=%d/%d/%d LSB%s" % (sdm, sdg[0], sdg[1], sdg[2],
                                              " (bi rung? de yen roi RESET)" if sdm >= 40 else ""))
    report("T7d", "TEMP", "PASS" if 0 < temp < 60 else "WARN", "%.1f C" % temp)


def run_tests():
    global i2c, int_ok
    for k in n:
        n[k] = 0
    int_ok = False
    print("\n# ===== MPU6050 TEST (VKU-NewBie, ESP32 %s: SCL=%d SDA=%d INT=%d) =====" % (_m, SCL, SDA, INT))
    print("# De cam bien NAM YEN trong suot qua trinh test (~6 s)")
    if not t1_bus():
        return False
    i2c = I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=400000)
    try:
        if not (t2_scan() and t3_whoami() and t4_config()):
            return False
        t5_selftest()
        t6_rate()
        t7_static()
    except OSError as e:
        report("T*", "I2C", "FAIL", "loi I2C: %s" % e)
        return False
    print("# SUMMARY pass=%d warn=%d fail=%d" % (n["PASS"], n["WARN"], n["FAIL"]))
    return True


def stream():
    print("# STREAM START (gyro da tru offset, int=%s)" % ("pin" if int_ok else "poll"))
    print("# t_ms,ax,ay,az,gx,gy,gz,btn")
    err = 0
    while True:
        try:
            wait_ready()
            t = time.ticks_ms()
            v = read7()
            err = 0
        except OSError as e:
            print("# ERR doc mau: %s" % e)
            err += 1
            if err >= 5:
                configure()
                err = 0
            continue
        print("%d,%d,%d,%d,%d,%d,%d,0" % (t, v[0], v[1], v[2],
                                         v[4] - goff[0], v[5] - goff[1], v[6] - goff[2]))


time.sleep_ms(100)                  # MPU6050 cần ~100 ms sau khi cấp nguồn
while not run_tests():
    print("# SUMMARY pass=%d warn=%d fail=%d" % (n["PASS"], n["WARN"], n["FAIL"]))
    print("# FATAL: sua loi roi cho, tu thu lai sau 2 s...")
    time.sleep(2)
stream()
