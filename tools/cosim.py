#!/usr/bin/env python
# tools/cosim.py — mô phỏng ghép firmware ↔ RTL trên dữ liệu ngã thật của D1 (trước khi có board; chuẩn bị cho RA-05,
# TH-07, G2/G4). Ba lượt:
#   1. mã C của firmware (preprocess.c + spi_frame.c, mã máy Cortex-M0 trong Unicorn) dựng khung ghi v3 từ dữ liệu 100 Hz
#   2. RTL fpga_top_v3 + engine E2 (Icarus) nhận đúng các byte đó qua chân SPI, trả khung đọc 20 byte
#   3. mã C của firmware (app_core.c) kiểm khung đọc bằng spi_parse_v3, bỏ phiếu, chạy Safety FSM
# rồi so: khung đọc của RTL == golden từng byte; kết quả firmware đọc được == golden; các lần đổi trạng thái == chuỗi
# golden Python (decimate, q8, forward, safety_model).
#
#   bash firmware/build.sh test && python tools/cosim.py --e2 ml/out/e2_matrix/n2s_p1 [--trials 3]
# Cần: unicorn, numpy, Icarus Verilog.
import argparse
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import golden_model as gm  # noqa: E402
import m0_test as mt  # noqa: E402
import safety_model as sm  # noqa: E402

PROJ = ROOT / "Document Board Kiwi Primer 20K" / "Kiwi20K_FallDetection_FPGA"


def stream(n_trials):
    D = np.load(ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz")
    acts = [901, 910, 905, 801, 815, 806][:n_trials]
    parts = []
    for act in acts:
        i = np.flatnonzero((D["act"] == act) & (D["subject"] == 104))[0]
        x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]].astype(np.int64)
        u = np.empty((2 * len(x) - 1, 6), np.int64)
        u[0::2], u[1::2] = x, (x[:-1] + x[1:]) // 2
        parts += [u, np.repeat(u[-1:], 300, 0)]
    return np.concatenate(parts).astype(np.int16), acts


def main():
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2", type=pathlib.Path, required=True, help="thư mục export_mem.py --engine e2 --params ...")
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--work", type=pathlib.Path)
    a = ap.parse_args()
    src = pathlib.Path((a.e2 / "params_src.txt").read_text(encoding="utf8").strip())
    z = np.load(src if src.is_absolute() else ROOT / src)        # params_src.txt: tương đối với gốc dự án
    P = {k: z[k] for k in z.files}
    P["n"], P["head"], P["score_shift"] = [int(v) for v in P["n"]], str(P["head"]), int(P["score_shift"])
    raw, acts = stream(a.trials)
    print(f"dữ liệu: {len(raw) / 100:.1f} s ở 100 Hz, hoạt động D1 {acts} (người 104)")

    # ---- lượt 1: firmware dựng khung ----
    _, out = mt.run(1, len(raw), raw.astype("<i2").tobytes())
    frames, i = [], 0
    while i < len(out):
        if out[i] == ord("S"):
            i += 7
        else:
            frames.append(bytes(out[i + 2:i + 774])); i += 1545
    print(f"lượt 1 (firmware, Unicorn): {len(frames)} khung ghi v3")

    # ---- lượt 2: RTL ----
    W = a.work or pathlib.Path(tempfile.mkdtemp())
    if W.exists():
        shutil.rmtree(W)
    (W / "tb").mkdir(parents=True)
    shutil.copytree(PROJ / "src", W / "src")
    shutil.copy(a.e2 / "cnn_params.vh", W / "src" / "cnn_params.vh")
    shutil.copy(a.e2 / "weights.mem", W / "src" / "weights_e2.mem")
    shutil.copy(a.e2 / "bias.mem", W / "src" / "bias_e2.mem")
    (W / "tb" / "stream_frames.mem").write_text("".join(f"{b:02X}\n" for f in frames for b in f), newline="\n")
    env = dict(os.environ)
    env["PATH"] = r"C:\iverilog\bin;" + env.get("PATH", "")
    V3 = ROOT / "fpga" / "src"
    src = [ROOT / "rtl" / "v3" / "tb_stream.v", V3 / "fpga_top_v3.v", V3 / "packet_parser_v3.v", V3 / "result_frame_v3.v",
           V3 / "spi_result_tx_v3.v", V3 / "crc16_ccitt.v", ROOT / "rtl" / "tb" / "pll_50m_sim.v",
           V3 / "spi_slave.v", V3 / "input_buffer.v", V3 / "cnn_e2.v"]
    subprocess.run(["iverilog", "-g2001", "-I", "src", f"-DTB_NF={len(frames)}", "-s", "tb_stream", "-o", "s.vvp"]
                   + [str(s) for s in src], cwd=W, env=env, check=True)
    subprocess.run(["vvp", "s.vvp"], cwd=W, env=env, check=True, capture_output=True)
    rb = bytes(int(v, 16) for v in (W / "tb" / "stream_results.mem").read_text().split())
    results = [rb[20 * k:20 * k + 20] for k in range(len(frames))]
    print(f"lượt 2 (RTL top v3 + E2, Icarus, thư mục {W}): {len(results)} khung đọc")

    # golden cho từng cửa sổ
    q = gm.q8(gm.decimate(raw.astype(np.int64)))
    ends = list(range(128, len(q) + 1, 16))
    bad_rtl, cyc = 0, set()
    gold = []
    for k, n in enumerate(ends[:len(frames)]):
        c, s, lg = gm.forward(q[n - 128:n], P)
        gold.append((c, s))
        e = gm.result_frame(k & 0xFF, 0x01, c, s, lg, 0)
        r = results[k]
        bad_rtl += r[:15] != e[:15] or gm.crc16(r[7:18]) != (r[18] << 8 | r[19])
        cyc.add(int.from_bytes(r[15:18], "big"))
        bad_rtl += frames[k] != gm.write_frame(k & 0xFF, q[n - 128:n])
    print(f"   khung ghi của firmware == golden và khung đọc của RTL == golden: {len(frames) - bad_rtl}/{len(frames)}; "
          f"CYCLES {sorted(cyc)}; lớp golden {dict(zip(*map(lambda v: v.tolist(), np.unique([g[0] for g in gold], return_counts=True))))}")

    # ---- lượt 3: firmware đọc khung của RTL, chạy FSM ----
    t_score, tilt, lat = 0, 1, 3
    blob = struct.pack("<IIBBBx", len(raw), len(results), t_score, tilt, lat) + raw.astype("<i2").tobytes() + b"".join(results)
    _, out = mt.run(10, 0, blob, max_insn=4_000_000_000)
    got_R, got_S, i = [], [], 0
    while i < len(out):
        if out[i] == ord("R"):
            got_R.append(tuple(out[i + 1:i + 5])); i += 5
        else:
            got_S.append((struct.unpack("<I", out[i + 1:i + 5])[0], out[i + 5], out[i + 6])); i += 7
    fsm, blk = sm.Safety(dict(t_score=t_score, tilt_en=tilt), 0), sm.Blocks(n=32)
    exp_R, exp_S, pend, w = [], [], None, 0
    r = raw.astype(np.int64)
    for k in range(len(r)):
        if pend and pend[0] <= k:
            fsm.on_result(pend[1], pend[2]); pend = None
        if blk.push(r[k]):
            fsm.on_block(blk.still_run, blk.az_tb)
        if k % 2 == 1 and (k + 1) // 2 >= 128 and ((k + 1) // 2) % 16 == 0:
            c, s = gold[w]
            exp_R.append((w & 0xFF, 0, c, s)); pend = (k + lat, c, s); w += 1
        fsm.tick(10 * k, 1, 0)
        if fsm.events & sm.EV_STATE:
            exp_S.append((10 * k, fsm.st, fsm.why))
    okR, okS = got_R == exp_R, got_S == exp_S
    print(f"lượt 3 (firmware app_core đọc khung RTL): {sum(1 for x in got_R if x[1] == 0)}/{len(got_R)} khung đọc qua "
          f"spi_parse_v3; kết quả == golden: {okR}; {len(got_S)} lần đổi trạng thái == golden: {okS} "
          f"({' → '.join(sm.NAMES[s[1]] for s in got_S)})")
    ok = bad_rtl == 0 and okR and okS and len(frames) > 0
    print("KẾT LUẬN mô phỏng ghép: " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
