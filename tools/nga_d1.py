#!/usr/bin/env python
# tools/nga_d1.py — đo tầng xác nhận ngã (nga.c) trên bản ghi D1: mỗi bản ghi chạy riêng qua nguyên lõi ESP32 (hub.c,
# CNN golden thay FPGA, Safety FSM, tư thế, nga.c) dạng mã máy Cortex-M0 trong Unicorn (m0_test mode 11), có 3 s đứng
# yên ở đầu. Mỗi bản ghi: CNN có nghi (vào SUSPECT) không, nga.c có xác nhận không.
#   python tools/nga_d1.py [--subject 102] [--out <file.csv>]
# Chỉ tiêu: ngã (901–920) được xác nhận; sinh hoạt (801–816) không được xác nhận.
# Lưu ý: d1_trials_50hz.npz hiện là kênh ĐẦU (kênh ngực dạng bản ghi liền chưa có, việc B1): chỉ là ước lượng.
import argparse
import pathlib
import struct
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import m0_test as m0  # noqa: E402

NGA_EV = []          # các lần xét ngã của lần chạy gần nhất
LD = ['-', 'trước không thẳng', 'không va chạm', 'không nằm / ngực không hạ', 'nằm', 'ngực hạ', 'bất động']
ST = ["STANDBY", "MONITOR", "SUSPECT", "PRE_ALARM", "ALARM", "COOLDOWN"]
WHY_KHONG_NGA = 9


def mot_ban_ghi(x50, P, truc, off):
    up = np.empty((2 * len(x50) - 1, 6), np.int64)          # 50 → 100 Hz như app_stream
    up[0::2] = x50
    up[1::2] = (x50[:-1] + x50[1:]) // 2
    b = np.concatenate([np.repeat(up[:1], 300, 0), up])
    b = np.clip(b, -32767 + 512, 32767 - 512)
    s_cb = np.zeros_like(b)
    for i_nguoi, c in enumerate(truc):
        s_cb[:, abs(c) - 1] = np.sign(c) * (b[:, i_nguoi] + off[i_nguoi])
        s_cb[:, 3 + abs(c) - 1] = np.sign(c) * b[:, 3 + i_nguoi]
    stream = b"".join(m0.node_pack(k, s_cb[k], 0) for k in range(len(s_cb)))
    blob = m0.cnn_blob(P, []) + struct.pack("<IBBBB", len(stream), 0, 1, 5, 1) + stream
    NGA_EV.clear()
    _, out = m0.run(11, 0, blob, max_insn=4_000_000_000)
    ev, i = [], 0
    while out[i] != ord("T"):
        if out[i] == ord("R"):
            i += 4
        elif out[i] == ord("N"):                           # 'N' t hd ly_do truoc_thang co_va_cham peak2 dh_dot co_dot
            t, hd, ld, tr, vc = struct.unpack("<IBBBB", out[i + 1:i + 9])
            pk2, dh, cd = struct.unpack("<IqB", out[i + 9:i + 22])
            NGA_EV.append((t, hd, ld, tr, vc, pk2 ** 0.5 / 2048, dh * 9.80665 / 2048 / 1e4 if cd else None))
            i += 22
        else:
            ev.append((struct.unpack("<I", out[i + 1:i + 5])[0], out[i + 5], out[i + 6])); i += 7
    # CNN nghi = có SUSPECT, hoặc có lần bị loại ngay trong khe vào SUSPECT (mode 11 chỉ thấy MONITOR, KHONG_NGA)
    nghi = any(ST[s] == "SUSPECT" for _, s, _ in ev) or any(w == WHY_KHONG_NGA for _, _, w in ev)
    # xác nhận = có SUSPECT mà sự kiện ngay sau không phải "về MONITOR vì KHONG_NGA"
    xn = False
    for j, (t, s, w) in enumerate(ev):
        if ST[s] == "SUSPECT" and not (j + 1 < len(ev) and ev[j + 1][2] == WHY_KHONG_NGA):
            xn = True
    return nghi, xn


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", type=int, default=102)
    ap.add_argument("--out")
    ap.add_argument("--act", type=int, nargs="*", help="chỉ chạy các mã hoạt động này")
    a = ap.parse_args()
    z = np.load(ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz")
    D, S, L, A, U = z["data"], z["start"], z["length"], z["act"], z["subject"]
    name, P = [(n, p) for n, p in m0.cnn_models()][0]
    truc, off = m0.vi_tri_deo()
    idx = np.flatnonzero((U == a.subject) & (np.isin(A, a.act) if a.act else True))
    print(f"D1 người {a.subject}: {len(idx)} bản ghi, mô hình {name}, vị trí đeo theo fw_config.h {truc} {off}")
    rows = []
    for n_i, i in enumerate(idx):
        act = int(A[i])
        nghi, xn = mot_ban_ghi(D[S[i]:S[i] + L[i]].astype(np.int64), P, truc, off)
        rows.append((act, nghi, xn))
        lydo = "; ".join(f"{'XÁC NHẬN' if hd == 1 else 'loại'}: {LD[ld]} (trước thẳng {tr}, đỉnh {pk:.2f} g, "
                         f"Δh {'-' if dh is None else f'{dh:+.2f} m'})" for _, hd, ld, tr, vc, pk, dh in NGA_EV)
        print(f"  {n_i + 1:3d}/{len(idx)} act {act}: CNN nghi {int(nghi)}, xác nhận ngã {int(xn)}  {lydo}", flush=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("act,cnn_nghi,xac_nhan\n")
            for act, nghi, xn in rows:
                f.write(f"{act},{int(nghi)},{int(xn)}\n")
    nga = [r for r in rows if r[0] >= 900]
    sh = [r for r in rows if r[0] < 900]
    print(f"\nngã {len(nga)} bản ghi: CNN nghi {sum(r[1] for r in nga)}, xác nhận {sum(r[2] for r in nga)} "
          f"({100 * sum(r[2] for r in nga) / max(1, len(nga)):.1f} %)")
    print(f"sinh hoạt {len(sh)} bản ghi: CNN nghi {sum(r[1] for r in sh)}, xác nhận (báo nhầm) {sum(r[2] for r in sh)}")
    for act in sorted({r[0] for r in rows}):
        rr = [r for r in rows if r[0] == act]
        print(f"  {act}: {len(rr)} bản ghi, CNN nghi {sum(r[1] for r in rr)}, xác nhận {sum(r[2] for r in rr)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
