#!/usr/bin/env python
# tools/nga_tren_log.py — chạy nguyên lõi ESP32 (hub.c: CNN golden thay FPGA, Safety FSM, tư thế, xác nhận ngã nga.c)
# trên một log LOG thật (ghi_uart --lenh LOG), dạng mã máy Cortex-M0 trong Unicorn (như m0_test mode 11), rồi in mọi lần
# FSM vào SUSPECT (CNN 2/3 FALL): không có / có tầng xác nhận ngã, mỗi lần nhóm đang làm động tác gì (mốc "# >>> TU THE").
#   python tools/nga_tren_log.py <log> [--chua-tru-offset]
# Log ghi bằng bản ESP32 trước 28/10 17:16 đã đổi trục nhưng CHƯA trừ ACC_OFF: thêm --chua-tru-offset.
# Cần unicorn (như m0_test) và firmware/build/test.bin (bash firmware/build.sh test).
import argparse
import pathlib
import struct
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import m0_test as m0  # noqa: E402
import truc_cam_bien as tc  # noqa: E402

WHY = ["NONE", "WEAR_ON", "WEAR_OFF", "VOTES", "STILL", "TIMEOUT", "CANCEL", "SOS", "ALARM_ACK", "KHONG_NGA"]
NGA_EV = []          # các lần xét ngã của lần chạy gần nhất
LD = ['-', 'trước không thẳng', 'không va chạm', 'không nằm / ngực không hạ', 'nằm', 'ngực hạ', 'bất động']
ST = ["STANDBY", "MONITOR", "SUSPECT", "PRE_ALARM", "ALARM", "COOLDOWN"]


def chay(stream, P, nga_en):
    blob = m0.cnn_blob(P, []) + struct.pack("<IBBBB", len(stream), 0, 1, 5, nga_en) + stream
    NGA_EV.clear()
    _, out = m0.run(11, 0, blob, max_insn=8_000_000_000)
    s_ev, i = [], 0
    while out[i] != ord("T"):
        if out[i] == ord("R"):
            i += 4
        elif out[i] == ord("N"):                           # 'N' t hd ly_do truoc_thang co_va_cham peak2 dh_dot co_dot
            t, hd, ld, tr, vc = struct.unpack("<IBBBB", out[i + 1:i + 9])
            pk2, dh, cd = struct.unpack("<IqB", out[i + 9:i + 22])
            NGA_EV.append((t, hd, ld, tr, vc, pk2 ** 0.5 / 2048, dh * 9.80665 / 2048 / 1e4 if cd else None))
            i += 22
        else:
            s_ev.append((struct.unpack("<I", out[i + 1:i + 5])[0], out[i + 5], out[i + 6])); i += 7
    return s_ev


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--chua-tru-offset", action="store_true")
    a = ap.parse_args()
    b, marks = tc.doc(a.log)                               # trục người
    truc, off = m0.vi_tri_deo()
    if not a.chua_tru_offset:
        b = b + np.array(list(off) + [0, 0, 0])            # log đã trừ offset: cộng lại cho giống luồng MCU
    b = np.clip(b, -32767, 32767)
    s_cb = np.zeros_like(b)                                # trục người → trục cảm biến (luồng MCU gửi)
    for i_nguoi, c in enumerate(truc):
        for g in (0, 3):
            s_cb[:, g + abs(c) - 1] = np.sign(c) * b[:, g + i_nguoi]
    stream = b"".join(m0.node_pack(k, s_cb[k], 0) for k in range(len(s_cb)))
    lab, cur, mk = [], "-", {k: f"{m}/{ph}" for k, m, ph in marks}
    for k in range(len(b)):
        cur = mk.get(k, cur)
        lab.append(cur)
    name, P = [(n, p) for n, p in m0.cnn_models()][0]
    print(f"{a.log}: {len(b)} mẫu ({len(b) / 100:.0f} s), mô hình {name}")
    for nga_en in (0, 1):
        ev = chay(stream, P, nga_en)
        sus = [(t, w) for t, st, w in ev if ST[st] == "SUSPECT"]
        print(f"\n{'CÓ' if nga_en else 'KHÔNG CÓ'} tầng xác nhận ngã:" + ("" if nga_en else f" {len(sus)} lần CNN vào SUSPECT"))
        for j, (t, st, w) in enumerate(ev):
            if ST[st] != "SUSPECT":
                continue
            nxt = ev[j + 1] if j + 1 < len(ev) else None
            kq = f"→ {ST[nxt[1]]} ({WHY[nxt[2]]}) sau {(nxt[0] - t) / 1000:.2f} s" if nxt else "→ (hết log)"
            k = min(t // 10, len(lab) - 1)
            print(f"  {t / 1000:7.2f} s  đang làm: {lab[k]:22s} {kq}")
        if nga_en:
            # loại ngay trong khe vào SUSPECT thì mode 11 chỉ thấy trạng thái cuối khe: MONITOR (KHONG_NGA)
            bo_ngay = [t for t, st, w in ev if ST[st] == "MONITOR" and WHY[w] == "KHONG_NGA"
                       and not any(t2 < t and ST[s2] == "SUSPECT" and t - t2 < 10_000 for t2, s2, _ in ev)]
            for t in bo_ngay:
                print(f"  {t / 1000:7.2f} s  đang làm: {lab[min(t // 10, len(lab) - 1)]:22s} → loại ngay (KHONG_NGA)")
            bo = sum(1 for j, (t, st, w) in enumerate(ev) if ST[st] == "SUSPECT" and j + 1 < len(ev)
                     and WHY[ev[j + 1][2]] == "KHONG_NGA") + len(bo_ngay)
            tong = len(sus) + len(bo_ngay)
            print(f"  → CNN nghi {tong} lần: loại (không phải ngã) {bo}, báo ngã cho người dùng {tong - bo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
