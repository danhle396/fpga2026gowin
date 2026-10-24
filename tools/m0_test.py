#!/usr/bin/env python
# tools/m0_test.py — chạy các module C thuần của firmware dưới dạng mã máy Cortex-M0 (build bằng armclang, giống hệt
# mã nạp lên SN32F407) trong trình giả lập Unicorn, rồi so với golden model. Thay cho "trình chạy trên PC" mà máy
# này không có (không có gcc). Cần: numpy, unicorn (pip install unicorn).
#
#   bash firmware/build.sh test && python tools/m0_test.py
#
# Kiểm: (1) hằng số A.2 / A.7 / A.10; (2) FW-07: 10.000 mẫu tv/pre_in.csv → tv/pre_out.csv từng byte, và 305 khung
# v3 + PROTO 1 từng byte; (3) FW-08: kiểm khung đọc v3 và PROTO 1, gồm các khung hỏng; (4) FW-11: khối + Safety FSM.
import pathlib
import struct
import sys

import numpy as np
from unicorn import UC_ARCH_ARM, UC_HOOK_MEM_INVALID, UC_HOOK_MEM_WRITE, UC_MODE_MCLASS, UC_MODE_THUMB, Uc, UcError
from unicorn.arm_const import UC_CPU_ARM_CORTEX_M0, UC_ARM_REG_PC, UC_ARM_REG_SP

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from golden_model import crc16, q8, result_frame, selftest_payload, write_frame  # noqa: E402
from gen_tv_pre import crc8, frame_v1  # noqa: E402

BIN = ROOT / "firmware" / "build" / "test.bin"
TV = ROOT / "firmware" / "tv"
MBOX, IN, OUT = 0x40000000, 0x60000000, 0x70000000


def run(mode, n, payload=b"", out_max=1 << 22, max_insn=400_000_000, bin_path=None, prof=None):
    """Chạy ảnh test một lần. Trả về (text in ra, bytes OUT). prof = dict: đếm lệnh theo loại (chậm)."""
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M0)          # chỉ tập lệnh ARMv6-M, như SN32F407
    img = (bin_path or BIN).read_bytes()
    if prof is not None:
        def on_code(uc_, addr, size, user):
            last = prof.get("_last")
            if last is not None and addr != last[0] + last[1]:
                prof["taken"] = prof.get("taken", 0) + 1           # lệnh trước là nhánh được lấy
            op = int.from_bytes(uc_.mem_read(addr, 2), "little")
            if size == 4:
                k = "bl32"
            elif op & 0xFFC0 == 0x4340:
                k = "muls"
            elif 0x4800 <= op <= 0x9FFF:                          # LDR literal, LDR/STR thanh ghi, tức thời, SP
                k = "ldst"
            elif 0xB400 <= op <= 0xB5FF or 0xBC00 <= op <= 0xBDFF or 0xC000 <= op <= 0xCFFF:
                k = "ldm" + str(1 + bin(op & 0x1FF if op < 0xC000 else op & 0xFF).count("1"))
            elif 0xD000 <= op <= 0xDEFF:
                k = "bcond"
            elif 0xE000 <= op <= 0xE7FF or 0x4700 <= op <= 0x47FF:
                k = "b"
            else:
                k = "alu"
            prof[k] = prof.get(k, 0) + 1
            prof["insn"] = prof.get("insn", 0) + 1
            prof["_last"] = (addr, size)
        prof["_hook"] = on_code
    uc.mem_map(0x00000000, 0x100000)
    uc.mem_map(0x20000000, 0x40000)
    uc.mem_map(MBOX, 0x1000)
    uc.mem_map(IN, 0x1000000)
    uc.mem_map(OUT, 0x800000)
    uc.mem_write(0, img)
    uc.mem_write(IN, struct.pack("<II", mode, n) + payload)
    text, state = [], {"len": None, "fault": False}

    def on_write(uc_, access, addr, size, value, user):
        if addr == MBOX:
            text.append(chr(value & 0xFF))
        elif addr == MBOX + 4:
            state["len"] = value
            uc_.emu_stop()
        elif addr == MBOX + 8:
            state["fault"] = True
            uc_.emu_stop()

    def on_invalid(uc_, access, addr, size, value, user):
        print(f"truy cập bộ nhớ không hợp lệ: 0x{addr:08X} tại PC 0x{uc_.reg_read(UC_ARM_REG_PC):08X}")
        return False

    uc.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=MBOX, end=MBOX + 0xFFF)
    uc.hook_add(UC_HOOK_MEM_INVALID, on_invalid)
    if prof is not None:
        from unicorn import UC_HOOK_CODE
        uc.hook_add(UC_HOOK_CODE, prof.pop("_hook"))
    sp, pc = struct.unpack("<II", img[:8])
    uc.reg_write(UC_ARM_REG_SP, sp)
    try:
        uc.emu_start(pc | 1, 0xFFFFFFFF, count=max_insn)
    except UcError as e:
        raise SystemExit(f"Unicorn dừng vì lỗi: {e}")
    if state["fault"] or state["len"] is None:
        raise SystemExit("ảnh test không kết thúc bình thường (HardFault hoặc chạy quá số lệnh)")
    return "".join(text), bytes(uc.mem_read(OUT, state["len"])) if state["len"] else b""


def report(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    return ok


def test_consts():
    vals = [2048, -2048, 16384, -16384, 63, 64, 0, 1640, -1640, 8192, -8192, 31, 32,
            -32768, 32767, -1, -63, -64, -65, -31, -32, -33, 16319, 16320, 8127, 8128]
    vals += list(range(-300, 301)) + list(np.random.default_rng(1).integers(-40000, 40000, 2000))
    _, out = run(3, len(vals), struct.pack(f"<{len(vals)}i", *vals))
    ok = report("A.10 khung tự kiểm LFSR 768 byte == selftest_payload()",
                out[:768] == selftest_payload().astype(np.int8).tobytes())
    ok &= report("A.7 CRC-16 \"123456789\" = 0x29B1", out[768:770] == bytes([0x29, 0xB1]),
                 f"C cho 0x{out[768]:02X}{out[769]:02X}")
    ok &= report("CRC-8 (PROTO 1) \"123456789\" == crc8.v của RTL", out[770] == crc8(b"123456789"),
                 f"0x{out[770]:02X}")
    q = np.frombuffer(out[771:], np.int8).reshape(-1, 2)
    v = np.array(vals, np.int64)
    exp = np.stack([q8(v[:, None].repeat(6, 1))[:, 0], q8(v[:, None].repeat(6, 1))[:, 3]], 1)
    ok &= report(f"A.2 q8 trên {len(vals)} giá trị (gồm bảng tự kiểm A.2) == golden", np.array_equal(q, exp))
    return ok


def test_pre():
    raw = np.loadtxt(TV / "pre_in.csv", delimiter=",", skiprows=1, dtype=np.int64).astype(np.int16)
    exp = np.loadtxt(TV / "pre_out.csv", delimiter=",", skiprows=1, dtype=np.int64).astype(np.int8)
    frames = [ln.split(",") for ln in (TV / "pre_frames.csv").read_text().split()[1:]]
    _, out = run(1, len(raw), raw.astype("<i2").tobytes())
    samples, wins, i = [], [], 0
    while i < len(out):
        if out[i] == ord("S"):
            samples.append(out[i + 1:i + 7]); i += 7
        elif out[i] == ord("W"):
            wins.append((out[i + 1], out[i + 2:i + 774], out[i + 774:i + 1545])); i += 1545
        else:
            raise SystemExit(f"OUT hỏng ở byte {i}")
    got = np.frombuffer(b"".join(samples), np.int8).reshape(-1, 6)
    ok = report(f"FW-07 {len(raw)} mẫu tv/pre_in.csv → {len(got)} mẫu, khớp tv/pre_out.csv từng byte",
                got.shape == exp.shape and np.array_equal(got, exp),
                "" if got.shape != exp.shape or np.array_equal(got, exp)
                else f"lệch đầu tiên ở mẫu {int(np.argwhere((got != exp).any(1))[0][0])}")
    ok &= report(f"FW-07 số cửa sổ: {len(wins)} (mong đợi {len(frames)}, bước 16 mẫu)", len(wins) == len(frames))
    bad3 = bad1 = 0
    for k, (seq, f3, f1) in enumerate(wins[:len(frames)]):
        n = 128 + 16 * k
        x = exp[n - 128:n]
        bad3 += f3 != write_frame(seq, x)
        bad1 += f1 != frame_v1(seq, x)
        bad3 += f"{f3[-2] << 8 | f3[-1]:04X}" != frames[k][1]
        bad1 += f"{f1[-1]:02X}" != frames[k][2]
    ok &= report(f"FW-08 {len(wins)} khung v3 (772 B) khớp write_frame() từng byte và tv/pre_frames.csv",
                 len(wins) == len(frames) and bad3 == 0, f"sai {bad3}")
    ok &= report(f"FW-08 {len(wins)} khung PROTO 1 (771 B, CRC-8 của RTL) khớp từng byte", bad1 == 0, f"sai {bad1}")
    return ok


SPI_OK, SPI_E_TIMEOUT, SPI_E_HDR, SPI_E_CRC, SPI_E_STATUS, SPI_E_SEQ, SPI_E_CLASS, SPI_E_TAIL = range(8)


def test_parse():
    rng = np.random.default_rng(7)
    cases = []          # (proto, n_read, seq_expect, bytes, rc mong đợi, mô tả)
    for k in range(40):
        seq, cls = int(rng.integers(256)), int(rng.choice([0, 1, 3]))
        logits = rng.integers(-40000, 40000, 4)
        f = result_frame(seq, 0x01, cls, int(rng.integers(128)), logits, int(rng.integers(1 << 24)))
        cases.append((3, 20, seq, f, SPI_OK, "v3 HIL hợp lệ"))
        cases.append((3, 7, seq, f[:7], SPI_OK, "v3 RUN hợp lệ"))
    f = bytearray(result_frame(9, 0x01, 3, 100, [5, 6, 7, 8], 699800))
    cases += [(3, 7, 10, bytes(f[:7]), SPI_E_SEQ, "SEQ lệch")]
    g = bytearray(f); g[4] ^= 1
    cases += [(3, 7, 9, bytes(g[:7]), SPI_E_CRC, "1 bit sai ở SCORE")]
    g = bytearray(f); g[0] = 0x00
    cases += [(3, 7, 9, bytes(g[:7]), SPI_E_HDR, "MISO toàn 0 / sai đầu")]
    g = bytearray(f); g[12] ^= 0x80
    cases += [(3, 20, 9, bytes(g), SPI_E_TAIL, "đuôi HIL hỏng")]
    cases += [(3, 7, 9, result_frame(9, 0x00, 0xFF, 0, [0] * 4, 0)[:7], SPI_E_STATUS, "FPGA báo CRC khung ghi sai")]
    cases += [(3, 7, 9, result_frame(9, 0x03, 3, 5, [0] * 4, 0)[:7], SPI_E_STATUS, "STATUS có BUSY")]
    cases += [(3, 7, 9, result_frame(9, 0x01, 7, 5, [0] * 4, 0)[:7], SPI_E_CLASS, "CLASS ngoài 0..3")]
    for cls, sc in [(0, 1611), (3, -5), (1, 0x7FFFFFFF), (2, -0x80000000)]:     # PROTO 1: như spi_result_tx.v
        body = bytes([cls]) + (sc & 0xFFFFFFFF).to_bytes(4, "big")
        f1 = bytes([0x5A]) + body + bytes([crc8(body)])
        cases.append((1, 7, 0, f1, SPI_OK, "PROTO 1 hợp lệ"))
    cases.append((1, 7, 0, f1[:6] + bytes([f1[6] ^ 1]), SPI_E_CRC, "PROTO 1 CRC-8 sai"))

    blob = b"".join(bytes([p, n, s]) + f.ljust(20, b"\0") for p, n, s, f, _, _ in cases)
    _, out = run(2, len(cases), blob)
    bad = []
    for k, (p, n, s, f, rc, desc) in enumerate(cases):
        o = out[20 * k:20 * k + 20]
        good = o[0] == rc
        if good and rc == SPI_OK and p == 3:
            good = o[1:5] == f[1:5] and (n < 20 or (o[5:13] == f[7:15] and o[13:16] == f[15:18]))
        if good and rc == SPI_OK and p == 1:
            good = o[3] == f[1] and o[16:20] == f[2:6]
        if not good:
            bad.append(f"{desc}: rc={o[0]} mong đợi {rc}")
    return report(f"FW-08 kiểm khung đọc: {len(cases)} ca (v3 RUN/HIL, PROTO 1, SEQ lệch, CRC sai, STATUS, đuôi)",
                  not bad, "; ".join(bad[:3]))


def test_safety():
    text, _ = run(4, 0)
    print("".join("    " + ln + "\n" for ln in text.strip().splitlines()), end="")
    lines = text.strip().splitlines()
    return report("FW-11 khối + Safety FSM (A.8)",
                  not any(ln.startswith("FAIL") for ln in lines) and lines[-1].endswith(" 0 FAIL"))


def fsm_stream(rng, n_ticks, t0):
    """Chuỗi ngẫu nhiên có cấu trúc: đoạn đội/tháo mũ, giữ nút 0,05–4,5 s, kết quả CNN mỗi 32 tick, khối mỗi 32 tick."""
    recs, t = [], t0
    wear, btn, wear_left, btn_left = 1, 0, 0, 0
    for k in range(n_ticks):
        if wear_left <= 0:
            wear, wear_left = int(rng.random() < 0.85), int(rng.integers(20, 800))
        if btn_left <= 0:
            btn = int(rng.random() < 0.25)
            btn_left = int(rng.integers(5, 450)) if btn else int(rng.integers(50, 3000))
        wear_left -= 1
        btn_left -= 1
        if k % 32 == 7:
            cls = int(rng.choice([0, 1, 3], p=[0.5, 0.15, 0.35]))
            recs.append((1, cls, int(rng.integers(0, 128)), 0, 0, 0))
        if k % 32 == 21:
            recs.append((2, int(rng.choice([0, 3, 7, 8, 9, 12, 255])), 0, 0, int(rng.choice([2048, 1449, 1450, 0, -900, -1449, -1450, -2040])), 0))
        t = (t + 10) & 0xFFFFFFFF
        recs.append((3, wear, btn, 0, 0, t))
    return recs


def test_fsm_equiv():
    sys.path.insert(0, str(ROOT / "ml" / "src"))
    import safety_model as sm
    rng = np.random.default_rng(11)
    total, bad, seen = 0, 0, set()
    for t_score, tilt_en, t0 in [(0, 1, 0), (64, 1, 0xFFFF0000), (100, 0, 123456), (32, 1, 0xFFFFFFF0)]:
        recs = fsm_stream(rng, 60000, t0)
        blob = struct.pack("<BBxxI", t_score, tilt_en, t0) + b"".join(
            struct.pack("<BBBBhxxI", r[0], r[1], r[2], r[3], r[4], r[5]) for r in recs)
        _, out = run(5, len(recs), blob)
        py = sm.Safety(dict(t_score=t_score, tilt_en=tilt_en), t0)
        k = 0
        for r in recs:
            if r[0] == 1:
                py.on_result(r[1], r[2])
            elif r[0] == 2:
                py.on_block(r[1], r[4])
            else:
                py.tick(r[5], r[1], r[2])
                total += 1
                seen.add(py.st)
                bad += (py.st, py.why, py.events) != tuple(out[3 * k:3 * k + 3])
                k += 1
    ok = report(f"AI-10 safety_model.py == safety.c trên {total} tick ngẫu nhiên (4 cấu hình, có tràn ms)",
                bad == 0 and len(seen) == 6, f"sai {bad}, trạng thái đã đi qua {sorted(seen)}")
    raw = np.random.default_rng(3).integers(-200, 200, (6400, 6)).astype(np.int16)
    raw[::7] = 0
    raw[1000:3000] = [0, 0, 2048, 0, 0, 0]
    g = np.random.default_rng(4)
    raw[1000:3000] += np.c_[g.integers(-150, 151, (2000, 3)), g.integers(-125, 126, (2000, 3))].astype(np.int16)
    raw[4000:4600] = [0, 0, -1449, 0, 0, 0]
    raw[4000:4600] += g.integers(-60, 60, (600, 6)).astype(np.int16)
    _, out = run(6, len(raw), raw.astype("<i2").tobytes())
    b = sm.Blocks()
    recs = [(b.still, b.still_run, b.az_tb) for r in raw if b.push(r)]
    exp = b"".join(struct.pack("<BBh", *x) for x in recs)
    n_still = sum(x[0] for x in recs)
    ok &= report(f"AI-10 safety_model.Blocks == blocks.c trên {len(raw)} mẫu ({len(recs)} khối, {n_still} bất động, "
                 f"still_run lớn nhất {max(x[1] for x in recs)})", exp == out and 0 < n_still < len(recs))
    return ok


def cnn_models():
    """(tên, tham số golden) cho các mô hình có sẵn trên máy."""
    ms = []
    for arch in ("n2_11",):                                 # mô hình của bitstream đang nạp (ml/out/n2_11_d1)
        f = ROOT / "ml" / "out" / f"{arch}_d1" / "params_int8.npz"
        if f.exists():
            z = np.load(f)
            P = {k: z[k] for k in z.files}
            P["n"], P["head"], P["score_shift"] = [int(v) for v in P["n"]], str(P["head"]), int(P["score_shift"])
            ms.append((f"{arch.upper()} D1", P))
    return ms


def cnn_blob(P, X):
    nl = len(P["n"])
    hdr = bytes([nl, 1 if P["head"] == "gap" else 0, P["score_shift"], 0])
    for i in range(1, nl + 1):
        oc, ic = P[f"w{i}"].shape[:2]
        hdr += struct.pack("<HHI", oc, ic, P["n"][i - 1])
    F = P["wd"].shape[1]
    hdr += struct.pack("<II", F, len(X))
    w = b"".join(np.asarray(P[f"w{i}"], np.int8).tobytes() for i in range(1, nl + 1)) + np.asarray(P["wd"], np.int8).tobytes()
    w += b"\0" * (-len(w) % 4)
    b = b"".join(np.asarray(P[f"b{i}"], "<i4").tobytes() for i in range(1, nl + 1)) + np.asarray(P["bd"], "<i4").tobytes()
    return hdr + w + b + b"".join(np.asarray(x, np.int8).tobytes() for x in X)


def test_cnn_mcu():
    from golden_model import forward
    rng = np.random.default_rng(9)
    d = np.load(ROOT / "ml" / "data" / "public" / "d1_windows.npz")
    X = [d["X"][i] for i in np.r_[rng.choice(np.flatnonzero(d["y"] == 3), 15, replace=False),
                                  rng.choice(np.flatnonzero(d["y"] == 0), 15, replace=False)]]
    X += [selftest_payload(), np.full((128, 6), 127, np.int8), np.full((128, 6), -128, np.int8),
          np.zeros((128, 6), np.int8)] + [rng.integers(-128, 128, (128, 6)).astype(np.int8) for _ in range(16)]
    ok = True
    for name, P in cnn_models():
        _, out = run(7, 0, cnn_blob(P, X))
        bad = 0
        for k, x in enumerate(X):
            c, s, lg = forward(x, P)
            r = out[20 * k:20 * k + 20]
            bad += not (list(struct.unpack("<4i", r[:16])) == [int(v) for v in lg] and r[16] == c and r[17] == s)
        ok &= report(f"FW-15 cnn_mcu.c ({name}) == golden: lớp, SCORE, 4 logit trên {len(X) - bad}/{len(X)} cửa sổ",
                     bad == 0)
    return ok


def app_stream():
    """Chuỗi 100 Hz cho chế độ 8: bản ghi D1 (ngã nằm, ngã kết thúc ngồi, sinh hoạt) nội suy ×2, nối bằng 4 s đứng yên."""
    D = np.load(ROOT / "ml" / "data" / "public" / "d1_trials_50hz.npz")
    pick = []
    for act in (901, 905, 916, 920, 801, 806, 811):
        idx = np.flatnonzero((D["act"] == act) & (D["subject"] == 102))
        if len(idx):
            pick.append(idx[0])
    parts = []
    for i in pick:
        x = D["data"][D["start"][i]:D["start"][i] + D["length"][i]].astype(np.int64)
        up = np.empty((2 * len(x) - 1, 6), np.int64)
        up[0::2] = x
        up[1::2] = (x[:-1] + x[1:]) // 2
        parts.append(up)
        parts.append(np.repeat(up[-1:], 400, 0))
    raw = np.concatenate(parts)
    return raw, [int(D["act"][i]) for i in pick]


def test_app():
    import golden_model as gm
    import safety_model as sm
    ms = dict(cnn_models())
    name = "N2S D1" if "N2S D1" in ms else list(ms)[0]
    P = ms[name]
    raw, acts = app_stream()
    off = np.array([37, -20, 5])
    raw_dev = np.clip(raw + np.r_[[0, 0, 0], off], -32768, 32767).astype(np.int16)    # cảm biến có offset gyro
    t_score, tilt, lat = 0, 1, 3
    blob = cnn_blob(P, []) + struct.pack("<IBBBx3hxx", len(raw_dev), t_score, tilt, lat, *off.tolist())
    cancel = np.zeros(len(raw_dev), np.uint8)
    for a0, dur in ((2500, 120), (5200, 40), (7400, 350), (9800, 120), (11500, 120)):   # tick bắt đầu, số tick giữ
        cancel[a0:a0 + dur] = 1
    blob += raw_dev.astype("<i2").tobytes() + cancel.tobytes()
    _, out = run(8, 0, blob, max_insn=4_000_000_000)
    got_R, got_S, i = [], [], 0
    while i < len(out):
        if out[i] == ord("R"):
            got_R.append(tuple(out[i + 1:i + 4])); i += 4
        else:
            got_S.append((struct.unpack("<I", out[i + 1:i + 5])[0], out[i + 5], out[i + 6])); i += 7
    # tham chiếu Python: cùng thứ tự trong mỗi tick: kết quả đến hạn → khối → cửa sổ → tick
    r = np.clip(raw_dev.astype(np.int64) - np.r_[[0, 0, 0], off], -32768, 32767)
    q = gm.q8(gm.decimate(r))
    fsm, blk = sm.Safety(dict(t_score=t_score, tilt_en=tilt), 0), sm.Blocks(n=32)
    exp_R, exp_S, pend, seq = [], [], None, 0
    for k in range(len(r)):
        if pend and pend[0] <= k:
            fsm.on_result(pend[1], pend[2]); pend = None
        if blk.push(r[k]):
            fsm.on_block(blk.still_run, blk.az_tb)
        if k % 2 == 1:
            n = (k + 1) // 2
            if n >= 128 and n % 16 == 0:
                c, s, _ = gm.forward(q[n - 128:n], P)
                exp_R.append((seq & 0xFF, c, s)); pend = (k + lat, c, s); seq += 1
        fsm.tick(10 * k, 1, int(cancel[k]))
        if fsm.events & sm.EV_STATE:
            exp_S.append((10 * k, fsm.st, fsm.why))
    states = [sm.NAMES[s[1]] for s in exp_S]
    ok = report(f"FW lõi (app_core.c, {name}) == golden + safety_model: {len(got_R)} kết quả, {len(got_S)} lần đổi trạng "
                f"thái trên {len(raw) / 100:.0f} s (hoạt động {acts})", got_R == exp_R and got_S == exp_S,
                f"đã đi qua {sorted(set(states))}" if got_S == exp_S else
                f"R khớp {got_R == exp_R}, S khớp {got_S == exp_S}: C {got_S[:4]} / Py {exp_S[:4]}")
    # FW-05: hiệu chuẩn gyro
    g = np.random.default_rng(5)
    st = np.zeros((900, 6), np.int64)
    st[:, 3:] = np.array([41, -17, 3]) + g.integers(-8, 9, (900, 3))
    st[60:70, 4] += 400                                      # mũ bị rung lúc đầu: phải bắt đầu lại
    _, out = run(9, len(st), st.astype("<i2").tobytes())
    done, _, restarts, used = struct.unpack("<BBHH", out[:6])
    offc = struct.unpack("<3h", out[6:12])
    ref = st[used - 200:used, 3:]
    exp_off = [int(np.sign(v) * ((abs(v) + 100) // 200)) for v in ref.sum(0)]
    ok &= report(f"FW-05 hiệu chuẩn gyro: xong sau {used} mẫu, làm lại {restarts} lần, offset {list(offc)} "
                 f"(thật 41/−17/3)", done == 1 and restarts >= 1 and list(offc) == exp_off)
    return ok


def node_pack(seq, r, keys):
    """Khung node_link MCU → ESP32 (firmware/src/node_link.h), viết lại độc lập bằng Python."""
    body = bytes([seq & 0xFF, 14, 0, ord("D")]) + struct.pack("<6h", *[int(v) for v in r]) + bytes([keys])
    return b"\xF1\x7E" + body + struct.pack("<H", crc16(body))


def test_node():
    """node_link.c: đóng gói của MCU == Python từng byte; bên ESP32 tách đúng mẫu, dòng chữ, khung hỏng, mẫu mất."""
    g = np.random.default_rng(11)
    n = 50
    raw = g.integers(-32768, 32768, (n, 6))
    raw[0] = [0xF1 - 256 * 0, 0x7EF1, -1, 0, 32767, -32768]          # có byte F1 7E ngay trong dữ liệu
    keys = g.integers(0, 4, n)
    seqs = (np.arange(n) + 250) & 0xFF                                  # SEQ quay vòng qua 255 → 0
    blob = b"".join(bytes([int(s), int(k)]) + struct.pack("<6h", *[int(v) for v in r])
                    for s, k, r in zip(seqs, keys, raw))
    exp_pack = b"".join(node_pack(s, r, k) for s, k, r in zip(seqs, keys, raw))
    # luồng nhận: chữ xen giữa, một khung hỏng CRC (mẫu 20), bỏ hẳn mẫu 30–32 (mất 3 mẫu)
    stream, exp_ev = b"# MPU6050 OK\r\n", [("T", "# MPU6050 OK")]
    for i in range(n):
        f = node_pack(seqs[i], raw[i], keys[i])
        if i == 20:
            f = f[:10] + bytes([f[10] ^ 0x55]) + f[11:]
            exp_ev.append(("B",))
        elif 30 <= i <= 32:
            continue
        else:
            exp_ev.append(("D", int(seqs[i]), int(keys[i]), tuple(int(v) for v in raw[i])))
        stream += f
        if i == 10:
            stream += b"STAT,1,2,3\n"
            exp_ev.append(("T", "STAT,1,2,3"))
    _, out = run(12, n, blob + struct.pack("<I", len(stream)) + stream)
    got_pack, rest = out[:len(exp_pack)], out[len(exp_pack):]
    ev, i = [], 0
    while rest[i] != ord("Z"):
        c = chr(rest[i])
        if c == "D":
            ev.append(("D", rest[i + 1], rest[i + 2], struct.unpack("<6h", rest[i + 3:i + 15]))); i += 15
        elif c == "T":
            ln = rest[i + 1]; ev.append(("T", rest[i + 2:i + 2 + ln].decode())); i += 2 + ln
        else:
            ev.append(("B",)); i += 1
    lost = struct.unpack("<I", rest[i + 1:i + 5])[0]
    ok = report(f"node_link.c: {n} khung MCU → ESP32 khớp Python từng byte (21 B/mẫu, CRC-16)", got_pack == exp_pack)
    ok &= report(f"node_link.c tách luồng: {sum(e[0] == 'D' for e in ev)} mẫu, dòng chữ, 1 khung hỏng, mất {lost} mẫu",
                 ev == exp_ev and lost == 4, f"mất {lost} (mong đợi 4 = 1 hỏng + 3 bỏ), sự kiện khớp {ev == exp_ev}")
    return ok


def test_hub():
    """hub.c (chạy trên ESP32): luồng UART của MCU → app_core → khung v3 → FPGA giả lập (hỏi vòng, không IRQ) → FSM.
    So với cùng tham chiếu Python của test_app (golden + safety_model), kết quả đến sau 1 khe 10 ms."""
    import golden_model as gm
    import safety_model as sm
    ms = dict(cnn_models())
    name = "N2 D1" if "N2 D1" in ms else list(ms)[0]
    P = ms[name]
    raw, acts = app_stream()
    r = np.clip(raw.astype(np.int64), -32768, 32767)                  # MCU đã trừ offset gyro trước khi gửi
    cancel = np.zeros(len(r), np.uint8)
    for a0, dur in ((2500, 120), (5200, 40), (7400, 350), (9800, 120), (11500, 120)):
        cancel[a0:a0 + dur] = 1
    stream = b"# MPU6050 OK: WHO_AM_I=0x68\n# gyro_off,1,2,3\n"
    for k in range(len(r)):
        stream += node_pack(k, r[k], int(cancel[k]))
        if k % 1000 == 999:
            stream += b"STAT,raw,%d\n" % k
    t_score, tilt, eng = 0, 1, 5
    blob = cnn_blob(P, []) + struct.pack("<IBBBx", len(stream), t_score, tilt, eng) + stream
    _, out = run(11, 0, blob, max_insn=4_000_000_000)
    got_R, got_S, i = [], [], 0
    while out[i] != ord("T"):
        if out[i] == ord("R"):
            got_R.append(tuple(out[i + 1:i + 4])); i += 4
        else:
            got_S.append((struct.unpack("<I", out[i + 1:i + 5])[0], out[i + 5], out[i + 6])); i += 7
    st = struct.unpack("<6I", out[i + 1:i + 25])
    n_text, n_bad = struct.unpack("<2I", out[i + 26:i + 34])
    q = gm.q8(gm.decimate(r))
    fsm, blk = sm.Safety(dict(t_score=t_score, tilt_en=tilt), 0), sm.Blocks(n=32)
    exp_R, exp_S, pend, seq = [], [], None, 0
    for k in range(len(r)):
        if pend and pend[0] <= k:
            fsm.on_result(pend[1], pend[2]); pend = None
        if blk.push(r[k]):
            fsm.on_block(blk.still_run, blk.az_tb)
        if k % 2 == 1:
            n = (k + 1) // 2
            if n >= 128 and n % 16 == 0:
                c, s, _ = gm.forward(q[n - 128:n], P)
                exp_R.append((seq & 0xFF, c, s)); pend = (k + 1, c, s); seq += 1
        fsm.tick(10 * k, 1, int(cancel[k]))
        if fsm.events & sm.EV_STATE:
            exp_S.append((10 * k, fsm.st, fsm.why))
    stats_ok = st[0] == len(r) and st[1] == len(exp_R) and st[2] == len(exp_R) and st[3:] == (0, 0, 0)
    ok = report(f"ESP32 hub.c ({name}) == golden + safety_model: {len(got_R)} khung qua FPGA giả lập (hỏi vòng sau "
                f"{eng} ms), {len(got_S)} lần đổi trạng thái trên {len(r) / 100:.0f} s (hoạt động {acts})",
                got_R == exp_R and got_S == exp_S and stats_ok and n_bad == 0 and n_text == 2 + len(r) // 1000,
                f"đã đi qua {sorted({sm.NAMES[s[1]] for s in exp_S})}; thống kê mẫu/gửi/OK/timeout/lỗi/bỏ {st}"
                if got_R == exp_R and got_S == exp_S else
                f"R khớp {got_R == exp_R}, S khớp {got_S == exp_S}: C {got_S[:4]} / Py {exp_S[:4]}; thống kê {st}")
    # FPGA không trả lời: mọi khung phải thành timeout, FSM vẫn chạy (lỗi hiện ERR, không kẹt)
    blob = cnn_blob(P, []) + struct.pack("<IBBBx", len(stream), t_score, tilt, 200) + stream
    _, out = run(11, 0, blob, max_insn=4_000_000_000)
    j = out.index(b"T", len(out) - 34)
    st2 = struct.unpack("<6I", out[j + 1:j + 25])
    ok &= report(f"ESP32 hub.c: FPGA không trả lời trong {SPI_TIMEOUT_MS} ms → {st2[3]} timeout / {st2[1]} khung gửi, "
                 f"0 OK, {st2[5]} cửa sổ bỏ qua lúc chờ", st2[2] == 0 and st2[3] == st2[1] and st2[1] > 0, f"{st2}")
    return ok


SPI_TIMEOUT_MS = 50


def profile_cnn(bin_path):
    """Đếm lệnh Cortex-M0 cho một lần suy luận, rồi dự toán chu kỳ (TRM Cortex-M0: LDR/STR 2, nhánh lấy 3, BL 4,
    PUSH/POP 1+N, MULS 1 hoặc 32 tùy bộ nhân — X7)."""
    x = selftest_payload()
    for name, P in cnn_models():
        prof = {}
        run(7, 0, cnn_blob(P, [x]), bin_path=bin_path, prof=prof)
        prof.pop("_last", None)
        ldm = sum(int(k[3:]) * v for k, v in prof.items() if k.startswith("ldm"))
        base = (prof.get("alu", 0) + 2 * prof.get("ldst", 0) + prof.get("bcond", 0) + prof.get("b", 0)
                + 4 * prof.get("bl32", 0) / 2 + ldm + 2 * prof.get("taken", 0))
        fast, slow = base + prof.get("muls", 0), base + 32 * prof.get("muls", 0)
        ws = prof["insn"] / 2 + prof.get("taken", 0)           # ước: 1 wait-state Flash ở 48 MHz, không có bộ đệm
        print(f"  {name}: {prof['insn']:,} lệnh (MULS {prof.get('muls', 0):,}, LDR/STR {prof.get('ldst', 0):,}, "
              f"nhánh lấy {prof.get('taken', 0):,}) → nhân 1 chu kỳ: {fast:,.0f} chu kỳ = {fast / 48e3:.1f} ms; "
              f"nhân 32 chu kỳ: {slow:,.0f} = {slow / 48e3:.1f} ms ở 48 MHz (+ ≈ {ws / 48e3:.1f} ms nếu Flash 1 wait-state)")


def main():
    sys.stdout.reconfigure(encoding="utf8")
    if "--profile" in sys.argv:
        b = pathlib.Path(sys.argv[sys.argv.index("--profile") + 1])
        print(f"đếm lệnh trên {b}")
        profile_cnn(b)
        return
    if not BIN.exists():
        raise SystemExit("chưa có firmware/build/test.bin — chạy: bash firmware/build.sh test")
    ok = test_consts() & test_pre() & test_parse() & test_safety() & test_fsm_equiv() & test_cnn_mcu() & test_app() & test_node() & test_hub()
    print("TẤT CẢ PASS" if ok else "CÓ FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
