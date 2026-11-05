"""So từng cửa sổ FPGA trả về với số học golden và tính chỉ số từ chính kết quả của chip.
  so_cua_so.py <kq head .npz> <kq nguc .npz>"""
import pathlib, sys
import numpy as np

ROOT = pathlib.Path(r"D:\hoctap\fpga\fpga2026gowin")
sys.path.insert(0, str(ROOT / "ml"))
sys.path.insert(0, str(ROOT / "ml" / "src"))
import cnn_numpy as cn  # noqa: E402
from train_cnn import event_metrics, macro_f1  # noqa: E402

PUB = ROOT / "ml" / "data" / "public"
MODEL = ROOT / "ml" / "out" / "n2_11_d1"


def crc_be(b):
    c = 0xFFFF
    for x in b:
        c ^= int(x) << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c


z = np.load(MODEL / "params_int8.npz")
Q = {k: z[k] for k in z.files}
Q["n"] = [int(v) for v in Q["n"]]
Q["head"] = str(Q["head"])
SS = int(Q["score_shift"])


def phan_tich(ten, f_x, f_kq, subjects=None):
    d = np.load(f_x)
    k = np.load(f_kq)
    raw, rc = k["raw"], k["rc"]
    D = {n: d[n] for n in ("X", "y", "subject", "act", "trial")}
    D["y"] = D["y"].astype(np.int64)
    N = len(raw)
    print(f"\n===== {ten}: {N} cua so; rc 0: {int((rc == 0).sum())}, chua xong/that bai: {int((rc != 0).sum())}")
    p, lg, mg = cn.int_forward(D["X"][:N], Q)
    sc = cn.score(mg, SS)
    sat = np.clip(lg, -32768, 32767)
    ch_cls, ch_sc = raw[:, 3].astype(np.int64), raw[:, 4].astype(np.int64)
    ch_lg = np.stack([(raw[:, 7 + 2 * i].astype(np.int32) << 8 | raw[:, 8 + 2 * i]).astype(np.int32) for i in range(4)], 1)
    ch_lg = np.where(ch_lg >= 32768, ch_lg - 65536, ch_lg)
    cyc = raw[:, 15].astype(np.int64) << 16 | raw[:, 16].astype(np.int64) << 8 | raw[:, 17]
    seq_ok = raw[:, 1] == (np.arange(N) & 0xFF)
    st_ok = raw[:, 2] == 1
    hdr_ok = raw[:, 0] == 0x5A
    # CRC đầu và đuôi: kiểm mọi khung duy nhất để nhanh
    u, inv = np.unique(raw, axis=0, return_inverse=True)
    crc_u = np.array([crc_be(r[:5]) == (int(r[5]) << 8 | int(r[6])) and crc_be(r[7:18]) == (int(r[18]) << 8 | int(r[19])) for r in u])
    crc_ok = crc_u[inv.ravel()]
    print(f"khung: header {int(hdr_ok.sum())}, status {int(st_ok.sum())}, seq {int(seq_ok.sum())}, ca hai CRC {int(crc_ok.sum())}")
    print("CYCLES:", dict(zip(*[x.tolist() for x in np.unique(cyc, return_counts=True)])))
    print(f"khop golden: lop {int((ch_cls == p).sum())}/{N}, SCORE {int((ch_sc == sc).sum())}/{N}, 4 logit INT16 {int((ch_lg == sat).all(1).sum())}/{N}, tat ca {int(((ch_cls == p) & (ch_sc == sc) & (ch_lg == sat).all(1)).sum())}/{N}")
    print(f"lop chip: {dict(zip(*[x.tolist() for x in np.unique(ch_cls, return_counts=True)]))}; so logit dang bao hoa: {int((np.abs(lg) > 32767).sum())}/{lg.size}")
    print(f"t_us (ghi xong -> co ket qua): min {k['t_us'][rc == 0].min()} trung vi {int(np.median(k['t_us'][rc == 0]))} max {k['t_us'][rc == 0].max()}")
    D2 = {n: v[:N] for n, v in D.items()}
    for nhom, s in (("tat ca", None), ("8 nguoi 101-108", np.arange(101, 109))):
        i = np.arange(N) if s is None else np.flatnonzero(np.isin(D2["subject"], s))
        if s is not None and len(i) == N and ten.startswith("nguc"):
            pass
        ds = np.unique(D2["subject"][i])
        f1 = float(np.mean([macro_f1(D2["y"][np.flatnonzero(D2["subject"] == u_)], ch_cls[np.flatnonzero(D2["subject"] == u_)]) for u_ in ds]))
        D3 = {n: v[i] for n, v in D2.items()}
        j = np.arange(len(i))
        e = event_metrics(D3, j, ch_cls[i], ch_sc[i], 0)
        y = D3["y"]
        c = ch_cls[i]
        print(f"[{nhom}] {len(ds)} nguoi, {len(i)} cua so: Macro-F1 TB {f1:.4f}; su kien {e['detected']}/{e['fall_events']} = {e['recall']:.4f}; "
              f"2/3 phieu nham {e['adl_alarms']} lan / {e['adl_hours']:.2f} h = {e['alarms_per_hour']:.2f}/h; "
              f"cua so: FALL dung {int(((y == 3) & (c == 3)).sum())}, lot {int(((y == 3) & (c != 3)).sum())}, NORMAL dung {int(((y == 0) & (c != 3)).sum())}, goi FALL {int(((y == 0) & (c == 3)).sum())}")


phan_tich("head (340540)", PUB / "d1_windows.npz", sys.argv[1])
if len(sys.argv) > 2:
    phan_tich("nguc (340539)", PUB / "d1_windows_nguc_340539.npz", sys.argv[2])
