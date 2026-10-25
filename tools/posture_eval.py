#!/usr/bin/env python
# tools/posture_eval.py — chấm bộ nhận dạng tư thế (ml/src/posture_model.py = firmware/src/posture.c) trên D1:
# mỗi bản ghi bắt đầu ở tư thế đứng; tư thế ở cuối bản ghi so với tư thế thật suy từ mã hoạt động (Information.pdf).
# D1 là 50 Hz (mẫu gốc 25 Hz): lặp mỗi mẫu 2 lần để thành 100 Hz như luồng MCU → ESP32.
#   python -I tools/posture_eval.py [--detail]
import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
import posture_model as pm  # noqa: E402

NAM = "NAM"     # nằm, hướng nào cũng được (tư thế cuối của bản ghi không ghi rõ hướng)
# tư thế thật ở cuối bản ghi, theo mô tả hoạt động của D1
KY_VONG = {
    801: "DUNG", 802: "DUNG", 803: "DUNG", 804: "DUNG", 806: "DUNG", 807: "DUNG", 808: "DUNG", 809: "DUNG",
    810: "DUNG", 811: "NGOI", 812: "NGOI", 814: "NGOI", 816: "NGOI", 815: NAM,
    901: NAM, 902: "NAM_SAP", 904: NAM, 907: "NGHIENG_PHAI", 908: "NGHIENG_TRAI", 909: "NGOI", 910: "NAM_NGUA",
    911: "NGHIENG_PHAI", 912: "NGHIENG_TRAI", 913: "NGHIENG_PHAI", 915: "NGHIENG_TRAI", 917: NAM, 919: NAM,
    905: "DUNG", 906: "DUNG", 914: "DUNG", 916: "DUNG",
}
NHOM = {"DUNG": "đứng", "DI_LAI": "đứng", "NGOI": "ngồi", "NAM_NGUA": "nằm", "NAM_SAP": "nằm",
        "NGHIENG_TRAI": "nằm", "NGHIENG_PHAI": "nằm", "CUI": "cúi", NAM: "nằm"}


def chay(raw50):
    p = pm.Posture()
    for r in np.repeat(raw50, 2, axis=0):
        p.push(r)
    return pm.TEN[p.tt]


def dung(kv, tt):
    if kv == NAM:
        return tt.startswith("NAM") or tt.startswith("NGHIENG")
    if kv == "DUNG":
        return tt in ("DUNG", "DI_LAI")
    return tt == kv


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--ngoi-h", type=float, help="thử ngưỡng hạ đầu khi ngồi (m), mặc định theo posture_model")
    a = ap.parse_args()
    if a.ngoi_h:
        pm.NGOI_H = int(a.ngoi_h * pm.M_TO_H)
    z = np.load(ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz")
    D, S, L, A = z["data"], z["start"], z["length"], z["act"]
    theo_act, nhom_ok, nhom_n = {}, {}, {}
    for i in range(len(S)):
        act = int(A[i])
        if act not in KY_VONG:
            continue
        kv = KY_VONG[act]
        tt = chay(D[S[i]:S[i] + L[i]])
        ok = dung(kv, tt)
        theo_act.setdefault(act, []).append((ok, tt))
        g = NHOM[kv]
        nhom_ok[g] = nhom_ok.get(g, 0) + ok
        nhom_n[g] = nhom_n.get(g, 0) + 1
    print(f"{'act':>4} {'kỳ vọng':<13} {'đúng':>9}  tư thế ra (nhiều nhất)")
    for act in sorted(theo_act):
        r = theo_act[act]
        k = sum(x[0] for x in r)
        top = {}
        for _, tt in r:
            top[tt] = top.get(tt, 0) + 1
        print(f"{act:>4} {KY_VONG[act]:<13} {k:>3}/{len(r):<4}  {dict(sorted(top.items(), key=lambda t: -t[1])[:3])}")
    print("theo nhóm tư thế cuối:", {g: f"{nhom_ok[g]}/{nhom_n[g]} = {100 * nhom_ok[g] / nhom_n[g]:.1f} %" for g in nhom_n})
    nam = [(kv, tt) for act, r in theo_act.items() for ok, tt in r for kv in [KY_VONG[act]] if NHOM[kv] == "nằm"]
    k = sum(dung(NAM, tt) for _, tt in nam)
    print(f"nằm (nhận ra là nằm, không xét hướng): {k}/{len(nam)} = {100 * k / len(nam):.1f} %")
    tong = sum(nhom_ok.values()), sum(nhom_n.values())
    print(f"tổng: {tong[0]}/{tong[1]} = {100 * tong[0] / tong[1]:.1f} %")


if __name__ == "__main__":
    main()
