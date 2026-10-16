# Hướng dẫn đợt B — làm trên board thật, từng bước

Dành cho thành viên cầm board. Làm **đúng thứ tự**; xong mỗi bước, gửi lại cho trưởng nhóm (hoặc gửi AI) bằng lệnh `Cập nhật: B<số> ...` kèm số đo, ảnh hoặc file log ghi ở cột "Gửi lại". Bước nào không đạt Pass thì **dừng**, gửi `Kẹt: B<số> <triệu chứng>`, đừng làm bước sau.

Chuẩn bị:
- Máy có Keil MDK (`%LOCALAPPDATA%\Keil_v5`), Gowin EDA hoặc Gowin Programmer, Python 3 với `pyserial numpy` (`pip install pyserial numpy`).
- Đồng hồ vạn năng. Logic analyzer nếu có.
- Dây dupont cái–cái ≤ 15 cm.
- Terminal nối tiếp: PuTTY, Tera Term, hoặc `python -m serial.tools.miniterm COMx 460800`.

**An toàn điện:** chưa nối board với nhau khi chưa qua B1 và B6. Mọi lần nối dây đều rút nguồn trước và **nối GND trước tiên**.

---

## B1. Nguồn EVK — đo VDD (TH-02, E.4 bước 1)

1. Đặt jumper theo E.4: J5 `T_DATA`–`SWDIO_P35`, J4 `T_CLK`–`SWCLK_P36`, J3 `T_VDD`–`32F407_VDD`, J1 `SW_ON_3.3V`–`32F407_VDD`, SW1 ở ON.
2. Cắm USB của EVK. Quan sát LED D4 và D5.
3. Đo điện áp giữa chân `32F407_VDD` của J1 và GND (chân GND của J10 hoặc J12).

| Pass | Gửi lại |
|---|---|
| D4, D5 xanh; VDD = 3,30 ± 0,10 V | số đo VDD, ảnh jumper |

Chưa đạt: kiểm SW1 và jumper J1; **không** đi tiếp nếu VDD gần 5 V.

## B2. Nạp firmware chính, vào menu chẩn đoán (FW-03)

1. Mở `firmware/keil/fw.uvprojx`, bấm Build (F7), rồi Download (F8). Mạch nạp SN-Link đã chọn sẵn.
2. Nối terminal 460800 8N1 vào UART0. Cổng là header J10 `UTX_P31` / `URX_P32` / GND, qua mạch USB-UART 3,3 V: RX của mạch nối `UTX_P31`, TX của mạch nối `URX_P32`.
3. **Giữ phím SW3** rồi nhấn reset (hoặc cắm lại USB). Giữ đến khi thấy chữ.

Mong đợi:
```
# mu bao ho - firmware chinh (...)
hello SN32F407 EVK - firmware FW-03 (...)
HCLK = 48000000 Hz
CRC "123456789": hw=0x29B1 sw=0x29B1 PASS
CRC khung tu kiem SEQ=0xEE: hw=.... sw=.... PASS
lenh: h f c 1 4 p s t w q
```
4. LED D6 phải nháy 1 Hz. Nhấn/nhả SW3, SW6 thì terminal in `SW3 nhan` / `SW3 nha`.
5. Gõ `w`: firmware ngừng nuôi watchdog và in `wdt <ms>` mỗi 20 ms cho tới khi chip tự khởi động lại (màn hình lại hiện dòng `# mu bao ho`). **Ghi số `wdt` cuối cùng**: mong đợi khoảng 1.024 ms (ILRC 32 kHz). Nếu chỉ khoảng 128 ms thì báo lại (X16). Sau đó giữ SW3 + reset để vào lại menu.

| Pass | Gửi lại |
|---|---|
| có `hello`, HCLK = 48000000, hai dòng CRC đều PASS, LED nháy, đọc được hai phím, lệnh `w` làm chip tự khởi động lại | chép toàn bộ chữ trên terminal, kèm số `wdt` cuối |

Ghi chú: dòng CRC kiểm khối CRC phần cứng (X5). Nếu `hw` khác 0x29B1 mà `sw` đúng, vẫn đi tiếp được (firmware dùng được CRC phần mềm); ghi lại để sửa.

## B3. Flash SPI của EVK dùng chân chọn nào (E.4 bước 2, X2)

**Chưa nối FPGA.** Trong menu B2, gõ `f`.

Mong đợi: ba dòng `P1.8: JEDEC = .. .. ..`, `P2.8: ...`, `P2.9: ...`.

| Pass | Gửi lại |
|---|---|
| P2.8 và P2.9 đều "khong co flash" (P1.8 có hay không đều được) | ba dòng JEDEC |

Nếu P2.8 hoặc P2.9 "CO FLASH": **dừng**, gửi lại. Khi đó phải đổi CS/IRQ của FPGA sang P2.1/P2.3 trước khi nối dây.

## B4. Cảm biến MPU6050 (FW-02)

1. Rút USB. Nối MPU6050 vào J13: `SCL_P010` → SCL, `SDA_P011` → SDA, GND → GND; `P22` của J7 → INT; AD0 → GND.
2. **VCC 3,3 V:** header của EVK không có chân 3,3 V (X2c). Lấy ở chân `32F407_VDD` của jumper J1/J3 (đã đo ở B1) bằng dây cái kẹp vào chân jumper, **đo lại 3,3 V trước khi nối**. Không lấy 5 V nếu module không có ổn áp.
3. Nạp `test_sensor/firmware/keil/mpu6050_test.uvprojx`, rồi chạy `python test_sensor/tools/sensor_check.py check --port COMx`. Làm theo hướng dẫn trên màn hình: đặt yên, lật trục.

| Pass | Gửi lại |
|---|---|
| "KẾT LUẬN: PASS"; `\|a\|` ≈ 2048 ± 10 %; INT 200 xung / 2 s | toàn bộ chữ của `sensor_check.py` |

## B5. Firmware chính với cảm biến (FW-04, FW-05, FW-06)

1. Nạp lại `firmware/keil/fw.uvprojx`. Reset, **không** giữ phím, mũ (hoặc board) đặt yên 3 s.
2. Mong đợi lần lượt:
   - `# MPU6050 OK: WHO_AM_I=0x68, 7 thanh ghi doc lai dung`
   - `# gyro_off,a,b,c lam_lai=0`
   - `tu kiem FPGA (A.10): rc=1 ... FAIL` (đúng, vì chưa nối FPGA: timeout)
   - `# start`
   
   Rồi mỗi 0,32 s có một dòng kết quả với `err` = 1 (timeout) cho tới khi nối FPGA.
3. Gõ `LOG` và Enter: luồng mẫu 100 Hz. Ghi 10 phút bằng `python tools/logger.py --port COMx --subject s00 --activity bench --trial 1 --seconds 600` (tắt terminal trước).
4. **FW-05 (offset gyro dư):** board phải nằm yên suốt lúc ghi. Chạy `python tools/gyro_residual.py ml/data/raw/s00_bench_01.csv`. Ở chế độ LOG, gyro đã được trừ offset hiệu chuẩn lúc khởi động, nên trung bình 500 mẫu đầu của mỗi trục phải trong ±2 LSB. Dòng thứ hai in 500 mẫu lệch nhất trên cả 10 phút, dùng để xem độ trôi. (Lệnh `STAT` chỉ in bộ đếm `raw`, `lost`, `timeout`…, không in offset.)
5. Mở terminal lại, gõ `STAT`: `lost` phải bằng 0.

| Pass | Gửi lại |
|---|---|
| WHO_AM_I và 7 thanh ghi đúng; logger báo "mất 0 mẫu -> PASS" sau 10 phút; `gyro_residual.py` in PASS | dòng khởi động, kết quả logger, hai dòng của `gyro_residual.py`, dòng `STAT` |

Nếu `MPU6050 loi ... i2c=2` (timeout): hạ `I2C_HZ` trong `app_main.c` xuống 100000 rồi nạp lại.

Nếu dòng `# cho ngat INT cua MPU6050 (P2.2, J7)` lặp lại mỗi 2 s và không có dòng `# gyro_off`, nghĩa là I²C chạy được nhưng chân INT không có xung. Kiểm dây `P22` của J7 với INT của module.

## B6. Dò 6 chân J1 của Kiwi (TH-02, RA-02, E.4 bước 3)

**Chưa nối dây với MCU.** Nạp `rtl/pin_probe/pin_probe.fs` vào Kiwi (Gowin Programmer, SRAM mode). LED1 nháy chậm. Đo DC từng chân J1-3 … J1-8 so với GND (J1-1).

| Pass | Gửi lại |
|---|---|
| J1-3..J1-8 lần lượt ≈ 0,21 / 0,41 / 0,62 / 0,83 / 1,03 / 1,24 V; hoặc logic analyzer đếm 1..6 xung mỗi 8 ms | 6 số đo |

## B7. Bitstream chính và thông mạch SPI lần đầu (RA-04, FW-09 a)

1. Nạp `bitstreams/1_e1_proto1_sisfall/fpga_project.fs` vào Kiwi bằng Gowin Programmer; kiểm `SHA256.txt` trước. Đây là bitstream dựng sẵn với shift 8, giao thức PROTO 1 (RA-01). Không cần mở project hay chạy lại Run All. Đo J1-6 (MISO) và J1-7 (IRQ) ≤ 3,3 V (E.4 bước 4).
2. Rút nguồn cả hai board. Nối **GND trước**, rồi theo E.1:

   | MCU | FPGA |
   |---|---|
   | P1.0 `SCK_P10` | J1-4 |
   | P1.2 `MOSI_P12` | J1-5 |
   | P1.1 `MISO_P11` | J1-6 |
   | P2.8 `P28` | J1-3 (CS) |
   | P2.9 `P29` | J1-7 (IRQ) |

3. Cấp nguồn, giữ SW3 + reset để vào menu. Gõ lần lượt `p` (cho tới khi in `PROTO=1`), `1` (1 MHz), `s`.

| Pass | Gửi lại |
|---|---|
| `OK 100 / 100`, timeout 0, crc 0 | dòng thống kê; ảnh logic analyzer một vòng ghi + đọc (TH-05) nếu có |

Rồi gõ `4` (4 MHz) và `s`: vẫn phải 100/100.

## B8. Chạy cả chuỗi (FW-10, TH-07, FW-13)

1. Reset không giữ phím. Lúc này dòng tự kiểm phải là `tu kiem FPGA (A.10): rc=0 class=3  PASS`, đáp án nằm trong `firmware/src/selftest_expect.h` với weight SisFall của nhóm.
2. **FW-10:** `python tools/check_frames.py --port COMx --seconds 400 --out trc.log --proto 1` (cần ≥ 1.000 khung, khoảng 330 s).
3. **TH-07 / FW-13:** `python tools/hil_test.py --port COMx --n 500 --proto 1`.

| Pass | Gửi lại |
|---|---|
| check_frames: "CRC của MCU trùng Python: N/N", "mất 0 mẫu"; hil_test: "500 khớp golden, 0 sai" → **PASS** | hai dòng kết luận + file `trc.log` |

## B9. Nút bấm duy nhất: bật/tắt, CANCEL, SOS (đề cương v2.1, FW-14)

1. Rút nguồn. Nối nút nhấn ngoài (loại nhấn–nhả) **song song với phím SW3**: một chân vào P2.4, một chân vào GND. Nếu P2.4 không ra header thì hàn song song vào hai chân của SW3. Firmware mặc định đã bật tính năng (`BTN_POWER 1` trong `firmware/src/fw_config.h`); giữ `WEAR_PRESENT 0`.
2. Nạp `firmware/keil/fw.uvprojx`, reset không giữ phím. Terminal ở chế độ RUN in mỗi lần đổi trạng thái là `S,<t_ms>,<trạng thái>,<lý do>`.
3. Thử lần lượt, ghi các dòng `S,...`:

| Thao tác | Mong đợi |
|---|---|
| Cấp nguồn | `S,...,MONITOR,...` (hệ thống BẬT) |
| Nhấn nhanh 2 lần | 1 bíp dài; sau 3 s có `S,...,STANDBY,...`; LED 7 đoạn `oFF` |
| Ở STANDBY giữ 1 s rồi nhả | không đổi |
| Ở STANDBY giữ 2 s | 2 bíp ngắn, `S,...,MONITOR,...`; giữ tiếp tới 6 s vẫn MONITOR (không SOS) |
| Ở MONITOR giữ 3 s | `S,...,ALARM,...` (SOS); giữ 1 s nữa để tắt còi |

| Pass | Gửi lại |
|---|---|
| Đúng cả 5 dòng của bảng | các dòng `S,...` trên terminal |

---

## Sau đợt B

Khi B1–B8 đạt: cổng G0 và phần lớn G2 đóng được.

Việc tiếp theo cần người là **thu D2 đợt 1** (AI-05, không ai phải ngã), theo `docs/data_protocol.md`. Lý do: AI-09 / AI-10 chỉ chốt được khi có dữ liệu đội mũ. Trên D1, báo giả hiện là 1,26 lần/giờ (SPEC v3.1, N2), hoặc 0,88 lần/giờ khi thêm dữ liệu ngực và thắt lưng, so với chỉ tiêu ≤ 1. Các nguồn báo giả còn lại (nằm xuống giường, cúi gập) phải đo lại trên mũ.

Thư mục cần biết:
- `firmware/README.md`: lệnh firmware.
- `rtl/v3/`, `rtl/e2/`: giao thức v3 và engine nhanh, dùng sau khi PROTO 1 chạy được trên board.
- `docs/bao_cao/`: bằng chứng các bước đã làm trên máy.
