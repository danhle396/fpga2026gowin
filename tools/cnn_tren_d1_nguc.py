#!/usr/bin/env python
# tools/cnn_tren_d1_nguc.py — đo CNN N2 đã có (học từ D1 kênh đầu) trên D1 kênh ngực, không huấn luyện lại, không đổi weight.
# Chỉ đo CNN + 2/3 phiếu; chưa qua Safety FSM và nga.c (kênh ngực chưa có bản ghi liền, xem tools/nga_d1.py).
#
#   python -I tools/cnn_tren_d1_nguc.py [--out <file.txt>]
#
# Hai mô hình, cùng 8 người có kênh ngực (101–108):
#   - cuối (params_int8.npz): đúng weight đang nạp trên FPGA; cả 8 người đều nằm trong tập huấn luyện (kênh đầu).
#   - LOSO (loso_params.npz): mỗi người dùng mô hình của lượt để riêng người đó, không phải weight đang nạp.
# Đối chứng: LOSO trên kênh đầu phải trùng từng người với report.txt của mô hình, nếu không thì dừng.
import argparse
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml"))
sys.path.insert(0, str(ROOT / "ml" / "src"))
import cnn_numpy as cn  # noqa: E402
from train_cnn import event_metrics, macro_f1  # noqa: E402

MODEL = ROOT / "ml" / "out" / "n2_11_d1"
PUBLIC = ROOT / "ml" / "data" / "public"
FILES = {"đầu": PUBLIC / "d1_windows.npz", "ngực": PUBLIC / "d1_windows_nguc_340539.npz"}
T_LIST = [0, 8, 16]


def model_q(z, prefix=""):
    q = {k[len(prefix):]: z[k] for k in z.files if k.startswith(prefix)}
    q["n"] = [int(v) for v in q["n"]]
    q["head"] = str(q["head"])
    return q, int(q["score_shift"])


def load(path, subjects):
    z = np.load(path)
    keep = np.isin(z["subject"], subjects)
    D = {k: z[k][keep] for k in ("X", "y", "subject", "act", "trial")}
    D["y"] = D["y"].astype(np.int64)
    return D, str(z["sensor"])


def run(D, models):
    """models: {người: (Q, score_shift)}. Trả về (lớp, SCORE) theo từng cửa sổ."""
    pred, sc = np.zeros(len(D["y"]), np.int64), np.zeros(len(D["y"]), np.int64)
    for s, (q, ss) in models.items():
        i = np.flatnonzero(D["subject"] == s)
        p, _, mg = cn.int_forward(D["X"][i], q)
        pred[i], sc[i] = p, cn.score(mg, ss)
    return pred, sc


def tinh(D, pred, sc):
    """Mỗi người một dòng + dòng tổng, cùng công thức với ml/train_cnn.py."""
    subj = np.unique(D["subject"])
    rows = {}
    for s in subj:
        i = np.flatnonzero(D["subject"] == s)
        e = event_metrics(D, i, pred[i], sc[i], 0)
        rows[int(s)] = (macro_f1(D["y"][i], pred[i]), e)
    i = np.arange(len(D["y"]))
    tong = {t: event_metrics(D, i, pred, sc, t) for t in T_LIST}
    y = D["y"]
    cm = dict(fn=int(np.sum((y == 3) & (pred != 3))), pos=int(np.sum(y == 3)),
              fp=int(np.sum((y == 0) & (pred == 3))), neg=int(np.sum(y == 0)))
    return rows, tong, cm, float(np.mean([r[0] for r in rows.values()]))


def report_old():
    """{người: (Macro-F1, số phát hiện, số cú ngã)} từ report.txt của mô hình."""
    pat = re.compile(r"người (\d+):.*Macro-F1 INT8 ([0-9.]+).*sự kiện (\d+)/(\d+)")
    out = {}
    for ln in (MODEL / "report.txt").read_text(encoding="utf8").splitlines():
        m = pat.search(ln)
        if m:
            out[int(m[1])] = (float(m[2]), int(m[3]), int(m[4]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf8")
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    subjects = np.unique(np.load(FILES["ngực"])["subject"])
    final = model_q(np.load(MODEL / "params_int8.npz"))
    zl = np.load(MODEL / "loso_params.npz")
    loso = {int(s): model_q(zl, f"{s}/") for s in subjects}
    all_final = {int(s): final for s in subjects}
    old = report_old()
    log(f"Mô hình {MODEL.relative_to(ROOT).as_posix()}: học từ D1 kênh đầu (340540), không huấn luyện lại. "
        f"Người: {subjects.tolist()}")
    log("Chỉ đo CNN + 2/3 phiếu; chưa qua Safety FSM và nga.c. Nguồn: D1 công khai, không phải thiết bị của nhóm.")

    kq = {}
    for kenh, path in FILES.items():
        D, sensor = load(path, subjects)
        log(f"\n===== Kênh {kenh} (cảm biến {sensor}): {len(D['y'])} cửa sổ =====")
        for ten, models in (("LOSO, người để riêng", loso), ("cuối, đang nạp trên FPGA", all_final)):
            pred, sc = run(D, models)
            rows, tong, cm, f1 = tinh(D, pred, sc)
            kq[kenh, ten] = (rows, tong, cm, f1)
            log(f"--- {ten} ---")
            for s, (fi, e) in rows.items():
                log(f"  người {s}: Macro-F1 {fi:.4f}  sự kiện {e['detected']}/{e['fall_events']}  "
                    f"phiếu sinh hoạt {e['alarms_per_hour']:.1f}/h")
            log(f"  Macro-F1 TB {f1:.4f}; FALL bị lọt {cm['fn']}/{cm['pos']} cửa sổ; "
                f"NORMAL gọi FALL {cm['fp']}/{cm['neg']} cửa sổ")
            for t, e in tong.items():
                log(f"  T_SCORE {t:2d}: recall sự kiện {e['detected']}/{e['fall_events']} = {e['recall']:.3f}; "
                    f"2/3 phiếu nhầm {e['adl_alarms']} lần / {e['adl_hours']:.2f} h = {e['alarms_per_hour']:.2f}/h")

    # đối chứng: cùng mã, kênh đầu, LOSO phải trùng report.txt của mô hình
    rows = kq["đầu", "LOSO, người để riêng"][0]
    sai = [s for s, (fi, e) in rows.items()
           if (round(fi, 4), e["detected"], e["fall_events"]) != old[s]]
    log(f"\nĐối chứng LOSO kênh đầu so với report.txt, {len(rows)} người: {'PASS' if not sai else f'FAIL người {sai}'}")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text("\n".join(lines) + "\n", encoding="utf8", newline="\n")
    sys.exit(1 if sai else 0)


if __name__ == "__main__":
    main()
