#!/usr/bin/env python
# tools/ghi_uart.py — ghi mọi dòng MCU in qua UART0 (460800 8N1) ra màn hình và ra file, để gửi lại kết quả từng bước đợt B.
#
#   python -I tools/ghi_uart.py --port COM5 --buoc B5                       # ghi 20 s → ket_qua_board/B5_<giờ>.txt
#   python -I tools/ghi_uart.py --port COM5 --buoc B7 --lenh 1 s --giay 30  # gửi lệnh menu "1" rồi "s", ghi 30 s
#   python -I tools/ghi_uart.py --port COM5 --buoc B5 --lenh STAT --reset   # nhấn reset trên board trong 3 s đầu
#   python -I tools/ghi_uart.py --liet-ke                                    # xem có cổng COM nào
#
# Đóng Tera Term, PuTTY, miniterm trước khi chạy: Windows chỉ cho một chương trình mở cổng COM.
# File nằm trong ket_qua_board/ (không lên git); gửi lại bằng cách dán nội dung vào chat kèm "Cập nhật: B<số>".
import argparse
import datetime
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="ghi UART của MCU ra file (đợt B)")
    ap.add_argument("--port", help="cổng COM của mạch USB-UART, ví dụ COM5")
    ap.add_argument("--baud", type=int, default=460800)
    ap.add_argument("--buoc", default="log", help="tên bước, ví dụ B5 (đặt tên file)")
    ap.add_argument("--giay", type=float, default=20, help="ghi bao nhiêu giây")
    ap.add_argument("--lenh", nargs="*", default=[], help="lệnh gửi lần lượt, cách nhau 1 s (ví dụ: 1 s, hoặc STAT)")
    ap.add_argument("--reset", action="store_true", help="chờ 3 s để nhấn reset trên board trước khi gửi lệnh")
    ap.add_argument("--liet-ke", action="store_true", help="liệt kê cổng COM rồi thoát")
    a = ap.parse_args()
    try:
        import serial
        from serial.tools import list_ports
    except ImportError:
        sys.exit("Thiếu pyserial: python -m pip install pyserial")
    if a.liet_ke or not a.port:
        for p in list_ports.comports():
            print(f"{p.device}: {p.description}")
        if not a.port:
            print("Chọn cổng bằng --port COMx")
        return 0
    out_dir = ROOT / "ket_qua_board"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{a.buoc}_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
    try:
        s = serial.Serial(a.port, a.baud, timeout=0.1)
    except serial.SerialException as e:
        sys.exit(f"Không mở được {a.port}: {e}\nKiểm cáp USB-UART, tên cổng (--liet-ke), và đóng chương trình khác đang mở cổng.")
    with s, open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# ghi_uart {a.port} {a.baud} bước {a.buoc} lệnh {a.lenh} lúc {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        t0 = time.monotonic()
        pending = list(a.lenh)
        t_next = t0 + (3.0 if a.reset else 0.5)
        if a.reset:
            print("Nhấn reset trên EVK ngay bây giờ (giữ SW3 nếu cần vào menu chẩn đoán)…")
        buf = b""
        while time.monotonic() - t0 < a.giay:
            if pending and time.monotonic() >= t_next:
                cmd = pending.pop(0)
                s.write((cmd + ("\r\n" if len(cmd) > 1 else "")).encode())
                f.write(f"# >>> gửi: {cmd}\n")
                print(f">>> gửi: {cmd}")
                t_next = time.monotonic() + 1.0
            buf += s.read(4096)
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                txt = line.decode("utf-8", "replace").rstrip("\r")
                print(txt)
                f.write(txt + "\n")
        if buf:
            f.write(buf.decode("utf-8", "replace") + "\n")
    print(f"\nĐã lưu: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
