#!/usr/bin/env python
# tools/ghi_uart.py — ghi mọi dòng MCU in qua UART0 (460800 8N1) ra màn hình và ra file, để gửi lại kết quả từng bước đợt B.
#
#   python -I tools/ghi_uart.py --port COM5 --buoc B5                       # ghi 20 s → ket_qua_board/B5_<giờ>.txt
#   python -I tools/ghi_uart.py --port COM5 --buoc B7 --lenh 1 s --giay 30  # gửi lệnh menu "1" rồi "s", ghi 30 s
#   python -I tools/ghi_uart.py --port COM5 --buoc B5 --lenh STAT --reset   # nhấn reset trên board trong 3 s đầu
#   python -I tools/ghi_uart.py --liet-ke                                    # xem có cổng COM nào
#   python -I tools/ghi_uart.py --tcp 192.168.88.97 --lenh LOG --buoc truc_nguc --tu-the
#       đo hướng cảm biến khi đeo: nhắc lần lượt 9 tư thế (TU_THE, mỗi tư thế 6 s đổi + 10 s giữ yên, ≈ 2,5 phút),
#       ghi mốc "# >>> TU THE" vào file; mất WiFi thì tự nối lại. Đọc kết quả: tools/truc_cam_bien.py
#   python -I tools/ghi_uart.py --tcp 192.168.88.97 --lenh LOG --buoc dong_tac --kich-ban dong_tac   (≈ 9 phút)
#   python -I tools/ghi_uart.py --tcp 192.168.88.97 --lenh LOG --buoc nga --kich-ban nga             (≈ 5 phút, nệm dày)
#       dữ liệu đeo ngực để chốt ngưỡng xác nhận ngã (KICH_BAN); chấm: tools/nga_tren_log.py <file>
#
# Đóng Tera Term, PuTTY, miniterm trước khi chạy: Windows chỉ cho một chương trình mở cổng COM.
# File nằm trong ket_qua_board/ (không lên git); gửi lại bằng cách dán nội dung vào chat kèm "Cập nhật: B<số>".
import argparse
import datetime
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent


# Đeo trên người (28/10: lần đo trước chỉ cầm tay). Ngồi và đứng cùng hướng ngực, phân biệt bằng độ cao thay đổi lúc
# ngồi xuống / đứng dậy (A.11), nên có cả hai động tác; mã dung_2, dung_3 là đứng lại sau ngồi và sau cúi.
TU_THE = [("dung", "ĐỨNG THẲNG"),
          ("ngoi", "NGỒI XUỐNG GHẾ, lưng thẳng"),
          ("dung_2", "ĐỨNG DẬY, đứng thẳng"),
          ("cui", "CÚI NGƯỜI VỀ TRƯỚC (như nhặt đồ), giữ nguyên"),
          ("dung_3", "ĐỨNG THẲNG LẠI"),
          ("nam_ngua", "NẰM NGỬA"),
          ("nghieng_phai", "NẰM NGHIÊNG PHẢI (vai phải chạm đất)"),
          ("nghieng_trai", "NẰM NGHIÊNG TRÁI (vai trái chạm đất)"),
          ("nam_sap", "NẰM SẤP (úp mặt xuống)")]
TU_THE_DOI, TU_THE_GIU = 6.0, 10.0      # giây để đổi tư thế, giây giữ yên


def _lap(ma, ten, lan, doi, lam):
    return [(f"{ma}_{k}", f"{ten} (lần {k}/{lan})", doi, lam, "LÀM") for k in range(1, lan + 1)]


# Kịch bản (28/10, việc B2): dữ liệu đeo ngực để chốt ngưỡng xác nhận ngã (nga.c). Mỗi bước: (mã, lời nhắc, giây chuẩn
# bị, giây làm, chữ của pha làm). Mốc ghi vào file: "# >>> TU THE <mã> doi" lúc chuẩn bị, "... giu" lúc bắt đầu làm.
KICH_BAN = {
    "tu_the": [(m, ten, TU_THE_DOI, TU_THE_GIU, "GIỮ YÊN") for m, ten in TU_THE],
    # không phải ngã, dễ bị CNN nghi: ≈ 9 phút; cần ghế và giường / nệm
    "dong_tac": [("dung", "ĐỨNG YÊN", 3, 10, "GIỮ YÊN")]
                + _lap("ngoi_manh", "NGỒI PHỊCH XUỐNG GHẾ THẬT MẠNH, rồi đứng lên", 10, 3, 8)
                + _lap("cui", "CÚI NHẶT ĐỒ DƯỚI ĐẤT, rồi đứng thẳng", 5, 3, 8)
                + [("di", "ĐI LẠI BÌNH THƯỜNG", 3, 30, "LÀM")]
                + _lap("nam_xuong", "NẰM XUỐNG GIƯỜNG (như đi ngủ), nằm yên", 5, 4, 10)
                + _lap("ngoi_day", "NGỒI DẬY trên giường", 5, 3, 6)
                + _lap("lan", "ĐANG NẰM: LĂN NGƯỜI THẬT MẠNH qua trái / phải, nằm yên", 10, 3, 8),
    # ngã thật LÊN NỆM DÀY, có người đỡ: ≈ 5 phút
    "nga": [("dung", "ĐỨNG YÊN", 3, 10, "GIỮ YÊN")]
           + _lap("nga_nam", "NGÃ XUỐNG NỆM rồi NẰM YÊN", 10, 5, 12)
           + _lap("nga_nhe", "NGÃ NHẸ XUỐNG NỆM rồi NGỒI DẬY NGAY", 5, 5, 10),
}


class _Tcp:
    """Log TCP của ESP32 hub (esp32/mu_nga_hub, cổng 3333), cùng giao diện read/write như cổng COM.
    Mất kết nối (WiFi chập chờn khi nằm xuống) thì thử nối lại mỗi 1 s; ghi chú vào self.note để _record ghi ra file."""
    def __init__(self, host, port):
        import socket
        self.addr, self.note, self.t_retry = (host, port), [], 0.0
        self.s = socket.create_connection(self.addr, timeout=5)
        self.s.settimeout(0.1)

    def _lost(self, why):
        if self.s is not None:
            self.s.close()
            self.s = None
            self.note.append(f"# TCP mất kết nối ({why}), đang nối lại")

    def read(self, n):
        import socket
        if self.s is None:
            if time.monotonic() < self.t_retry:
                time.sleep(0.05)
                return b""
            self.t_retry = time.monotonic() + 1.0
            try:
                self.s = socket.create_connection(self.addr, timeout=2)
                self.s.settimeout(0.1)
                self.note.append("# TCP đã nối lại")
            except OSError:
                return b""
        try:
            b = self.s.recv(n)
        except socket.timeout:
            return b""
        except OSError as e:
            self._lost(e)
            return b""
        if not b:
            self._lost("ESP32 đóng")
        return b

    def write(self, b):
        try:
            self.s.sendall(b)
        except (OSError, AttributeError) as e:
            self._lost(e)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.s is not None:
            self.s.close()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="ghi UART của MCU ra file (đợt B)")
    ap.add_argument("--port", help="cổng COM của mạch USB-UART, ví dụ COM5")
    ap.add_argument("--baud", type=int, default=460800)
    ap.add_argument("--buoc", default="log", help="tên bước, ví dụ B5 (đặt tên file)")
    ap.add_argument("--giay", type=float, default=20, help="ghi bao nhiêu giây")
    ap.add_argument("--lenh", nargs="*", default=[], help="lệnh gửi lần lượt, cách nhau 1 s (ví dụ: 1 s, hoặc STAT)")
    ap.add_argument("--reset", action="store_true", help="chờ 3 s để nhấn reset trên board trước khi gửi lệnh")
    ap.add_argument("--liet-ke", action="store_true", help="liệt kê cổng COM rồi thoát")
    ap.add_argument("--tcp", help="đọc log ESP32 qua WiFi thay cho cổng COM: IP hoặc IP:cổng (mặc định 3333)")
    ap.add_argument("--tu-the", action="store_true", help="= --kich-ban tu_the (đo hướng cảm biến, 9 tư thế)")
    ap.add_argument("--kich-ban", choices=sorted(KICH_BAN),
                    help="nhắc từng bước trên màn hình, ghi mốc vào file; tự đặt --giay; màn hình chỉ hiện lời nhắc")
    a = ap.parse_args()
    if a.tu_the:
        a.kich_ban = "tu_the"
    a.tu_the = bool(a.kich_ban)
    if a.kich_ban:
        a.giay = 3 + sum(doi + lam for _, _, doi, lam, _ in KICH_BAN[a.kich_ban]) + 2
    try:
        import serial
        from serial.tools import list_ports
    except ImportError:
        sys.exit("Thiếu pyserial: python -m pip install pyserial")
    if a.liet_ke or not (a.port or a.tcp):
        for p in list_ports.comports():
            print(f"{p.device}: {p.description}")
        if not a.port:
            print("Chọn cổng bằng --port COMx")
        return 0
    out_dir = ROOT / "ket_qua_board"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{a.buoc}_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
    if a.tcp:
        host, _, port = a.tcp.partition(":")
        try:
            s = _Tcp(host, int(port or 3333))
        except OSError as e:
            sys.exit(f"Không kết nối được {a.tcp}: {e}\nLaptop phải vào cùng WiFi với ESP32; IP lấy ở dòng '# WiFi ... IP' trên USB.")
        a.port = f"tcp://{host}:{port or 3333}"
    else:
        s = _open_serial(serial, a)
    with s, open(out, "w", encoding="utf-8", newline="\n") as f:
        _record(s, f, a)
    print(f"\nĐã lưu: {out}")
    return 0


def _open_serial(serial, a):
    try:
        return serial.Serial(a.port, a.baud, timeout=0.1)
    except serial.SerialException as e:
        sys.exit(f"Không mở được {a.port}: {e}\nKiểm cáp USB-UART, tên cổng (--liet-ke), và đóng chương trình khác đang mở cổng.")


def _record(s, f, a):
    f.write(f"# ghi_uart {a.port} {a.baud} bước {a.buoc} lệnh {a.lenh} lúc {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
    t0 = time.monotonic()
    pending = list(a.lenh)
    t_next = t0 + (3.0 if a.reset else 0.5)
    if a.reset:
        print("Nhấn reset trên board ngay bây giờ (giữ SW3 nếu cần vào menu chẩn đoán của MCU)…")
    buf = b""
    # lịch: (lúc bắt đầu chuẩn bị, lúc bắt đầu làm, mã, lời nhắc, giây chuẩn bị, giây làm, chữ pha làm); bắt đầu sau 3 s
    lich, t = [], 3.0
    for m, ten, doi, lam, chu in (KICH_BAN[a.kich_ban] if a.kich_ban else []):
        lich.append((t, t + doi, m, ten, doi, lam, chu))
        t += doi + lam
    da_nhac, n_mau, t_dem = set(), 0, -1
    while time.monotonic() - t0 < a.giay:
        dt = time.monotonic() - t0
        for k, (t_doi, t_giu, m, ten, doi, lam, chu) in enumerate(lich):
            if dt >= t_doi and (k, 0) not in da_nhac:
                da_nhac.add((k, 0))
                print(f"\n=== {k + 1}/{len(lich)}: chuẩn bị {ten} ({doi:.0f} s) ===")
                f.write(f"# >>> TU THE {m} doi\n")
            if dt >= t_giu and (k, 1) not in da_nhac:
                da_nhac.add((k, 1))
                print(f"=== {chu}: {ten} ({lam:.0f} s) ===")
                f.write(f"# >>> TU THE {m} giu\n")
        if lich and int(dt) != t_dem:
            t_dem = int(dt)
            print(f"  {t_dem:3d} s, đã nhận {n_mau} mẫu", end="\r")
        for nt in getattr(s, "note", []):
            print("\n" + nt)
            f.write(nt + "\n")
            if "nối lại" in nt and "đã" in nt:      # ESP32 có thể vừa khởi động lại: gửi lại lệnh (LOG)
                pending, t_next = list(a.lenh), time.monotonic()
        if hasattr(s, "note"):
            s.note.clear()
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
            if not (a.tu_the and txt[:1].isdigit()):
                print(txt)
            elif txt.count(",") == 8:
                n_mau += 1
            f.write(txt + "\n")
    if buf:
        f.write(buf.decode("utf-8", "replace") + "\n")
    if lich:
        print(f"\n=== XONG: {n_mau} mẫu ({n_mau / 100:.0f} s ở 100 Hz). Đủ khi gần {a.giay - 3:.0f} s ===")


if __name__ == "__main__":
    sys.exit(main())
