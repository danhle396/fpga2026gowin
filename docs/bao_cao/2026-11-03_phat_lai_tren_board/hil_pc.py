"""Phía PC của hil_board.ino.
  hil_pc.py tk
  hil_pc.py win <file npz có X> <file ra .npz> [--n N]
  hil_pc.py log <file log thật> <file ra .txt> [--chua-tru-offset] [--nhanh]
  hil_pc.py d1 <file ra .jsonl> [--subject S]
"""
import argparse, json, pathlib, struct, sys, time
import numpy as np
import serial

ROOT = pathlib.Path(r"D:\hoctap\fpga\fpga2026gowin")
TRUC, OFF = (3, -1, -2), (204, -3, -4)     # FW_VI_TRI_DEO 1, firmware/src/fw_config.h


def crc16(b):
    c = 0xFFFF
    for x in b:
        c ^= x << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c


# bảng để tính CRC nhanh cho khối lớn
_T = []
for _i in range(256):
    _c = _i << 8
    for _ in range(8):
        _c = ((_c << 1) ^ 0x1021) & 0xFFFF if _c & 0x8000 else (_c << 1) & 0xFFFF
    _T.append(_c)


def crc16_n(b):
    c = 0xFFFF
    for x in b:
        c = ((c << 8) & 0xFFFF) ^ _T[((c >> 8) ^ x) & 0xFF]
    return c


class Link:
    def __init__(self):
        s = serial.Serial()
        s.port, s.baudrate, s.timeout, s.write_timeout = "COM4", 921600, 0.02, 10
        s.dtr = False
        s.rts = False
        s.set_buffer_size(rx_size=1 << 20, tx_size=1 << 16)
        s.open()
        self.s, self.du, self.cho, self.rac = s, b"", 0.02, 0

    def dong(self, cho=0.02):
        """Các dòng đã nhận đủ."""
        if cho != self.cho:              # đổi timeout là cấu hình lại cổng, chỉ làm khi thật sự đổi
            self.s.timeout = self.cho = cho
        n = self.s.in_waiting
        b = self.s.read(n if n else 1)
        self.rac += b.count(b"\xff")     # 0xFF không thuộc dòng ASCII nào; cụm 64 byte rác từ cổng USB
        self.du += b.replace(b"\xff", b"")
        ra = []
        while b"\n" in self.du:
            l, self.du = self.du.split(b"\n", 1)
            l = l.decode("ascii", "replace").strip()
            if l:
                ra.append(l)
        return ra

    def cho_dong(self, dk, han=5.0):
        t = time.time()
        while time.time() - t < han:
            for l in self.dong():
                if dk(l):
                    return l
        raise TimeoutError("khong nhan duoc tra loi")

    def close(self):
        print("byte rac 0xFF da loc:", self.rac, flush=True)
        self.s.close()


def tu_kiem(L):
    L.s.write(b"T")
    l = L.cho_dong(lambda x: x.startswith("TK,"))
    print(l, flush=True)
    return l


def cmd_win(a):
    z = np.load(a.vao)
    X = z["X"]
    N = a.n or len(X)
    ra = pathlib.Path(a.ra)
    raw = np.zeros((N, 20), np.uint8)
    t_us = np.zeros(N, np.uint32)
    rc = np.full(N, 255, np.uint8)
    tam = ra.with_suffix(".tam.npz")
    if tam.exists():
        o = np.load(tam)
        if len(o["rc"]) == N:
            raw, t_us, rc = o["raw"], o["t_us"], o["rc"]
            print("tiep tuc, da co", int((rc != 255).sum()), flush=True)
    L = Link()
    tu_kiem(L)
    OUT = 8
    con = np.flatnonzero(rc == 255).tolist()
    p = 0
    dang = {}
    t0 = t_log = time.time()
    n_xong, n_loi, n_gui_lai = int((rc != 255).sum()), 0, 0
    lan_cuoi = t_xong = time.time()
    while p < len(con) or dang:
        if time.time() - t_xong > 60:
            np.savez(tam, raw=raw, t_us=t_us, rc=rc)
            raise TimeoutError(f"60 s khong co cua so nao xong, da xong {n_xong}/{N}")
        while p < len(con) and len(dang) < OUT:
            i = con[p]
            p += 1
            b = struct.pack("<I", i) + X[i].astype(np.int8).tobytes()
            L.s.write(b"W" + b + struct.pack(">H", crc16_n(b)))
            dang[i] = time.time()
        for l in L.dong(0.005):
            if l.startswith("r,"):
                q = l.split(",")
                if len(q) == 5 and len(q[4]) == 40:
                    try:
                        i, r, t, h = int(q[1]), int(q[2]), int(q[3]), bytes.fromhex(q[4])
                    except ValueError:
                        continue
                    if i in dang:
                        del dang[i]
                        raw[i] = np.frombuffer(h, np.uint8)
                        t_us[i] = t
                        rc[i] = r
                        n_xong += 1
                        lan_cuoi = t_xong = time.time()
            elif l.startswith("X,"):
                n_loi += 1
                print("ESP32:", l, flush=True)
                time.sleep(0.5)
                L.s.reset_input_buffer()
                L.du = b""
                con[p:p] = sorted(dang)
                n_gui_lai += len(dang)
                dang = {}
                lan_cuoi = time.time()
        if dang and time.time() - lan_cuoi > 3:
            print("qua han, gui lai", len(dang), flush=True)
            time.sleep(1.5)
            L.s.reset_input_buffer()
            L.du = b""
            con[p:p] = sorted(dang)
            n_gui_lai += len(dang)
            dang = {}
            lan_cuoi = time.time()
        if time.time() - t_log > 30:
            t_log = time.time()
            print(f"{n_xong}/{N} cua so, {n_xong / max(1e-3, time.time() - t0):.1f}/s, loi duong truyen {n_loi}", flush=True)
            np.savez(tam, raw=raw, t_us=t_us, rc=rc)
    tu_kiem(L)
    L.close()
    np.savez_compressed(ra, raw=raw, t_us=t_us, rc=rc)
    if tam.exists():
        tam.unlink()
    print(f"xong {N} cua so trong {time.time() - t0:.0f} s, loi duong truyen {n_loi}, gui lai {n_gui_lai}", flush=True)


def phien(L, s_cb, nga_en, pace, in_r, ghi=None):
    """Một phiên qua hub.c. s_cb: n × 6 int16, trục cảm biến. Trả về danh sách dòng sự kiện và dòng E."""
    L.s.write(b"I" + bytes([nga_en, pace, in_r]))
    L.cho_dong(lambda x: x == "i")
    ev, n = [], len(s_cb)
    BATCH = 32
    p = a_cho = 0
    t_a = time.time()
    gan_day = []
    while p < n or a_cho:
        while p < n and a_cho < 4:
            k = s_cb[p:p + BATCH]
            b = bytes([len(k)]) + k.astype("<i2").tobytes()
            L.s.write(b"B" + b + struct.pack(">H", crc16_n(b)))
            p += len(k)
            a_cho += 1
        for l in L.dong(0.005):
            gan_day = (gan_day + [l])[-8:]
            if l == "a":
                a_cho -= 1
                t_a = time.time()
            elif l.startswith("X,"):
                raise RuntimeError("ESP32 " + l)
            elif l[:2] in ("F,", "N,", "P,", "R,"):
                ev.append(l)
                if ghi:
                    ghi.write(l + "\n")
                    ghi.flush()
            else:
                print("dong la:", repr(l), flush=True)
                if ghi:
                    ghi.write("# dong la " + repr(l) + "\n")
                    ghi.flush()
        if time.time() - t_a > 15:
            raise TimeoutError(f"khong co xac nhan 15 s: da gui {p}/{n} mau, cho {a_cho} goi, dong cuoi {gan_day}")
    L.s.write(b"E")
    e = L.cho_dong(lambda x: x.startswith("E,"), 10)
    return ev, e


def sang_truc_cb(b):
    s = np.zeros_like(b)
    for i_nguoi, c in enumerate(TRUC):
        for g in (0, 3):
            s[:, g + abs(c) - 1] = np.sign(c) * b[:, g + i_nguoi]
    return s


def doc_log(path):
    rows, marks = [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line.startswith("# >>> TU THE"):
            _, _, _, _, m, ph = line.split()
            marks.append((len(rows), m, ph))
            continue
        p = line.split(",")
        if len(p) == 9 and p[0].isdigit():
            try:
                rows.append([int(x) for x in p[1:7]])
            except ValueError:
                pass
    return np.array(rows, np.int64), marks


def cmd_log(a):
    b, marks = doc_log(a.vao)
    if not a.chua_tru_offset:
        b = b + np.array(list(OFF) + [0, 0, 0])    # log đã trừ offset: cộng lại cho giống luồng MCU
    b = np.clip(b, -32767, 32767)
    s_cb = sang_truc_cb(b)
    L = Link()
    tk = tu_kiem(L)
    t0 = time.time()
    with open(a.ra, "w", encoding="utf8") as f:
        f.write(f"# nguon {pathlib.Path(a.vao).name} mau {len(b)} pace {0 if a.nhanh else 1} {tk}\n")
        for k, m, ph in marks:
            f.write(f"M,{k},{m},{ph}\n")
        ev, e = phien(L, s_cb, 1, 0 if a.nhanh else 1, 1, f)
        f.write(e + "\n")
        f.write(tu_kiem(L) + "\n")
    L.close()
    print(pathlib.Path(a.vao).name, e, f"{time.time() - t0:.0f} s", flush=True)


def cmd_d1(a):
    z = np.load(ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz")
    D, S, Ln, A, U, E = z["data"], z["start"], z["length"], z["act"], z["subject"], z["event"]
    idx = np.flatnonzero(U == a.subject) if a.subject else np.arange(len(A))
    ra = pathlib.Path(a.ra)
    xong = set()
    if ra.exists():
        for l in open(ra, encoding="utf8"):
            xong.add(json.loads(l)["i"])
    L = Link()
    tu_kiem(L)
    t0 = time.time()
    with open(ra, "a", encoding="utf8") as f:
        for n_i, i in enumerate(idx):
            if int(i) in xong:
                continue
            x50 = D[S[i]:S[i] + Ln[i]].astype(np.int64)
            up = np.empty((2 * len(x50) - 1, 6), np.int64)
            up[0::2] = x50
            up[1::2] = (x50[:-1] + x50[1:]) // 2
            b = np.concatenate([np.repeat(up[:1], 300, 0), up])      # như tools/nga_d1.py
            b = np.clip(b, -32767 + 512, 32767 - 512)
            s_cb = np.zeros_like(b)
            for i_nguoi, c in enumerate(TRUC):
                s_cb[:, abs(c) - 1] = np.sign(c) * (b[:, i_nguoi] + OFF[i_nguoi])
                s_cb[:, 3 + abs(c) - 1] = np.sign(c) * b[:, 3 + i_nguoi]
            ev, e = phien(L, s_cb, 1, 0, 0)
            f.write(json.dumps({"i": int(i), "s": int(U[i]), "act": int(A[i]), "event": int(E[i]), "ev": ev, "e": e}) + "\n")
            f.flush()
            if (n_i + 1) % 50 == 0:
                print(f"{n_i + 1}/{len(idx)} ban ghi, {time.time() - t0:.0f} s", flush=True)
    tu_kiem(L)
    L.close()
    print(f"xong {len(idx)} ban ghi, {time.time() - t0:.0f} s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="c", required=True)
    sp.add_parser("tk")
    w = sp.add_parser("win"); w.add_argument("vao"); w.add_argument("ra"); w.add_argument("--n", type=int)
    g = sp.add_parser("log"); g.add_argument("vao"); g.add_argument("ra"); g.add_argument("--chua-tru-offset", action="store_true"); g.add_argument("--nhanh", action="store_true")
    d = sp.add_parser("d1"); d.add_argument("ra"); d.add_argument("--subject", type=int)
    a = ap.parse_args()
    if a.c == "tk":
        L = Link(); tu_kiem(L); L.close()
    elif a.c == "win":
        cmd_win(a)
    elif a.c == "log":
        cmd_log(a)
    else:
        cmd_d1(a)


if __name__ == "__main__":
    main()
