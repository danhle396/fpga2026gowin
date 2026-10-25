# Nạp và chạy trên phần cứng nối cố định (từ 24/10)

Dây đã cố định theo `codecanthiet/` của nhóm, không tháo dây nào. Còi trên EVK cần **thêm một dây ESP32 GPIO17 → EVK J10 `URX_P32` (P3.2)**; nhóm **chưa nối được** (25/10) nên còi đang tắt (`COI_TU_ESP32 0`). Luồng dữ liệu:

```
MPU6050 ──I²C──► SN32F407 (MCU) ──UART 115200──► ESP32 ──SPI──► Kiwi Primer 20K (FPGA, CNN)
                  đọc cảm biến 100 Hz      P3.1 → GPIO16     │  27/18/23/19 → J2-16/10/11/13
                  gửi từng mẫu + nút                         │
                                                             ├─ tiền xử lý, cửa sổ, Safety FSM (lõi C đã kiểm khớp golden)
                                                             ├─ LED GPIO2 (báo động), nút BOOT (CANCEL phụ)
                                                             ├─ GPIO17 → MCU P3.2: lệnh còi → còi PZ1 trên EVK kêu
                                                             └─ log: USB 460800 + WiFi TCP cổng 3333
```

| Board | Nạp gì | Bằng gì |
|---|---|---|
| MCU SN32F407 | `firmware/keil/fw.uvprojx` (mặc định `FW_NODE 1`: chỉ đọc cảm biến và gửi cho ESP32) | Keil: F7, F8 (cần driver SN-Link, B2) |
| FPGA Kiwi | `fpga/fpga_project.gprj` = `fpga/bitstream/fpga_project.fs` | Gowin Programmer, External Flash Mode (đã nạp 24/10) |
| ESP32 | `esp32/mu_nga_hub/mu_nga_hub.ino` | Arduino IDE |

**Chỉ nạp `fpga/bitstream/fpga_project.fs` vào FPGA.** Bitstream này an toàn với dây ESP32: trên CS, SCK, MOSI FPGA chỉ nhận vào, riêng MISO là FPGA phát ra cho ESP32 nhận. Bitstream khác có thể lái các chân J2 và tranh dây với ESP32.

**Trước lần đầu:** đo VDD của EVK = 3,3 ± 0,1 V (jumper J5 `T_DATA`–`SWDIO_P35`, J4 `T_CLK`–`SWCLK_P36`, J3 `T_VDD`–`32F407_VDD`, J1 `SW_ON_3.3V`–`32F407_VDD`, SW1 ON). Keil cần **driver SN-Link** ("SN-Link_Driver for Keil Cortex-M" của SONiX, cài vào đúng thư mục Keil); thiếu driver thì F8 không làm gì.

## 1. MCU

1. Cắm USB SN-Link của EVK.
2. Keil mở `firmware/keil/fw.uvprojx`, F7 rồi F8. Phải thấy `Verify OK`.
3. Đặt board **đứng yên 3 s** sau khi reset (hiệu chuẩn gyro). Sau đó LED D6 nháy 1 Hz, nghĩa là MCU đang gửi mẫu sang ESP32.

MCU in chữ ra chân TX, tức là sang ESP32. ESP32 chuyển các dòng đó lên log với tiền tố `MCU `.

**Còi (tạm tắt, chờ nối dây):** khi nối dây GPIO17 → P3.2 thì đặt `#define COI_TU_ESP32 1` trong `firmware/src/fw_config.h`, chạy `bash esp32/dong_bo_core.sh`, rồi nạp lại MCU. ESP32 gửi lệnh bật/tắt còi (1 byte) qua dây đó; MCU kêu còi PZ1 trên EVK ở 500 Hz theo nhịp của Safety FSM:
- CẢNH BÁO: bíp ngắn mỗi giây trong 10 s đếm ngược;
- BÁO ĐỘNG: hú liên tục;
- bật/tắt hệ thống: bíp xác nhận.

Mất lệnh quá 0,5 s (ESP32 reset, đứt dây) thì MCU tự tắt còi. Trong `STAT` của MCU, `lenh_coi` tăng đều khoảng 10 mỗi giây là dây còi đã thông.

## 2. ESP32

1. Arduino IDE → Boards Manager → cài **esp32 by Espressif Systems** (đã build thử bản 3.0.7; bản 2.0.x cũng chạy được).
2. Mở `esp32/mu_nga_hub/mu_nga_hub.ino`, chọn board **ESP32 Dev Module** và cổng COM của ESP32.
3. WiFi: `Tro Bao Tran T4` (ghi ở đầu `mu_nga_hub.ino`). Mang đi nơi khác (thi, demo) thì sửa `WIFI_STA_SSID`, `WIFI_STA_PASSWORD` sang hotspot điện thoại rồi nạp lại ESP32.
4. Upload. Không phải cài thêm thư viện nào.

Các file `.c`/`.h` trong thư mục sketch là **bản chép** từ `firmware/src`. Sửa ở `firmware/src` rồi chạy `bash esp32/dong_bo_core.sh`; `rtl/tb/run_all.sh` sẽ báo FAIL nếu hai nơi lệch nhau.

## 3. Xem dữ liệu

**Cách dễ nhất: trang web của ESP32.** Điện thoại hoặc laptop vào cùng WiFi với ESP32, mở trình duyệt, gõ `http://<IP ESP32>`; IP in ở dòng `# WiFi ... IP ...`. Trang hiện:
- trạng thái Safety FSM bằng màu: xanh = theo dõi, cam = nghi ngã, đỏ nhấp nháy = cảnh báo;
- kết quả CNN mới nhất;
- biểu đồ |a| 30 s, có tô đỏ các cửa sổ FALL;
- thống kê, 20 sự kiện gần nhất;
- nút **Hủy cảnh báo**.

Trang tự cập nhật 3 lần/giây và không cần Internet.

**Ghi log ra file để gửi lại:**


- **Qua USB của ESP32:** `python -I tools/ghi_uart.py --port COMx --buoc chay --giay 60`. `COMx` là cổng của ESP32; baud mặc định 460800 đã khớp.
- **Qua WiFi:** laptop vào cùng mạng `Tro Bao Tran T4`. IP của ESP32 in ở dòng `# WiFi ... IP ...` trên USB. Chạy `python -I tools/ghi_uart.py --tcp <IP> --buoc chay --giay 60`, hoặc công cụ của nhóm `wifi_live_log.py --host <IP>`.

Mong đợi sau khi bật nguồn:

```
# mu bao ho - ESP32 hub (MCU -> UART -> ESP32 -> SPI -> FPGA), firmware/src + hub.c
tu kiem FPGA (A.10) SPI 1000 kHz: doc 5A EE 01 03 00 06 43, mong doi 5A EE 01 03 00 06 43 class=3  PASS
# start
MCU # MPU6050 OK: WHO_AM_I=0x68, 7 thanh ghi doc lai dung
MCU # gyro_off,...
MCU # NODE: mau 100 Hz -> ESP32 (node_link F1 7E, 115200)
12345,7,0,0,MONITOR,0          ← mỗi 0,32 s: t_ms, seq, class (0 NORMAL / 3 FALL), score, trạng thái, rc (0 = OK)
STAT,mau=...,mat=0,khung_hong=0,gui=...,ok=...,timeout=0,loi=0,bo_qua=0,spi_khz=1000,tcp_bo=0
```

| Pass | Gửi lại |
|---|---|
| Tự kiểm `PASS`; trong `STAT`, `mau` tăng khoảng 500 mỗi 5 s; `mat` = 0, `khung_hong` = 0; `ok` tăng khoảng 15 mỗi 5 s; `timeout` = 0, `loi` = 0 | toàn bộ file trong `ket_qua_board/` |

**Thử ngã nhanh:** lắc mạnh board (sau này là mũ) rồi đặt nằm nghiêng yên. Phải thấy `S,...,SUSPECT`, `S,...,PRE_ALARM`, LED GPIO2 của ESP32 nháy, rồi `ALARM` nếu không ai hủy. Nhấn SW3 trên EVK (hoặc nút BOOT của ESP32) trong lúc PRE_ALARM để hủy.

## 4. Lệnh

Gõ trên USB hoặc TCP, kết thúc bằng Enter.

| Lệnh | Tác dụng |
|---|---|
| `LOG` | In từng mẫu 100 Hz `t,ax,ay,az,gx,gy,gz,btn,wear` (dùng cho buổi thử trên mũ) |
| `RUN` | Quay về in kết quả |
| `ST` | Chạy lại tự kiểm FPGA |
| `SPI 100` | Đặt SCK 100 kHz (tốc độ nhóm đã chạy thông). Mặc định 1000; nếu tự kiểm ở 1 MHz FAIL thì ESP32 tự hạ xuống 100 |

Ghi dữ liệu buổi thử qua cổng USB của ESP32:

```
python -I tools/logger.py --port COMx --gui LOG --subject s01 --activity di_bo --trial 1 --seconds 600
```

Thời điểm trong LOG tính theo số mẫu MCU đã gửi (10 ms mỗi mẫu, cộng cả mẫu mất), nên không bị lệch khi UART dồn cục.

## 5. Lỗi hay gặp

| Triệu chứng | Kiểm |
|---|---|
| `# chua nhan mau tu MCU` lặp lại | MCU đã nạp firmware mới chưa (LED D6 nháy 1 Hz); dây P3.1 → GPIO16; GND chung |
| `khung_hong` tăng đều | Baud lệch: MCU phải là bản `FW_NODE 1` (115200) |
| Tự kiểm `doc 00 00 ...` ở cả 1 MHz và 100 kHz | FPGA chưa có bitstream (bật lại nguồn Kiwi, hoặc nạp lại `fpga/`); dây SPI J2 |
| Tự kiểm đọc ra byte lạ | Sai bitstream: phải là bản 24/10 (`cd fpga/bitstream && sha256sum -c SHA256.txt`) |
| `timeout` tăng, `ok` không tăng | FPGA không trả kết quả: thử `SPI 100`, gửi log cho AI |
| `MCU # MPU6050 loi` | Dây I²C P0.10/P0.11 và nguồn 3,3 V của MPU6050 |
