# 2026-10-24 — Gom về một project FPGA và một project MCU

## Vì sao làm

Nhóm cần biết **mở file nào để nạp chạy**. Trước ngày này:
- RTL sản phẩm nằm ở 2 nơi (`rtl/v3/`, `rtl/e2/`) cộng với vài file trong project của nhóm.
- Có 3 bitstream, và firmware mặc định trỏ vào bitstream 1.
- File `.gprj` duy nhất trong repo là của nhóm, vẫn mang chân J1.

## Sau khi gom

| Board | Project | Bản dựng sẵn |
|---|---|---|
| FPGA | `fpga/fpga_project.gprj`. Nguồn duy nhất ở `fpga/src/`: top v3, parser, khung kết quả, CRC-16, SPI, BSRAM đầu vào, engine E2, rPLL, `.cst` (J2), `.sdc`, mô hình N2 11 người | `bitstreams/3_v3_e2_n2/fpga_project.fs` |
| MCU | `firmware/keil/fw.uvprojx`, `FW_BITSTREAM 3` mặc định (chuyển từ `app_main.c` sang `fw_config.h`); menu chẩn đoán mặc định `PROTO=3` | — |

- **Chuyển bằng `git mv`, nội dung giữ nguyên** (chỉ sửa dòng chú thích đầu file): `rtl/v3/{fpga_top_v3, packet_parser_v3, result_frame_v3, spi_result_tx_v3, crc16_ccitt}.v`, `fpga_top_v3.cst`, `fpga_top_v3.sdc`, `rtl/e2/cnn_e2.v` → `fpga/src/`.
- **Chép vào `fpga/src/`:**
  - `spi_slave.v`, `input_buffer.v`, `gowin_rpll/` từ project của nhóm. Mọi luồng (kể cả E1) đều chép đè từ `fpga/src`, nên chỉ còn một bản dùng thật.
  - `cnn_params.vh`, `weights_e2.mem`, `bias_e2.mem` từ `ml/out/e2_matrix/n2_11_p1`.
- **Script đọc từ `fpga/src`:** `pnr_v3.sh`, `run_tb_proto.sh`, `run_all.sh`, `run_tb_e2.sh`, `cosim.py`, `kiem_tu_kiem_rtl.py`.
- **`run_all.sh` thêm một mục:** kiểm `fpga/src` có mang đúng mô hình `n2_11_p1` không, và chạy `tb_proto` thẳng trên `fpga/src`.
- **Hướng dẫn đợt B:**
  - B7 nạp bitstream 3 với 6 dây (gồm RST_N).
  - B8 chạy cả chuỗi bằng mô hình demo.
  - B10 thành đường lùi bằng bitstream 1 (PROTO 1).

## Kiểm (`hoi_quy.log`)

| Bộ kiểm | Kết quả |
|---|---|
| `rtl/tb/run_all.sh` (Icarus 0.9.7) | 8/8 PASS, gồm mục mới `fpga/` |
| `tools/cosim.py --e2 n2_11_p1` (firmware ↔ RTL `fpga/src`) | 423/423 khung khớp golden, FSM khớp, PASS |
| Tự kiểm A.10 của bitstream 3 (`kiem_tu_kiem_rtl.py`) | `5a ee 01 03 00 06 43` = đáp án firmware, PASS |
| `pnr_v3.sh` dựng lại bitstream 1 / 2 / 3 | `.fs` trùng bản phát hành từng dòng (ngoài chú thích) |
| **Mở `fpga/fpga_project.gprj` như IDE (`gw_sh open_project` + `run all`)** | `.fs` trùng `bitstreams/3_v3_e2_n2` từng dòng |
| `firmware/build.sh test` + `tools/m0_test.py` | TẤT CẢ PASS |
| Keil `fw.uvprojx` | 0 lỗi, 0 cảnh báo, Code 16.172 B |
