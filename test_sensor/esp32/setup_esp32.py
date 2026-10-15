#!/usr/bin/env python3
"""
setup_esp32.py — cài MicroPython + script test MPU6050 lên ESP32 bằng một lệnh.

    python setup_esp32.py                 # tự tìm cổng COM của ESP32
    python setup_esp32.py --port COM5
    python setup_esp32.py --flash         # nạp lại MicroPython dù board đã có
    python setup_esp32.py --copy-only     # chỉ chép lại mpu6050_test.py (sau khi sửa script)

Các bước: tìm cổng -> kiểm tra board đã có MicroPython chưa -> (nếu chưa) nhận
dạng chip, tải firmware từ micropython.org, xóa flash, nạp -> chép
mpu6050_test.py thành main.py -> reset.
Cần: pip install esptool mpremote pyserial
"""
import argparse
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

MP_VERSION = "20260824-v1.29.0"
BOARDS = {                       # chip -> (tên board MicroPython, địa chỉ nạp)
    "ESP32":    ("ESP32_GENERIC", 0x1000),
    "ESP32-S3": ("ESP32_GENERIC_S3", 0x0),
    "ESP32-C3": ("ESP32_GENERIC_C3", 0x0),
}
PINS = {"ESP32": (22, 21, 4), "ESP32-S3": (9, 8, 7), "ESP32-C3": (5, 4, 6)}
USB_VIDS = {0x10C4: "CP210x", 0x1A86: "CH340/CH343", 0x303A: "ESP32 USB", 0x0403: "FTDI"}
HERE = Path(__file__).resolve().parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def run(args, check=True, capture=False, timeout=None):
    print("   $ " + " ".join(str(a) for a in args))
    r = subprocess.run([str(a) for a in args], text=True, capture_output=capture, timeout=timeout)
    if check and r.returncode != 0:
        if capture:
            print(r.stdout, r.stderr)
        sys.exit(f"Lệnh lỗi (mã {r.returncode}). Xem thông báo ở trên.")
    return r


def find_port():
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    esp = [p for p in ports if p.vid in USB_VIDS]
    for p in ports:
        tag = USB_VIDS.get(p.vid, "")
        print(f"   {p.device:<7} {p.description} {('<- ' + tag) if tag else ''}")
    if len(esp) == 1:
        return esp[0].device
    if not esp:
        sys.exit("Không thấy ESP32. Cắm cáp USB (loại có dây data), cài driver CP210x/CH340 nếu cần,\n"
                 "rồi chạy lại; hoặc chỉ định --port COMx.")
    sys.exit("Có nhiều cổng giống ESP32, chỉ định bằng --port COMx.")


def has_micropython(port):
    try:
        r = subprocess.run([sys.executable, "-m", "mpremote", "connect", port, "exec",
                            "import sys; print('MPY', sys.implementation._machine)"],
                           text=True, capture_output=True, timeout=20)
    except subprocess.TimeoutExpired:
        return None
    m = re.search(r"MPY (.+)", r.stdout)
    return m.group(1).strip() if m else None


def detect_chip(port):
    r = run([sys.executable, "-m", "esptool", "--port", port, "chip-id"], check=False, capture=True, timeout=60)
    out = r.stdout + r.stderr
    m = re.search(r"(ESP32(?:-[A-Z]\d+)?)", out)
    if not m:
        print(out)
        sys.exit("Không nhận được chip. Giữ nút BOOT trên ESP32, nhấn EN, thả BOOT rồi chạy lại.")
    chip = m.group(1)
    if chip not in BOARDS:
        sys.exit(f"Chip {chip} chưa hỗ trợ trong script (chỉ ESP32, ESP32-S3, ESP32-C3).")
    return chip


def download(board):
    name = f"{board}-{MP_VERSION}.bin"
    dst = HERE / "firmware" / name
    if dst.exists() and dst.stat().st_size > 500_000:
        print(f"   đã có {dst.name}")
        return dst
    dst.parent.mkdir(exist_ok=True)
    url = f"https://micropython.org/resources/firmware/{name}"
    print(f"   tải {url}")
    urllib.request.urlretrieve(url, dst)
    print(f"   {dst.stat().st_size // 1024} KB")
    return dst


def flash(port, chip):
    board, addr = BOARDS[chip]
    fw = download(board)
    run([sys.executable, "-m", "esptool", "--port", port, "erase-flash"], timeout=180)
    run([sys.executable, "-m", "esptool", "--port", port, "--baud", "460800",
         "write-flash", hex(addr), fw], timeout=300)
    print("   chờ board khởi động lại...")
    time.sleep(4)


def copy_script(port):
    run([sys.executable, "-m", "mpremote", "connect", port,
         "fs", "cp", HERE / "mpu6050_test.py", ":main.py", "+", "reset"], timeout=60)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port")
    ap.add_argument("--flash", action="store_true", help="luôn nạp lại MicroPython")
    ap.add_argument("--copy-only", action="store_true", help="chỉ chép script")
    a = ap.parse_args()

    print("[1] Tìm cổng ESP32")
    port = a.port or find_port()
    print(f"   -> {port}")

    if not a.copy_only:
        print("[2] Kiểm tra MicroPython trên board")
        mach = None if a.flash else has_micropython(port)
        if mach:
            print(f"   đã có MicroPython: {mach}")
        else:
            print("[3] Nhận dạng chip")
            chip = detect_chip(port)
            print(f"   -> {chip}")
            print("[4] Nạp MicroPython")
            flash(port, chip)

    print("[5] Chép mpu6050_test.py -> main.py và reset")
    copy_script(port)

    print("\nXONG. Nối MPU6050 (VCC 3V3, GND, AD0 -> GND):")
    for chip, (scl, sda, intp) in PINS.items():
        print(f"   {chip:<9} SCL=GPIO{scl:<3} SDA=GPIO{sda:<3} INT=GPIO{intp}")
    print("Rồi chạy (nhấn EN/RESET trên ESP32 khi được nhắc):")
    print(f"   python ..\\tools\\sensor_check.py check --port {port} --baud 115200")


if __name__ == "__main__":
    main()
