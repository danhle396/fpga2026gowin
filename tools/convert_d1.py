#!/usr/bin/env python
# tools/convert_d1.py — chuyển bộ D1 (Özdemir & Barshan, UCI #455) về định dạng của thiết bị (việc AI-13).
# Lấy một cảm biến (mặc định là cảm biến ở đầu), xoay trục về quy ước của mũ (X trước, Y trái, Z lên),
# nội suy 25 → 50 Hz, đổi sang LSB của MPU6050 ở ±16 g / ±2000 °/s, rồi cắt cửa sổ và gán nhãn theo A.3, A.4.
#
#   python tools/convert_d1.py --src <thư mục chứa 101, 102, ...> --out ml/data/public
#
# Chỉ cần numpy. Dữ liệu tải về là dữ liệu ngoài: chạy bằng `python -I`.
import argparse
import os
import pathlib
import sys

import numpy as np

G = 9.80665
ACC_LSB_PER_G = 2048.0        # A.1: ±16 g
GYR_LSB_PER_DPS = 16.4        # A.1: ±2000 °/s
SHIFTS = (7, 7, 7, 6, 6, 6)   # A.2: ACC_SHIFT, GYR_SHIFT
WIN, HOP = 128, 16            # A.3
POS = (56, 103)               # A.4: vùng dương
DROP = ((24, 55), (104, 127))  # A.4: vùng bỏ
NORMAL, FALL = 0, 3
ACC_RANGE = 120.0 * 1.05      # m/s²; giá trị ngoài dải đo của MTw là mẫu hỏng
# Cờ của từng bản ghi
F_GAP, F_BAD, F_SHORT = 1, 2, 4


def read_trial(path):
    """Trả về (acc m/s² [N,3], gyr rad/s [N,3], áp suất hPa [N], cờ) trên lưới 25 Hz đều."""
    with open(path, "rb") as f:
        lines = f.read().decode("latin1").splitlines()
    k = next(i for i, l in enumerate(lines) if l.startswith("Counter"))
    hdr = [c for c in lines[k].split("\t") if c]
    col = {n: i for i, n in enumerate(hdr)}
    need = [col[n] for n in ("Counter", "Acc_X", "Acc_Y", "Acc_Z", "Gyr_X", "Gyr_Y", "Gyr_Z", "Pressure")]
    rows = []
    for l in lines[k + 1:]:
        r = l.split("\t")
        try:
            rows.append([float(r[i]) for i in need])
        except (ValueError, IndexError):       # dòng thiếu trường
            pass
    x = np.array(rows).reshape(-1, len(need))
    flags = 0
    if len(x) < 50:
        return None, None, None, F_SHORT
    bad = np.abs(x[:, 1:4]).max(axis=1) > ACC_RANGE
    if bad.any():
        flags |= F_BAD
        x = x[~bad]
    cnt = np.unwrap(x[:, 0] * (2 * np.pi / 65536.0)) * (65536.0 / (2 * np.pi))   # bộ đếm 16 bit quay vòng
    cnt = np.round(cnt - cnt[0]).astype(np.int64)
    keep = np.concatenate(([True], np.diff(cnt) > 0))
    x, cnt = x[keep], cnt[keep]
    if np.diff(cnt).max() > 1:
        flags |= F_GAP
    grid = np.arange(cnt[-1] + 1)
    y = np.stack([np.interp(grid, cnt, x[:, i]) for i in range(1, 8)], axis=1)
    return y[:, 0:3], y[:, 3:6], y[:, 6], flags


def upsample2(x):
    """25 → 50 Hz: giữ nguyên mẫu gốc, mẫu chen giữa = (−1, 9, 9, −1)/16."""
    p = np.concatenate((x[:1], x, x[-1:], x[-1:]))
    mid = (-p[:-3] + 9 * p[1:-2] + 9 * p[2:-1] - p[3:]) / 16.0
    y = np.empty((2 * len(x) - 1,) + x.shape[1:])
    y[0::2] = x
    y[1::2] = mid[:len(x) - 1]
    return y


def q8(d):
    """A.2 bước 3, trùng với q8() của golden model."""
    s = np.array(SHIFTS)
    return np.clip((d.astype(np.int32) + (1 << (s - 1))) >> s, -128, 127).astype(np.int8)


def unit(v):
    return v / np.linalg.norm(v)


def snap(v):
    """Trục tọa độ có dấu gần v nhất, và góc lệch (độ)."""
    i = int(np.argmax(np.abs(v)))
    e = np.zeros(3)
    e[i] = np.sign(v[i])
    return e, float(np.degrees(np.arccos(min(1.0, abs(v[i]) / np.linalg.norm(v)))))


def tilt_deg(u, v):
    return float(np.degrees(np.arccos(np.clip(np.dot(unit(u), unit(v)), -1, 1))))


def find_subjects(src):
    out = {}
    for root, dirs, _ in os.walk(src):
        if "Testler Export" in dirs:
            out[os.path.basename(root)] = os.path.join(root, "Testler Export")
            dirs[:] = []
    return dict(sorted(out.items()))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="thư mục chứa các thư mục người 101, 102, ...")
    ap.add_argument("--out", default="ml/data/public")
    ap.add_argument("--sensor", default="340540", help="mã cảm biến; xem ml/data/public/README.md về mã nào là đầu")
    a = ap.parse_args()

    subjects = find_subjects(a.src)
    if not subjects:
        sys.exit(f"Không thấy thư mục 'Testler Export' nào dưới {a.src}")
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    T = dict(data=[], subject=[], act=[], rep=[], event=[], flags=[], length=[])
    W = dict(X=[], y=[], subject=[], act=[], trial=[], p=[])
    rep_rows, n_skip = [], 0
    for sid, exp in subjects.items():
        trials = []                                            # (mã hoạt động, lần, acc, gyr, áp suất, cờ)
        for act_dir in sorted(os.listdir(exp)):
            if not act_dir[:3].isdigit():
                continue
            for test in sorted(os.listdir(os.path.join(exp, act_dir))):
                p = os.path.join(exp, act_dir, test, a.sensor + ".txt")
                if not os.path.isfile(p):
                    n_skip += 1
                    continue
                acc, gyr, pr, fl = read_trial(p)
                if acc is None:
                    n_skip += 1
                    continue
                digits = "".join(ch for ch in test if ch.isdigit())
                trials.append((int(act_dir[:3]), int(digits or 0), acc, gyr, pr, fl))
        if not trials:
            continue

        # --- Hướng trục của cảm biến trên người này
        # Lên: trung bình gia tốc khi đi bộ (801, 802). Trước: nằm sấp sau 901, 902 thì trục trước chỉ xuống đất,
        # nằm ngửa sau 910 thì chỉ lên trời.
        ups = [t[2].mean(axis=0) for t in trials if t[0] in (801, 802)]
        fw = [-t[2][-50:].mean(axis=0) for t in trials if t[0] in (901, 902)]
        fw += [t[2][-50:].mean(axis=0) for t in trials if t[0] == 910]
        if not ups or not fw:
            print(f"{sid}: thiếu bản ghi 801/802 hoặc 901/902/910 để tìm hướng trục — bỏ qua")
            continue
        up_est = unit(np.median(ups, axis=0))
        fw_est = np.median(fw, axis=0)
        fw_est = unit(fw_est - np.dot(fw_est, up_est) * up_est)
        up, up_err = snap(up_est)
        fwd, fw_err = snap(fw_est - np.dot(fw_est, up) * up)
        R = np.stack([fwd, np.cross(up, fwd), up])             # hàng: X trước, Y trái, Z lên (thuận tay phải)

        # --- Ba phép kiểm "cảm biến này có thật ở đầu không"
        walk_g = np.mean([np.sqrt((t[3] ** 2).sum(axis=1).mean()) for t in trials if t[0] == 801] or [np.nan])
        bend = np.mean([max(tilt_deg(t[2][:25].mean(axis=0), v)
                            for v in np.stack([np.convolve(t[2][:, i], np.ones(12) / 12, "valid") for i in range(3)], 1))
                        for t in trials if t[0] == 805] or [np.nan])
        dpr = np.mean([np.median(t[4][-75:]) - np.median(t[4][:75]) for t in trials if t[0] >= 900])
        n_fall = sum(1 for t in trials if t[0] >= 900)
        z_walk = []                                            # kênh Z (INT8) khi đi bộ; 1 g = 16 mức

        for code, rep, acc, gyr, _, fl in trials:
            x = np.concatenate((acc @ R.T / G * ACC_LSB_PER_G,
                                np.degrees(gyr @ R.T) * GYR_LSB_PER_DPS), axis=1)
            x = np.clip(np.round(upsample2(x)), -32768, 32767).astype(np.int16)
            ev = -1
            if code >= 900:                                    # A.4: mẫu có |a| lệch khỏi 1 g nhiều nhất
                mag = np.linalg.norm(x[:, :3].astype(np.float64), axis=1) / ACC_LSB_PER_G
                ev = int(np.argmax(np.abs(mag - 1.0)))
            ti = len(T["length"])
            T["data"].append(x); T["subject"].append(int(sid)); T["act"].append(code); T["rep"].append(rep)
            T["event"].append(ev); T["flags"].append(fl); T["length"].append(len(x))

            q = q8(x)
            if code == 801:
                z_walk.append(q[:, 2].mean())
            for s in range(0, len(q) - WIN + 1, HOP):
                p = ev - s if ev >= 0 else -1
                if ev >= 0 and any(lo <= p <= hi for lo, hi in DROP):
                    continue
                W["X"].append(q[s:s + WIN])
                W["y"].append(FALL if ev >= 0 and POS[0] <= p <= POS[1] else NORMAL)
                W["subject"].append(int(sid)); W["act"].append(code); W["trial"].append(ti)
                W["p"].append(p if 0 <= p < WIN else -1)

        rep_rows.append((sid, len(trials), n_fall, walk_g, bend, dpr, np.mean(z_walk or [np.nan]), up_err, fw_err,
                         "".join("+-"[int(R[i].sum() < 0)] + "XYZ"[int(np.argmax(np.abs(R[i])))] + " " for i in range(3))))

    if not T["length"]:
        sys.exit("Không đọc được bản ghi nào")
    length = np.array(T["length"])
    data = np.concatenate(T["data"])
    np.savez_compressed(out / "d1_trials_50hz.npz", data=data, start=np.cumsum(length) - length, length=length,
                        subject=np.array(T["subject"], np.int16), act=np.array(T["act"], np.int16),
                        rep=np.array(T["rep"], np.int8), event=np.array(T["event"], np.int32),
                        flags=np.array(T["flags"], np.uint8), sensor=a.sensor)
    y = np.array(W["y"], np.uint8)
    np.savez_compressed(out / "d1_windows.npz", X=np.stack(W["X"]), y=y,
                        subject=np.array(W["subject"], np.int16), act=np.array(W["act"], np.int16),
                        trial=np.array(W["trial"], np.int32), p=np.array(W["p"], np.int16), sensor=a.sensor)

    # --- Báo cáo
    L = []
    L.append(f"Cảm biến {a.sensor} · {len(rep_rows)} người · {len(length)} bản ghi "
             f"({int((np.array(T['act']) >= 900).sum())} ngã, {int((np.array(T['act']) < 900).sum())} hoạt động thường ngày) · "
             f"bỏ {n_skip} file thiếu hoặc quá ngắn")
    L.append(f"Tổng {len(data) / 50.0 / 3600:.2f} giờ ở 50 Hz · bản ghi dài {length.min() / 50:.1f}–{length.max() / 50:.1f} s")
    fl = np.array(T["flags"])
    L.append(f"Bản ghi có khoảng trống đã nội suy: {int((fl & F_GAP > 0).sum())} · có mẫu ngoài dải đã bỏ: {int((fl & F_BAD > 0).sum())}")
    acc_g = np.abs(data[:, :3]) / ACC_LSB_PER_G
    gyr_d = np.abs(data[:, 3:]) / GYR_LSB_PER_DPS
    L.append(f"Mẫu có trục gia tốc vượt 7,94 g: {100.0 * (acc_g.max(axis=1) > 7.94).mean():.4f} % · "
             f"có trục gyro vượt 496 °/s: {100.0 * (gyr_d.max(axis=1) > 496).mean():.4f} % · "
             f"lớn nhất {acc_g.max():.2f} g, {gyr_d.max():.0f} °/s")
    ev_tr = [i for i, e in enumerate(T["event"]) if e >= 0]
    pk = np.array([np.linalg.norm(T["data"][i][T["event"][i], :3].astype(float)) / ACC_LSB_PER_G for i in ev_tr])
    L.append(f"Đỉnh |a| tại điểm va chạm của các cú ngã: trung vị {np.median(pk):.2f} g, "
             f"phân vị 5 % {np.percentile(pk, 5):.2f} g, lớn nhất {pk.max():.2f} g")
    L.append(f"Cửa sổ: {len(y)} (NORMAL {int((y == NORMAL).sum())}, FALL {int((y == FALL).sum())}); "
             f"số cú ngã có đủ 3 cửa sổ dương: "
             f"{int((np.bincount(np.array(W['trial'])[y == FALL], minlength=len(length)) == 3).sum())}/{len(ev_tr)}")
    L.append("")
    L.append("người | bản ghi | ngã | gyro rms khi đi bộ (rad/s) | nghiêng lớn nhất khi cúi (độ) | Δ áp suất khi ngã (hPa) "
             "| Z khi đi bộ (mức INT8) | lệch trục lên / trước (độ) | trục mũ X Y Z lấy từ trục cảm biến")
    for r in rep_rows:
        L.append("%5s | %4d | %3d | %5.2f | %4.0f | %+.3f | %5.1f | %4.1f / %4.1f | %s" % r)
    text = "\n".join(L)
    (out / "d1_report.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
