# test_sensor — Kiểm tra cảm biến MPU6050

Bộ test này phục vụ việc **FW-02** trong [PROJECT_MASTER.md](../PROJECT_MASTER.md).

> Lưu ý (2026-10-13): cảm biến đã được kiểm tra PASS trên ESP32 và SN32F407, nhưng bằng mã riêng của một
> thành viên. Firmware trong `firmware/` của thư mục này chưa từng chạy trên board SN32F407.

> Cập nhật 2026-10-13: bộ test đã chuyển sang cấu hình hiện hành (100 Hz, ±16 g, ±2000 °/s, gắn trên mũ với
> trục Z hướng lên) và sang chân của board "32F407 EVK V1.0" (I2C trên P0.10/P0.11, UART0 trên P3.1/P3.2,
> INT trên P2.2). Firmware đã biên dịch được bằng MDK-ARM 5.43 nhưng **chưa chạy trên board**. Các chỗ ghi
> "SPEC 2.x" và "Bước 4.x" bên dưới trỏ tới tài liệu cũ đã bỏ; nay là Phụ lục A.1 và A.9 của file chính.

```
test_sensor/
├── firmware/                  firmware test cho SN32F407 (Keil)
│   ├── board_port.h           giao diện phần cứng (hàm board_*)
│   ├── board_sn32f407.c       ← FILE DUY NHẤT CẦN SỬA: chân, GPIO, UART
│   ├── i2c_soft.c/.h          I2C bit-bang ~100 kHz + gỡ bus treo (9 xung SCL)
│   ├── mpu6050.c/.h           driver: init theo SPEC 2.1, đọc burst 14 byte, self-test
│   └── test_main.c            chạy T1..T7, rồi stream CSV 100 Hz
├── arduino/mpu6050_quick/     sketch Arduino để khoanh vùng lỗi module
└── tools/sensor_check.py      tool PC: chấm PASS/FAIL, 6 tư thế, vẽ realtime
```

---

## 1. Nối dây (module GY-521)

| GY-521 | SN32F407 | Ghi chú |
|---|---|---|
| VCC | 3V3 | Module có ổn áp, cấp 3,3 V hoặc 5 V đều được; I/O vẫn là 3,3 V |
| GND | GND | |
| SCL | chân `SCL_PORT/SCL_BIT` | Module đã có điện trở kéo lên |
| SDA | chân `SDA_PORT/SDA_BIT` | |
| INT | chân `INT_PORT/INT_BIT` | Dùng cho T6 và cho firmware chính |
| AD0 | GND | Địa chỉ 0x68. Để hở trên một số module cũng là 0x68, nối GND cho chắc |
| XDA, XCL | để trống | |

Chọn chân theo Phụ lục E của `PROJECT_MASTER.md` rồi ghi vào mục (1) của [board_sn32f407.c](firmware/board_sn32f407.c).
UART của MCU nối qua USB-UART lên PC, **460800 8N1** (SPEC 2.9).

---

## 2. Trình tự test (từ dễ đến khó)

### Bước A0 (khuyên dùng, 5 phút) — thử module bằng ESP32 + MicroPython
Chạy đủ T1..T7 giống firmware SN32, không cần Arduino IDE (chỉ cần `pip install esptool mpremote pyserial`).

| MPU6050 | ESP32 (DevKit/WROOM) | ESP32-S3 | ESP32-C3 |
|---|---|---|---|
| VCC | 3V3 | 3V3 | 3V3 |
| GND | GND | GND | GND |
| SCL | GPIO22 | GPIO9 | GPIO5 |
| SDA | GPIO21 | GPIO8 | GPIO4 |
| INT | GPIO4 | GPIO7 | GPIO6 |
| AD0 | GND | GND | GND |

```bash
cd test_sensor/esp32
python setup_esp32.py                                         # tự tìm COM, nạp MicroPython, chép script
python ../tools/sensor_check.py check --port COMx --baud 115200   # rồi nhấn EN/RESET trên ESP32
python ../tools/sensor_check.py orient --port COMx --baud 115200
python ../tools/sensor_check.py plot   --port COMx --baud 115200
```
Sửa [mpu6050_test.py](esp32/mpu6050_test.py) xong thì `python setup_esp32.py --copy-only` để chép lại.
Bản ESP32 dùng I²C phần cứng 400 kHz (đúng SPEC); cấu hình thanh ghi giống hệt bản SN32.

### Bước A (tùy chọn, 10 phút) — thử module bằng Arduino
Có Arduino/ESP32 thì làm trước để biết module tốt hay hỏng, tránh nghi nhầm firmware MCU.

1. Nạp [mpu6050_quick.ino](arduino/mpu6050_quick/mpu6050_quick.ino), nối dây như đầu file.
2. `python tools/sensor_check.py check --port COM7 --baud 115200`
3. T2, T3, T4 PASS và phần phân tích PASS (riêng `GYRO_BIAS` được phép WARN vì sketch không trừ offset) → module tốt.

### Bước B — chuẩn bị firmware trên SN32F407
Nối dây theo board "32F407 EVK V1.0" (Phụ lục E của file chính). Nhãn header đọc từ ảnh board trong
hướng dẫn EVK ([docs/datasheet/](../docs/datasheet/SONiX_32F407_EVK_Guide_Ver1.0_VN.pdf), hình 16):

| GY-521 / USB-UART | Header trên EVK | Ghi chú |
|---|---|---|
| SCL, SDA | J13: `SCL_P010`, `SDA_P011`, `GND` | Bus I²C có sẵn, kéo lên 10 kΩ, chung bus với EEPROM 0x50 |
| INT | J7: `P22` | |
| GND | GND của J13 | |
| VCC | điểm 3,3 V nào đó trên board | **Các header trong ảnh không có chân 3,3 V.** Tìm điểm 3,3 V trên sơ đồ EVK hoặc đo bằng đồng hồ trước khi cấp |
| RX / TX của USB-UART | J10: `UTX_P31` / `URX_P32`, `GND` | TX của MCU nối RX của USB-UART |

LED báo = D6 (P3.8), nút đánh dấu = phím SW3. Đổi chân ở mục (1) của
[board_sn32f407.c](firmware/board_sn32f407.c).

Thiết lập board theo mục 4.2.1 của hướng dẫn EVK: J5 nối `T_DATA`–`SWDIO_P35`, J4 nối `T_CLK`–`SWCLK_P36`,
J3 nối `T_VDD`–`32F407_VDD`, J1 nối `SW_ON_3.3V`–`32F407_VDD`, công tắc SW1 ở ON (LDO 3,3 V cấp cho MCU).
Cắm USB: LED D4 xanh là PC thấy mạch nạp SN-Link, D5 xanh là mạch nạp thấy MCU.
**Đo VDD của MCU = 3,3 V bằng đồng hồ trước khi nối cảm biến.**

Cách 1 — uVision, nạp luôn (đã build thử: 0 lỗi, 0 cảnh báo, Code 14.756 + RO 2.028 byte, RAM 548 byte):
mở [firmware/keil/mpu6050_test.uvprojx](firmware/keil/mpu6050_test.uvprojx), bấm Build rồi Download (F8).
Project này dựng từ project vòng 1 của nhóm trên cùng EVK, đã chọn SN-Link Debugger và thuật toán
nạp `SN32F400_32.FLM`, bật MicroLIB. Cần cài driver SN-Link cho Keil theo mục 3.2 của hướng dẫn EVK.

Cách 2 — dòng lệnh, chỉ để kiểm biên dịch:
```bash
bash test_sensor/firmware/build.sh      # ra firmware/build/mpu6050_test.hex, 13,6 KB Flash, 552 byte RAM
```

Firmware này chưa từng chạy trên board.

### Bước C — đọc báo cáo T1..T7
Mở terminal 460800 baud (hoặc dùng luôn bước D), **để cảm biến nằm yên trên bàn**, nhấn RESET:

```
# ===== MPU6050 TEST (VKU-NewBie) =====
# T1 BUS_IDLE      : SDA=1 SCL=1 -> PASS
# T2 I2C_SCAN      : 1 thiet bi: 0x68 -> PASS
# T3 WHO_AM_I      : 0x68 -> PASS
# T4 CONFIG        : 7 thanh ghi doc lai dung -> PASS
# T5 SELF_TEST     : AX+2.1% AY-1.3% AZ+0.8% GX+3.0% GY-2.2% GZ+1.1% (dat: |x|<=14%) -> PASS
# T6 SAMPLE_RATE   : INT: 200 xung/2s = 100.0 Hz -> PASS
# T7a GYRO_OFFSET  : gx=-41 gy=17 gz=-9 LSB (se tru o moi mau) -> PASS
# T7b ACCEL_1G     : |a|=4102 LSB = 1.00 g -> PASS
# T7c NOISE        : std|a|=9 std g=2/2/1 LSB -> PASS
# T7d TEMP         : 29.4 C -> PASS
# SUMMARY pass=10 warn=0 fail=0
# STREAM START (gyro da tru offset, int=pin)
# t_ms,ax,ay,az,gx,gy,gz,btn
51234,31,-12,4101,1,-2,0,0
...
```

| Test | Kiểm tra gì | Đạt khi |
|---|---|---|
| T1 BUS_IDLE | SDA, SCL ở mức 1 sau khi phát 9 xung gỡ treo | cả hai = 1 |
| T2 I2C_SCAN | quét 0x08..0x77 | thấy 0x68 |
| T3 WHO_AM_I | thanh ghi 0x75 | = 0x68 (0x70/0x71/0x72/0x98 → WARN: chip clone/MPU6500) |
| T4 CONFIG | reset chip, ghi bảng SPEC 2.1, **đọc lại từng thanh ghi** | khớp hết |
| T5 SELF_TEST | self-test nội của chip (rev 4.2 register map) | 6 trục trong ±14 % |
| T6 SAMPLE_RATE | đếm xung chân INT trong 2 s | 194..206 xung (100 Hz ±3 %) |
| T7a GYRO_OFFSET | trung bình 200 mẫu gyro (hiệu chuẩn Bước 4.1) | \|offset\| ≤ 328 LSB (±20 °/s) |
| T7b ACCEL_1G | độ lớn gia tốc khi nằm yên | 2048 ±10 % |
| T7c NOISE | độ lệch chuẩn khi nằm yên | std\|a\| < 20 LSB, std gyro < 3 LSB |
| T7d TEMP | cảm biến nhiệt | 0..60 °C |

T1–T4 lỗi là **lỗi nặng**: firmware in `FATAL` và tự thử lại mỗi 2 s, LED nháy nhanh → có thể vừa sửa dây vừa xem.
T5 chỉ WARN khi không đạt, vì nhiều module GY-521 dùng chip clone không qua self-test mà vẫn đo đúng — kết luận cuối dựa vào T7 và bước D.

### Bước D — chấm tự động trên PC
```bash
cd test_sensor/tools
pip install -r requirements.txt
python sensor_check.py check --port COM5            # rồi nhấn RESET trên board
```
Tool đọc báo cáo T1..T7, sau đó thu 10 s dữ liệu tĩnh và tính lại: tần số mẫu, khoảng hở `t_ms`
(mất mẫu), giá trị bão hòa/đứng yên, \|a\| ≈ 1 g, bias gyro sau hiệu chuẩn ≤ 1 LSB, nhiễu. In `KẾT LUẬN: PASS/WARN/FAIL`.

Board đang stream sẵn, không muốn reset: thêm `--no-header`. Chưa có board: thêm `--sim` thay cho `--port` để chạy thử tool.

### Bước E — kiểm tra chiều trục và ghi `AZ_dung_yen`
```bash
python sensor_check.py orient --port COM5
```
Lần lượt đặt 6 tư thế (±X, ±Y, ±Z hướng lên trời, theo mũi tên in trên module). Trục hướng lên
phải đọc ≈ +2048, hướng xuống ≈ −2048, hai trục còn lại ≈ 0 (sai số ≤ 0,1 g).
Bước cuối: gắn cảm biến lên mũ đúng như Phụ lục A.1 (Z lên trời, X về trước), đội mũ đứng thẳng → tool in giá trị
`AZ_dung_yen`, **ghi vào Phụ lục A.1 của file chính**.

### Bước F — xem tín hiệu realtime
```bash
python sensor_check.py plot --port COM5
```
Lắc, xoay, gõ nhẹ: accel và gyro phải phản ứng đúng trục, \|a\| ≈ 1 g khi đứng yên.

### Bước G — test dài 10 phút (tiêu chí Bước 4.1)
```bash
python sensor_check.py check --port COM5 --no-header --seconds 600 --save log_10phut.csv
python sensor_check.py analyze log_10phut.csv       # phân tích lại sau
```
Thêm `--moving` nếu trong lúc thu có cầm lên di chuyển (bỏ các kiểm tra "nằm yên").

### Bước H — soi bằng logic analyzer (khi có lỗi khó)
- Kênh 0 = SCL, kênh 1 = SDA, kênh 2 = INT; PulseView decoder **I²C**.
- Bản test chạy I²C ~100 kHz nên lấy mẫu ≥ 1 MHz là đủ.
- Đọc burst đúng: `START 0xD0(W) ACK 0x3B ACK RESTART 0xD1(R) ACK` + 14 byte, byte cuối NACK, `STOP`.
- INT: xung có chu kỳ **10,0 ms**.

---

## 3. Bảng tra lỗi

| Hiện tượng | Nguyên nhân hay gặp | Cách sửa |
|---|---|---|
| Không thấy gì trên terminal | UART chưa điền / sai baud / TX-RX chéo | Kiểm tra mục (3) board file; terminal 460800; TX MCU → RX USB-UART |
| T1 FAIL, SDA=0 | SDA chập GND, module chưa cấp nguồn, sai chân | Đo VCC module; đo SDA bằng đồng hồ khi rút MCU ra (phải ≈ 3,3 V) |
| T1 FAIL, SCL=0 | Sai tên thanh ghi GPIO, chân là chân nạp (SWD) | Xem lại macro `PIN_*`; chọn chân khác |
| T2: không thiết bị nào | Đảo SDA/SCL, lỏng dây, không có GND chung | Đảo lại SDA/SCL; nối GND |
| T2: thấy 0x69 | AD0 đang ở mức 1 | Nối AD0 xuống GND |
| T3: 0x70/0x71/0x72/0x98 | Chip MPU6500/clone | Dùng tạm được (WARN); nên mua module khác để giống lúc thu dữ liệu |
| T4: đọc lại sai | Chip chưa thoát sleep, nhiễu dây dài | Dây ngắn < 20 cm; tăng `I2C_HALF_US` lên 10 |
| T6: 0 xung, poll INT_STATUS = 200 | Dây INT chưa nối / sai chân | Kiểm tra chân INT; firmware vẫn stream ở chế độ poll |
| T6: ~2000 xung/2s | SMPLRT_DIV/CONFIG không đúng | Xem T4 |
| T7b: \|a\| ≈ 0 | Chip còn sleep | `PWR_MGMT_1 = 0x01` (T4 phải PASS trước) |
| T7b: \|a\| ≈ 4096 hoặc 8192 | Sai dải accel | `ACCEL_CONFIG = 0x18` (±16 g) |
| T7c WARN | Bàn rung, cầm trên tay khi reset | Đặt yên rồi RESET lại |
| `GAPS` FAIL (mất mẫu) | UART chậm, vòng lặp bị chặn | Baud 460800; dùng cổng USB-UART tốt (CP2102/CH340 đời mới/FT232) |
| Treo sau khi reset MCU giữa chừng | Bus I²C treo | T1 đã tự phát 9 xung SCL; nếu vẫn treo → rút nguồn module |

---

## 4. Lưu ý so với SPEC

1. **`INT_PIN_CFG` (0x37) = 0x30 chỉ ở bản test**: chốt mức INT đến khi MCU đọc dữ liệu, để
   firmware test poll được chân INT mà không cần cấu hình ngắt ngoài. Firmware chính (Bước 4.1)
   dùng ngắt cạnh lên nên để mặc định 0x00 (xung 50 µs) như SPEC 2.1 — không cần đổi SPEC.
2. **I²C ~100 kHz bit-bang** thay vì 400 kHz phần cứng: đọc 14 byte mất ~1,7 ms, vẫn dư trong 10 ms.
   Firmware chính dùng I²C phần cứng 400 kHz theo SPEC.
3. **Khoảng `t_ms` không phải lúc nào cũng đúng 10**: MPU6050 lấy mẫu theo dao động của chính nó
   (sai số ~±1 %), còn `t_ms` theo SysTick của MCU, nên thỉnh thoảng có khoảng 9 hoặc 11 ms dù
   không mất mẫu nào. Tool coi 9/10/11 ms là bình thường và chỉ báo **mất mẫu** khi khoảng ≥ 15 ms.
   Tiêu chí "không có khoảng hở `t_ms` nào khác 10 ms" ở Bước 4.1 nên hiểu theo nghĩa này —
   đề nghị nhóm cập nhật câu chữ trong tài liệu.
