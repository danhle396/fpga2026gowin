#!/usr/bin/env python
# tools/playback_log.py — chấm buổi thử trên mũ: phát lại file LOG 100 Hz (tools/logger.py) qua đúng chuỗi của thiết bị
# rồi in các chỉ tiêu Pass của đề cương v2.1 (AI-05 / AI-08 / TH-10, docs/data_protocol.md mục 5).
#
#   python -I tools/playback_log.py ml/data/raw                       # mô hình của bitstream 3 (ml/out/n2_11_d1)
#   python -I tools/playback_log.py ml/data/raw --params <params_int8.npz> --t-score 8 --detail
#
# Chuỗi giống hệt tham chiếu Python mà tools/m0_test.py đã kiểm trùng firmware/src/app_core.c (test_app): decimate + q8
# của golden_model → cửa sổ 128 mẫu 50 Hz bước 16 → mô hình INT8 → kết quả đến sau LAT tick (10 ms/tick) → khối bất
# động 32 mẫu 100 Hz (safety_model.Blocks) → Safety FSM tick 10 ms. File LOG đã trừ offset gyro (chế độ LOG), nên dùng
# thẳng. Hệ thống BẬT suốt file (WEAR = 1). Cột btn là SW6 đánh dấu sự kiện, không đưa vào FSM. File ngã: không ai bấm
# CANCEL. File NORMAL / va đập: mỗi lần vào PRE_ALARM giả lập người đội nhấn hủy sau --auto-cancel-ms (mặc định 2 s), để
# FSM về MONITOR và đếm tiếp các lần báo nhầm sau đó (không hủy thì FSM kẹt ở ALARM tới hết file và đếm thiếu).
#
# Mỗi file chạy một FSM mới. Cách tính:
#   ngã (nga_*, mỗi file một cú): trúng nếu vào PRE_ALARM sau điểm va chạm (|a| lệch 1 g nhiều nhất); trễ = PRE_ALARM − va chạm.
#     Pass TH-10 tính trên ngã kết thúc nằm (nga_truoc/sau/trai/phai); nga_dung_day phải 0 lần; nga_ngoi chỉ báo số (X15)
#   va đập (roi_mu, va_mu, …): số đoạn bấm SW6 (= số va đập) và số lần vào PRE_ALARM trong file
#   NORMAL (di_bo, nam_xuong, …): số lần vào PRE_ALARM = báo giả; chia cho tổng giờ của các file NORMAL
import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import cnn_numpy as cn  # noqa: E402
import safety_model as sm  # noqa: E402
from golden_model import decimate, q8  # noqa: E402
from windowing import ACTS, FALL, IMPACT, find_events, parse_name, read_log  # noqa: E402

DEFAULT_PARAMS = ROOT / "ml" / "out" / "n2_11_d1" / "params_int8.npz"


def load_params(path):
    z = np.load(path)
    Q = {k: z[k] for k in z.files}
    Q["n"] = [int(v) for v in Q["n"]]
    Q["head"] = str(Q["head"])
    return Q, int(Q["score_shift"])


def run_file(raw, Q, ss, cfg, lat, auto_cancel_ms=None):
    """Phát lại raw (N×6, 100 Hz). Trả về (danh sách (t_ms, trạng thái mới, lý do), mảng nút CANCEL đã dùng).
    auto_cancel_ms: vào PRE_ALARM thì giả lập người đội nhấn nút 100 ms sau ngần ấy ms (hủy báo nhầm), để FSM về
    MONITOR và đếm tiếp; None = không ai bấm (file ngã)."""
    r = raw.astype(np.int64)
    q = q8(decimate(r))
    ends = [n for n in range(128, len(q) + 1, 16)]
    res = {}
    if ends:
        W = np.stack([q[n - 128:n] for n in ends])
        cls, _, margin = cn.int_forward(W, Q)
        sc = cn.score(margin, ss)
        res = {2 * n - 1: (int(c), int(s)) for n, c, s in zip(ends, cls, sc)}   # cửa sổ đóng ở mẫu 100 Hz thứ 2n−1
    fsm, blk = sm.Safety(cfg, 0), sm.Blocks(n=32)
    out, pend = [], []
    cancel = np.zeros(len(r), np.uint8)
    for k in range(len(r)):
        while pend and pend[0][0] <= k:
            _, c, s = pend.pop(0)
            fsm.on_result(c, s)
        if blk.push(r[k]):
            fsm.on_block(blk.still_run, blk.az_tb)
        if k in res:
            pend.append((k + lat, *res[k]))
        fsm.tick(10 * k, 1, int(cancel[k]))
        if fsm.events & sm.EV_STATE:
            out.append((10 * k, fsm.st, fsm.why))
            if fsm.st == sm.PRE_ALARM and auto_cancel_ms is not None:
                a0 = k + auto_cancel_ms // 10
                cancel[a0:a0 + 10] = 1
    return out, cancel


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="chấm buổi thử trên mũ (đề cương v2.1)")
    ap.add_argument("src", nargs="+", type=pathlib.Path, help="thư mục hoặc file .csv của tools/logger.py")
    ap.add_argument("--params", type=pathlib.Path, default=DEFAULT_PARAMS)
    ap.add_argument("--t-score", type=int, default=8)
    ap.add_argument("--lat", type=int, default=3, help="tick (10 ms) từ lúc cửa sổ đóng tới khi có kết quả")
    ap.add_argument("--auto-cancel-ms", type=int, default=2000,
                    help="file NORMAL / va đập: vào PRE_ALARM thì giả lập nhấn hủy sau ngần ấy ms (âm = không hủy)")
    ap.add_argument("--detail", action="store_true", help="in từng file")
    a = ap.parse_args()
    Q, ss = load_params(a.params)
    cfg = dict(t_score=a.t_score)
    files = sorted(f for s in a.src for f in (s.rglob("*.csv") if s.is_dir() else [s]))
    falls, impacts, normal = [], [], []
    skipped = []
    for f in files:
        try:
            subj, _, act, _ = parse_name(f)
        except ValueError as e:
            skipped.append((f.name, str(e)))
            continue
        t, raw, btn, lost = read_log(f)
        if lost:
            skipped.append((f.name, f"mất {lost} mẫu"))
            continue
        lab, _, mode = ACTS[act]
        ac = None if lab == FALL or a.auto_cancel_ms < 0 else a.auto_cancel_ms
        tr, _ = run_file(raw, Q, ss, cfg, a.lat, ac)
        pre = [tt for tt, st, _ in tr if st == sm.PRE_ALARM]
        hours = len(raw) / 100 / 3600
        if lab == FALL:
            ev = find_events(raw, btn, "single")[0] * 10
            hit = [tt for tt in pre if tt >= ev]
            falls.append((f.name, subj, act, bool(hit), (hit[0] - ev) / 1000 if hit else None))
            row = f"ngã     {f.name}: {'PRE_ALARM sau %.2f s' % ((hit[0] - ev) / 1000) if hit else 'KHÔNG vào PRE_ALARM'}"
        elif lab == IMPACT:
            n_ev = len(find_events(raw, btn, "button"))
            impacts.append((f.name, subj, act, n_ev, len(pre)))
            row = f"va đập  {f.name}: {n_ev} va đập (đoạn SW6), {len(pre)} lần vào PRE_ALARM"
        else:
            normal.append((f.name, subj, act, hours, len(pre)))
            row = f"NORMAL  {f.name}: {hours * 60:.1f} phút, {len(pre)} PRE_ALARM giả"
        if a.detail:
            print(row)

    print(f"mô hình {a.params}, T_SCORE {a.t_score}, trễ kết quả {a.lat * 10} ms; {len(files)} file, bỏ {len(skipped)}")
    for name, why in skipped:
        print(f"  bỏ {name}: {why}")
    if falls:
        LYING = ("nga_truoc", "nga_sau", "nga_trai", "nga_phai")       # kết thúc nằm: phải báo động
        lying = [x for x in falls if x[2] in LYING]
        rec = [x for x in falls if x[2] == "nga_dung_day"]             # ngã rồi đứng dậy: KHÔNG được báo động
        sit = [x for x in falls if x[2] == "nga_ngoi"]                 # kết thúc ngồi: X15, nhóm chưa quyết
        lat = [x[4] for x in lying if x[4] is not None]
        n_hit = sum(x[3] for x in lying)
        print(f"NGÃ kết thúc nằm: {n_hit}/{len(lying)} vào PRE_ALARM; trễ va chạm → PRE_ALARM trung vị "
              f"{np.median(lat) if lat else float('nan'):.2f} s, lớn nhất {max(lat) if lat else float('nan'):.2f} s; "
              f"người {sorted({x[1] for x in lying})}")
        miss = [x[0] for x in lying if not x[3]]
        if miss:
            print(f"  không vào PRE_ALARM: {miss}")
        print(f"  Pass TH-10 (≥ 18/20 cú ngã vào PRE_ALARM): "
              f"{'ĐẠT' if len(lying) >= 20 and n_hit >= 0.9 * len(lying) else 'chưa đủ 20 cú' if len(lying) < 20 else 'KHÔNG ĐẠT'}")
        if rec:
            bad = [x[0] for x in rec if x[3]]
            print(f"NGÃ rồi đứng dậy: {len(bad)}/{len(rec)} vào PRE_ALARM (phải 0) → {'ĐÚNG' if not bad else 'SAI: ' + str(bad)}")
        if sit:
            print(f"NGÃ kết thúc ngồi: {sum(x[3] for x in sit)}/{len(sit)} vào PRE_ALARM (X15: SPEC v3.1 chỉ báo khi nằm)")
    if normal:
        h = sum(x[3] for x in normal)
        n_fa = sum(x[4] for x in normal)
        people = sorted({x[1] for x in normal})
        by_act = {}
        for x in normal:
            by_act[x[2]] = by_act.get(x[2], 0) + x[4]
        print(f"NORMAL: {h:.2f} giờ từ {len(people)} người {people}; PRE_ALARM giả {n_fa} = {n_fa / h:.2f}/giờ; "
              f"theo hoạt động {dict(sorted(by_act.items()))}")
        print(f"  Pass (≤ 1 PRE_ALARM giả/giờ, ≥ 2 giờ từ ≥ 2 người): "
              f"{'ĐẠT' if h >= 2 and len(people) >= 2 and n_fa / h <= 1 else 'chưa đủ 2 giờ / 2 người' if h < 2 or len(people) < 2 else 'KHÔNG ĐẠT'}")
    if impacts:
        for kind in sorted({x[2] for x in impacts}):
            rows = [x for x in impacts if x[2] == kind]
            print(f"VA ĐẬP {kind}: {sum(x[3] for x in rows)} va đập, {sum(x[4] for x in rows)} lần vào PRE_ALARM "
                  f"(mỗi lần phải hủy được trong 10 s)")
        va = [x for x in impacts if x[2] == "va_mu"]
        if va:
            n_ev, n_pre = sum(x[3] for x in va), sum(x[4] for x in va)
            print(f"  đường lùi IMPACT (va mũ khi đang đội > 2/20 vào PRE_ALARM thì phải thu IMPACT): "
                  f"{n_pre}/{n_ev} → {'PHẢI THU IMPACT' if n_ev and n_pre / n_ev > 0.1 else 'không cần'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
