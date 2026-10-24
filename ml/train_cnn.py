#!/usr/bin/env python
# ml/train_cnn.py — huấn luyện họ mạng A.4 (N1, N2, N2-S, N2-L) bằng numpy, LOSO theo người, xuất INT8, kiểm bằng
# golden model (AI-07, AI-09). Thay cho ml/train_n1.py cũ (đã xóa 15/10): `--arch n1` cho đúng từng số như bản cũ.
#
#   python ml/train_cnn.py --arch n2                       # LOSO 6 người + mô hình cuối + xuất
#   python ml/train_cnn.py --arch n2 --no-loso --epochs 5  # thử nhanh
#   python ml/train_cnn.py --arch n2 --extra ml/data/d2/d2_windows.npz
#   python ml/train_cnn.py --arch n2 --train-only <ngực.npz> <thắt lưng.npz>   # AI-09: thêm dữ liệu thân chỉ để huấn
#       luyện; LOSO vẫn chỉ kiểm trên --data và --extra (cửa sổ đầu), loso.npz giữ đúng chỉ số của --data
#
# Ra (mặc định ml/out/<arch>_d1/): params_int8.npz (golden_model), quant_params.json, golden_vectors.npz, fp32.npz,
# loso.npz (dự đoán INT8 của từng cửa sổ khi nó nằm ở người để riêng — dùng cho AI-10), report.txt.
# Với N1 còn ghi fpga_export/ định dạng engine E1 cũ (weights.mem, bias.mem); engine E1 đã bỏ 24/10.
import argparse
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
import cnn_numpy as cn  # noqa: E402
from golden_model import forward as golden_forward  # noqa: E402

CLASSES = {"0": "NORMAL", "1": "IMPACT", "2": "RESERVED", "3": "FALL"}
T_GRID = [0, 4, 8, 16, 32, 64]


def load(paths, train_only=()):
    parts = [np.load(p) for p in list(paths) + list(train_only)]
    cat = {k: np.concatenate([d[k] for d in parts]) for k in ("X", "y", "subject", "act", "trial")}
    cat["y"] = cat["y"].astype(np.int64)
    cat["test"] = np.concatenate([np.full(len(d["y"]), i < len(paths)) for i, d in enumerate(parts)])
    return cat


def macro_f1(y, pred):
    f1 = []
    for c in np.unique(y):
        tp = np.sum((pred == c) & (y == c))
        fp = np.sum((pred == c) & (y != c))
        fn = np.sum((pred != c) & (y == c))
        f1.append(2 * tp / max(1, 2 * tp + fp + fn))
    return float(np.mean(f1))


def trial_keys(D, idx):
    return D["subject"][idx].astype(np.int64) * 10**7 + D["act"][idx].astype(np.int64) * 10**4 + D["trial"][idx]


def event_metrics(D, idx, pred, sc, t_score, missed=None):
    """Recall sự kiện (≥ 2/3 cửa sổ dương báo FALL, SCORE ≥ T) và số lần đạt 2/3 phiếu mỗi giờ trên sinh hoạt."""
    vote = (pred == 3) & (sc >= t_score)
    key = trial_keys(D, idx)
    act, y = D["act"][idx], D["y"][idx]
    falls = det = alarms = 0
    seconds = 0.0
    order = np.argsort(key, kind="stable")
    bounds = np.flatnonzero(np.r_[True, key[order][1:] != key[order][:-1], True])
    for a, b in zip(bounds[:-1], bounds[1:]):
        m = order[a:b]
        if act[m[0]] >= 900:
            pos = m[y[m] == 3]
            if len(pos):
                falls += 1
                hit = vote[pos].sum() >= 2
                det += hit
                if missed is not None and not hit:
                    missed[int(act[m[0]])] = missed.get(int(act[m[0]]), 0) + 1
        else:
            v = vote[m].astype(int)
            run = np.convolve(v, [1, 1, 1])[:len(v)] >= 2
            alarms += int(np.sum(run & ~np.r_[False, run[:-1]]))
            seconds += (len(m) - 1) * 0.32 + 2.56
    return dict(fall_events=falls, detected=int(det), recall=det / max(1, falls),
                adl_hours=seconds / 3600, adl_alarms=alarms, alarms_per_hour=alarms / max(1e-9, seconds / 3600))


def fit(arch, D, idx, a, rng, log):
    P = cn.train(arch, D["X"][idx], D["y"][idx], rng, epochs=a.epochs, lr=a.lr, fall_frac=a.fall_frac,
                 log=log if a.verbose else None, ema=a.ema)
    cal = rng.choice(idx, min(len(idx), 8000), replace=False)
    cal = np.union1d(cal, idx[D["y"][idx] != 0])
    Q = cn.quantize(P, D["X"][cal])
    p8, _, margin = cn.int_forward(D["X"][cal], Q)
    good = margin[(p8 == 3) & (D["y"][cal] == 3)]
    med = float(np.median(good)) if good.size else 64.0
    return P, Q, max(0, int(round(np.log2(max(med, 1) / 64))))


def golden_check(D, Q, ss, rng, n=1000):
    G = cn.golden_params(Q, ss)
    sel = rng.choice(len(D["y"]), min(n, len(D["y"])), replace=False)
    cls, lg, margin = cn.int_forward(D["X"][sel], Q)
    sc = cn.score(margin, ss)
    bad = 0
    for k, i in enumerate(sel):
        c, s, l_ = golden_forward(D["X"][i], G)
        bad += not (c == cls[k] and s == sc[k] and np.array_equal(l_, lg[k]))
    return len(sel) - bad, len(sel)


def export(out, arch, D, Q, ss, rng, log):
    np.savez(out / "params_int8.npz", **{k: np.asarray(v) for k, v in cn.golden_params(Q, ss).items()})
    nw = sum(Q[k].size for k in Q if k[0] == "w")
    nb = sum(Q[k].size for k in Q if k[0] == "b")
    q = {"arch": arch, "input_shape": [128, 6], "input_dtype": "signed int8",
         "channel_order": ["ax", "ay", "az", "gx", "gy", "gz"], "input_memory_order": "sample-major: sample*6 + channel",
         **{f"conv{i + 1}_shift": int(s) for i, s in enumerate(Q["n"])},
         "head": Q["head"], "score_shift": ss, "classes": CLASSES, "weight_count": int(nw), "bias_count": int(nb),
         "source": "ml/train_cnn.py (numpy, PTQ shift lũy thừa 2, bias cộng sẵn 2^(n-1))"}
    if Q["head"] == "gap":
        q["gap_shift"] = 5
    (out / "quant_params.json").write_text(json.dumps(q, indent=2, ensure_ascii=False), encoding="utf8")
    sel = np.concatenate([rng.choice(np.flatnonzero(D["y"] == 3), 10, replace=False),
                          rng.choice(np.flatnonzero(D["y"] == 0), 10, replace=False)])
    G = cn.golden_params(Q, ss)
    res = [golden_forward(D["X"][i], G) for i in sel]
    np.savez(out / "golden_vectors.npz", input_windows=D["X"][sel], true_labels=D["y"][sel].astype(np.uint8),
             expected_classes=np.array([r[0] for r in res], np.uint8),
             expected_logits=np.array([r[2] for r in res], np.int32))
    if arch == "n1":                                   # bố trí E1: W[oc][ic][k] nối liền, bias nối liền
        ex = out / "fpga_export"
        ex.mkdir(exist_ok=True)
        W = np.concatenate([Q["w1"].ravel(), Q["w2"].ravel(), Q["wd"].ravel()])
        B = np.concatenate([Q["b1"], Q["b2"], Q["bd"]])
        (ex / "weights.mem").write_text("".join(f"{int(v) & 0xFF:02X}\n" for v in W), newline="\n")
        (ex / "bias.mem").write_text("".join(f"{int(v) & 0xFFFFFFFF:08X}\n" for v in B), newline="\n")
        (ex / "quant_params.json").write_text((out / "quant_params.json").read_text(encoding="utf8"), encoding="utf8")
        (ex / "golden_vectors.npz").write_bytes((out / "golden_vectors.npz").read_bytes())
    log(f"xuất {out}: shift {Q['n']}, score_shift {ss}, {nw} weight, {nb} bias")


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", default="n1", choices=sorted(cn.ARCH))
    ap.add_argument("--data", default=str(ROOT / "ml" / "data" / "public" / "d1_windows.npz"))
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--train-only", nargs="*", default=[], help="chỉ để huấn luyện, không vào tập kiểm LOSO")
    ap.add_argument("--out", default=None)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--fall-frac", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--ema", type=float, default=0.0, help="trung bình trượt mũ trọng số, ví dụ 0.995 (0 = tắt)")
    ap.add_argument("--subjects", type=int, nargs="*", default=[],
                    help="chỉ dùng các người này; mô hình ml/out/*_d1 (13–15/10) là 101 102 103 104 105 106")
    ap.add_argument("--no-loso", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out or ROOT / "ml" / "out" / f"{a.arch}_d1")
    out.mkdir(parents=True, exist_ok=True)
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    D = load([a.data] + a.extra, a.train_only)
    if a.subjects:                  # chỉ giữ các người này (cả --train-only), vd. tái lập mô hình trên 6 người đầu
        keep = np.isin(D["subject"], a.subjects)
        D = {k: v[keep] for k, v in D.items()}
    subj = np.unique(D["subject"][D["test"]])
    log(f"{a.arch}: {cn.ARCH[a.arch]}; dữ liệu {len(D['y'])} cửa sổ, người {subj.tolist()}, "
        f"lớp {dict(zip(*map(np.ndarray.tolist, np.unique(D['y'], return_counts=True))))}")
    if a.train_only:
        log(f"chỉ huấn luyện: {a.train_only} ({int(np.sum(~D['test']))} cửa sổ); tập kiểm LOSO "
            f"{int(np.sum(D['test']))} cửa sổ")
    log(f"epochs {a.epochs}, lr {a.lr}, fall_frac {a.fall_frac}, seed {a.seed}" + (f", EMA {a.ema}" if a.ema else ""))
    rng = np.random.default_rng(a.seed)
    t0 = time.time()

    if not a.no_loso:
        log("== LOSO ==")
        N = len(D["y"])
        pred8, margin8, pred32, shift8 = (np.zeros(N, np.int64), np.zeros(N, np.int64), np.zeros(N, np.int64),
                                          np.zeros(N, np.int64))
        fold_params = {}
        for s in subj:
            tr, te = np.flatnonzero(D["subject"] != s), np.flatnonzero((D["subject"] == s) & D["test"])
            P, Q, ss = fit(a.arch, D, tr, a, rng, log)
            for k, v in cn.golden_params(Q, ss).items():
                fold_params[f"{s}/{k}"] = np.asarray(v)
            p8, _, mg = cn.int_forward(D["X"][te], Q)
            pred8[te], margin8[te], shift8[te] = p8, mg, ss
            pred32[te] = cn.forward(P, D["X"][te]).argmax(1)
            e = event_metrics(D, te, p8, cn.score(mg, ss), 0)
            log(f"  người {s}: shift {Q['n']} ss {ss}  acc INT8 {np.mean(p8 == D['y'][te]):.4f}  Macro-F1 INT8 "
                f"{macro_f1(D['y'][te], p8):.4f} FP32 {macro_f1(D['y'][te], pred32[te]):.4f}  sự kiện "
                f"{e['detected']}/{e['fall_events']} = {e['recall']:.3f}  phiếu sinh hoạt {e['alarms_per_hour']:.1f}/h")
        allidx = np.flatnonzero(D["test"])
        sc8 = np.clip(margin8 >> shift8, 0, 127)
        f1s = [macro_f1(D["y"][(D["subject"] == s) & D["test"]], pred8[(D["subject"] == s) & D["test"]]) for s in subj]
        f1s32 = [macro_f1(D["y"][(D["subject"] == s) & D["test"]], pred32[(D["subject"] == s) & D["test"]])
                 for s in subj]
        yt, p8t, p32t = D["y"][allidx], pred8[allidx], pred32[allidx]
        log(f"  TỔNG LOSO {a.arch}: Macro-F1 trung bình INT8 {np.mean(f1s):.4f} (FP32 {np.mean(f1s32):.4f}); "
            f"accuracy INT8 {np.mean(p8t == yt):.4f}; FP32→INT8 trùng nhãn {np.mean(p8t == p32t):.4f}")
        log("  T_SCORE | recall sự kiện | phiếu 2/3 nhầm trên sinh hoạt")
        for t in T_GRID:
            missed = {} if t == 0 else None
            e = event_metrics(D, allidx, pred8, sc8, t, missed)
            log(f"  {t:7d} | {e['detected']}/{e['fall_events']} = {e['recall']:.3f} | {e['adl_alarms']} lần / "
                f"{e['adl_hours']:.2f} h = {e['alarms_per_hour']:.2f}/h")
            if missed is not None:
                log(f"  cú ngã bị lọt theo mã hoạt động (T = 0): {dict(sorted(missed.items()))}")
        cm = [[int(np.sum((yt == r) & (p8t == c))) for c in range(4)] for r in range(4)]
        log(f"  ma trận nhầm lẫn INT8 (hàng = thật 0..3): {cm}")
        np.savez(out / "loso.npz", pred=pred8[allidx], margin=margin8[allidx], score_shift=shift8[allidx],
                 pred32=pred32[allidx])
        np.savez(out / "loso_params.npz", **fold_params)     # mô hình INT8 của từng lượt, khóa "<người>/<tên>"

    log("== mô hình cuối trên mọi người ==")
    P, Q, ss = fit(a.arch, D, np.arange(len(D["y"])), a, rng, log)
    np.savez(out / "fp32.npz", **{k: P[k] for k in cn.weights(P)})
    ok, n = golden_check(D, Q, ss, rng)
    log(f"  {'PASS' if ok == n else 'FAIL'}  INT8 theo lô trùng golden_model.forward (lớp, SCORE, 4 logit): {ok}/{n}")
    export(out, a.arch, D, Q, ss, rng, log)
    log(f"thời gian {time.time() - t0:.0f} s")
    (out / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()
