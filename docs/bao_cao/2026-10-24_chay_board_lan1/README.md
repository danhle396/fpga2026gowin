# 2026-10-24 — Chạy trên board lần 1 (phần cứng nối cố định, v2.2)

Đã nạp: FPGA `fpga/bitstream/fpga_project.fs` vào flash, MCU firmware `FW_NODE` (Keil, build 22:28), ESP32 `esp32/mu_nga_hub`. Log ESP32 qua USB (COM4, CP210x, 460800), 40 s sau khi reset: `esp32_log.txt`. Tên WiFi và IP đã che.

## Kết quả

| Kiểm | Kết quả |
|---|---|
| **Tự kiểm A.10 của FPGA qua SPI từ ESP32 (1 MHz, dây cố định J2)** | **PASS**: đọc `5A EE 01 03 00 06 43` = đáp án mô phỏng (lớp 3). Đây là lần đầu bitstream 3 (giao thức v3 + engine E2 + mô hình N2) chạy trên chip và cho kết quả trùng golden. ESP32 không phải hạ xuống 100 kHz |
| ESP32 khởi động, Safety FSM | `# start`, `S,693,MONITOR,1` |
| WiFi | Kết nối được, log TCP cổng 3333 sẵn sàng |
| Mẫu từ MCU | **0 mẫu**, 0 khung hỏng, không có dòng `MCU ...` trong 40 s: ESP32 không nhận byte nào ở GPIO16 |

## Chưa đạt, cần kiểm

Không nhận byte nào, kể cả byte rác, nên khả năng cao nhất là MCU không chạy hoặc dây TX không tới ESP32:
1. EVK có nguồn không. EVK lấy điện từ cổng USB SN-Link; lúc ghi log, SN-Link không cắm vào máy. LED D6 phải nháy 1 Hz.
2. MCU đã nạp đúng bản `FW_NODE` (build 22:28, "Verify OK").
3. Dây P3.1 (`UTX_P31`, J10) → ESP32 GPIO16, GND chung.

## Gỡ lỗi MCU → ESP32 và chạy thông (23:10–23:15)

| Bước | Hiện tượng | Sửa |
|---|---|---|
| 1 | `byte_rx=0` | `uart_putc` tự ghi byte đầu khi THR rỗng → nhận 6 byte rồi dừng: ngắt UART của MCU không chạy |
| 2 | Vẫn kẹt | Bỏ phát bằng ngắt, chờ THRE rồi ghi TH (như `uart.c` của nhóm) → `byte_rx` tăng nhưng toàn byte rác (`00 80 F0 FC ...`) |
| 3 | Byte rác = sai baud | Đặt `SN_SYS0->AHBCP = 0` (HCLK = SYSCLK / 1, như `board.c` của nhóm); DLL tính từ `SystemCoreClock` |
| 4 | Nạp xong MCU không tự chạy | Tùy chọn nạp Keil `-FO7` → `-FO15` (thêm Reset and Run): `Application running ...` |

Kết quả sau bước 4 (`chay_thong_log.txt`, log qua WiFi TCP 3333; MCU, ESP32, FPGA cùng cấp nguồn bằng pin, cắm thêm USB để nạp):
- `MCU # HCLK=48000000`; `MPU6050 OK` (WHO_AM_I 0x68, 7 thanh ghi đúng); `gyro_off,48,32,-16 lam_lai=0`.
- **Mỗi 0,32 s một kết quả FPGA**: `t,seq,0,72,MONITOR,0`, tức board đứng yên → lớp 0 NORMAL, rc 0 = OK.
- `STAT,mau=391,mat=0,khung_hong=0,gui=5,ok=5,timeout=0,loi=0,bo_qua=0`; MCU `STAT,mau=502,i2c_loi=0,mat=0` (≈ 100 Hz).

**Luồng MPU6050 → MCU → UART → ESP32 → SPI → FPGA (CNN) → ESP32 (Safety FSM) → WiFi chạy thông trên phần cứng thật lần đầu.** Chưa thử ngã, chưa đo lâu.
