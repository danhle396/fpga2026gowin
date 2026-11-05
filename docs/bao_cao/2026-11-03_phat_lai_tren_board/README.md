# Phát lại dữ liệu thật qua ESP32 + FPGA thật, 3/11/2026

Sketch tạm `hil_board.ino` chạy lõi sản phẩm chép nguyên từ `esp32/nguc_nga_hub` (`hub.c`, `nga.c`, `posture.c`, `safety.c`, `app_core.c`) trên ESP32 thật, nói chuyện với FPGA thật qua SPI 1 MHz như sản phẩm. PC gửi dữ liệu qua USB 921600 bằng `hil_pc.py`.

Nhãn đúng của kết quả: **phát lại trên board**. ESP32 và FPGA là thật, dữ liệu là log đã ghi, không phải người ngã trực tiếp. Không dùng mẫu của MCU và MPU6050 trong phép đo này.

## Kết quả

| Phép đo | Kết quả | File |
|---|---|---|
| Log ngã của nhóm, 26.299 mẫu, thời gian thực | 814 kết quả FPGA, 0 lỗi, cách đều 320 ms; 20 lần xét: 15 xác nhận, 5 loại; cả 14 cú ngã được tính đều có xác nhận (`nga_nam_4` hai lần) | `log_nga.txt` |
| Cùng log, chạy nhanh | E: 26.299 mẫu, gửi 814, ok 814, timeout 0, lỗi 0, xác nhận 15, loại 5; 20 dòng N trùng hoàn toàn với lượt thời gian thực | `thu_nga_nhanh.txt` |
| 500 cửa sổ thật đầu tiên của `d1_windows.npz` | Khớp golden 500/500: lớp, SCORE, 4 logit INT16, CRC, SEQ; CYCLES đều 258.080; từ lúc ghi xong đến lúc có kết quả 5.110–5.152 µs | `thu_500.npz` |
| Chạy thực trên bàn trước khi nạp, khoảng 33 phút | STAT: 200.607 mẫu, mất 0, hỏng 0, FPGA 6.261/6.261, timeout 0, lỗi 0. MCU tự đếm 48 lần lấy mẫu trễ từ 15 ms trên 207.868 mẫu | `truoc/` |

Thời gian FPGA và MCU cùng 2.000 cửa sổ giả ngẫu nhiên nằm ở `../2026-11-03_do_thoi_gian_fpga_tren_board/` và `../2026-11-03_do_thoi_gian_cnn_mcu_tren_chip/`.

## Giới hạn

- 500 cửa sổ thật đều thuộc một người và đều cho lớp NORMAL, nên chưa kiểm được lớp FALL trên cửa sổ thật. 2.000 cửa sổ giả ngẫu nhiên chỉ so lớp và SCORE.
- Lượt `log_nga.txt` xử lý đủ mẫu nhưng không có dòng E và tự kiểm cuối, vì PC thiếu một xác nhận `a` rồi dừng sau 15 s. Số E lấy từ lượt chạy nhanh.
- Đầu ra USB đôi khi có cụm 64 byte `0xFF`. `hil_pc.py` lọc các byte này. Lượt đầu `log_nga_lan1_bi_ngat.txt` treo hơn 2 giờ, thiếu ít nhất một dòng P so với lượt sau, và mất phần cuối, nên không dùng để lấy số. Chưa chứng minh được cụm `0xFF` là nguyên nhân mất dòng.
- Dừng theo quyết định của nhóm, **không chạy**: log động tác, log 9 tư thế, 189.094 cửa sổ, D1 2.141 bản ghi qua hub. `so_cua_so.py` và `so_log.py` là công cụ cho các phép đo đó.

## Khôi phục

ESP32 đã nạp lại đúng bản 31/10: `verify_goc.txt` khớp 4/4 vùng (bootloader, partitions, boot_app0, app), tự kiểm FPGA PASS (`sau_khoi_phuc_serial.log`). MCU và FPGA không bị nạp lại.

Trong `sau_khoi_phuc_serial.log`, thiết bị báo 0 mẫu vì MPU6050 treo. Bộ đếm MCU cho thấy cảm biến treo khoảng 16:06, trước khi nạp lại, khi ESP32 đang chạy sketch tạm. Nguyên nhân chưa đo. Cần tắt nguồn khoảng 5 giây để cảm biến hoạt động lại.
