#!/usr/bin/env python
# tools/truc_cam_bien.py — đọc log 5 tư thế (ghi_uart --tu-the) rồi suy ra bảng đổi trục cảm biến → trục người
# (X trước, Y trái, Z lên) cho fw_config.h (TRUC_X/Y/Z), và kiểm lại bằng posture_model trên chính log đó.
#   python -I tools/truc_cam_bien.py ket_qua_board/truc_nguc_<giờ>.txt [--da-doi]
# --da-doi: log ghi bằng firmware đã đổi trục (LOG in trục người) → chỉ kiểm, bảng đúng phải là (+1, +2, +3).
# Đứng → trục chỉ lên (Z); nằm ngửa → trục chỉ ra trước (X); nằm nghiêng phải (vai phải chạm đất) → trục chỉ sang trái (Y).
import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
import posture_model as pm  # noqa: E402

KY_VONG = {"dung": "DUNG", "nam_ngua": "NAM_NGUA", "nghieng_phai": "NGHIENG_PHAI", "nghieng_trai": "NGHIENG_TRAI",
           "cui": "CUI"}


def doc(path):
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


def doan_giu(marks, n):
    """{tư thế: (đầu, cuối)} của đoạn giữ yên, bỏ 30 % đầu (lúc vừa vào tư thế)."""
    out = {}
    for i, (k, m, ph) in enumerate(marks):
        if ph == "giu":
            end = marks[i + 1][0] if i + 1 < len(marks) else n
            out[m] = (k + (end - k) * 3 // 10, end)
    return out


def doi_truc(a, t):
    b = np.zeros_like(a)
    for i, c in enumerate(t):
        for g in (0, 3):
            b[:, g + i] = np.clip(np.sign(c) * a[:, g + abs(c) - 1], -32767, 32767)
    return b


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--da-doi", action="store_true")
    a = ap.parse_args()
    s, marks = doc(a.log)
    seg = doan_giu(marks, len(s))
    print(f"{len(s)} mẫu; trọng lực trung bình lúc giữ yên (LSB, 2048 = 1 g):")
    tb = {}
    for m, (i0, i1) in seg.items():
        tb[m] = s[i0:i1, :3].mean(0)
        g = np.linalg.norm(tb[m])
        print(f"  {m:13s} n={i1 - i0:4d}  x {tb[m][0]:7.0f}  y {tb[m][1]:7.0f}  z {tb[m][2]:7.0f}  |g| {g:5.0f}")

    def truc_chinh(v):
        i = int(np.argmax(np.abs(v)))
        return (i + 1) * (1 if v[i] > 0 else -1), abs(v[i]) / np.linalg.norm(v)

    t, ok = [], True
    for m, ten in (("nam_ngua", "X trước"), ("nghieng_phai", "Y trái"), ("dung", "Z lên")):
        if m not in tb:
            sys.exit(f"thiếu đoạn giữ yên '{m}'")
        c, ty = truc_chinh(tb[m])
        t.append(c)
        print(f"  {ten}: {'+-'[c < 0]}{'XYZ'[abs(c) - 1]} cảm biến (trục đó mang {100 * ty:.0f} % trọng lực)")
        ok &= ty > 0.85
    t = tuple(t)
    if sorted(abs(c) for c in t) != [1, 2, 3]:
        sys.exit(f"bảng {t} không phải phép xoay (hai tư thế cùng một trục): đo lại")
    m3 = np.zeros((3, 3))
    for i, c in enumerate(t):
        m3[i, abs(c) - 1] = np.sign(c)
    det = round(np.linalg.det(m3))
    print(f"bảng đổi trục: TRUC_X {t[0]:+d}, TRUC_Y {t[1]:+d}, TRUC_Z {t[2]:+d}  (định thức {det:+d}"
          f"{', phép xoay đúng' if det == 1 else ': trục bị lật gương, kiểm lại nghiêng trái/phải'})")
    if "nghieng_trai" in tb:
        c, _ = truc_chinh(tb["nghieng_trai"])
        print(f"  kiểm chéo: nghiêng trái ra {'+-'[c < 0]}{'XYZ'[abs(c) - 1]}, phải là ngược dấu Y trái → "
              f"{'đúng' if c == -t[1] else 'SAI'}")
        ok &= c == -t[1]
    if a.da_doi:
        print("log đã đổi trục: bảng phải là (+1, +2, +3) →", "ĐÚNG" if t == (1, 2, 3) else "SAI")
        ok &= t == (1, 2, 3)
    b = s if a.da_doi else doi_truc(s, t)
    p, tt = pm.Posture(), []
    for r in b:
        p.push(r)
        tt.append(pm.TEN[p.tt])
    print("posture_model trên log đã đổi trục, tư thế ở cuối mỗi đoạn giữ yên:")
    for m, (_, i1) in seg.items():
        kv = KY_VONG.get(m, "?")
        print(f"  {m:13s} → {tt[i1 - 1]:13s} {'✓' if tt[i1 - 1] == kv else '✗ (kỳ vọng ' + kv + ')'}")
    print("KẾT LUẬN:", "bảng rõ ràng" if ok else "có trục không rõ (< 85 % trọng lực) hoặc kiểm chéo sai: đo lại")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
