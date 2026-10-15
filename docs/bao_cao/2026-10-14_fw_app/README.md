# 2026-10-14 — firmware chính đủ chức năng tầng 1 (chỉ biên dịch + kiểm phần C thuần)

Chưa chạy trên board. Sau đợt A buổi chiều, firmware có thêm:

| File | Việc | Kiểm thế nào |
|---|---|---|
| `app_main.c` | Vòng lặp chính (mục 4.3): ngắt INT cảm biến → đọc 14 byte → `app_core` → gửi khung không chặn → hỏi kết quả mỗi vòng → khe 10 ms (phím, WEAR, FSM, còi, LED) → lệnh UART. Chế độ RUN / LOG / TRC / HIL / DIAG / STAT (A.9). Tự kiểm A.10 lúc khởi động | biên dịch |
| `app_core.c` | Lõi C thuần: trừ offset gyro → khối + tiền xử lý → SEQ → kết quả → FSM → mẫu còi và LED | **Unicorn, chế độ 8:** 131 s dữ liệu D1 (ngã nằm, ngã có đứng dậy, ngã trượt tường, sinh hoạt) nội suy 100 Hz, cộng offset gyro giả, có lịch bấm CANCEL; `cnn_mcu.c` thay FPGA, kết quả về sau 30 ms. 402 kết quả và 11 lần đổi trạng thái **trùng từng mục** với chuỗi golden Python (`decimate`, `q8`, `forward`, `safety_model`) |
| `gyro_cal.c` | FW-05 | Unicorn, chế độ 9: làm lại khi rung, offset trùng tham chiếu |
| `i2c0.c`, `imu.c` | FW-04: I2C0 phần cứng, cấu hình A.1, đọc lại 7 thanh ghi | biên dịch |
| `board.c` | UART buffer vòng + ngắt TX/RX (FW-06), còi, WEAR, watchdog | biên dịch |
| `spi_fpga.c` | thêm `spi_fpga_start` / `spi_fpga_poll` không chặn | biên dịch |
| `diag.c` | menu chẩn đoán cũ (giữ SW3 lúc khởi động, hoặc lệnh `DIAG`) | biên dịch |
| `selftest_expect.h` | đáp án tự kiểm cho weight SisFall đang có trong bitstream (`tools/export_mem.py`) | `export_mem.py` đọc ngược |

Kích thước:

| Bản build | Flash | RAM |
|---|---|---|
| `bash firmware/build.sh` (`-Oz`) | 10.036 byte | 5.416 byte |
| Keil `fw.uvprojx` (0 lỗi, 0 cảnh báo) | Code 14.588 + RO 1.468 = 16,1 KB / 32 KB | 5.412 byte / 8 KB |

`m0_test.log`: toàn bộ phép kiểm C thuần, TẤT CẢ PASS.

**Cập nhật 15/10** (thêm LED 7 đoạn FW-12 và chế độ 10 cho mô phỏng ghép): `keil_uv4_rebuild_15_10.log` Code 15.164 + RO 1.480 = 16,6 KB / 32 KB, ZI 5.416 byte, 0 lỗi 0 cảnh báo; `m0_test_15_10.log` 51/51 ca FSM + LED, TẤT CẢ PASS.

Công cụ PC đi kèm: `tools/check_frames.py` (FW-10) và `tools/hil_test.py` (TH-07). Cả hai đã thử bằng dữ liệu giả, có phép âm.
