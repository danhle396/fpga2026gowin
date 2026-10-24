# firmware/ — mã C của mũ: SN32F407 (nút cảm biến) và lõi dùng chung với ESP32

Phần cứng nối cố định (đề cương v2.2): `SN32F407 → UART 115200 → ESP32 → SPI → FPGA`. Thư mục này có hai phần:

| Phần | File | Chạy ở |
|---|---|---|
| **MCU** | `app_main.c`, `board.c`, `i2c0.c`, `imu.c`, `gyro_cal.c` + `node_link.c`, `crc.c` | SN32F407: đọc MPU6050 100 Hz (hỏi INT_STATUS), hiệu chuẩn gyro, gửi từng mẫu + nút thành khung `F1 7E` |
| **Lõi dùng chung** | `hub.c`, `app_core.c`, `preprocess.c`, `blocks.c`, `safety.c`, `pwr_btn.c`, `spi_frame.c`, `crc.c`, `node_link.c`, `fw_config.h`, `selftest_expect_v3_e2_n2.h` | ESP32 (`esp32/mu_nga_hub`, bản chép bằng `esp32/dong_bo_core.sh`) và bộ test trên PC |

## Nạp MCU

Keil mở `keil/fw.uvprojx`, F7 rồi F8 (cần driver SN-Link cho Keil). Không mở Keil thì chạy `bash firmware/build.sh` → `build/fw.hex`. Sau khi reset, giữ board **đứng yên 3 s** để hiệu chuẩn gyro. LED D6 nháy 1 Hz là đang gửi mẫu; nháy 2 Hz là MPU6050 lỗi.

MCU in ra cùng đường UART sang ESP32 (ESP32 chuyển lên log với tiền tố `MCU `):
- `# MPU6050 OK ...`, `# gyro_off,...`, `# NODE: ...` lúc khởi động;
- `STAT,mau=,i2c_loi=,mat=` mỗi 5 s.

Khung mẫu (21 byte, `node_link.h`): `F1 7E | SEQ | 0E 00 | 'D' AX AY AZ GX GY GZ (INT16 LE, gyro đã trừ offset) KEYS | CRC-16 LE`. KEYS bit 0 = SW3 (nút duy nhất: bật/tắt, CANCEL, SOS), bit 1 = SW6.

## Lõi dùng chung, đã kiểm

| File | Việc | Kiểm (`tools/m0_test.py`, mã máy Cortex-M0 trong Unicorn) |
|---|---|---|
| `preprocess.c` | A.2: lọc [1,3,3,1]/8, 100 → 50 Hz, INT8, cửa sổ 128 mẫu mỗi 16 mẫu | 10.000 mẫu khớp golden từng byte |
| `spi_frame.c` | A.7: khung ghi v3 772 B, kiểm khung đọc, payload tự kiểm LFSR | 305 khung khớp từng byte; 92 ca khung đọc |
| `blocks.c`, `safety.c` | A.8: khối bất động, bỏ phiếu 2/3, Safety FSM | trùng `ml/src/safety_model.py` trên 240.000 tick |
| `pwr_btn.c` | một nút: bật/tắt, CANCEL, SOS | 9 ca |
| `app_core.c` | lõi vòng lặp: mẫu → cửa sổ → kết quả → FSM | 131 s dữ liệu D1 trùng golden |
| `hub.c` | lõi ESP32: app_core + gửi khung v3 + hỏi vòng FPGA (không IRQ) + tự kiểm A.10 | 402/402 kết quả, 11/11 lần đổi trạng thái trùng golden; FPGA im lặng → timeout, không treo |
| `node_link.c` | khung MCU → ESP32 | khớp Python từng byte; tách luồng có chữ xen, khung hỏng, mẫu mất |
| `gyro_cal.c` | FW-05 hiệu chuẩn gyro | Unicorn |

`test/cnn_mcu.c` là CNN INT8 thuần C, chỉ dùng trong test để đứng thay FPGA (khớp golden 50/50).

## Kiểm trên PC

```
bash firmware/build.sh test && python -I tools/m0_test.py      # cần: pip install unicorn numpy
```

`firmware/vendor/SONiX.SN32F4_DFP.1.1.2.pack`: pack thiết bị của SONiX cho Keil (nhấp đúp để cài trên máy mới).
