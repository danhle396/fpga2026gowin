# fpga/ — project FPGA duy nhất của sản phẩm (Kiwi Primer 20K, GW2A-18C)

Mở bằng Gowin IDE: **File → Open Project → `fpga/fpga_project.gprj`**, bấm **Run All**, ra `impl/pnr/fpga_project.fs`. Nạp bằng **Tools → Programmer** (SRAM Mode để thử, External Flash Mode để giữ sau khi tắt nguồn). Bản dựng sẵn trùng từng bit: `bitstreams/3_v3_e2_n2/fpga_project.fs`.

| File trong `src/` | Vai trò |
|---|---|
| `fpga_top_v3.v` | Top-level: rPLL 27 → 50,143 MHz, nối mọi khối |
| `spi_slave.v` | SPI mode 0 với MCU |
| `packet_parser_v3.v`, `crc16_ccitt.v` | Nhận khung 772 byte, kiểm CRC-16 và SEQ |
| `input_buffer.v` | BSRAM chứa cửa sổ 128 × 6 mẫu |
| `cnn_e2.v` | Lõi 1D-CNN INT8 (engine E2, 1 chu kỳ/MAC), 258.080 chu kỳ = 5,15 ms |
| `result_frame_v3.v`, `spi_result_tx_v3.v` | Khung kết quả 20 byte, IRQ |
| `gowin_rpll/` | IP rPLL của Gowin |
| `cnn_params.vh`, `weights_e2.mem`, `bias_e2.mem` | Mô hình N2 11 người (`ml/out/e2_matrix/n2_11_p1`, sinh bằng `tools/export_mem.py --engine e2`) |
| `fpga_top_v3.cst` | Chân trên header J2 (Phụ lục E.1) |
| `fpga_top_v3.sdc` | Ràng buộc clock |

Đây là nơi **duy nhất** chứa RTL sản phẩm. Testbench (`rtl/v3/tb_proto.v`, `rtl/e2/tb_e2.v`), `rtl/tb/run_all.sh`, `tools/cosim.py` và `rtl/v3/pnr_v3.sh` đều đọc từ đây. Đổi mô hình: chạy `export_mem.py --engine e2`, rồi chép `cnn_params.vh`, `weights.mem` → `weights_e2.mem`, `bias.mem` → `bias_e2.mem` vào `src/`; `run_all.sh` sẽ báo FAIL nếu `src/` lệch với `ml/out/e2_matrix/n2_11_p1`.

Firmware đi cùng: `firmware/keil/fw.uvprojx` với `FW_BITSTREAM 3` (mặc định trong `firmware/src/fw_config.h`).
