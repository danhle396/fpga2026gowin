# fpga/ — project FPGA của sản phẩm (Kiwi Primer 20K, GW2A-18C)

Mở bằng Gowin IDE: **File → Open Project → `fpga/fpga_project.gprj`**, bấm **Run All**, ra `impl/pnr/fpga_project.fs`. Nạp bằng **Tools → Programmer** (SRAM Mode để thử, External Flash Mode để giữ sau khi tắt nguồn). Bản dựng sẵn trùng từng bit: `bitstream/fpga_project.fs` (kiểm bằng `sha256sum -c bitstream/SHA256.txt`).

| Thư mục | Nội dung |
|---|---|
| `src/` | RTL sản phẩm, **nơi duy nhất**: xem bảng dưới |
| `sim/` | Testbench Icarus: `tb_proto.v` (top qua chân SPI, giao thức v3), `tb_e2.v` (engine E2 từng tầng), `tb_stream.v` (chuỗi khung của firmware, cho `tools/cosim.py`), `pll_50m_sim.v`, `rpll_stub.v` |
| `scripts/` | `build.sh` (Gowin, trên bản sao; `--release` chép vào `bitstream/`), `test.sh` (Icarus), `gl.sh` (netlist sau P&R) |
| `bitstream/` | `fpga_project.fs`, `SHA256.txt`, `fpga_project.rpt.txt` (Logic 1.473 / 20.736, BSRAM 8/46, DSP 2,25/24, Fmax 111,01 MHz) |

| File trong `src/` | Vai trò |
|---|---|
| `fpga_top_v3.v` | Top-level: rPLL 27 → 50,143 MHz, nối mọi khối |
| `spi_slave.v` | SPI mode 0 (master là ESP32) |
| `packet_parser_v3.v`, `crc16_ccitt.v` | Nhận khung 772 byte, kiểm CRC-16 và SEQ |
| `input_buffer.v` | BSRAM chứa cửa sổ 128 × 6 mẫu |
| `cnn_e2.v` | Lõi 1D-CNN INT8 (engine E2, 1 chu kỳ/MAC): 258.080 chu kỳ = 5,15 ms |
| `result_frame_v3.v`, `spi_result_tx_v3.v` | Khung kết quả; "có kết quả" chốt lúc CS xuống, đọc sớm trả toàn 0 (ESP32 hỏi vòng) |
| `gowin_rpll/` | IP rPLL của Gowin |
| `cnn_params.vh`, `weights_e2.mem`, `bias_e2.mem` | Mô hình N2 11 người (`ml/out/e2_matrix/n2_11_p1`) |
| `fpga_top_v3.cst` | Chân header J2: CS R11, SCK T14, MOSI R13, MISO R12 (nối ESP32); IRQ R8, RST_N T8 (không nối) |
| `fpga_top_v3.sdc` | Ràng buộc clock |

Đổi mô hình: chạy `tools/export_mem.py --engine e2`, chép `cnn_params.vh`, `weights.mem` → `weights_e2.mem`, `bias.mem` → `bias_e2.mem` vào `src/`, cập nhật `firmware/src/selftest_expect_v3_e2_n2.h`, rồi `scripts/test.sh` và `scripts/build.sh --release`.
