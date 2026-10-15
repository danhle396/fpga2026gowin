# 2026-10-15 — Rà mọi lệnh ghi thanh ghi của firmware theo SVD và datasheet SN32F407 V2.2

Phần firmware chạm ngoại vi (`board.c`, `spi_fpga.c`, `i2c0.c`, `diag.c`) mới chỉ biên dịch, chưa chạy trên board. Tên thanh ghi lấy từ `SN32F400.h` của SONiX nên địa chỉ chắc chắn đúng. Thứ có thể sai là **giá trị ghi vào**.

**Công cụ mới `tools/svd_decode.py`:**
- Đọc `sdk/SN32F4_DFP/SVD/SN32F400.svd`.
- Tìm mọi lệnh `SN_X->REG = / |= …`, kể cả lệnh trải nhiều dòng, và tính giá trị hằng (có thay macro).
- In tên và giá trị của từng trường.
- Cảnh báo khi: ghi vào bit dự trữ, ghi vào trường chỉ đọc, giá trị vượt độ rộng trường, hoặc thanh ghi không có trong SVD.

Kết quả (`svd_decode_firmware.log`, `svd_decode_test_sensor.log`):
- Firmware chính: 39 lệnh ghi hằng, 19 lệnh có biến hoặc xóa bit, **0 cảnh báo**.
- Bộ test cảm biến: 12 / 1 / 0.

## Đối chiếu nghĩa từng giá trị với datasheet

SVD không ghi nghĩa từng giá trị, nên phần này tra datasheet.

| Lệnh | Datasheet | Kết luận |
|---|---|---|
| `SPI0->CTRL0 = DL 7 \| SELDIS`, MS = 0 | 14.9.1: MS = 0 là master; DL + 1 = 8 bit; FORMAT 0 = SPI | đúng |
| `SPI0->CTRL1 = 0` | 14.9.2: MLSB 0 = MSB trước; CPOL 0, CPHA 0 = mode 0 | đúng với A.7 |
| `SPI0->CLKDIV = DIV` | 14.9.3: SCK = PCLK / (2·DIV + 2) | đúng như chú thích |
| `UART0`: LC 0x83 → 0x03, DLL 13, FD = OVER8 | 16.7.11: MUL = MULVAL + 1, nên MULVAL = 0 → MUL = 1 hợp lệ; DIVADDVAL = 0 thì bộ chia phân số tắt; baud = 48 MHz / (8·13) = 461.538 (lệch +0,16 %) | đúng |
| PCLK của SPI0, UART0, I2C0 | 3.4.2: `APBCP1` chỉ có bộ chia cho I2C0, WDT, CLKOUT, reset đều /1; SPI0/UART0 lấy HCLK; `AHBCP` reset /1 | PCLK = 48 MHz, đúng giả định |
| `I2C0->TOCTRL = 0xFFFF` | 15.10.9: timeout = TO·32 chu kỳ PCLK = 43,7 ms | đúng như chú thích |
| `WDT`: TC 0xFF, CFG = WDTEN, khóa 0x5AFA | 12.3: TC 8 bit; timeout = T_WDT·128·(TC + 1); WDTIE = 0 → chế độ reset | đúng; chu kỳ xem dưới |

## Hai chỗ đã sửa

1. **I2C quá 400 kHz có thể xảy ra.**
   - Datasheet 15.10.7 ghi hai công thức không khớp nhau: `f = PCLK / (SCLHT + SCLLT)` và "thời gian cao = (SCLH + 1) chu kỳ".
   - Firmware ghi `half − 1 = 59`. Nếu công thức thứ nhất đúng thì SCL = 406,8 kHz, vượt chuẩn Fast-mode 1,7 %.
   - Nay ghi `half = 60`: ra 400 hoặc 393 kHz tùy công thức. 100 kHz vẫn vừa trường 8 bit (240).
2. **Chu kỳ WDT chưa chắc chắn.** `[CẦN XÁC MINH – nguồn: đo bằng lệnh w trên board]`
   - Datasheet ghi ILRC là 32 kHz (3.2.1, ví dụ 31,25 µs ở 12.3.2), nên timeout ≈ 1.024 ms.
   - Nhưng sơ đồ clock ở trang 19 ghi "ILRC 256KHz", tức timeout chỉ ≈ 128 ms.
   - Vòng chờ khi khởi tạo IMU lỗi trước đây feed mỗi 500 ms. Nếu ILRC thật là 256 kHz, chip sẽ tự reset liên tục khi chưa cắm cảm biến.
   - Đã sửa: feed mỗi 250 ms trong vòng đó.
   - Thêm lệnh **`w`** vào menu chẩn đoán: ngừng feed và in thời gian mỗi 20 ms, số in cuối trước khi chip khởi động lại là chu kỳ WDT. Đưa vào bước B2.
   - Nếu đo ra khoảng 128 ms thì còn phải xem lại các đoạn chặn dài khác, ví dụ I2C timeout 43 ms nhân nhiều lần.

Sau khi sửa:
- Keil `fw.uvprojx` (gồm cả dòng nhắc INT ở dưới): 0 lỗi, 0 cảnh báo, Code 15.360 + RO 1.680 byte (`keil_fw.log`).
- Thêm: vòng hiệu chuẩn gyro chờ ngắt INT (P2.2) không có thời hạn; dây INT chưa nối thì firmware đứng im không in gì. Nay in `# cho ngat INT cua MPU6050 (P2.2, J7)` mỗi 2 s (bước B5).
- `m0_test.py`: TẤT CẢ PASS. Các phần C thuần không đổi.

## Giới hạn

- Công cụ chỉ giải mã giá trị **hằng**. 19 lệnh có biến (CLKDIV, SCLHT, BSET/BCLR, IE…) đã rà bằng mắt cùng phép tính ở trên.
- Giá trị PFPA (chọn chân: UART0 = 0x0A, SPI0 = 0x2A, I2C0 = 0x0A) đã đối chiếu từ 12/10 (Phụ lục E).
