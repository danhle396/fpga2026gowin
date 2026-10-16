import re, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
def per(path):
    d = {}
    for l in open(path, encoding="utf-8"):
        m = re.search(r"người (\d+):.*Macro-F1 INT8 ([0-9.]+).*sự kiện (\d+)/(\d+)", l)
        if m and int(m.group(1)) not in d:
            d[int(m.group(1))] = (float(m.group(2)), int(m.group(3)), int(m.group(4)))
    return d
old6 = {20261014: "fpga2026gowin/ml/out/n2_d1/report.txt"}
for tag, pat in [("n2_8", "runs/n2_8_s{}/report.txt"), ("n2t_8", "runs/n2t_8_s{}/report.txt")]:
    rows = []
    for s in (20261014, 7, 99):
        p = pathlib.Path(pat.format(s))
        if not p.exists():
            continue
        d = per(p)
        six = [d[k][0] for k in range(101, 107)]
        rows.append((s, sum(v[0] for v in d.values()) / len(d), sum(six) / 6, sum(d[k][1] for k in range(101, 107)), d))
        print(f"{tag} seed {s}: Macro-F1 8 người {rows[-1][1]:.4f}; trên 101–106 {rows[-1][2]:.4f}; sự kiện 101–106 {rows[-1][3]}/604")
    if rows:
        print(f"{tag} TB 3 seed: 8 người {sum(r[1] for r in rows)/len(rows):.4f}; trên 101–106 {sum(r[2] for r in rows)/len(rows):.4f}")
