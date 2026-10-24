# bitstreams/ — bitstream đã dựng sẵn cho Kiwi Primer 20K

Dựng bằng Gowin EDA V1.9.11.03 Education (`gw_sh`, script `rtl/v3/pnr_v3.sh`) trên bản sao project. **Bitstream 1 và 2 dựng lại chiều 15/10** sau khi mô phỏng netlist phát hiện lỗi `conv_start` lên nguồn bằng 1 (xem dưới); **bitstream 3 dựng lại 16/10** với N2 11 người. Bản cũ hơn thì đừng nạp. **Cả 3 bitstream dựng lại 24/10 với chân trên header J2** theo sơ đồ nối thực tế của nhóm (Phụ lục E.1: SCK J2-10, MOSI J2-11, MISO J2-13, CS J2-16, IRQ J2-24, RST_N J2-23; LVCMOS33). Bản trước 24/10 dùng J1, đừng nạp. Mô phỏng netlist sau P&R ngày 24/10: bitstream 1 `tb_top_spi` 5/5, bitstream 3 `tb_proto` 3 khung + 7 kịch bản PASS, file `.fs` trùng từng bit bản đã mô phỏng (`docs/bao_cao/2026-10-24_so_do_noi_nhom/`); clock 27 MHz ở H11 → rPLL 50,143 MHz. Nạp bằng Gowin Programmer (SRAM để thử, Flash để giữ sau khi tắt nguồn). Kiểm tra file trước khi nạp: `sha256sum -c SHA256.txt`.

| Thư mục | Top / engine / mô hình | Giao thức | Firmware: `FW_BITSTREAM` trong `fw_config.h` | Đã kiểm trong mô phỏng | P&R |
|---|---|---|---|---|---|
| `1_e1_proto1_sisfall` | `fpga_top` / E1 / N1 SisFall của nhóm, shift (8, 8) | PROTO 1 (CRC-8, đọc 7 byte) | `1` (mặc định) | `tb_cnn_core_golden` 50/50 có bão hòa, `tb_e1_layers` 50/50 mọi tầng, `tb_top_spi` qua chân SPI; **netlist sau P&R: `tb_top_spi` 5/5** | Logic 907 (5 %), BSRAM 6/46, DSP 1,25/24, **103,33 MHz** |
| `2_v3_e1_sisfall` | `fpga_top_v3` / E1 / cùng mô hình | v3 (CRC-16, SEQ, STATUS, 20 byte), RST_N ở J2-23 | `2` | `tb_proto` 50 khung + 7 kịch bản lỗi; **netlist sau P&R: 1 khung + 7 kịch bản** | Logic 1.521 (8 %), **104,92 MHz** |
| `3_v3_e2_n2` | `fpga_top_v3` / E2, P = 1 / N2 chỉ kênh đầu huấn luyện trên D1 **11 người** (`ml/out/n2_11_d1`, dựng lại 16/10; bản trước: 6 người) | v3 | `3` | `tb_e2` 50/50 mọi tầng, `tb_proto` 10 khung + 7 kịch bản, 258.080 chu kỳ = 5,15 ms; **netlist sau P&R: 3 khung + 7 kịch bản PASS** (16/10; file này trùng bit bản đã mô phỏng trừ dấu thời gian; `docs/bao_cao/2026-10-16_n2_11_nguoi/`) | Logic 1.473 (8 %), **111,01 MHz** |

Mỗi thư mục có:
- `fpga_project.fs`: bitstream;
- `fpga_project.rpt.txt`: báo cáo tài nguyên;
- `cnn_params.vh`: tham số đã tổng hợp vào;
- `SHA256.txt`.

**Dùng cho đợt B (từ 24/10):**
- **Chỉ cần `3_v3_e2_n2`**: đây là bản dựng của project chính `fpga/fpga_project.gprj` (trùng từng bit), và firmware mặc định đã là `FW_BITSTREAM 3`. Nạp ở B7, chạy cả chuỗi ở B8.
- `1_e1_proto1_sisfall` chỉ là đường lùi (B10): khi B7 không đạt, nạp nó để tách lỗi dây với lỗi giao thức.
- `2_v3_e1_sisfall` không còn dùng trong đợt B, giữ để tra lại.
- Mô hình tầng 2 nhanh gấp 2,7 lần E1. HIL cho bản này phải so với **đúng mô hình đã nạp**: `python tools/hil_test.py --port COMx --n 2000 --proto 3 --params ml/out/n2_11_d1/params_int8.npz` (TH-09). Dùng `--params` của mô hình khác thì mọi cửa sổ sẽ báo sai lệch dù chip chạy đúng.

**Mô phỏng netlist sau P&R** (`bash rtl/gl/run_gl.sh <thư mục> p1 | v3 | ml/out/e2_matrix/n2_11_p1`): chạy chính netlist Gowin xuất cho file `.fs` này (dựng lại không có tùy chọn netlist cho file trùng bit), kể cả nội dung ROM weight. Lần chạy đầu 15/10 tìm ra lỗi: `cnn_controller.v` để `conv_start` không có giá trị khởi tạo, Gowin chọn `INIT = 1`, nên vừa nạp cấu hình engine conv đã tự chạy và **khung đầu tiên sau khi bật nguồn cho kết quả sai** (đúng khung tự kiểm A.10 của firmware). Đã sửa bằng cách khởi tạo 0 mọi thanh ghi điều khiển; chi tiết ở `docs/bao_cao/2026-10-15_loi_init_conv_start/`.

**Chưa chạy trên chip.** Mọi số ở đây là mô phỏng và báo cáo P&R.
