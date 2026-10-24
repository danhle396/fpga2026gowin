# 2026-10-24 — ESP32 làm trung tâm theo phần cứng nối cố định của nhóm (v2.2)

## Bối cảnh

Nhóm cho biết dây đã cố định theo `codecanthiet`, không tháo và không thêm dây:
- MCU chỉ có dây UART TX P3.1 → ESP32 GPIO16;
- ESP32 làm master SPI tới Kiwi J2;
- không có dây SPI, IRQ, RST_N giữa MCU và FPGA, không có dây INT của MPU6050.

Nhóm chọn "không thêm dây", nên kết quả FPGA không quay về MCU được; Safety FSM phải chạy ở ESP32. Code tham khảo của nhóm (`round2/project`) đã chạy được trên phần cứng: khung UART `F1 7E`, ESP32 SPI ở 100 kHz, log WiFi TCP 3333. Ta dùng lại đúng phần truyền dẫn và hiển thị đó.

## Đã làm

| Phần | File | Nội dung |
|---|---|---|
| Khung MCU → ESP32 | `firmware/src/node_link.c/.h` | `F1 7E | SEQ | LEN | 'D' + 6 × INT16 + KEYS | CRC-16` (21 B/mẫu); bên nhận tách khung, gom dòng chữ, đếm khung hỏng và mẫu mất theo SEQ |
| Lõi ESP32 | `firmware/src/hub.c/.h` | Dùng nguyên `app_core`; ghi khung v3 772 B; hỏi vòng 7 B sau 6 ms, mỗi 1 ms, timeout 50 ms; đọc xả sau timeout; tự kiểm A.10 |
| MCU | `app_main.c`, `imu.c`, `board.c`, `fw_config.h` | `FW_NODE 1` (mặc định): đọc MPU6050 bằng cách hỏi INT_STATUS (`IMU_INT_WIRED 0`), trừ offset gyro (bão hòa như `app_core`), gửi khung; UART 115200; LED D6 nháy 1 Hz. `FW_NODE 0` giữ thiết kế gốc |
| ESP32 | `esp32/mu_nga_hub/` | Sketch Arduino; lõi C là bản chép (`esp32/dong_bo_core.sh`, `run_all.sh` kiểm trùng) |
| Công cụ | `tools/ghi_uart.py --tcp`, `tools/logger.py --gui LOG` | Đọc log qua WiFi; ghi buổi thử qua ESP32 |
| Hướng dẫn | `docs/huong_dan_nap_chay.md` | Nạp, xem log, lệnh, lỗi hay gặp |

## Kiểm (không cần board)

| Bộ kiểm | Kết quả |
|---|---|
| `tools/m0_test.py` (mã máy Cortex-M0 trong Unicorn, `m0_test.log`) | **22/22 PASS**, gồm 4 phép mới |
| ↳ node_link: đóng gói của C == Python | 50 khung khớp từng byte (có byte F1 7E trong dữ liệu, SEQ quay vòng) |
| ↳ node_link: tách luồng | đúng mẫu, dòng chữ, 1 khung hỏng, mất 4 mẫu (1 hỏng + 3 bỏ) |
| ↳ **hub.c == golden + safety_model** (N2 D1, 131 s dữ liệu thật, FPGA giả lập trả kết quả sau 5 ms, không IRQ) | **402/402 kết quả, 11/11 lần đổi trạng thái** khớp; đi qua MONITOR, SUSPECT, PRE_ALARM, ALARM, COOLDOWN; thống kê 13.099 mẫu, 402 gửi, 402 OK, 0 timeout, 0 lỗi, 0 bỏ |
| ↳ hub.c khi FPGA không trả lời | 402 timeout / 402 gửi, không treo |
| Keil `fw.uvprojx` (FW_NODE 1) | 0 lỗi, 0 cảnh báo, Code 16.948 B |
| `firmware/build.sh` (FW_NODE 1) | 7,15 KB |
| `app_main.c`, `board.c` với `FW_NODE=0`, `IMU_INT_WIRED=1` | biên dịch 0 lỗi, 0 cảnh báo |
| ESP32 `arduino-cli compile` (esp32:esp32 3.0.7, ESP32 Dev Module, `--warnings all`) | build được: 927.281 B flash (70 %), 48.048 B RAM; 0 cảnh báo từ mã của dự án |
| `ghi_uart.py --tcp` với máy chủ TCP giả lập | nhận đủ dòng, gửi được lệnh |
| `esp32/dong_bo_core.sh --check`, `sync_spec.py --check` | PASS |

## Chưa làm

- Chưa nạp ESP32.
- Chưa nạp MCU bản FW_NODE: lúc nạp thì SN-Link đã rút khỏi máy, Keil báo "Target DLL has been cancelled".
- Chưa chạy trên board: chưa có số đo thật của tự kiểm, `STAT`, hay thử ngã.
- Đồng hồ ESP32 và tốc độ SPI 1 MHz trên dây của nhóm chưa kiểm. ESP32 tự hạ xuống 100 kHz nếu tự kiểm ở 1 MHz FAIL.
- Không có còi tại chỗ: còi EVK không dùng được trong kiến trúc này.
