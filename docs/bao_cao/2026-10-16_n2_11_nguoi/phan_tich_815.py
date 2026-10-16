# Phân tích báo giả còn lại (815, chủ động nằm xuống giường): với mỗi lần FSM vào PRE_ALARM, đo đỉnh |a| trong 3 s trước
# lúc vào SUSPECT, so giữa ngã nằm thật và báo giả. Mục đích: xem một ngưỡng "có va chạm" (đỉnh |a| ≥ X g) có tách được
# hai nhóm không, trước khi đề xuất thêm điều kiện vào A.8. Dùng đúng hàm suy luận / FSM của tools/playback_d1.py.
#   python -I docs/bao_cao/2026-10-16_n2_11_nguoi/phan_tich_815.py --model <thư mục mô hình LOSO> [--t-score 8]
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

LSB_G = 2048.0


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=pathlib.Path)
    ap.add_argument("--trials", default=ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz", type=pathlib.Path)
    ap.add_argument("--t-score", type=int, default=8)
    ap.add_argument("--win-s", type=float, default=3.0, help="cửa sổ tìm đỉnh |a| trước lúc vào SUSPECT")
    a = ap.parse_args()
    D = dict(np.load(a.trials))
    params = a.model / "loso_params.npz"
    have = {int(k.split("/", 1)[0]) for k in np.load(params).files}
    cfg = dict(t_score=a.t_score, vote_k=2, tilt_en=1, still_blocks=8, t_tilt=1450)
    rows = []                                     # (mã hoạt động, người, đỉnh |a| g, là ngã)
    for s in sorted(have):
        Q, ss = pb.load_fold(params, s)
        for i in np.flatnonzero(D["subject"] == s):
            act = int(D["act"][i])
            if act >= 900 and act not in pb.LYING:
                continue
            x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]]
            q = pb.q8(x)
            if len(q) < 128:
                continue
            W = np.stack([q[n - 128:n] for n in range(128, len(q) + 1, 16)])
            _, lg, _ = cn.int_forward(W, Q)
            c = lg.argmax(1)
            srt = np.sort(lg, 1)
            tr = pb.play(x, c, cn.score(srt[:, -1] - srt[:, -2], ss), cfg, (300, 250))
            t_pre = [t for t, st, _ in tr if st == sm.PRE_ALARM]
            if not t_pre:
                continue
            t_sus = max(t for t, st, _ in tr if st == sm.SUSPECT and t <= t_pre[0])
            n1 = int(t_sus / 20)
            n0 = max(0, n1 - int(a.win_s * 50))
            mag = np.sqrt((x[n0:n1 + 1, :3].astype(float) ** 2).sum(1)) / LSB_G
            rows.append((act, s, float(mag.max()), act >= 900))
    fall = np.array([r[2] for r in rows if r[3]])
    fa = [r for r in rows if not r[3]]
    print(f"mô hình {a.model.name}, T_SCORE {a.t_score}: {len(fall)} ngã nằm tới PRE_ALARM, {len(fa)} PRE_ALARM giả")
    print("đỉnh |a| (g) trong %.1f s trước SUSPECT, ngã nằm: min %.2f · p1 %.2f · p5 %.2f · p10 %.2f · trung vị %.2f"
          % (a.win_s, fall.min(), *np.percentile(fall, [1, 5, 10, 50])))
    print("báo giả (mã, người, đỉnh g):", sorted(((r[0], r[1], round(r[2], 2)) for r in fa), key=lambda r: r[2]))
    for thr in (1.5, 2.0, 2.5, 3.0):
        print(f"ngưỡng {thr:.1f} g: giữ {np.mean(fall >= thr) * 100:5.1f} % ngã nằm, loại {sum(r[2] < thr for r in fa)}/{len(fa)} báo giả")


if __name__ == "__main__":
    main()
