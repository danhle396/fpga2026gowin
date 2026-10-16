#!/usr/bin/env python
# tools/windowing.py — file LOG 100 Hz của mũ (tools/logger.py) → cửa sổ INT8 có nhãn theo SPEC v3 A.2–A.4 (việc AI-06).
#
#   python -I tools/windowing.py ml/data/raw --out ml/data/d2/d2_windows.npz             # D2: IMPACT + NORMAL
#   python -I tools/windowing.py ml/data/raw --only-falls --out ml/data/d3/d3_windows.npz   # D3: ngã trên đệm
#   ... --plot docs/bao_cao/<thư mục>                                                      # vẽ từng sự kiện
#
# Tên file: <người>_<hoạt động>_<lần>.csv (docs/data_protocol.md). Điểm sự kiện (A.4) = mẫu có |a| lệch khỏi 1 g nhiều
# nhất trong mỗi đoạn bấm nút (cột btn), hoặc trên cả file với các hoạt động mỗi file một sự kiện (D3).
# Tiền xử lý dùng đúng decimate() và q8() của ml/src/golden_model.py (= preprocess.c trên MCU, đã kiểm từng byte).
# Ra npz cùng khóa với ml/data/public/d1_windows.npz (X, y, subject, act, trial, p) + src → ml/train_cnn.py --extra.
import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
from golden_model import decimate, q8  # noqa: E402

WIN, HOP = 128, 16
POS = (56, 103)                  # A.4: vùng dương
DROP = ((24, 55), (104, 127))    # A.4: vùng bỏ
NORMAL, IMPACT, FALL = 0, 1, 3
G = 2048                         # LSB/g ở ±16 g
LOST_GAP_MS = 15

# hoạt động → (lớp, mã act, cách tìm sự kiện). Mã ≥ 900 là ngã: train_cnn.py tính recall sự kiện trên chúng;
# mã < 900 tính phiếu FALL nhầm mỗi giờ.
ACTS = {
    "roi_mu": (IMPACT, 701, "button"), "dat_manh": (IMPACT, 702, "button"), "va_mu": (IMPACT, 711, "button"),
    "go_mu": (IMPACT, 712, "button"), "thao_doi": (IMPACT, 713, "button"),
    "di_bo": (NORMAL, 751, "none"), "cau_thang": (NORMAL, 752, "none"), "cui_nhat": (NORMAL, 753, "none"),
    "ngoi_dung": (NORMAL, 754, "none"), "nam_xuong": (NORMAL, 755, "none"), "lam_viec": (NORMAL, 756, "none"),
    "chay": (NORMAL, 757, "none"), "suyt_nga": (NORMAL, 758, "none"),
    "nga_truoc": (FALL, 951, "single"), "nga_sau": (FALL, 952, "single"), "nga_trai": (FALL, 953, "single"),
    "nga_phai": (FALL, 954, "single"), "nga_dung_day": (FALL, 955, "single"), "nga_ngoi": (FALL, 956, "single"),
}


def parse_name(path):
    parts = path.stem.split("_")
    if len(parts) < 3:
        raise ValueError("tên file phải là <người>_<hoạt động>_<lần>.csv")
    subj, trial, act = parts[0], int(parts[-1]), "_".join(parts[1:-1])
    if act not in ACTS:
        raise ValueError(f"hoạt động lạ '{act}' (xem docs/data_protocol.md)")
    if subj == "h0":
        sid = 200
    elif subj.startswith("s") and subj[1:].isdigit() and int(subj[1:]) == 0:
        raise ValueError("s00 dành cho file thử trên bàn (đợt B), không vào dữ liệu; mã 200 đã là h0")
    elif subj.startswith("s") and subj[1:].isdigit():
        sid = 200 + int(subj[1:])
    else:
        raise ValueError(f"mã người lạ '{subj}' (s01, s02, … hoặc h0)")
    return subj, sid, act, trial


def read_log(path):
    a = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.int64, ndmin=2)
    t, raw, btn = a[:, 0], a[:, 1:7], a[:, 7] if a.shape[1] > 7 else np.zeros(len(a), np.int64)
    gaps = np.diff(t)
    lost = int(np.sum(np.round(gaps[gaps >= LOST_GAP_MS] / 10) - 1)) if len(gaps) else 0
    return t, raw, btn, lost


def find_events(raw, btn, mode):
    dev = np.abs(np.linalg.norm(raw[:, :3].astype(np.float64), axis=1) / G - 1.0)
    if mode == "none":
        return []
    if mode == "single":
        return [int(np.argmax(dev))]
    ev, on = [], np.flatnonzero(np.diff(np.r_[0, (btn > 0).astype(int), 0]))
    for a, b in zip(on[0::2], on[1::2]):                    # mỗi đoạn bấm [a, b)
        ev.append(int(a + np.argmax(dev[a:b])))
    return ev


def windows(q, ev50, label):
    out = []
    for s in range(0, len(q) - WIN + 1, HOP):
        ps = [e - s for e in ev50]
        if any(POS[0] <= p <= POS[1] for p in ps):
            out.append((s, label, next(p for p in ps if POS[0] <= p <= POS[1])))
        elif any(lo <= p <= hi for p in ps for lo, hi in DROP):
            continue
        else:
            out.append((s, NORMAL, next((p for p in ps if 0 <= p < WIN), -1)))
    return out


def plot_events(path, raw, ev, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if not ev:
        return
    fig, axs = plt.subplots(len(ev), 1, figsize=(8, 2.2 * len(ev)), squeeze=False)
    for ax, e in zip(axs[:, 0], ev):
        a, b = max(0, e - 300), min(len(raw), e + 500)
        tt = (np.arange(a, b) - e) / 100
        ax.plot(tt, np.linalg.norm(raw[a:b, :3], axis=1) / G, label="|a| (g)")
        ax.plot(tt, np.linalg.norm(raw[a:b, 3:], axis=1) / 16.4 / 100, label="|ω| (100 °/s)")
        ax.axvline(0, color="r", lw=0.8)
        ax.set_xlabel("s so với điểm sự kiện")
        ax.legend(loc="upper right", fontsize=7)
    fig.suptitle(path.name, fontsize=9)
    fig.tight_layout()
    fig.savefig(outdir / f"{path.stem}.png", dpi=90)
    plt.close(fig)


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="+", type=pathlib.Path, help="thư mục hoặc file .csv")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--only-falls", action="store_true", help="chỉ lấy file nga_* (D3)")
    ap.add_argument("--include-falls", action="store_true", help="lấy cả file nga_* cùng D2 (mặc định bỏ: D3 chỉ để kiểm tra)")
    ap.add_argument("--allow-lost", action="store_true")
    ap.add_argument("--plot", type=pathlib.Path)
    a = ap.parse_args()
    files = sorted(f for s in a.src for f in ([s] if s.is_file() else s.glob("*.csv")))
    W = {k: [] for k in ("X", "y", "subject", "act", "trial", "p")}
    if a.plot:
        a.plot.mkdir(parents=True, exist_ok=True)
    n_ev, skipped = 0, 0
    for f in files:
        try:
            subj, sid, act, trial = parse_name(f)
        except ValueError as e:
            print(f"BỎ   {f.name}: {e}")
            skipped += 1
            continue
        label, code, mode = ACTS[act]
        is_fall = code >= 900
        if a.only_falls != is_fall and not (a.include_falls and is_fall):
            continue
        t, raw, btn, lost = read_log(f)
        if lost and not a.allow_lost:
            print(f"BỎ   {f.name}: mất {lost} mẫu (thu lại, hoặc --allow-lost)")
            skipped += 1
            continue
        ev = find_events(raw, btn, mode)
        q = q8(decimate(raw))
        ev50 = [e // 2 for e in ev]
        ws = windows(q, ev50, label)
        for s, y, p in ws:
            W["X"].append(q[s:s + WIN]); W["y"].append(y); W["subject"].append(sid)
            W["act"].append(code); W["trial"].append(trial); W["p"].append(p)
        n_ev += len(ev)
        npos = sum(1 for _, y, _ in ws if y != NORMAL)
        print(f"     {f.name}: {len(raw) / 100:.1f} s, {len(ev)} sự kiện, {len(ws)} cửa sổ ({npos} dương)"
              + (f", btn bấm {int(np.sum(btn > 0))} mẫu" if mode == "button" else ""))
        if mode == "button" and not ev:
            print(f"     ⚠ {f.name}: không thấy đoạn bấm nút nào — cửa sổ đều thành NORMAL")
        if a.plot:
            plot_events(f, raw, ev, a.plot)
    if not W["X"]:
        raise SystemExit("không có cửa sổ nào")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.out, X=np.stack(W["X"]).astype(np.int8), y=np.array(W["y"], np.uint8),
                        subject=np.array(W["subject"], np.int16), act=np.array(W["act"], np.int16),
                        trial=np.array(W["trial"], np.int32), p=np.array(W["p"], np.int16),
                        src=np.array("d3" if a.only_falls else "d2"))
    y = np.array(W["y"])
    print(f"ghi {a.out}: {len(y)} cửa sổ (NORMAL {int(np.sum(y == 0))}, IMPACT {int(np.sum(y == 1))}, "
          f"FALL {int(np.sum(y == 3))}), {n_ev} sự kiện, bỏ {skipped} file")


if __name__ == "__main__":
    main()
