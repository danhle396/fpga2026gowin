<!-- Sinh tự động bằng tools/sync_spec.py từ Phụ lục A của PROJECT_MASTER.md. Đừng sửa tay: sửa Phụ lục A rồi chạy lại script. Khi hai bản khác nhau, Phụ lục A thắng. -->

## PHỤ LỤC A – SPEC v3 (LUẬT KỸ THUẬT)

### A.1 Cảm biến MPU6050

| Mục | Giá trị | Thanh ghi |
|---|---|---|
| Địa chỉ I²C | 0x68 (AD0 nối GND), `WHO_AM_I` = 0x68 | 0x75 |
| Đánh thức + clock | 0x01 | `PWR_MGMT_1` 0x6B |
| Bộ lọc DLPF | 0x03 (accel 44 Hz, gyro 42 Hz) | `CONFIG` 0x1A |
| Tần số mẫu | 0x09 → 1 kHz / 10 = **100 Hz** | `SMPLRT_DIV` 0x19 |
| Dải gyro | **0x18 → ±2000 °/s**, 16,4 LSB/(°/s) | `GYRO_CONFIG` 0x1B |
| Dải accel | **0x18 → ±16 g**, 2048 LSB/g | `ACCEL_CONFIG` 0x1C |
| Ngắt data-ready | 0x01 | `INT_ENABLE` 0x38 |
| Đọc dữ liệu | burst 14 byte từ 0x3B: AX AY AZ TEMP GX GY GZ, byte cao trước | 0x3B–0x48 |

**Gắn trên mũ:** đỉnh hoặc phía sau mũ, đệm xốp mỏng, **Z hướng lên trời, X hướng về trước** khi đội mũ đứng thẳng. `AZ_dung_yen = ______` (phải ≈ +2048). Đóng băng ở cổng G1.

### A.2 Tiền xử lý trên MCU

1. Mẫu thô `r[m]` ở 100 Hz, INT16; gyro đã trừ offset.
2. Giảm mẫu còn 50 Hz: `y[n] = (r[2n−2] + 3·r[2n−1] + 3·r[2n] + r[2n+1] + 4) >> 3`, với `r[−2] = r[−1] = r[0]`.
3. Lượng tử: `q = clamp((y + 2^(s−1)) >> s, −128, 127)`; gia tốc `s = ACC_SHIFT = 7`, gyro `s = GYR_SHIFT = 6`.

Một mức INT8 = 1/16 g và 3,90 °/s; bão hòa ở ±7,94 g và ±496 °/s. `>>` là dịch số học.
Tự kiểm gia tốc: `2048 → 16`, `−2048 → −16`, `16384 → 127`, `−16384 → −128`, `63 → 0`, `64 → 1`. Gyro: `1640 → 26`, `−1640 → −26`, `8192 → 127`, `31 → 0`, `32 → 1`.
Đáp ứng bộ lọc: −2,1 dB ở 12,5 Hz; −9,0 dB ở 25 Hz; −13,8 dB ở 30 Hz; −30,6 dB ở 40 Hz; triệt hoàn toàn ở 50 Hz.

### A.3 Cửa sổ

- Kênh `c = 0..5` ↔ `[AX, AY, AZ, GX, GY, GZ]`. Cửa sổ = 128 mẫu 50 Hz (2,56 s), `t = 0` cũ nhất.
- Cửa sổ mới sau mỗi **16** mẫu (0,32 s). `SEQ` 8 bit, tăng 1, quay vòng.
- Thứ tự byte ở mọi nơi (khung SPI, bộ đệm FPGA, mảng Python): `i = t × 6 + c`.

### A.4 Mạng và nhãn

| | N1 (tầng 1, đã có RTL) | N2 (tầng 2) |
|---|---|---|
| C1 | Conv 6→16, k = 5, pad 2 → requant + ReLU → MaxPool 2 → 64 × 16 | như N1 |
| C2 | Conv 16→32 → requant + ReLU → MaxPool 2 → 32 × 32 | Conv 16→16 → … → 32 × 16 |
| C3 | — | Conv 16→32 → … → 16 × 32 |
| Đầu ra | GAP: `(Σ_t a) >> 5` → Dense 32→4 | Flatten (`i = t × 32 + c`, 512 phần tử) → Dense 512→4 |
| Weight / bias / MAC | 3.168 / 52 / 225.408 | 6.368 / 68 / 227.328 |
| Mỗi ô thời gian nhìn | 16 mẫu = 0,32 s, sau đó mất thứ tự | 36 mẫu = 0,72 s, 16 ô giữ thứ tự |

Lớp: `0 = NORMAL`, `1 = IMPACT`, `2 = dự trữ`, `3 = FALL`. **Từ v3.2 chỉ huấn luyện 0 và 3**; 1 để dành (bật lại khi cần, không đổi RTL), đầu ra vẫn 4 logit. Lớp dự trữ: weight 0, bias −2^30.
`SCORE = clamp((logit_top1 − logit_top2) >> SCORE_SHIFT, 0, 127)`. Argmax: bằng nhau thì chọn chỉ số nhỏ.

**Nhãn cửa sổ.** Điểm sự kiện = mẫu có `|a|` lệch khỏi 1 g nhiều nhất trong đoạn nút đánh dấu được bấm; `p` là vị trí của nó trong cửa sổ. Với D1 không có nút đánh dấu: lấy trên cả bản ghi của một lần ngã (mỗi bản ghi chỉ chứa một sự kiện) và kiểm bằng mắt 20 bản ghi; các bản ghi hoạt động thường ngày của D1 cho toàn cửa sổ NORMAL.

| `p` | Nhãn |
|---|---|
| 56 .. 103 | Nhãn của sự kiện (FALL; IMPACT nếu bật lớp này) |
| 24 .. 55 hoặc 104 .. 127 | Bỏ khỏi tập huấn luyện |
| Còn lại, hoặc không có sự kiện | NORMAL |

Vùng dương rộng 48 mẫu = 3 bước, nên mỗi sự kiện có đúng 3 cửa sổ dương, với 0,48–1,42 s dữ liệu sau va chạm. Cửa sổ dương thứ hai kết thúc 0,80–1,10 s sau va chạm; thứ ba 1,12–1,42 s. Cộng ≈ 0,04 s cho lọc, truyền và suy luận.

### A.5 Số học (đúng như RTL hiện có)

| Đại lượng | Quy định |
|---|---|
| Đầu vào, weight | INT8 có dấu |
| Bias, accumulator, logit | INT32 có dấu |
| Phép nhân | 8 × 8 có dấu |
| Requant + ReLU | `acc ≤ 0 → 0`; ngược lại `min(acc >> n, 127)`. Dịch số học, **không làm tròn** |
| Activation | 0..127 |
| MaxPool 2 | Sau requant (hoặc trước, kết quả như nhau vì requant không giảm) |
| GAP (N1) | `(Σ 32 giá trị) >> 5`, lấy sàn |
| Logit gỡ lỗi | INT16: `clamp(logit >> LOGIT_SHIFT, −32768, 32767)` |

Muốn làm tròn thì `export_mem.py` cộng sẵn `2^(n−1)` vào bias; RTL không đổi.
Biên `|acc|` chưa kể bias: C1 487.680; Conv từ lớp 2 1.290.320; Dense 32 là 516.128; Dense 512 là 8.258.048.

### A.6 Bộ nhớ trên FPGA

Mọi mảng xếp **vị trí trước**: `địa_chỉ = vị_trí × số_kênh + kênh`.

| ROM | E1 (đã có) | E2 |
|---|---|---|
| Thứ tự weight Conv | `BASE + oc·(IC·5) + ic·5 + k` | `BASE + (g·5 + k)·IC + ic`, mỗi từ gồm P weight của kênh ra `g·P + p`, làn 0 ở byte thấp |
| Thứ tự weight Dense | `BASE + lớp·32 + đặc_trưng` | `BASE + g·F + i` |
| BASE của N1 | 0 / 480 / 3040 | P = 1: 0 / 480 / 3040 · P = 4: 0 / 120 / 760 |
| BASE của N2 | — | P = 1: 0 / 480 / 1760 / 4320 · P = 4: 0 / 120 / 440 / 1080 |
| Bias N1 | 0..15 / 16..47 / 48..51 | như E1 |
| Bias N2 | — | 0..15 / 16..31 / 32..63 / 64..67 |

RAM: bộ đệm đầu vào 768 × 8; hai RAM đặc trưng 2048 × 8 (E1) hoặc 1024 × 8 (E2).

### A.7 Giao tiếp MCU ↔ FPGA

**Dây:** SCK, MOSI, MISO, CS (thấp tích cực), IRQ (cao tích cực), RST_N (thấp tích cực), GND chung. Logic 3,3 V.
**SPI:** MCU master, mode 0, MSB trước. SCK 1 MHz khi thử, 4 MHz khi chạy; không vượt 4 MHz.

**Khung GHI, 772 byte trong một lần CS thấp:**

| Byte | Nội dung |
|---|---|
| 0 | `0xA5` — phải là byte đầu tiên sau khi CS xuống |
| 1 | `SEQ` |
| 2 .. 769 | 768 byte, `i = t × 6 + c` |
| 770, 771 | CRC-16 của byte 0..769, byte cao trước |

**Khung ĐỌC:** MCU kéo CS thấp, gửi `0x00`.

| Byte MISO | Nội dung |
|---|---|
| 0 | `0x5A` |
| 1 | `SEQ` của cửa sổ vừa xử lý |
| 2 | `STATUS`: bit0 = CRC_OK, bit1 = BUSY, bit2 = ERR (khung đến khi đang bận, hoặc thiếu byte). Hợp lệ khi bằng `0x01` |
| 3 | `CLASS` 0..3; `0xFF` nếu CRC khung ghi sai |
| 4 | `SCORE` 0..127 |
| 5, 6 | CRC-16 của byte 0..4 |
| *7 .. 14* | *4 logit INT16, byte cao trước* |
| *15 .. 17* | *`CYCLES` 24 bit* |
| *18, 19* | *CRC-16 của byte 7..17* |

Chế độ RUN đọc 7 byte; chế độ HIL đọc 20 byte. Không có kết quả mới thì MISO toàn 0.

**CRC-16/CCITT-FALSE:** đa thức 0x1021, khởi tạo 0xFFFF, không đảo bit, không XOR cuối; `"123456789"` → 0x29B1.
**IRQ:** lên CAO khi có khung kết quả (suy luận xong hoặc CRC khung ghi sai). Về THẤP khi MCU đã đọc xong byte thứ 7, hoặc khi RST_N thấp.
**Lỗi:** timeout 50 ms, CRC sai, `STATUS ≠ 0x01`, `SEQ` lệch → bỏ cửa sổ, đếm lỗi. 3 lỗi liên tiếp → RST_N thấp ≥ 1 ms, OLED hiện `ERR`.
**Một bộ đệm kết quả (làm rõ 14/10):** FPGA giữ đúng một khung kết quả; khung mới (kết quả hoặc lỗi) thay khung cũ chưa đọc. MCU chỉ gửi khung ghi mới sau khi đã đọc kết quả hoặc đã timeout. Khung đến khi CNN đang bận không ghi vào bộ đệm và trả `STATUS` = 0x07 (CRC_OK + BUSY + ERR); khung thiếu byte trả 0x04; CRC sai trả 0x00 với `CLASS` = 0xFF.

**Khung hiện có trong RTL (`PROTO = 1`, phương án lùi):** ghi `[A5][SEQ][768][CRC8]`, CRC-8 đa thức 0x07, khởi tạo 0, tính trên SEQ + dữ liệu; đọc `[5A][CLASS][SCORE 32 bit][CRC8]`, SCORE là logit lớn nhất.

### A.8 Type 2 và Safety FSM

**Khối** = 32 mẫu thô (0,32 s), tính ngay khi đọc mẫu: khối "bất động" khi `max − min` của cả 3 trục gia tốc < `T_STILL_A` và của cả 3 trục gyro < `T_STILL_G`. `still_run` = số khối bất động liên tiếp gần nhất. `az_tb` = (tổng AZ) >> 5.
**Bỏ phiếu:** `fall_votes` = số cửa sổ trong `VOTE_N` cửa sổ gần nhất có `CLASS = FALL` và `SCORE ≥ T_SCORE`.

| Chuyển trạng thái | Điều kiện |
|---|---|
| MONITOR → STANDBY | `WEAR = 0` (hệ thống TẮT bằng nút) liên tục 3 s |
| STANDBY → MONITOR | `WEAR = 1` (hệ thống BẬT) |
| MONITOR → SUSPECT | `fall_votes ≥ VOTE_K` và mũ đã được đội trong 3 s gần nhất |
| SUSPECT → PRE_ALARM | `still_run ≥ STILL_BLOCKS` và (nếu `TILT_EN`) **`\|az_tb\| < T_TILT`**: đầu nằm ngang, lệch 45°–135° khỏi phương thẳng đứng (v3.1, 15/10) |
| SUSPECT → MONITOR | Quá `SUSPECT_TIMEOUT` |
| PRE_ALARM → MONITOR | Bấm CANCEL |
| PRE_ALARM → ALARM | Hết `PRE_ALARM_TIME` |
| MONITOR, SUSPECT → ALARM | Giữ CANCEL 3 s (SOS) |
| ALARM → COOLDOWN → MONITOR | Giữ CANCEL 1 s; chờ `COOLDOWN_TIME` |

Từ SUSPECT trở đi bỏ qua WEAR. IMPACT khi đang đội (chỉ khi bật lớp này): một tiếng bíp + ghi log. Ưu tiên: CANCEL > timeout > phiếu CNN > khối.

**Nút (v3.2).** Chỉ có một nút. `pwr_btn.c` nằm ngoài FSM và tạo WEAR = trạng thái bật/tắt:
- cấp nguồn = BẬT;
- ở STANDBY, giữ ≥ 2 s = BẬT; lần nhấn này không đưa vào FSM;
- ở MONITOR, nhấn nhanh 2 lần (mỗi lần < 0,4 s, lần 2 bắt đầu < 0,6 s sau khi nhả lần 1) = TẮT;
- mọi cử chỉ khác đưa nguyên vào FSM như trên (giữ 3 s = SOS, nhấn ở PRE_ALARM = CANCEL, giữ 1 s ở ALARM).

Còi xác nhận: BẬT = 2 bíp 100 ms, TẮT = 1 bíp 600 ms. Còi theo trạng thái (`app_buzzer`): SUSPECT = bíp 400 ms mỗi giây suốt trạng thái (tối đa `SUSPECT_TIMEOUT_MS` 8 s; nhóm 28/10: nghi ngã, kể cả ngã nhẹ rồi ngồi/đứng dậy, cũng là ngã); PRE_ALARM = bíp 150 ms hai lần mỗi giây; ALARM = hú 350/500 ms. Chỉ là giao diện: chuyển trạng thái của FSM không đổi.

| Tham số | Giá trị đầu | Chốt ở |
|---|---|---|
| `T_SCORE`, `VOTE_K` / `VOTE_N` | theo validation; 2 / 3 | AI-10 |
| `T_STILL_A` / `T_STILL_G` | 300 LSB (≈ 0,15 g) / 250 LSB (≈ 15 °/s) | AI-10 |
| `STILL_BLOCKS` | 8 khối = 2,56 s | AI-10 |
| `T_TILT` | 1450 LSB (\|az_tb\| < 1450 ↔ đầu lệch 45°–135°; đầu thẳng hay lộn ngược khi cúi gập đều không tính là nằm) | AI-10 |
| `SUSPECT_TIMEOUT` | 8 s | — |
| `PRE_ALARM_TIME` / `COOLDOWN_TIME` | 10 s / 30 s | — |

### A.9 UART MCU ↔ PC (chỉ khi phát triển)

460800 baud, 8N1.
- **LOG** (giữ phím SW6 lúc khởi động): mỗi mẫu thô một dòng `t_ms,ax,ay,az,gx,gy,gz,btn,wear`.
- **TRC** (gửi `TRC\n`): như LOG, thêm `F,seq,crc` cho mỗi khung đã gửi.
- **HIL** (gửi `HIL\n`): PC gửi khung 772 byte; MCU trả 20 byte.
- **RUN** (mặc định): dòng sự kiện `t_ms,seq,class,score,state,err`.

Khoảng `t_ms` 9–11 ms là bình thường; mất mẫu là khoảng ≥ 15 ms.

Dữ liệu thô được định nghĩa bởi cảm biến và cấu hình A.1, không phụ thuộc mạch đọc. Vì vậy file LOG có thể do mạch ghi phụ (TH-12) tạo ra, miễn là cùng module cảm biến, cùng cấu hình thanh ghi, cùng vị trí gắn và cùng định dạng dòng; cột `wear` được phép thiếu.

### A.10 Tự kiểm khi bật nguồn

MCU tạo payload 768 byte bằng LFSR Galois 16 bit (đa thức 0xB400, mầm 0xACE1, mỗi byte dịch một bước và lấy 8 bit thấp), gửi với `SEQ = 0xEE`. Kết quả phải trùng `selftest_expect.h` do `export_mem.py` sinh cùng bộ weight.

### A.11 Nhận dạng tư thế (chỉ để hiển thị)

Chạy trên ESP32 (`firmware/src/posture.c`, gọi trong `hub_sample`), trên cùng mẫu thô 100 Hz (AX AY AZ, 2048 LSB/g; trục mũ X trước, Y trái, Z lên). **Không đưa vào Safety FSM, không đổi quyết định báo ngã.** Đáp án số nguyên: `ml/src/posture_model.py`; C phải trùng từng mẫu (`tools/m0_test.py`, mode 13).

| Tư thế | Mã | Điều kiện |
|---|---|---|
| Đứng thẳng | `DUNG` | đầu thẳng, đợt cử động gần nhất làm đầu lên ≥ 0,25 m (hoặc lúc bật) |
| Ngồi | `NGOI` | đầu thẳng, đợt cử động gần nhất làm đầu hạ ≥ 0,25 m (≥ 0,15 m nếu trong đợt có lúc đầu chốt NẰM) |
| Nằm ngửa (nằm thẳng) / nằm sấp | `NAM_NGUA` / `NAM_SAP` | đầu nằm, \|ax\| ≥ \|ay\|: ax > 0 ngửa, ngược lại sấp |
| Nằm nghiêng phải / trái | `NGHIENG_PHAI` / `NGHIENG_TRAI` | đầu nằm, \|ay\| > \|ax\|: ay > 0 phải, ngược lại trái |
| Cúi người | `CUI` | đầu không thẳng, không nằm |
| Đang di chuyển | `DI_LAI` | đầu thẳng, đợt cử động liên tục > 4 s (hết đợt → đứng) |

- **Hướng đầu:** trung bình khối 32 mẫu (mx, my, mz), gm = √(mx² + my² + mz²): mz·100 > 82·gm → THẲNG; mz·100 < 50·gm → NẰM; còn lại CÚI. Chốt khi 3 khối liên tiếp cùng kết quả.
- **Đợt cử động:** \| \|a\| − 2048 \| > 120 LSB trong 30 mẫu gần nhất. Trong đợt: v += \|a\| − g_yên, h += v (g_yên = trung bình \|a\| của mỗi khối 32 mẫu yên). Hết đợt: Δh = h − v·(n + 1)/2 (vận tốc 0 hai đầu); 1 m = 2048·10⁴/9,80665 đơn vị (0,25 m = 522.094; 0,15 m = 313.256; 1,5 m = 3.132.568). Đợt kết thúc khi đầu chưa thẳng thì chờ đầu chốt THẲNG mới quyết.
- **Dậy sau khi nằm ≥ 300 mẫu (3 s):** khi đầu chốt THẲNG lại (kể cả qua giai đoạn CÚI), Δh của đợt dậy < 1,5 m → NGỒI, ngược lại ĐỨNG.
- Căn bậc hai nguyên theo bit; mọi phép chia làm tròn về 0. Lúc bật: ĐỨNG.
- **Đo trên D1** (`tools/posture_eval.py`, mẫu 50 Hz lặp thành 100 Hz, tư thế ở cuối 1.844 bản ghi so với mô tả hoạt động): đứng 93,2 %, ngồi 82,0 %, nhận ra nằm 93,2 % (đúng cả hướng 79,9 %), tổng 85,8 %. Chưa đo trên mũ [CẦN XÁC MINH – nguồn: buổi thử trên mũ].

### Lịch sử thay đổi SPEC

| Ngày | Nội dung |
|---|---|
| 2026-10-03 | v1: đeo thắt lưng, 100 Hz, 3 lớp Conv |
| 2026-10-12 | v2: mũ, 50 Hz, 2 lớp Conv, kênh trước, UINT8 |
| 2026-10-12 | v3: lấy RTL hiện có làm gốc (vị trí trước, 0..127, dịch sàn); cảm biến 100 Hz ±16 g ±2000 °/s, MCU giảm còn 50 Hz; bước 0,32 s + bỏ phiếu; N1/N2; E1/E2; lớp 0 NORMAL, 1 IMPACT, 3 FALL; giao thức v3; bỏ CONFIRM, thêm SOS và tự kiểm |
| 2026-10-16 | **v3.2** (đi cùng đề cương v2.1): A.4 chỉ huấn luyện 2 lớp 0 NORMAL và 3 FALL, lớp 1 IMPACT để dành; A.8 đầu vào WEAR là trạng thái bật/tắt do một nút bấm tạo (`pwr_btn.c`), thêm quy ước nút. Không đổi khung, số học, FSM hay vector; mô hình đã có vốn là 2 lớp vì D1 không có IMPACT |
| 2026-10-15 | **v3.1**: A.8 điều kiện nghiêng thành hai phía `\|az_tb\| < T_TILT` (trước: `az_tb < T_TILT`). Lý do: phát lại D1 cho thấy 15/22 PRE_ALARM giả có `az_tb` ≈ −2040 (đầu lộn ngược khi cúi gập sau khi vấp, nhặt đồ), còn 375/375 cú ngã nằm tới PRE_ALARM có `az_tb` ≥ −1074. Không đổi khung, số học hay vector |
| 2026-10-25 | **v3.3**: thêm A.11 nhận dạng tư thế trên ESP32, chỉ để hiển thị. Không đổi A.1–A.10, khung, FSM hay vector |
| 2026-10-28 | v3.3 (làm rõ giao diện, không đổi FSM): A.8 ghi mẫu còi theo trạng thái; SUSPECT kêu suốt trạng thái |
| 2026-10-14 | v3 (làm rõ, không đổi số học hay khung): A.7 thêm quy ước một bộ đệm kết quả và giá trị `STATUS` cho từng lỗi; `cnn_params.vh` thêm `CNN_SCORE_SHIFT` (lấy từ `score_shift` trong json) |
