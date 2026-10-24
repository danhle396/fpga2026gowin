# 2026-10-24 — Dọn thư mục theo hệ thống đang nạp (v2.2)

Nhóm yêu cầu repo gọn, chỉ còn file của hệ thống đang nạp: MCU (nút cảm biến) → UART → ESP32 → SPI → FPGA bitstream 3. Mọi thứ đã bỏ vẫn lấy lại được từ lịch sử git (commit trước "dọn thư mục").

## Đã bỏ

| Thứ | Vì sao không còn dùng |
|---|---|
| `Document Board Kiwi Primer 20K/` (project Gowin E1 cũ của nhóm), `FPGA_Fall_Detection_AI-…/` (weight E1) | Engine E1 không nằm trong bitstream đang nạp; dự án thật của nhóm ở `round2` |
| `bitstreams/1_*`, `2_*` | Giao thức PROTO 1 và E1; ESP32 chỉ nói giao thức v3 |
| `rtl/pin_probe` | Lái 6 chân J2 làm ngõ ra, tranh dây với ESP32 đang nối cố định |
| `rtl/gowin`, `rtl/v3/pnr_v3.sh`, `rtl/tb/run_all.sh`, `rtl/gl/run_gl.sh`, testbench E1 | Thay bằng `fpga/scripts/{build,test,gl}.sh` chỉ cho project `fpga/` |
| `test_sensor/` | Bản thử cảm biến cũ; cảm biến nay kiểm qua log của ESP32 |
| `sdk/SN32F4_DFP/` (bản giải nén) | Keil dùng pack đã cài; giữ `firmware/vendor/SONiX.SN32F4_DFP.1.1.2.pack` |
| `firmware/src/spi_fpga.c`, `diag.c`, `selftest_expect.h`, chế độ RUN/LOG/TRC/HIL trên MCU | MCU không còn dây SPI/RX; `app_main.c` chỉ còn vai trò nút cảm biến (Code 5.030 B) |
| `tools/check_frames.py`, `hil_test.py`, `gen_cnn_params.py`, `gen_tb_top.py`, `verify_spec_v3.py`, `svd_decode.py` | Dùng cho MCU nối thẳng FPGA hoặc cho E1 |
| `ml/out/` các mô hình thử nghiệm (n1, n2, n2s, n2t, export E1, e2_matrix khác) | Giữ mô hình đang nạp `n2_11_d1` và bản xuất `e2_matrix/n2_11_p1`; số liệu của các lần thử nằm ở `docs/bao_cao/` |
| `docs/huong_dan_dot_B.md` | Thay bằng `docs/huong_dan_nap_chay.md` |

## Đã gom

- `fpga/`:
  - `src/`: RTL, giữ nguyên;
  - `sim/`: `tb_proto`, `tb_stream`, `tb_e2`, `pll_50m_sim`, `rpll_stub`;
  - `scripts/build.sh`: mở `.gprj` như IDE, `--release` chép vào `bitstream/`; `scripts/test.sh`; `scripts/gl.sh`;
  - `bitstream/`: `.fs` + SHA256 + báo cáo.
- `firmware/`:
  - `test/cnn_mcu.c`: chỉ dùng làm FPGA giả lập;
  - `build.sh`: tách nhóm CORE (dùng chung với ESP32) và nhóm MCU;
  - Keil project còn 7 file.

## Hồi quy sau khi dọn (`hoi_quy.log`, `gl.log`)

| Bộ kiểm | Kết quả |
|---|---|
| `fpga/scripts/test.sh` | 5/5 PASS: mô hình trong `fpga/src` đúng; tb_e2 P = 1 và 4; tb_proto 10 khung + 7 kịch bản; lõi ESP32 trùng `firmware/src` |
| `tools/m0_test.py` | 19/19 PASS. Trước là 22; bớt 3 phép FW-15 trên các mô hình thử nghiệm đã bỏ. Giữ đủ node_link, hub.c, app_core trên mô hình đang nạp |
| `tools/cosim.py --e2 n2_11_p1` | 423/423 khung khớp golden, FSM khớp, PASS |
| Tự kiểm A.10 với RTL | `5a ee 01 03 00 06 43` = đáp án, PASS |
| `fpga/scripts/build.sh` | Fmax 111,01 MHz; `.fs` **trùng từng dòng** `fpga/bitstream/fpga_project.fs` (SHA256 `e7d5884c…`, không đổi) |
| `fpga/scripts/gl.sh` (netlist sau P&R) | PASS: 1 khung + 7 kịch bản, CYCLES 258.080; FF INIT=1 chỉ là khởi tạo cố ý (cs_sync, crc, state, f[2], top2) |
| Keil `fw.uvprojx` | 0 lỗi, 0 cảnh báo, Code 5.030 B |
| ESP32 `arduino-cli compile` (3.0.7) | 927.281 B flash, 48.048 B RAM, 0 cảnh báo từ mã dự án |
