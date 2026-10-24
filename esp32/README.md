# esp32/ — ESP32 trung tâm (phần cứng nối cố định theo codecanthiet của nhóm, 24/10)

`mu_nga_hub/mu_nga_hub.ino`: nhận mẫu 100 Hz từ SN32F407 (UART2 GPIO16, 115200, khung `F1 7E` của `node_link.h`),
chạy lõi C của firmware (`hub.c` → `app_core`: tiền xử lý A.2, khối A.8, bỏ phiếu + Safety FSM, nút), gửi khung v3
772 byte sang Kiwi (SPI GPIO27/18/23/19), hỏi vòng kết quả 7 byte, in log ra USB 460800 và WiFi TCP cổng 3333.

- Nạp: Arduino IDE, board **ESP32 Dev Module** (esp32 by Espressif; đã build thử 3.0.7: 927 KB flash, 48 KB RAM, 0 cảnh báo).
- Các file `.c/.h` trong `mu_nga_hub/` là bản chép từ `firmware/src`; sửa ở đó rồi `bash esp32/dong_bo_core.sh`.
- Cách dùng, dòng log, lệnh, lỗi hay gặp: [docs/huong_dan_nap_chay.md](../docs/huong_dan_nap_chay.md).
