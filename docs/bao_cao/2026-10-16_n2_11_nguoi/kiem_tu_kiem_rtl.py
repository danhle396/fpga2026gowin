# Kiểm đáp án tự kiểm A.10 của firmware với RTL: khung tự kiểm (SEQ 0xEE, payload LFSR) đi qua tb_stream (top v3 + E2,
# weight của một bản xuất E2), so 7 byte đầu khung RTL trả về với selftest_frame7 trong header của firmware.
#   python -I docs/bao_cao/2026-10-16_n2_11_nguoi/kiem_tu_kiem_rtl.py ml/out/e2_matrix/n2_11_p1 firmware/src/selftest_expect_v3_e2_n2.h
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ml" / "src"))
import golden_model as gm  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    e2, hdr = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    want = bytes(int(v, 16) for v in re.search(r"selftest_frame7\[7\] = \{([^}]*)\}", hdr.read_text(encoding="utf-8"))
                 .group(1).replace("0x", "").split(","))
    frame = gm.write_frame(0xEE, gm.selftest_payload())
    W = pathlib.Path(tempfile.mkdtemp())
    (W / "tb").mkdir()
    shutil.copytree(ROOT / "Document Board Kiwi Primer 20K" / "Kiwi20K_FallDetection_FPGA" / "src", W / "src")
    shutil.copy(e2 / "cnn_params.vh", W / "src" / "cnn_params.vh")
    shutil.copy(e2 / "weights.mem", W / "src" / "weights_e2.mem")
    shutil.copy(e2 / "bias.mem", W / "src" / "bias_e2.mem")
    (W / "tb" / "stream_frames.mem").write_text("".join(f"{b:02X}\n" for b in frame), newline="\n")
    env = dict(os.environ)
    env["PATH"] = r"C:\iverilog\bin;" + env.get("PATH", "")
    V3 = ROOT / "rtl" / "v3"
    src = [V3 / "tb_stream.v", V3 / "fpga_top_v3.v", V3 / "packet_parser_v3.v", V3 / "result_frame_v3.v",
           V3 / "spi_result_tx_v3.v", V3 / "crc16_ccitt.v", ROOT / "rtl" / "tb" / "pll_50m_sim.v",
           W / "src" / "spi_slave.v", W / "src" / "input_buffer.v", ROOT / "rtl" / "e2" / "cnn_e2.v"]
    subprocess.run(["iverilog", "-g2001", "-I", "src", "-DTB_NF=1", "-s", "tb_stream", "-o", "s.vvp"] + [str(s) for s in src],
                   cwd=W, env=env, check=True)
    subprocess.run(["vvp", "s.vvp"], cwd=W, env=env, check=True, capture_output=True)
    got = bytes(int(v, 16) for v in (W / "tb" / "stream_results.mem").read_text().split())[:20]
    ok = got[:7] == want
    print(f"RTL trả về 7 byte đầu {got[:7].hex(' ')}; firmware mong đợi {want.hex(' ')} → {'PASS' if ok else 'FAIL'}")
    print(f"khung 20 byte của RTL: {got.hex(' ')}")
    shutil.rmtree(W, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
