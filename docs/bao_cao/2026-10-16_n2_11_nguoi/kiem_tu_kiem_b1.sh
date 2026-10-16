#!/usr/bin/env bash
# Kiểm đáp án tự kiểm A.10 của firmware cho bitstream 1 (PROTO 1, E1, weight SisFall của nhóm) với RTL: 5 khung tự kiểm
# (SEQ 0xEE, khung số 2 sai CRC) qua chân SPI của fpga_top (tb_top_spi); kết quả mong đợi lấy từ firmware/src/selftest_expect.h.
#   bash docs/bao_cao/2026-10-16_n2_11_nguoi/kiem_tu_kiem_b1.sh [thư mục làm việc]
set -eu
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
W="${1:-$(mktemp -d)}"; rm -rf "$W"; mkdir -p "$W/tb"
command -v iverilog >/dev/null || export PATH="/c/iverilog/bin:$PATH"
PY="$(command -v python3 || command -v python)"
cp -r "$ROOT/Document Board Kiwi Primer 20K/Kiwi20K_FallDetection_FPGA/src" "$W/"
"$PY" -I "$ROOT/tools/gen_cnn_params.py" --project "$W" > /dev/null
"$PY" -I - "$ROOT" "$W" <<'PYEOF'
import pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")
ROOT, W = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sys.path.insert(0, str(ROOT / "ml/src")); sys.path.insert(0, str(ROOT / "tools"))
import golden_model as gm
from gen_tv_pre import crc8, frame_v1
h = (ROOT / "firmware/src/selftest_expect.h").read_text(encoding="utf-8")
cls = int(re.search(r"SELFTEST_CLASS\s+(\d+)", h).group(1))
lg = [int(v) for v in re.search(r"selftest_logits\[4\] = \{([^}]*)\}", h).group(1).split(",")]
frames, exp = [], []
for k in range(5):
    f = bytearray(frame_v1(0xEE, gm.selftest_payload()))
    if k == 2:
        f[-1] ^= 1; e = bytes([0xEE] * 7)
    else:
        body = bytes([cls]) + (lg[cls] & 0xFFFFFFFF).to_bytes(4, "big"); e = bytes([0x5A]) + body + bytes([crc8(body)])
    frames.append(bytes(f)); exp.append(e)
(W / "tb/spi_frames.mem").write_text("".join(f"{b:02X}\n" for f in frames for b in f), newline="\n")
(W / "tb/spi_exp.mem").write_text("".join(f"{b:02X}\n" for e in exp for b in e), newline="\n")
print("firmware mong đợi: lớp", cls, "logit", lg[cls], "->", exp[0].hex(" "))
PYEOF
cd "$W"
S=src
iverilog -g2001 -I src -s tb_top_spi -o t.vvp "$ROOT/rtl/tb/tb_top_spi.v" $S/fpga_top.v $S/spi_slave.v $S/packet_parser.v \
    $S/crc8.v $S/input_buffer.v $S/result_register.v $S/spi_result_tx.v "$ROOT/rtl/tb/pll_50m_sim.v" $S/cnn_core.v \
    $S/cnn_controller.v $S/conv1d_engine.v $S/requantize_relu.v $S/maxpool1d_engine.v $S/feature_ram.v $S/gap_engine.v \
    $S/gap_buffer.v $S/dense_engine.v $S/argmax4.v $S/mac_unit.v $S/weight_rom.v $S/bias_rom.v
vvp t.vvp | grep -v "^$" | tee t.log | tail -8
[ "$(grep -E '^(PASS|FAIL)' t.log | tail -1)" = "PASS" ]
