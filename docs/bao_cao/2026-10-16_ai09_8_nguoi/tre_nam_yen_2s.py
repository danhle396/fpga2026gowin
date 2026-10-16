# Độ trễ va chạm → PRE_ALARM theo đúng điều kiện của DE_CUONG_v2: "≤ 5 s khi người nằm yên trong 2 s sau va chạm".
# Cú ngã đạt điều kiện = có chuỗi khối bất động (Blocks của safety_model, 16 mẫu 50 Hz) bắt đầu trong vòng 2 s sau điểm
# va chạm và kéo dài ≥ STILL_BLOCKS khối. Dùng cùng hàm suy luận / FSM với tools/playback_d1.py (một mô hình, LOSO).
#   python -I docs/bao_cao/2026-10-16_ai09_8_nguoi/tre_nam_yen_2s.py --model <thư mục mô hình> [--t-score 8]
import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "ml" / "src"))
import cnn_numpy as cn  # noqa: E402
import playback_d1 as pb  # noqa: E402
import safety_model as sm  # noqa: E402

BLK_MS = 16 * 20


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=pathlib.Path)
    ap.add_argument("--trials", default=ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz", type=pathlib.Path)
    ap.add_argument("--t-score", type=int, default=8)
    ap.add_argument("--within-ms", type=int, default=2000)
    a = ap.parse_args()
    D = dict(np.load(a.trials))
    params = a.model / "loso_params.npz"
    have = {int(k.split("/", 1)[0]) for k in np.load(params).files}
    cfg = dict(t_score=a.t_score, vote_k=2, tilt_en=1, still_blocks=sm.DEFAULT["still_blocks"], t_tilt=1450,
               still_upright=0)
    nb = cfg["still_blocks"]
    rows = []                                  # (act, đạt điều kiện, tới PRE_ALARM, trễ ms)
    for s in sorted(have):
        Q, ss = pb.load_fold(params, s)
        for i in np.flatnonzero((D["subject"] == s) & (D["event"] >= 0)):
            x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]]
            q = pb.q8(x)
            W = np.stack([q[n - 128:n] for n in range(128, len(q) + 1, 16)])
            lg = cn.int_forward(W, Q)[1]
            srt = np.sort(lg, 1)
            tr = pb.play(x, lg.argmax(1), cn.score(srt[:, -1] - srt[:, -2], ss), cfg, (300, 250))
            te = int(D["event"][i]) * 20
            blk = sm.Blocks(300, 250, 16)
            ok = False
            for k in range(len(x)):
                if blk.push(x[k]) and blk.still_run >= nb:
                    start = (k + 1) * 20 - blk.still_run * BLK_MS          # đầu chuỗi bất động hiện tại
                    if te <= start + BLK_MS and start - te <= a.within_ms:
                        ok = True
                        break
                    if start - te > a.within_ms:
                        break
            tp = [t for t, st, _ in tr if st == sm.PRE_ALARM and t >= te]
            rows.append((int(D["act"][i]), ok, bool(tp), (tp[0] - te) if tp else None))
    R = np.array([(r[0], r[1], r[2], r[3] if r[3] is not None else -1) for r in rows])
    cond = R[:, 1] == 1
    lying = np.isin(R[:, 0], list(pb.LYING))
    print(f"mô hình {a.model.name}, T_SCORE {a.t_score}, {len(R)} cú ngã; đạt điều kiện 'nằm yên trong "
          f"{a.within_ms / 1000:g} s sau va chạm' (≥ {nb} khối): {int(cond.sum())} ({int((cond & lying).sum())} thuộc nhóm ngã NẰM)")
    for name, m in (("đạt điều kiện", cond), ("đạt điều kiện, nhóm NẰM", cond & lying), ("mọi cú ngã tới PRE_ALARM", R[:, 2] == 1)):
        hit = m & (R[:, 2] == 1)
        lat = R[hit, 3] / 1000.0
        if not len(lat):
            continue
        print(f"  {name}: tới PRE_ALARM {int(hit.sum())}/{int(m.sum())}; trễ trung vị {np.median(lat):.2f} s, "
              f"p90 {np.percentile(lat, 90):.2f} s, lớn nhất {lat.max():.2f} s; > 5 s: {int((lat > 5).sum())}")
    slow = [(int(r[0]), r[3] / 1000) for r in R[cond & (R[:, 2] == 1) & (R[:, 3] > 5000)]]
    if slow:
        print(f"  đạt điều kiện mà > 5 s (mã hoạt động, s): {sorted(slow)}")


if __name__ == "__main__":
    main()
