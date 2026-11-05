"""Tổng hợp phát lại trên board: log nhóm (log_nga, log_dong_tac, log_9_tu_the) và D1 qua hub.
  so_log.py <thư mục kq>"""
import json, pathlib, sys
import numpy as np

ROOT = pathlib.Path(r"D:\hoctap\fpga\fpga2026gowin")
sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import safety_model as sm  # noqa: E402

kq = pathlib.Path(sys.argv[1])
LD = ['-', 'truoc khong thang', 'khong va cham', 'nguc khong nghieng', 'khong quay nhanh', 'du 4 dau hieu']
ST = ["STANDBY", "MONITOR", "SUSPECT", "PRE_ALARM", "ALARM", "COOLDOWN"]
WHY_KHONG_NGA = 9
LYING = {901, 902, 904, 907, 908, 910, 911, 912, 913, 915, 917, 918, 919}
KY_VONG = None


def doc_phien(f):
    M, N, F, P, R, E, TK = [], [], [], [], [], None, []
    for l in open(f, encoding="utf8", errors="replace"):
        l = l.strip()
        if not l:
            continue
        q = l.split(",")
        if l.startswith("# "):
            print(l)
        elif q[0] == "M":
            M.append((int(q[1]), q[2], q[3]))
        elif q[0] == "N":
            t, hd, ld, tr, vc, p2, w2, ng = [int(x) for x in q[1:9]]
            N.append((t, hd, ld, tr, vc, p2 ** 0.5 / 2048, w2 ** 0.5 / 16.4, ng))
        elif q[0] == "F":
            F.append(tuple(int(x) for x in q[1:4]))
        elif q[0] == "P":
            P.append((int(q[1]), q[2]))
        elif q[0] == "R":
            R.append((int(q[1]), int(q[2]), int(q[3]), int(q[4]), int(q[5])))
        elif q[0] == "E":
            E = [int(x) for x in q[1:]]
        elif q[0] == "TK":
            TK.append(q[1])
    return M, N, F, P, R, E, TK


def nhan(M, t):
    k = t // 10
    cur = "-"
    for a, m, ph in M:
        if a <= k:
            cur = f"{m}/{ph}"
    return cur


for ten in ("log_nga", "log_dong_tac", "log_9_tu_the"):
    f = kq / f"{ten}.txt"
    if not f.exists():
        continue
    M, N, F, P, R, E, TK = doc_phien(f)
    print(f"\n=== {ten}: E mau,gui,ok,timeout,loi,bo_qua,xac_nhan,loai = {E}; tu kiem cuoi {TK}")
    print(f"  R: {len(R)} ket qua FPGA, rc != 0: {sum(1 for r in R if r[4] != 0)}, lop FALL: {sum(1 for r in R if r[2] == 3)}")
    dem = {}
    for t, hd, ld, tr, vc, pk, w, ng in N:
        m = nhan(M, t)
        print(f"  {t / 1000:7.2f} s {m:22s} {'XAC NHAN' if hd == 1 else 'loai':8s} {LD[ld]:20s} dinh {pk:4.2f} g quay {w:3.0f} nghieng {ng} truoc thang {tr}")
        dem.setdefault(m.split("/")[0], []).append(hd == 1)
    print(f"  N: {len(N)} lan xet, xac nhan {sum(1 for n in N if n[1] == 1)}, loai {sum(1 for n in N if n[1] != 1)}")
    print("  theo dong tac (so lan xet, xac nhan):", {k: (len(v), sum(v)) for k, v in dem.items()})
    if ten == "log_9_tu_the":
        import truc_cam_bien as tc
        n = E[0]
        seg = tc.doan_giu(M, n)
        ok = 0
        for m, (_, i1) in seg.items():
            tt = "DUNG"
            for t, x in P:
                if t // 10 <= i1 - 1:
                    tt = x
            d = tt == tc.KY_VONG[m]
            ok += d
            print(f"  {m:14s} cuoi doan: {tt:15s} ky vong {tc.KY_VONG[m]:15s} {'dung' if d else 'SAI'}")
        print(f"  tu the: {ok}/{len(seg)}")

f = kq / "d1_hub.jsonl"
if f.exists():
    z = np.load(ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz")
    D, S, Ln = z["data"], z["start"], z["length"]
    rows = [json.loads(l) for l in open(f, encoding="utf8")]
    print(f"\n=== D1 qua hub + FPGA: {len(rows)} ban ghi")
    tong = np.zeros(8, np.int64)
    lat_s, lat_p, kq_rec = [], [], []
    for r in rows:
        e = [int(x) for x in r["e"].split(",")[1:]]
        tong += np.array(e)
        ev = [(int(a), int(b), int(c)) for a, b, c in (x.split(",")[1:4] for x in r["ev"] if x[0] == "F")]
        n_ev = [x.split(",") for x in r["ev"] if x[0] == "N"]
        nghi = any(ST[s] == "SUSPECT" for _, s, _ in ev) or any(w == WHY_KHONG_NGA for _, _, w in ev)
        xn = any(ST[s] == "SUSPECT" and not (j + 1 < len(ev) and ev[j + 1][2] == WHY_KHONG_NGA) for j, (t, s, w) in enumerate(ev))
        xn2 = any(q[2] == "1" for q in n_ev)
        te = r["event"] * 20 + 3000 if r["event"] >= 0 else None
        ts = tp = None
        if te is not None:
            a = [t for t, s, w in ev if (ST[s] == "SUSPECT" or w == WHY_KHONG_NGA) and t >= te]
            b = [t for t, s, w in ev if ST[s] == "PRE_ALARM" and t >= te]
            ts = a[0] - te if a else None
            tp = b[0] - te if b else None
        kq_rec.append(dict(i=r["i"], s=r["s"], act=r["act"], nghi=nghi, xn=xn, xn2=xn2, ts=ts, tp=tp, n_ev=len(n_ev)))
    print("  tong E (mau,gui,ok,timeout,loi,bo_qua,xac_nhan,loai):", tong.tolist())
    print("  xn khac xn2 (hai cach dem):", sum(1 for x in kq_rec if x["xn"] != x["xn2"]))

    def bang(rs, ten):
        ng = [x for x in rs if x["act"] >= 900]
        sh = [x for x in rs if x["act"] < 900]
        print(f"  [{ten}] nga {len(ng)}: CNN nghi {sum(x['nghi'] for x in ng)}, bao nga {sum(x['xn'] for x in ng)} = {100 * sum(x['xn'] for x in ng) / max(1, len(ng)):.1f} %"
              f"; sinh hoat {len(sh)}: CNN nghi {sum(x['nghi'] for x in sh)}, bao nham {sum(x['xn'] for x in sh)}")

    bang(kq_rec, "11 nguoi")
    bang([x for x in kq_rec if x["s"] == 102], "nguoi 102")
    gio = sum(Ln[x["i"]] for x in kq_rec if x["act"] < 900) / 50 / 3600
    bn = sum(x["xn"] for x in kq_rec if x["act"] < 900)
    print(f"  sinh hoat {gio:.2f} gio, bao nham {bn} = {bn / max(gio, 1e-9):.2f}/gio")
    bo_nghi = [x for x in kq_rec if x["act"] < 900 and x["xn"]]
    print("  bao nham theo act:", {a: sum(1 for x in bo_nghi if x["act"] == a) for a in sorted({x["act"] for x in bo_nghi})})
    v = [x["ts"] for x in kq_rec if x["ts"] is not None]
    if v:
        print(f"  va cham -> nghi: {len(v)} cu nga, trung vi {np.median(v) / 1000:.2f} s, p90 {np.percentile(v, 90) / 1000:.2f} s, lon nhat {max(v) / 1000:.2f} s, > 1,5 s: {sum(1 for x in v if x > 1500)}")
    # điều kiện đề cương: nằm yên trong 2 s sau va chạm, như tre_nam_yen_2s.py
    NB = sm.DEFAULT["still_blocks"]
    BLK = 16 * 20
    lat_cd, n_cd, lat_cd_nam, n_cd_nam = [], 0, [], 0
    for x, r in zip(kq_rec, rows):
        if r["event"] < 0:
            continue
        d = D[S[x["i"]]:S[x["i"]] + Ln[x["i"]]]
        te = r["event"] * 20
        blk = sm.Blocks(300, 250, 16)
        ok = False
        for k in range(len(d)):
            if blk.push(d[k]) and blk.still_run >= NB:
                st = (k + 1) * 20 - blk.still_run * BLK
                if te <= st + BLK and st - te <= 2000:
                    ok = True
                    break
                if st - te > 2000:
                    break
        if ok:
            n_cd += 1
            nam = x["act"] in LYING
            n_cd_nam += nam
            if x["tp"] is not None:
                lat_cd.append(x["tp"])
                if nam:
                    lat_cd_nam.append(x["tp"])
    for ten, v, n in (("dat dieu kien", lat_cd, n_cd), ("dat dieu kien, nhom NAM", lat_cd_nam, n_cd_nam)):
        if v:
            print(f"  -> PRE_ALARM {ten}: {len(v)}/{n}; trung vi {np.median(v) / 1000:.2f} s, p90 {np.percentile(v, 90) / 1000:.2f} s, lon nhat {max(v) / 1000:.2f} s, > 5 s: {sum(1 for x in v if x > 5000)}")
    c = ROOT / "docs" / "bao_cao" / "2026-10-28_nga_that" / "nga_d1_102_v3.csv"
    if c.exists():
        old = [l.strip().split(",") for l in open(c)][1:]
        moi = [x for x in kq_rec if x["s"] == 102]
        if len(old) == len(moi):
            sai = sum(1 for o, m in zip(old, moi) if (int(o[0]), int(o[1]), int(o[2])) != (m["act"], int(m["nghi"]), int(m["xn"])))
            print(f"  so voi phat lai PC nguoi 102 (nga_d1_102_v3.csv): {len(moi) - sai}/{len(moi)} ban ghi trung")
