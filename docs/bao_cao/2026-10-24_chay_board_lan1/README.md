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
