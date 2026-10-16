#!/usr/bin/env python
# tools/playback_d1.py — phát lại D1 qua chuỗi đầy đủ của thiết bị (AI-10): cửa sổ 128 mẫu bước 16 → mô hình INT8 của
# lượt LOSO mà người đó được để riêng → bỏ phiếu → khối bất động + độ nghiêng → Safety FSM (ml/src/safety_model.py,
# đã kiểm trùng firmware/src/safety.c bằng tools/m0_test.py). Mỗi bản ghi chạy một FSM mới, WEAR = 1, không bấm CANCEL.
#
#   python tools/playback_d1.py --model ml/out/n2_d1 [--t-score 0 8 16] [--no-tilt]
#   python tools/playback_d1.py --model ... --still-upright 16    # thí nghiệm X15: báo cả khi bất động ≥ 16 khối, đầu thẳng
#
# Khác thiết bị thật (ghi trong báo cáo): D1 chỉ có 50 Hz (vốn 25 Hz nội suy) nên khối = 16 mẫu 50 Hz thay cho 32 mẫu
# 100 Hz; ngưỡng T_STILL_A/G giữ nguyên LSB. Kết quả CNN đến sau khi cửa sổ kết thúc 40 ms (lọc + SPI + 14 ms suy luận).
import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
import cnn_numpy as cn  # noqa: E402
import safety_model as sm  # noqa: E402

SHIFTS = np.array([7, 7, 7, 6, 6, 6])
LAT_MS = 40
# Nhóm kiểu ngã của D1 theo tư thế cuối (Information.pdf): hệ thống chỉ cần báo động khi người NẰM bất động.
LYING = {901, 902, 904, 907, 908, 910, 911, 912, 913, 915, 917, 918, 919}
RECOVER = {905, 906, 914, 916}                # ngã rồi đứng dậy: không được tới ALARM
UPRIGHT = {903, 909, 920}                     # kết thúc quỳ / ngồi, đầu thẳng


def q8(x):
    return np.clip((x.astype(np.int64) + (1 << (SHIFTS - 1))) >> SHIFTS, -128, 127).astype(np.int8)


def load_fold(path, s):
    z = np.load(path)
    Q = {k.split("/", 1)[1]: z[k] for k in z.files if k.startswith(f"{s}/")}
    Q["n"] = [int(v) for v in Q["n"]]
    Q["head"] = str(Q["head"])
    return Q, int(Q["score_shift"])


class SafetyX15(sm.Safety):
    """Thí nghiệm X15, CHƯA có trong SPEC và safety.c: thêm nhánh SUSPECT → PRE_ALARM khi bất động ≥ still_upright
    khối dù đầu thẳng (ngã kết thúc quỳ/ngồi). still_upright = 0 thì y hệt sm.Safety."""
    def tick(self, now, wear, cancel):
        super().tick(now, wear, cancel)
        n = self.c.get("still_upright", 0)
        if n and self.st == sm.SUSPECT and not (self.events & sm.EV_STATE) and self.still_run >= n:
            self._go(sm.PRE_ALARM, sm.WHY_STILL, now & sm.M32)


def play(x, cls, sc, cfg, still_cfg):
    """Một bản ghi: trả về danh sách (t_ms, trạng thái mới, lý do)."""
    L = len(x)
    fsm = SafetyX15(cfg, 0)
    blk = sm.Blocks(still_cfg[0], still_cfg[1], 16)
    events = []                                              # (t_ms, loại, a, b)
    for k in range(len(cls)):
        events.append(((128 + 16 * k) * 20 + LAT_MS, 1, int(cls[k]), int(sc[k])))
    for i in range(L):
        if blk.push(x[i]):
            events.append(((i + 1) * 20, 2, blk.still_run, blk.az_tb))
    events.sort(key=lambda e: (e[0], e[1]))
    out, j = [], 0
    end_ms = L * 20 + 2000
    for t in range(0, end_ms + 1, 10):
        while j < len(events) and events[j][0] <= t:
            _, typ, a, b = events[j]
            if typ == 1:
                fsm.on_result(a, b)
            else:
                fsm.on_block(a, b)
            j += 1
        fsm.tick(t, 1, 0)
        if fsm.events & sm.EV_STATE:
            out.append((t, fsm.st, fsm.why))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=pathlib.Path, nargs="+",
                    help="một hoặc nhiều thư mục mô hình; nhiều thư mục = gộp (cộng logit INT8 của các mô hình)")
    ap.add_argument("--trials", default=ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz", type=pathlib.Path)
    ap.add_argument("--t-score", type=int, nargs="*", default=[0, 8, 16, 32])
    ap.add_argument("--vote-k", type=int, default=2)
    ap.add_argument("--no-tilt", action="store_true")
    ap.add_argument("--t-still-a", type=int, default=300)
    ap.add_argument("--t-still-g", type=int, default=250)
    ap.add_argument("--still-blocks", type=int, default=8)
    ap.add_argument("--t-tilt", type=int, default=1450)
    ap.add_argument("--still-upright", type=int, default=0, help="thí nghiệm X15 (0 = tắt, đúng SPEC v3.1)")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    D = dict(np.load(a.trials))      # nạp một lần: NpzFile đọc lại cả mảng mỗi lần truy cập D["data"]
    params = [m / "loso_params.npz" for m in a.model]
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    log(f"mô hình {' + '.join(m.name for m in a.model)}, VOTE_K {a.vote_k}/3, TILT {'tắt' if a.no_tilt else 'bật'} (T_TILT {a.t_tilt}), "
        f"STILL_BLOCKS {a.still_blocks}, T_STILL_A/G {a.t_still_a}/{a.t_still_g}, khối 16 mẫu 50 Hz"
        + (f", THÍ NGHIỆM X15: bất động ≥ {a.still_upright} khối dù đầu thẳng" if a.still_upright else ""))
    # chỉ phát lại những người mà mọi mô hình đều có lượt LOSO (mô hình huấn luyện trên 6 người vẫn chạy được khi
    # file dữ liệu đã có thêm người)
    have = set.intersection(*[{int(k.split("/", 1)[0]) for k in np.load(pp).files} for pp in params])
    subj = [int(s) for s in np.unique(D["subject"]) if int(s) in have]
    skip = sorted(set(int(s) for s in np.unique(D["subject"])) - have)
    if skip:
        log(f"bỏ {len(skip)} người không có lượt LOSO trong mô hình: {skip}")
    on = np.isin(D["subject"], subj)
    # suy luận một lần cho mọi bản ghi, theo mô hình của người được để riêng
    preds = {}
    for s in subj:
        folds = [load_fold(pp, s) for pp in params]
        ss = folds[0][1] + int(np.ceil(np.log2(len(folds))))       # tổng logit lớn ~ n lần: thêm log2(n) vào shift
        for i in np.flatnonzero(D["subject"] == s):
            x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]]
            q = q8(x)
            if len(q) < 128:
                preds[i] = (np.zeros(0, int), np.zeros(0, int))
                continue
            W = np.stack([q[n - 128:n] for n in range(128, len(q) + 1, 16)])
            lg = sum(cn.int_forward(W, Q)[1] for Q, _ in folds)    # gộp: cộng logit (lớp dự trữ vẫn −n·2^30)
            c = lg.argmax(1)
            srt = np.sort(lg, 1)
            preds[i] = (c, cn.score(srt[:, -1] - srt[:, -2], ss))
    falls = np.flatnonzero((D["event"] >= 0) & on)
    adl = np.flatnonzero((D["event"] < 0) & on)
    adl_h = D["length"][adl].sum() / 50 / 3600
    log(f"{len(falls)} bản ghi ngã, {len(adl)} bản ghi sinh hoạt = {adl_h:.2f} giờ")
    log("T_SCORE | ngã → SUSPECT | ngã → PRE_ALARM | trễ va chạm→SUSPECT trung vị / p90 | →PRE_ALARM trung vị / p90 "
        "| PRE_ALARM giả trên sinh hoạt | SUSPECT giả")
    for t_score in a.t_score:
        cfg = dict(t_score=t_score, vote_k=a.vote_k, tilt_en=0 if a.no_tilt else 1, still_blocks=a.still_blocks,
                   t_tilt=a.t_tilt, still_upright=a.still_upright)
        n_sus = n_pre = 0
        lat_s, lat_p, miss_pre = [], [], {}
        for i in falls:
            te = D["event"][i] * 20
            tr = play(D["data"][D["start"][i]:D["start"][i] + D["length"][i]], *preds[i], cfg,
                      (a.t_still_a, a.t_still_g))
            ts = [t for t, st, _ in tr if st == sm.SUSPECT and t >= te]
            tp = [t for t, st, _ in tr if st == sm.PRE_ALARM and t >= te]
            if ts:
                n_sus += 1
                lat_s.append(ts[0] - te)
            if tp:
                n_pre += 1
                lat_p.append(tp[0] - te)
            else:
                miss_pre[int(D["act"][i])] = miss_pre.get(int(D["act"][i]), 0) + 1
        fa_pre = fa_sus = 0
        fa_acts = {}
        for i in adl:
            tr = play(D["data"][D["start"][i]:D["start"][i] + D["length"][i]], *preds[i], cfg,
                      (a.t_still_a, a.t_still_g))
            fa_sus += sum(st == sm.SUSPECT for _, st, _ in tr)
            k = sum(st == sm.PRE_ALARM for _, st, _ in tr)
            fa_pre += k
            if k:
                fa_acts[int(D["act"][i])] = fa_acts.get(int(D["act"][i]), 0) + k
        q = lambda v, p: np.percentile(v, p) / 1000 if v else float("nan")  # noqa: E731
        log(f"{t_score:7d} | {n_sus}/{len(falls)} = {n_sus / len(falls):.3f} | {n_pre}/{len(falls)} = "
            f"{n_pre / len(falls):.3f} | {q(lat_s, 50):.2f} / {q(lat_s, 90):.2f} s | {q(lat_p, 50):.2f} / "
            f"{q(lat_p, 90):.2f} s | {fa_pre} = {fa_pre / adl_h:.2f}/h | {fa_sus} = {fa_sus / adl_h:.2f}/h")
        log(f"        ngã không tới PRE_ALARM theo mã hoạt động: {dict(sorted(miss_pre.items()))}")
        for name, grp in (("kết thúc NẰM (13 kiểu)", LYING), ("ngã rồi ĐỨNG DẬY (4 kiểu)", RECOVER),
                          ("kết thúc QUỲ/NGỒI (3 kiểu)", UPRIGHT)):
            tot = int(np.sum(np.isin(D["act"][falls], list(grp))))
            miss = sum(v for k, v in miss_pre.items() if k in grp)
            log(f"        → PRE_ALARM với ngã {name}: {tot - miss}/{tot} = {(tot - miss) / max(1, tot):.3f}")
        if fa_acts:
            log(f"        PRE_ALARM giả theo mã hoạt động sinh hoạt: {dict(sorted(fa_acts.items()))}")
    tag = a.tag or ("notilt" if a.no_tilt else "tilt")
    (a.model[0] / f"playback_{tag}.txt").write_text("\n".join(lines) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
