# firmware/ — firmware chính cho SN32F407 trên "32F407 EVK V1.0"

Chân, thanh ghi và giao thức theo `PROJECT_MASTER.md`, Phụ lục A (SPEC v3) và Phụ lục E. **Chưa dòng nào chạy trên board.** Phần C thuần đã chạy dưới dạng mã máy Cortex-M0 trong trình giả lập và khớp golden. Phần chạm ngoại vi mới chỉ biên dịch.

## Nạp và dùng

1. Mở `keil/fw.uvprojx`, Build (F7), Download (F8). Mạch nạp SN-Link trên EVK đã chọn sẵn. Không mở Keil thì chạy `bash firmware/build.sh` → `build/fw.hex`.
2. Terminal 460800 8N1 trên UART0 (header J10: `UTX_P31`, `URX_P32`, GND).
3. Khởi động: `# mu bao ho ...` → kiểm MPU6050 (WHO_AM_I và đọc lại 7 thanh ghi) → hiệu chuẩn gyro 2 s, **để mũ đứng yên** → tự kiểm FPGA bằng khung LFSR (A.10) → `# start`.

| Vào bằng | Chế độ | In ra |
|---|---|---|
| mặc định, hoặc lệnh `RUN` | RUN | mỗi kết quả `t_ms,seq,class,score,state,err`; mỗi lần đổi trạng thái `S,t_ms,STATE,why` |
| giữ **SW6** lúc khởi động, hoặc `LOG` | LOG (A.9) | mỗi mẫu `t_ms,ax,ay,az,gx,gy,gz,btn,wear` (gyro đã trừ offset) → `tools/logger.py` |
| `TRC` | TRC | như LOG, thêm `F,seq,crc` cho mỗi khung → `tools/check_frames.py` (FW-10) |
| `HIL` | HIL | nhận khung 772 byte, trả 20 byte → `tools/hil_test.py` (TH-07); `Q` để thoát |
| giữ **SW3** lúc khởi động, hoặc `DIAG` | menu chẩn đoán | `c` CRC phần cứng, `f` thử flash E.4 bước 2, `s` 100 vòng SPI, `1`/`4` SCK, `p` PROTO, `w` đo chu kỳ WDT (ngừng feed tới khi reset), `q` thoát |
| `STAT` | — | đếm mẫu, khung, lỗi, mất mẫu, tràn UART |

Trong `fw_config.h`: `FW_BITSTREAM` (mặc định 3 = project chính `fpga/`; 1 = bitstream gỡ lỗi PROTO 1), quyết định `FW_PROTO` và đáp án tự kiểm. Trong `app_main.c`: `I2C_HZ`. Trong `board.h`: `WEAR_PRESENT` (0 khi chưa có cảm biến đội mũ) và `BUZZER_ACTIVE_HIGH`. Đổi weight trong bitstream thì chép lại `selftest_expect.h` do `tools/export_mem.py` sinh.

## Các file

| File | Việc | C thuần? | Đã kiểm |
|---|---|---|---|
| `fw_config.h` | Hằng số A.2, A.3, A.7, A.8 | — | — |
| `crc.c` | CRC-16/CCITT-FALSE, CRC-8 (PROTO 1) | có | Unicorn |
| `preprocess.c` | FW-07: lọc [1,3,3,1]/8, 100 → 50 Hz, INT8, ring, cửa sổ mỗi 16 mẫu | có | 10.000 mẫu khớp từng byte |
| `spi_frame.c` | FW-08: khung ghi v3 / PROTO 1, kiểm khung đọc, payload LFSR | có | 610 khung, 92 ca khung đọc |
| `blocks.c`, `safety.c` | FW-11: khối bất động, bỏ phiếu, Safety FSM | có | 49 ca; trùng `ml/src/safety_model.py` trên 240.000 tick |
| `gyro_cal.c` | FW-05 | có | Unicorn |
| `pwr_btn.c` | một nút cho bật/tắt + CANCEL + SOS (đề cương v2.1): ở STANDBY giữ 2 s = bật; ở MONITOR nhấn nhanh 2 lần = tắt; còn lại như A.8. `BTN_POWER` trong `fw_config.h` | có | 9 ca (mode 4 của `test/host_main.c`); phép âm `BTN_POWER=0` → 4 ca FAIL |
| `app_core.c` | lõi vòng lặp chính | có | 131 s dữ liệu D1 trùng chuỗi golden từng kết quả và từng lần đổi trạng thái |
| `cnn_mcu.c` | FW-15: CNN thuần trên MCU | có | khớp golden 50/50 trên 5 mô hình; đếm lệnh |
| `board.c` | clock 48 MHz, SysTick, UART ngắt, phím, còi, WEAR, watchdog, ngắt P2 | không | biên dịch |
| `i2c0.c`, `imu.c` | FW-04: I2C0 phần cứng, MPU6050 theo A.1 | không | biên dịch |
| `spi_fpga.c` | FW-08: SPI0, CS P2.8, IRQ P2.9, CRC phần cứng, không chặn | không | biên dịch |
| `app_main.c`, `diag.c` | vòng lặp chính, menu chẩn đoán | không | biên dịch |

## Kiểm trên PC

```
bash firmware/build.sh test && python tools/m0_test.py        # cần: pip install unicorn numpy
OPT=-O3 bash firmware/build.sh test && cp firmware/build/test.bin firmware/build/test_o3.bin \
    && python tools/m0_test.py --profile firmware/build/test_o3.bin   # đếm lệnh FW-15
```

LED 7 đoạn của EVK hiện trạng thái: `oFF` STANDBY · `rUn` MONITOR · `SUS` SUSPECT · `P 10`…`P 00` đếm ngược PRE_ALARM · `ALr` ALARM · `CL` COOLDOWN · `Err` lỗi FPGA.

Chưa có: OLED (FW-12), PWM phần cứng cho còi (đang đảo chân trong SysTick), ghi Flash (FW-16, tầng 3).
