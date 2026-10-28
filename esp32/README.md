# esp32/ — ESP32 trung tâm của thiết bị đeo ngực (phần cứng nối cố định theo codecanthiet của nhóm, 24/10)

`mu_nga_hub/mu_nga_hub.ino` làm các việc sau:
- **Nhận mẫu:** mẫu 100 Hz từ SN32F407 qua UART2 GPIO16, 115200, khung `F1 7E` của `node_link.h`. Bộ tách chịu nhiễu; mẫu mất ≤ 50 được chèn bù.
- **Đổi trục:** cảm biến → trục người khi đeo ngực (`FW_VI_TRI_DEO 1`), trừ `ACC_OFF`.
- **Lõi C của firmware** (`hub.c` → `app_core`): tiền xử lý A.2, khối A.8, bỏ phiếu + Safety FSM, nút, tư thế A.11, xác nhận ngã thật A.12 (`nga.c`).
- **FPGA:** gửi khung v3 772 byte sang Kiwi (SPI GPIO27/18/23/19), hỏi vòng kết quả 7 byte.
- **Còi:** gửi lệnh còi cho MCU qua GPIO17 → P3.2; âm 2 kHz cố định.
- **MẤT CẢM BIẾN:** báo khi quá 3 s không có mẫu.
- **Giao diện:** trang web `http://<IP>/` (trạng thái, tư thế, kết quả CNN, biểu đồ, thống kê, sự kiện, nút hủy / bật lại); log USB 460800 và WiFi TCP cổng 3333.

Cách dùng:
- **Nạp:** Arduino IDE, board **ESP32 Dev Module** (esp32 by Espressif 3.0.7). Bản dựng ngày 28/10: 956.624 B flash (72 %), 54.000 B RAM.
- **Sửa lõi C:** các file `.c/.h` trong `mu_nga_hub/` là bản chép từ `firmware/src`. Sửa ở `firmware/src` rồi chạy `bash esp32/dong_bo_core.sh`; `fpga/scripts/test.sh` kiểm hai nơi trùng nhau.
- **Nguồn MPU6050:** lấy từ 3,3 V của ESP32 (`MPU_NGUON_GPIO 0`, không dùng GPIO25).
- **Tài liệu:** dòng log, lệnh, lỗi hay gặp ở [docs/huong_dan_nap_chay.md](../docs/huong_dan_nap_chay.md).
