# MŨ BẢO HỘ PHÁT HIỆN TÉ NGÃ – Project Master
## Mạng 1D-CNN INT8 bằng RTL tự viết trên FPGA Gowin, MCU SONiX thu IMU và ra quyết định
### Target: một chiếc mũ bảo hộ chạy độc lập — người đội ngã và nằm bất động thì đếm ngược 10 s rồi hú còi; rơi mũ, va mũ, tháo mũ, sinh hoạt bình thường không báo động

**Platform:** Kiwi Primer 20K (GW2A-LV18PG256C8/I7) + SN32F407 (Cortex-M0, Flash 32 KB, RAM 8 KB) + MPU6050 | **Tool:** Gowin EDA V1.9.11.03 Education · Keil MDK-ARM Lite 5.43 (Arm Compiler 6.24) · Icarus Verilog · Python 3
**Goal (tầng 2, cam kết):** Recall FALL mức sự kiện ≥ 95 %, Macro-F1 ≥ 0,90, ≤ 1 báo giả/giờ, va chạm → SUSPECT ≤ 1,5 s, suy luận FPGA ≤ 6 ms, RTL khớp golden model 100 % trên ≥ 2.000 cửa sổ.

> **TRẠNG THÁI (2026-10-15): Tầng 1 · chưa qua cổng G0 → 0 % theo cổng.** Mọi việc không cần board của tầng 1 và phần lớn tầng 2 đã xong ở mức mô phỏng; **chưa dòng nào chạy trên board**
> - **RTL:** E1 (P = 1, N1) khớp golden 50/50 có bão hòa, 13,96 ms, Fmax 105,20 MHz (15/10, sau khi sửa lỗi `conv_start` khởi tạo bằng 1 mà mô phỏng netlist tìm ra; bitstream 1, 2 đã dựng lại). **Giao thức v3** (`rtl/v3/`, RA-03 [x]) qua chân SPI 50/50 + 7 kịch bản lỗi. **Engine E2** (`rtl/e2/`, RB-03/RB-04/RA-07/RA-08 [x] mô phỏng): 12 cấu hình 50/50 ở mọi tầng; N2-S 2,65 ms (P = 1) / 0,80 ms (P = 4); top v3 + E2 105,58 MHz, Logic 8 %. Bitstream dựng sẵn để nạp thẳng: [bitstreams/](bitstreams/README.md) (PROTO 1 + E1 cho đợt B; v3 + E1; v3 + E2 + N2 11 người 98,12 MHz, 16/10). Mô phỏng ghép firmware ↔ RTL: 423/423 khung khớp golden. **Netlist sau P&R của cả 3 bitstream (mô phỏng gate-level, `rtl/gl/run_gl.sh`): PASS** sau khi sửa lỗi `conv_start` lên nguồn bằng 1, lỗi mà chỉ mô phỏng netlist mới thấy; phép âm lật 1 bit weight → FAIL. Verify toàn dự án sau khi dọn 15/10: mọi bộ kiểm PASS ([docs/bao_cao/2026-10-15_verify_sau_don/](docs/bao_cao/2026-10-15_verify_sau_don/README.md))
> - **SPEC v3.1 (15/10):** điều kiện nghiêng hai phía `|az_tb| < T_TILT` → báo giả khi phát lại D1 giảm từ 5,9 xuống 1,3/giờ (gộp 3 mô hình: 0,75/giờ), recall ngã nằm giữ 95,5 %
> - **Đề cương v2.1 (16/10): gọn đề tài** theo hướng tham khảo: mạng **2 lớp NORMAL / FALL**; va đập mũ loại bằng trình tự ba pha của FSM (bất động + đầu nằm ngang + 10 s hủy); **một nút bấm** (giữ 2 s = bật, nhấn nhanh 2 lần = tắt, CANCEL, SOS; `firmware/src/pwr_btn.c`) thay cảm biến đội mũ; huấn luyện chỉ bằng D1, D2 + D3 gộp thành một buổi thử nhỏ (≥ 20 cú ngã, ≥ 2 giờ đội mũ từ ≥ 2 người, 20 va mũ, 20 rơi mũ); LED 7 đoạn thay OLED. Không đổi phần cứng, RTL, khung, FSM. [THAY_DOI mục Điều chỉnh v2.1](THAY_DOI_SO_VOI_v1.md)
> - **AI:** D1 **11/17 người** từ 16/10 (101–110, 203; 1.180 cú ngã, 109.970 cửa sổ; [d1_11_nguoi](docs/bao_cao/2026-10-16_d1_11_nguoi/README.md)). **Nhóm quyết: chỉ kênh đầu, mạng 2 lớp NORMAL / FALL (SPEC v3.2), mô hình phần cứng N2 trên E2 (bitstream 3)**; N1/E1 chỉ để thông mạch SPI ở B7. **Số mới nhất, D1 11 người (16/10 tối), N2 chỉ đầu, LOSO, TB 3 seed: Macro-F1 0,983, recall sự kiện 99,6 %; FSM v3.1 T_SCORE 8: ngã nằm → PRE_ALARM 96,2 %, PRE_ALARM giả 1,11/giờ** (toàn bộ từ 815 "nằm xuống giường"; gộp 3 seed 95,6 % / 0,74; T_SCORE 16 thì ≤ 0,92/giờ nhưng ngã nằm 92–94 %); trễ PRE_ALARM khi nằm yên trong 2 s: p90 4,32 s, 0 cú > 5 s ([n2_11_nguoi](docs/bao_cao/2026-10-16_n2_11_nguoi/README.md)). 8 người: 0,977 / 99,6 %; 96,3 % / 0,68/giờ ([ai09_8_nguoi](docs/bao_cao/2026-10-16_ai09_8_nguoi/README.md)). N1 trên 8 người: 0,842 / 87,0 % → không đạt. Dữ liệu ngực + thắt lưng: có lợi trên 6 người (15/10) nhưng hết lợi trên 8 người (Macro-F1 0,970 so với 0,977, phiếu nhầm gấp đôi) → **bỏ**. Lịch sử 6 người (13–15/10): N2 0,968 / 98,7 %, PRE_ALARM giả 1,26/giờ. X15 đã đo: nhánh "bất động dù đầu thẳng" báo nhầm cả ngã đã đứng dậy → không thêm. **Bitstream 3 dựng lại 16/10 với N2 11 người** (`ml/out/n2_11_d1`, seed 20261014): `tb_e2` 50/50, netlist sau P&R PASS, Fmax 98,12 MHz. Chưa có buổi thử trên mũ (D2 + D3 gộp theo đề cương v2.1); chỉ tiêu ≤ 1 báo giả/giờ cần xác nhận trên mũ
> - **FW:** [firmware/](firmware/README.md) đủ chức năng tầng 1 (RUN/LOG/TRC/HIL/DIAG, tự kiểm A.10, watchdog), Keil 0 lỗi, 16 KB / 32 KB Flash, 5,4 KB / 8 KB RAM. Phần C thuần (tiền xử lý, khung, FSM, lõi vòng lặp, CNN MCU-only) chạy mã máy Cortex-M0 trong Unicorn và **trùng golden từng byte / từng lần đổi trạng thái**; phần chạm ngoại vi mới chỉ biên dịch. Công cụ đợt B sẵn: `check_frames.py`, `hil_test.py`, `logger.py`, `sensor_check.py`
> - Chân: SPI trên J12 (P1.0/P1.1/P1.2), CS P2.8, IRQ P2.9 (J7), I²C J13; FPGA J1-3..8 (+ RST_N J1-8 ở top v3). **Chưa đo trên board**; đo VDD = 3,3 V trước khi nối
> - **G0 còn thiếu:** FW-02, FW-03 (cần board), TH-01..03. RB-01 xong 15/10: `run_all` 7/7 PASS trên cả Icarus 0.9.7 và 12.0 (máy thứ hai; bitstream 1 dựng lại ở đó trùng từng dòng, [may2_icarus12](docs/bao_cao/2026-10-15_may2_icarus12/README.md))
> - **Bước tiếp theo NGAY (đợt B):** (1) jumper EVK, đo VDD, nạp `firmware/keil/fw.uvprojx` (giữ SW3 để vào menu), gõ `c` rồi `f` — FW-03, X2, X5; (2) nạp bộ test cảm biến, `sensor_check.py` — FW-02; (3) nạp `rtl/pin_probe`, dò J1 — TH-02. Song song: thu D2 đợt 1 (AI-05) để chốt AI-09/AI-10

**Tài liệu và thứ tự ưu tiên khi mâu thuẫn:** [DE_CUONG_v2.md](DE_CUONG_v2.md) (cam kết với BTC) → **file này** (Phụ lục A là SPEC v3, là luật). Khác biệt so với đề cương đã nộp nằm ở [THAY_DOI_SO_VOI_v1.md](THAY_DOI_SO_VOI_v1.md). Hai tài liệu cũ chứa SPEC v1 và v2 (`cac_buoc_xay_dung_de_tai.md`, `yeu_cau_cong_viec.md`) đã được bỏ ngày 2026-10-12 vì mâu thuẫn với RTL đang chạy; mục 3.1 giữ lại phần đánh giá chúng.

---

## 1. Tóm tắt một trang

**Hệ thống làm gì.** MPU6050 gắn trên mũ đo 6 trục ở 100 Hz. MCU lọc và giảm còn 50 Hz, đổi về INT8, giữ cửa sổ 2,56 s. Cứ 0,32 s MCU gửi một cửa sổ sang FPGA. FPGA chạy mạng 1D-CNN và trả lớp NORMAL / IMPACT / FALL kèm độ tin cậy. MCU cần 2 trong 3 cửa sổ liên tiếp báo FALL mới nghi ngã, rồi chờ người nằm bất động 2,56 s với đầu nằm ngang (lệch 45°–135° khỏi phương thẳng đứng) mới đếm ngược 10 s và hú còi.

```
MPU6050 ─I²C 100 Hz─► MCU: lọc [1,3,3,1]/8 ↓2 ─► INT8 ─► ring 128×6 ─SPI 772 B / 0,32 s─► FPGA: 1D-CNN INT8
                       │  (Type 2, mỗi 0,32 s)                                              │ IRQ + SPI 7 B
                       ├─► khối bất động + độ nghiêng đầu ──┐                               ▼ (CLASS, SCORE)
                       └─► WEAR, CANCEL/SOS ────────────────┴─► bỏ phiếu 2/3 ─► Safety FSM ─► OLED, còi, LED
```

**Ba tầng tham vọng** (tầng dưới chạy trước; mỗi tính năng tầng 2–3 có công tắc tắt):

| Tầng | Nội dung | FPGA | Mạng |
|---|---|---|---|
| **1 – LÕI** | Mũ chạy độc lập: ngã + bất động → PRE_ALARM → ALARM, bấm CANCEL | Engine **E1** hiện có, P = 1, 14 ms | **N1**: 2 Conv + GAP (đã có RTL) |
| **2 – MẠNH** | Đạt mọi chỉ tiêu trong đề cương v2 | Bước 1: **E1 mở rộng** để chạy N2 (≈ 14 ms). Bước 2: engine **E2**, 1 chu kỳ/MAC, ≤ 6 ms | **N2**: 3 Conv + Flatten-Dense |
| **3 – ĐỘT PHÁ** | P = 4 (≤ 2 ms), Fmax ≥ 100 MHz, năng lượng/lần suy luận, lớp suýt ngã, cập nhật weight qua SPI, log Flash, chỉ suy luận khi có chuyển động | E2 nhiều làn | N2 mở rộng |

**Các con số cốt lõi**

| Thông số | Giá trị |
|---|---|
| Cảm biến | 100 Hz, DLPF 44 Hz, ghi thô ±16 g / ±2000 °/s |
| Đầu vào mạng | 50 Hz, 128 mẫu × 6 kênh = 768 byte INT8 (2,56 s) |
| Bước suy luận | 16 mẫu = 0,32 s (mỗi sự kiện được nhìn 3 lần) |
| N1 / N2 | 3.168 / 6.368 weight · 225.408 / 227.328 MAC |
| Thời gian suy luận | Đo trong mô phỏng: E1 + N1: 13,96 ms · E2 + N2: 5,15 ms (P = 1), 1,50 ms (P = 4) · **E2 + N2-S: 2,65 ms (P = 1), 0,80 ms (P = 4)** (14/10) |
| Lớp | **Cam kết 2 lớp (v2.1, 16/10): 0 NORMAL · 3 FALL.** 1 IMPACT và 2 suýt ngã để dành cho mở rộng; phần cứng vẫn xuất 4 logit |
| Dữ liệu | **D1** công khai, cảm biến ở đầu, 25 Hz: FALL + NORMAL, nguồn huấn luyện duy nhất (v2.1) · **D2** NORMAL khi đội mũ + va/rơi mũ và **D3** ngã trên đệm: gộp thành một buổi thử trên mũ, chỉ để kiểm tra |

---

## 2. Hiện trạng đã kiểm chứng (2026-10-12)

Tôi đã chạy lại các phép kiểm dưới đây trên máy này; số liệu là số đo, không phải ước tính.

| # | Tài sản | Đã kiểm thế nào | Kết quả |
|---|---|---|---|
| H1 | RTL `Kiwi20K_FallDetection_FPGA` (cnn_core, P = 1) | Icarus, 20 vector của `golden_vectors.npz` | **20/20 khớp khi shift = (8, 8)**; 0/20 khi shift = (7, 8). Ngày 14/10: `fpga_top.v` và testbench lấy shift từ `src/cnn_params.vh` sinh từ `quant_params.json`; testbench 20 vector của project in 20/20 ([docs/bao_cao/2026-10-14_ra01_conv1_shift/](docs/bao_cao/2026-10-14_ra01_conv1_shift/README.md)) |
| H2 | Thời gian suy luận E1 | Đếm chu kỳ trong mô phỏng | 699.800 chu kỳ = 13,96 ms ở 50,143 MHz (≈ 3 chu kỳ mỗi MAC). Trước ngày 13/10 là 699.798; `argmax` 2 tầng thêm 2 chu kỳ |
| H3 | Tài nguyên, timing | Chạy P&R với chân cố định trên J1 và shift (8, 8); báo cáo ở `docs/bao_cao/2026-10-14_ra01_conv1_shift/` (14/10) và `bitstreams/1_e1_proto1_sisfall/fpga_project.rpt.txt` (15/10; máy thứ hai dựng lại 16/10 ra cùng số) | Hiện tại (bitstream 1): **Logic 907/20.736 (5 %), Register 589, BSRAM 6/46 (14 %), DSP 1,25/24, Fmax 105,20 MHz** (3 tầng logic). Diễn biến: 57,35 MHz khi công cụ tự đặt chân (05/10) → 53,60 MHz khi cố định chân → 101,86 MHz sau khi tách `argmax4` thành 2 tầng (13/10; Logic 923, FF 590) → 108,49 MHz khi chỉ đổi hằng shift 7 → 8 (14/10; phần chênh chủ yếu do đặt và đi dây khác nhau giữa hai lần chạy) → **Logic 907, 105,20 MHz** sau khi thêm giá trị khởi tạo cho các thanh ghi điều khiển (15/10, [loi_init_conv_start](docs/bao_cao/2026-10-15_loi_init_conv_start/README.md)) |
| H4 | Công suất | Báo cáo Gowin, toggle mặc định | 156,5 mW (tĩnh 122,8 + động 33,7). Là ước lượng của công cụ, chưa đo |
| H5 | Mô hình SisFall của nhóm | Golden model số nguyên trên tập test (3.549 cửa sổ, 6 người lạ) | INT8 shift (8, 8): accuracy 94,39 %, Macro-F1 0,845, recall FALL 96,71 %. FP32 nhóm báo: 94,73 % / 0,801 / 98,76 %. Với shift (7, 8): recall FALL 97,78 % |
| H6 | Golden model SPEC v3 + mô hình địa chỉ engine E2 | `verify_spec_v3.py` | Tất cả PASS: N1 khớp 20/20; E2 (P = 1, 2, 4) khớp golden cho N1 và N2; tiền xử lý; CRC; khung |
| H7 | Cảm biến | Nhóm báo ngày 12/10; mã và log chưa có trong thư mục | Đọc và kiểm tra được MPU6050 trên ESP32 và trên SN32F407 bằng mã riêng của một thành viên. Chưa đối chiếu được tần số, thang đo, chân. Mã `test_sensor/firmware` trong thư mục chưa chạy trên board |
| H8 | Board MCU | Datasheet V2.2 trong `docs/datasheet/`; ghi chú phần cứng của dự án vòng 1 (`D:\hoctap\fpga\thi_fpga\MCU\docs\`) | Board thật là "32F407 EVK V1.0": LED 7 đoạn ở P0.0–P0.7 và P1.9–P1.12, phím ma trận ở P1.4–P1.7 / P2.4–P2.7, I²C0 ở P0.10/P0.11 kèm EEPROM 24C05, UART0 ở P3.1/P3.2, còi P3.0, LED P3.8. Khối CRC phần cứng tính đúng CRC-16/CCITT-FALSE. SPI0, I2C0, UART0 mỗi tín hiệu có 4 lựa chọn chân. Sơ đồ Start-Kit trong `sdk/` không phải board này |

**Lỗi và rủi ro tìm thấy trong bản RTL hiện có** (việc sửa ở mục 6, nhánh RTL-A):

| # | Vấn đề | Hậu quả | Sửa |
|---|---|---|---|
| R1 | `conv1_shift` = 7 trong top/testbench, = 8 trong `quant_params.json` | Bitstream hiện tại tính khác mô hình | **Đã sửa 14/10:** `cnn_params.vh` sinh từ `quant_params.json` bằng `tools/gen_cnn_params.py`; script dừng nếu golden không khớp 20/20 (RA-01) |
| R2 | Chân SPI/IRQ chưa ràng buộc; công cụ tự đặt K14, R16, M10, K15, K11 ở LVCMOS18 | Không nối được với MCU 3,3 V | **Đã sửa 13/10:** 5 chân trên J1, LVCMOS33, đã qua P&R (Phụ lục E.3). Còn dò chân trên board (RA-02) |
| R3 | `packet_parser` không đồng bộ lại theo CS | Một khung thiếu byte làm lệch mọi khung sau | **Đã sửa 14/10 trong `rtl/v3/` (RA-03):** CS lên giữa khung → STATUS 0x04, khung sau vẫn đúng |
| R4 | Không chặn khung đến khi đang suy luận | Ghi đè bộ đệm vào giữa lúc tính | **Đã sửa 14/10 trong `rtl/v3/` (RA-03):** khung đến khi bận không ghi bộ đệm, STATUS 0x07; khung đang tính vẫn ra đúng |
| R5 | `crc_error` và `sequence` không được dùng | CRC sai thì MCU chỉ biết qua timeout; không đối chiếu được kết quả với cửa sổ | **Đã sửa 14/10 trong `rtl/v3/` (RA-03):** khung kết quả có SEQ, STATUS; IRQ cả khi CRC sai |
| R6 | `argmax4` thuần tổ hợp nối thẳng vào thanh ghi kết quả | Fmax chỉ 53,60 MHz khi chân đã cố định | **Đã sửa 13/10:** `argmax4` 2 tầng thanh ghi, vẫn khớp 20/20, Fmax 101,86 MHz |
| R7 | 3 trạng thái cho mỗi MAC | 14 ms thay vì ≈ 5 ms | **Đã có trong mô phỏng 14/10:** engine E2 (`rtl/e2/`), N2 5,15 ms, N2-S 2,65 ms, khớp golden ở mọi tầng; chưa chạy trên chip |
| R8 | `run_golden_sim.bat` dùng `-g2012`; máy này có Icarus 0.9.7 chỉ nhận `-g2001` | Script báo lỗi trên máy cũ | **Đã sửa 14/10:** `-g2001 -I src`, testbench viết theo Verilog-2001 (RA-01) |
| R9 | 20 vector kiểm đều là nhãn NORMAL, biên độ −73..57 | Không phủ FALL, không phủ bão hòa | **Đã sửa 14/10 (AI-04):** `tools/export_mem.py` sinh 50 vector gồm FALL, toàn ±127, toàn 0, LFSR, gyro bão hòa; RTL E1 với weight SisFall khớp golden **50/50**, 699.800 chu kỳ mỗi lần |
| R10 | Không có đầu vào reset, không có file `.sdc` | Không khôi phục được từ MCU | **Đã sửa 14/10 ở mức P&R:** `rtl/v3/top.sdc`, `fpga_top_v3.sdc`; `fpga_top_v3` có `rst_n` (J11), `tb_proto` kiểm RST_N |
| R11 | MISO đổi sau cạnh xuống SCK khoảng 3 chu kỳ clock (≈ 68 ns) | SCK 8–10 MHz như README ghi sẽ sai | Giới hạn SCK ≤ 4 MHz (A.7) |

---

## 3. Quyết định thiết kế

### 3.1. Đánh giá đề cương v1 và SPEC v2

**Điểm mạnh giữ lại:** ý tưởng mũ + lớp IMPACT + cảm biến đội mũ; chỉ tiêu có cách đo; golden model làm chuẩn; MCU chỉ đọc theo IRQ; khung 772 byte.

**Bảy mục phải kiểm:**

| Mục | Kết luận | Xử lý trong v3 |
|---|---|---|
| Buffer HIL 772 B so với `ring` 768 B | **Lỗi thật của SPEC v2**: "dùng lại `ring` làm buffer 772 byte" tràn 4 byte | Chỉ 768 byte payload vào `ring`; byte lệnh, SEQ và 2 byte CRC giữ ở 4 biến riêng (FW-13) |
| `mac.v` mẫu 24 bit so với SPEC 32 bit | Với mạng v2, biên lớn nhất 1.290.320 nên 24 bit vừa; SPEC v2 ghi 32 bit mà không chứng minh. RTL thật của nhóm đã dùng 32 bit | N2 có Dense 512 đầu vào: biên 8.258.048, chỉ còn dư 1,6 % so với 2^23 → **bắt buộc 32 bit**. `export_mem.py` kiểm biên cho từng mô hình |
| Khối bất động cần INT16 trong khi `ring` lưu INT8; RAM 8 KB | SPEC v2 đúng ý (tính trực tuyến) nhưng viết mơ hồ; ngưỡng 600 LSB không thể tính trên INT8 | Viết rõ: tính trên mẫu thô lúc vừa đọc, chỉ giữ 12 giá trị min/max + 1 tổng (28 byte). Ngân sách RAM ≈ 2,6 KB / 8 KB (4.3) |
| Độ trễ va chạm → SUSPECT | v2 ghi 1,42 s nhưng chỉ tính vị trí cửa sổ. Cộng lọc, truyền, suy luận ≈ 1,46 s, không còn dư; chỉ có **một** cửa sổ hợp lệ, trượt một cửa sổ là 2,7 s | Bước 0,32 s, 3 cửa sổ hợp lệ, bỏ phiếu 2/3: danh định ≤ 1,14 s; trượt một cửa sổ vẫn ≤ 1,46 s |
| Vùng tiếp nhận 0,32 s có tách được FALL và IMPACT | Không đủ về nguyên lý: khác biệt nằm ở trình tự "đứng → va chạm → nằm" dài hơn 1,5 s; GAP xóa thứ tự. Thêm nữa, nhãn v2 cho phép chỉ 0,16 s sau va chạm | N2: mỗi ô thời gian nhìn 0,72 s, Dense nhìn cả 16 ô theo thứ tự; nhãn bảo đảm ≥ 0,48 s sau va chạm. So N1 với N2 bằng dữ liệu (AI-09) |
| Ngưỡng tài nguyên so với GW2A-18 thật | Chip: 20.736 LUT, 15.552 FF, 46 BSRAM, 24 khối DSP. Bản hiện có dùng 5 % / 14 % / 5 %. Ngưỡng v1 (LUT < 30 %, DSP ≤ 35 %) quá rộng. Fmax của E1 là 53,60 MHz khi chân đã cố định và 101,86 MHz sau khi tách `argmax`; **engine E2 chưa có nên chưa có số đo** | Cam kết Logic ≤ 20 %, BSRAM ≤ 25 %, DSP ≤ 25 %, Fmax ≥ 55 MHz; 100 MHz để ở tầng 3 cho tới khi E2 có số đo |
| 9 điểm lệch ở Phụ lục B của SPEC v2 | Xem bảng dưới | — |

| # | Điểm lệch v2 so với v1 | Phán quyết v3 |
|---|---|---|
| 1 | DLPF 21 Hz ở 50 Hz | **Thay**: cảm biến 100 Hz / 44 Hz, MCU lọc rồi giảm mẫu. Chống aliasing tốt hơn và giữ được dữ liệu thô |
| 2 | Đọc theo ngắt data-ready | Giữ (đã PASS ở 100 Hz) |
| 3 | Requant chỉ dịch bit, DSP = P | Giữ, nhưng theo đúng số học của RTL hiện có: dịch lấy sàn, kẹp 0..127 |
| 4 | Khung 7 byte + 13 byte đuôi | Giữ |
| 5 | Một bộ đệm + BUSY/ERR | Giữ; RTL hiện có chưa có phần chặn (R4) |
| 6 | Hủy khi 2 khối có cử động | **Đơn giản hóa**: bỏ trạng thái CONFIRM, chỉ dùng timeout 8 s |
| 7 | Chỉ xét WEAR trước SUSPECT | Giữ |
| 8 | Bất động = max − min | Giữ, tính trên mẫu thô 100 Hz |
| 9 | Testbench Verilog bắt buộc | Giữ |

**Lỗi của chính SPEC v2 (do tôi viết khi chưa biết có RTL):** bố trí "kênh trước", activation UINT8 và làm tròn đều **trái với RTL đang chạy đúng** của nhóm; cấu hình cảm biến 50 Hz trái với cấu hình đã kiểm. SPEC v3 lấy RTL hiện có làm gốc.

### 3.2. Ba hướng và lựa chọn

| Tiêu chí | A. Thận trọng: giữ nguyên bản hiện có | **B. Cân bằng: tiến hóa (chọn)** | C. Tham vọng: viết lại toàn bộ |
|---|---|---|---|
| Nội dung | E1 + N1, bước 1,28 s, FSM cơ bản | Tầng 1 = E1 + N1; tầng 2 = E2 + N2, bước 0,32 s, bỏ phiếu, FSM đủ | Engine P = 16 dạng luồng, mạng dilated, cập nhật weight, số học mới |
| Độ chính xác kỳ vọng | Thấp nhất ở FALL so với IMPACT | Cao hơn nhờ thứ tự thời gian và 3 lần nhìn | Ngang B |
| Độ trễ SUSPECT | ≈ 1,46 s, không dư | ≤ 1,14 s danh định | ≈ 0,6 s |
| Suy luận | 14 ms | 5,15 ms với N2, 2,65 ms với N2-S (mô phỏng E2; cam kết ≤ 6) | ≈ 0,3 ms |
| Tài nguyên | 5 % logic | ≈ 8–12 % (ước) | 20–30 % |
| Rủi ro | Kỹ thuật thấp, dễ trượt chỉ tiêu | Trung bình, **luôn lùi được về A** | Cao |
| Công sức RTL | ≈ 1 người-tuần | ≈ 4–5 người-tuần | ≥ 8 người-tuần |
| Thuyết phục giám khảo | Yếu: "MCU cũng làm được" | Tốt: có số đo trước/sau, có lý do cho FPGA | Tốt nhưng dễ hỏng demo |

Chọn **B** vì nhóm đã có A chạy đúng trong mô phỏng. B lấy A làm tầng 1, nên mọi rủi ro của phần mới đều có đường lùi đã kiểm chứng.

### 3.3. Thay đổi lớn: lý do, cách kiểm, đường lùi

| Thay đổi | Lý do định lượng | Cách kiểm chứng | Phương án lùi |
|---|---|---|---|
| Lấy số học và bố trí bộ nhớ của RTL hiện có làm chuẩn | Đã khớp 20/20; kích hoạt bão hòa 127 chỉ 0,02 % nên 7 bit là đủ | `verify_spec_v3.py` | — |
| Cảm biến 100 Hz, MCU giảm còn 50 Hz | Suy giảm −13,8 dB ở 30 Hz, −30,6 dB ở 40 Hz; dữ liệu thô dùng lại được cho mô hình 100 Hz | Test vector chung C/Python (FW-07) | `DECIM = 1`: mạng nhận thẳng 100 Hz, cửa sổ 1,28 s |
| Ghi thô ±16 g / ±2000 °/s | INT8 vẫn là 1/16 g và 3,9 °/s mỗi mức như v1; đo được tỉ lệ vượt 8 g; đổi thang không phải thu lại | Thống kê thu thử (AI-03) | Đổi `ACC_SHIFT` 7 → 8, `GYR_SHIFT` 6 → 7 rồi huấn luyện lại |
| Bước 0,32 s + bỏ phiếu 2/3 | 3 cửa sổ hợp lệ thay vì 1; SUSPECT ≤ 1,14 s | Phát lại dữ liệu trên PC (AI-10) | `VOTE_K = 1` |
| N2: 3 Conv + Flatten-Dense | Ngữ cảnh 2,56 s có thứ tự; MAC chỉ tăng 0,9 % | LOSO so N1 / N2 (AI-09) | Giữ N1 |
| Engine E2 | 13,96 ms → 5,15 ms (N2), 2,65 ms (N2-S) trong mô phỏng 14/10 | Cùng bộ test vector với E1, so từng tầng (RB-04) | Giữ E1 |
| 3 lớp + 1 dự trữ | Bớt khoảng một phần ba số sự kiện phải thu; bỏ lớp mơ hồ nhất (F1 STUMBLE trên SisFall chỉ 0,55) | Macro-F1 3 lớp | Gộp tiếp IMPACT vào NORMAL (**đã áp dụng ở v2.1, 16/10**: 2 lớp) |
| Giao thức v3 (CRC-16, SEQ, STATUS) | Xác suất lọt lỗi 1/65.536 thay vì 1/256; MCU có CRC-16-CCITT phần cứng | `tb_proto` + 1.000 vòng trên board (RA-03, RA-04) | Khung CRC-8 hiện có (A.7) |
| Tách hai trục nâng cấp: **mô hình** (N1 → N2) và **tốc độ** (E1 → E2) | Trước đây N2 chỉ chạy được trên E2; E2 trễ thì mất luôn N2, tức mất các chỉ tiêu nhận dạng. Mở rộng E1 cho N2 chỉ là đổi hằng số ở 5 file | Cùng bộ test vector của N2 (RB-02b) | N1 trên E1 |
| Thông mạch lần đầu bằng **RTL hiện có** (CRC-8), bỏ `top_link.v` | RTL hiện có đã trả kết quả thật, không cần bản "kết quả giả". Tách lỗi dây/điện áp khỏi lỗi giao thức mới | 100 vòng ở SCK 1 MHz (RA-04) | — |
| Mạch phụ ESP32 (tùy chọn): ghi dữ liệu, và làm master SPI để thử FPGA | Lấy việc thu dữ liệu và việc kiểm FPGA trên chip ra khỏi sự phụ thuộc vào firmware SN32. `test_sensor/esp32` đã stream đúng định dạng ở 100 Hz | Đọc lại thanh ghi A.1, đếm xung INT, kiểm mất mẫu (TH-12); 20 vector khớp golden (TH-13) | Làm bằng SN32 như kế hoạch gốc |

---

## 4. Kiến trúc

### 4.1. RTL

```
SCK,CS,MOSI ─► spi_slave ─► packet_parser ─► input_buffer (768×8) ─┐
MISO ◄── spi_result_tx ◄── result_register ◄──────────┐            ▼
IRQ  ◄──────────────────── result_register            │      ENGINE (E1 hoặc E2) ◄─ weight_rom, bias_rom
RST_N ─► reset_sync                                   │            │  ▲
clk 27 MHz (H11) ─► rPLL ─► 50,143 MHz                └── argmax_score ◄─ feature_ram A ⇄ B
```

Một miền clock 50,143 MHz. Mọi tín hiệu ngoài qua 3 flip-flop đồng bộ (như `spi_slave.v` hiện có).

**Engine E1 (đã có, tầng 1).** `cnn_controller` chạy `CONV1 → POOL1 → CONV2 → POOL2 → GAP → DENSE`. Mỗi MAC mất 3 trạng thái (`ISSUE → WAIT → MAC`). Kích thước lớp viết cứng qua `layer_sel`. Chỉ chạy được N1.

**E1 mở rộng (tầng 2, bước 1).** Giữ nguyên cách điều khiển 3 trạng thái đã kiểm chứng, chỉ tổng quát hóa kích thước để chạy được N2: `layer_sel` 2 bit trong `conv1d_engine` và `maxpool1d_engine` (C3 đi cùng đường RAM B → RAM A → RAM B như C2); `cnn_controller` thêm `CONV3`, `POOL3` và bỏ qua `GAP`; `dense_engine` đọc 512 phần tử thẳng từ RAM B; ROM weight 6.368 từ (địa chỉ 13 bit), ROM bias 68 từ. Dự toán 3 × 227.328 + ≈ 20.500 chu kỳ phụ ≈ **702 nghìn chu kỳ ≈ 14,0 ms**; cùng công thức này cho N1 ra 699.784, sát số đo 699.800. BSRAM tăng từ 6 lên khoảng 8 khối.

**Engine E2 (mới, tầng 2, bước 2).** Một engine dạng bảng, 1 chu kỳ mỗi MAC, tham số P làn. Ý chính: dữ liệu xếp "vị trí trước" nên cửa sổ tích chập 5 × IC là **một dải địa chỉ liên tiếp**; xếp ROM weight theo `k` trước thì địa chỉ weight cũng liên tiếp. Cả ba địa chỉ (đọc dữ liệu, đọc weight, ghi kết quả) chỉ là bộ đếm cộng 1, không cần bộ nhân địa chỉ.

```
for mỗi lớp trong bảng:                              # C1, C2, C3 rồi DENSE
  wr = 0
  for j in 0 .. L/2 − 1:                             # vị trí sau pooling
    for g in 0 .. OC/P − 1:                          # nhóm P kênh ra
      best[p] = −∞
      for q in 0 .. 1:                               # 2 vị trí trước pooling
        t = 2j + q;  acc[p] = bias[g·P + p]
        sa = (t − 2)·IC;  wa = BASE + g·5·IC         # hai bộ đếm
        for run in 0 .. 5·IC − 1:                    # mỗi chu kỳ một MAC
          x = (0 ≤ t − 2 + run/IC < L) ? SRC[sa + run] : 0
          acc[p] += ROM[wa + run][p] · x             # P làn dùng chung x
        best[p] = max(best[p], acc[p])
      for p in 0 .. P − 1:  DST[wr++] = requant(best[p], n)
DENSE: một dải dài F = 512, không padding, không requant → 4 logit
```

| Module E2 | Chức năng | Ghi chú |
|---|---|---|
| `mac_lane.v` | Nhân 8 × 8 có dấu, cộng dồn 32 bit, 2 tầng pipeline | Dựa trên `mac_unit.v` |
| `requantize_relu.v` | Dùng lại nguyên bản | Đã kiểm |
| `conv_engine2.v` | Vòng lặp trên, tín hiệu `valid` / `pad` trễ cùng nhịp với BSRAM | Nguồn lỗi số 1: lệch một nhịp |
| `cnn_ctrl2.v` | Đọc bảng lớp từ `cnn_params.vh`, đếm `CYCLES` | |
| `gap_engine.v` | Dùng lại, chỉ bật khi đầu mạng là GAP | Để E2 chạy được cả N1 |
| `argmax_score.v` | Lớp thắng + hiệu top1 − top2, 2 tầng thanh ghi | Mở rộng `argmax4.v` (đã 2 tầng từ 13/10): thêm hiệu top1 − top2 |

Dự toán ban đầu cho N2: 227.328 MAC + ≈ 18.400 chu kỳ phụ ≈ 246 nghìn chu kỳ với P = 1; ≈ 63 nghìn với P = 4. Mô hình địa chỉ này đã được kiểm bằng Python (H6). **Số đo trong mô phỏng của `rtl/e2/cnn_e2.v` (14/10):** N2 258.080 chu kỳ = 5,15 ms (P = 1), 75.284 = 1,50 ms (P = 4); N2-S 132.896 = 2,65 ms (P = 1), 39.956 = 0,80 ms (P = 4). Chu kỳ phụ nhiều hơn dự toán (nạp bias 3 nhịp mỗi làn, xả pipeline 4 nhịp mỗi vị trí); với P = 4 phần phụ chiếm tỉ lệ lớn hơn nên không giảm đúng 4 lần.

### 4.2. Giao tiếp MCU ↔ FPGA

Chi tiết ở A.7. Trình tự: `[GHI 772 byte] → chờ IRQ (timeout 50 ms) → [ĐỌC 7 byte] → kiểm CRC, STATUS, SEQ`.

### 4.3. Firmware

Không RTOS. Ngắt chỉ đặt cờ: INT của MPU6050, IRQ của FPGA, SysTick 1 ms, nút.

Vòng lặp chính, mỗi khe 10 ms:
1. Có mẫu → đọc 14 byte, trừ offset gyro, cập nhật min/max của khối, đưa vào bộ lọc giảm mẫu. Cứ 2 mẫu thô → 1 mẫu 50 Hz → lượng tử INT8 → ghi `ring`.
2. Đủ 32 mẫu thô (0,32 s) → đóng khối bất động, gửi khung 772 byte thẳng từ `ring`, tính CRC trong lúc gửi.
3. Có IRQ → đọc 7 byte, kiểm, đưa vào bộ phiếu và Safety FSM.
4. Kiểm timeout, đếm lỗi.
5. Safety FSM, còi, LED.
6. OLED: tối đa một trang mỗi khe, không vẽ ở khe có gửi khung.
7. UART qua buffer vòng + ngắt TX; nuôi watchdog.

| Ngân sách một khe 10 ms | I²C phần cứng 400 kHz | I²C mềm (dự phòng) |
|---|---|---|
| Đọc cảm biến | ≈ 0,45 ms | ≈ 1,7 ms |
| Gửi khung (dây 1,54 ms + vòng lặp) | ≤ 4 ms | ≤ 4 ms |
| Một trang OLED | ≈ 2,9 ms | chia khúc ≤ 32 byte ≈ 3 ms |
| Khe nặng nhất | ≈ 4,6 ms | ≈ 5,7 ms |

RAM: `ring` 768 + UART TX 512 + RX 64 + trang OLED 128 + bộ lọc 36 + khối 28 + stack 1.024 ≈ **2,6 KB / 8 KB**. Flash 32 KB: không `float`, không `printf` số thực. Bản đối chứng MCU-only (thêm 1,5 KB feature map, 6,4 KB weight) build thành project riêng.

**Chân và nối dây:** toàn bộ bảng chân, giá trị thanh ghi thiết lập và mẫu file ràng buộc FPGA nằm ở **Phụ lục E**.

### 4.4. ML

- **Dữ liệu — chiến lược lai (chốt 13/10):** ba nguồn, mỗi nguồn một vai trò.
  - **D1 – công khai, cảm biến ở đầu:** bộ Özdemir–Barshan (AI-13). Cấp lớp FALL và phần lớn NORMAL để huấn luyện. Theo tài liệu đi kèm, bộ này có 17 người × 36 hoạt động × khoảng 5 lần = 3.060 bản ghi. **Đã có trong [ml/data/public/](ml/data/public/README.md) (16/10): 11 người, 1.180 cú ngã, 961 bản ghi hoạt động thường ngày, 11,57 giờ, 109.970 cửa sổ** (13/10: 6 người, 604 cú ngã; sáng 16/10: 8 người, 840 cú ngã). Riêng số cú ngã đã gấp 4,7 lần mức 250 nhóm định tự thu, và không ai trong nhóm phải ngã hàng trăm lần. 6 người còn lại chưa tải được vì máy chủ UCI cắt kết nối giữa chừng
  - **D2 – tự thu trên mũ, không có cú ngã nào** (v2.1: chỉ để kiểm tra, không huấn luyện): NORMAL khi đội mũ ≥ 2 giờ tổng từ ≥ 2 người, 20 lần va mũ khi đang đội, 20 lần rơi mũ (AI-05, AI-08). Lớp IMPACT chỉ thu khi buổi thử cho thấy cần (mục 9). Không bộ công khai nào có các sự kiện này
  - **D3 – ngã trên đệm khi đội mũ, ≥ 20 cú từ ≥ 2 người** (v2.1; trước: ≥ 40 cú từ ≥ 3 người): chỉ để kiểm tra mô hình trên đúng thiết bị (AI-03, AI-14, TH-07, TH-10). Không đưa vào huấn luyện
  - **Dữ liệu ở thân người (ngực, thắt lưng):** nhóm chấp nhận dùng, nhưng chỉ là nguồn bổ sung vì đã có kênh đầu. Phép đo ngày 13/10 trên 6 người của D1, nơi cùng một cú ngã được ghi đồng thời ở ba vị trí (mô hình thay thế là hồi quy logistic trên 31 đặc trưng, không phải CNN của đề tài): huấn luyện ở ngực hoặc thắt lưng rồi thử trên đầu của người để riêng cho recall sự kiện 93,9–95,0 %, ngang với huấn luyện ở đầu (94,0 %); nhưng số bản ghi thường ngày bị báo nhầm tăng từ 51/499 lên 79–87/499. Nguồn bổ sung gồm kênh ngực và thắt lưng của D1, và SisFall (thắt lưng, 200 Hz, có đủ băng tần tới 25 Hz mà D1 thiếu). Có đưa vào hay không do AI-09 quyết bằng số đo
- **Ba chỗ D1 khác thiết bị thật, phải đo chứ không giả định (AI-14):** (i) D1 lấy mẫu 25 Hz, chuỗi của ta 50 Hz, nên sau nội suy băng 12,5–25 Hz của D1 gần như trống; (ii) FALL chỉ có trong D1, IMPACT chỉ có trong D2, nên mạng có thể học phân biệt *nguồn dữ liệu* thay vì *chuyển động*; (iii) cảm biến của D1 buộc vào đầu, của ta nằm trên vỏ mũ, trục và độ rung khác nhau. Phương án lùi cuối cùng là kế hoạch cũ: tự thu ≥ 250 cú ngã từ ≥ 8 người
- **Hai bước mô hình:** N1 dùng lại notebook hiện có để có mô hình trên mũ sớm nhất (tầng 1). N2 huấn luyện có mô phỏng lượng tử đúng A.5.
- **Đánh giá:** Leave-One-Subject-Out theo người của D1. Chỉ số chính là **recall FALL mức sự kiện**: một cú ngã tính là phát hiện khi ít nhất 2 trong 3 cửa sổ vùng dương báo FALL với SCORE ≥ `T_SCORE`. Phép thử cuối là recall trên D3. Mọi con số báo cáo phải ghi rõ đo trên nguồn nào.
- **SisFall:** cảm biến ở thắt lưng, xa vị trí mũ hơn D1, nên không dùng để đánh giá đề tài. Giá trị của nó là đã thông chuỗi huấn luyện → INT8 → RTL (H1, H5).

### 4.5. Safety FSM

```
STANDBY ◄─ WEAR = 0 liên tục 3 s ─┐        ┌──────────── CANCEL ────────────┐
   │ WEAR = 1                     │        ▼                                │
   └────────────────────────► MONITOR ──► SUSPECT ──► PRE_ALARM (10 s) ──► ALARM
                                 ▲  │         │ quá 8 s                     │ giữ CANCEL 1 s
                                 │  └─ giữ CANCEL 3 s (SOS) ───────────────►│
                                 └────────────┴──────────────── COOLDOWN (30 s) ◄┘
```
Bảng chuyển trạng thái và tham số ở A.8.

---

## 5. Bảng cổng 0 % → 100 %

Chưa qua cổng thì chưa tính phần trăm.

| Cổng | % | Tầng | Việc phải xong | Điều kiện qua cổng |
|---|---|---|---|---|
| G0 | 5 | 1 | FW-02, FW-03, AI-01, AI-02, RA-01, RB-01, TH-01..03 | Một nguồn tham số, RTL khớp 20/20; chân phía MCU đã chốt, đo 3,3 V; cảm biến PASS ở ±16 g / ±2000 °/s |
| G1 | 15 | 1 | FW-04..06 (hoặc TH-12), AI-03, AI-13, TH-04 | Log 10 phút trên mũ không mất mẫu; thu thử xong; D1 đã chuyển về thang A.2; A.1–A.3 đóng băng |
| G2 | 30 | 1 | FW-07..10, FW-13, AI-04, RA-02..05, RB-02, TH-05 | 1.000 vòng ghi → IRQ → đọc trên board thật, 0 lỗi; 20 vector qua HIL khớp golden; 1.000 khung MCU khớp CRC với Python |
| G3 | 45 | 1 | AI-05..07, AI-14, FW-11, RB-03, TH-06 | Buổi thử nhỏ đầu tiên trên mũ xong (v2.1: NORMAL khi đội mũ ≥ 30 phút từ ≥ 2 người; ≥ 10 cú ngã trên đệm; 10 va mũ, 10 rơi mũ); mô hình huấn luyện trên D1 đã nạp lên chip và đạt recall ≥ 80 % trên các cú ngã thu thử (AI-14); FSM qua hết ca test trên PC |
| **G4** | **60** | **1 xong** | FW-12, RA-06, TH-07, TH-08 | **Mũ chạy độc lập:** HIL ≥ 500 cửa sổ khớp 100 %; ngã trên đệm 10 lần ≥ 8 lần PRE_ALARM; chạy 30 phút không treo |
| G5 | 75 | 2 | AI-08..10, RB-02b, RB-04, RA-07, RA-08, TH-09 | LOSO trên D1 đạt recall ≥ 95 % và Macro-F1 ≥ 0,90; recall trên D3 ≥ 90 % (≥ 20 cú ngã, ≥ 2 người; v2.1); N2 chạy trên chip khớp 100 % trên ≥ 2.000 cửa sổ HIL; với E2 thì `CYCLES` ≤ 300.000 |
| G6 | 90 | 2 | FW-14, FW-15, AI-11, TH-10 | Thử thực địa đạt: báo giả, va mũ, rơi mũ (đếm và hủy được), độ trễ, người mới; có số đo MCU-only |
| G7 | 100 | 2 xong | TH-11 | Đủ mọi chỉ tiêu cột "Tầng 2" ở mục 10; báo cáo, slide, video |
| — | — | 3 | FW-16, AI-12, RA-09, RB-05, RB-06 | Không cam kết; chỉ làm khi G6 đã qua |

```
G0 ─► G1 ─┬─► G3 (dữ liệu, N1 trên mũ) ──────────► G4 (TẦNG 1 trên mũ) ─► G5 ─► G6 ─► G7
          └─► G2 (SPI thật + E1 trên chip với weight hiện có) ─┘
```
Đường găng là dữ liệu. Nhánh RTL và đường truyền không chờ dữ liệu vì đã có weight SisFall để chạy thử toàn chuỗi.

---

## 6. Danh sách việc theo nhánh

Ký hiệu: `(cổng · tầng)`. Chỉ đánh `[x]` khi đạt *Pass* và có bằng chứng trong `docs/bao_cao/`.

### FW — firmware và phần điện trên mũ

- [x] **FW-01** (G0·1) Kiểm tra MPU6050 trên phần cứng — *Pass:* đọc được cảm biến trên ESP32 và SN32F407 ✅ (bằng mã riêng của một thành viên; cần đưa mã và log vào thư mục, X12)
- [ ] **FW-02** (G0·1) Chuyển `test_sensor` sang thang ghi thô của A.1 và sang chân của EVK — *Pass:* T1..T7 PASS; `|a|` = 2048 ± 10 %; INT 200 xung / 2 s
  - **Phần mã đã xong 14/10:** dải ±16 g / ±2000 °/s, các ngưỡng đổi theo, bước kiểm hướng trục đổi sang Z lên trời, chân theo E.1. `bash test_sensor/firmware/build.sh` biên dịch bằng Arm Compiler 6.24 ra `build/mpu6050_test.hex` (13,6 KB / 32 KB Flash, 552 byte / 8 KB RAM, dùng MicroLIB)
  - Thêm 14/10: project Keil [test_sensor/firmware/keil/mpu6050_test.uvprojx](test_sensor/firmware/keil/mpu6050_test.uvprojx), dựng từ project vòng 1 trên cùng EVK (SN-Link Debugger, thuật toán `SN32F400_32.FLM`, MicroLIB). `UV4 -b` báo 0 lỗi, 0 cảnh báo; Code 14.756 + RO 2.028 byte, RAM 548 byte
  - Còn lại: Download lên EVK và chạy `sensor_check.py`. Mã này chưa từng chạy trên board
  - [mpu6050.c:15-16](test_sensor/firmware/mpu6050.c#L15) và [:165-166](test_sensor/firmware/mpu6050.c#L165): `0x08` → `0x18`, `0x10` → `0x18`
  - [mpu6050.h:26](test_sensor/firmware/mpu6050.h#L26): 4096 → 2048
  - [test_main.c:299-311](test_sensor/firmware/test_main.c#L299): 4096 → 2048, ngưỡng offset 1310 → 328 (vẫn là ±20 °/s)
  - [test_main.c:313-316](test_sensor/firmware/test_main.c#L313): ngưỡng nhiễu `sd_m` 40 → 20, `sd_g` 10 → 3 (giữ nguyên theo đơn vị vật lý)
  - [sensor_check.py:28-29](test_sensor/tools/sensor_check.py#L28): 4096.0 → 2048.0, 65.5 → 16.4; ngưỡng gyro tính bằng LSB ở [dòng 248-250](test_sensor/tools/sensor_check.py#L248) chia 4
- [ ] **FW-03** (G0·1) Project Keil gốc từ `board_sn32f407.c` (hoặc dùng luôn `build.sh`): clock 48 MHz, SysTick, UART0 460800 trên P3.1/P3.2, LED D6, phím SW3 và SW6 — *Pass:* in `hello`, nháy LED, đọc được phím; đo VDD của EVK = 3,3 V (SW1 ON, jumper J1 và J3 theo E.4)
  - **Phần máy xong 14/10:** [firmware/](firmware/README.md) (`src/board.c`, `src/main.c`) và project [firmware/keil/fw.uvprojx](firmware/keil/fw.uvprojx) dựng từ project Keil của bộ test cảm biến. `UV4 -b` và `UV4 -r`: 0 lỗi, 0 cảnh báo; Code 6.716 + RO 948 byte (7,5 KB / 32 KB Flash), RAM 1.348 byte / 8 KB. `bash firmware/build.sh` cho cùng kết quả bằng dòng lệnh (4,6 KB với `-Oz`). Có sẵn lệnh UART cho đợt B: `c` kiểm CRC phần cứng (X5), `f` phép thử flash E.4 bước 2, `s` 100 vòng SPI (FW-09 a). Bằng chứng: [docs/bao_cao/2026-10-14_fw_dot_a/](docs/bao_cao/2026-10-14_fw_dot_a/README.md)
  - Còn lại (đợt B): nạp lên EVK, thấy `hello`, LED nháy, dòng SW3/SW6; đo VDD
- [ ] **FW-04** (G1·1) `mpu6050.c` theo A.1 trên I2C0 phần cứng (P0.10/P0.11, `PFPA->I2C0` = 0x0A) ở 400 kHz, hạ 100 kHz nếu sườn lên chậm; ngắt INT trên P2.2; canh mất mẫu 25 ms — *Pass:* chu kỳ INT 10,0 ms trên logic analyzer; đọc lại 7 thanh ghi đúng. Có thể lấy `i2c0.c` của dự án vòng 1 (`D:\hoctap\fpga\thi_fpga\MCU\firmware\drivers\`) làm gốc; mã đó đã biên dịch, chưa rõ đã chạy trên board chưa. *Lùi:* sau 1 ngày chưa chạy thì dùng `i2c_soft.c`
  - **Mã xong 14/10 (chỉ biên dịch):** [firmware/src/i2c0.c](firmware/src/i2c0.c) dựng từ `i2c0.c` của dự án vòng 1, theo datasheet mục 15.10 (START → địa chỉ → thanh ghi → START lặp → đọc, byte cuối NACK, timeout bằng vòng lặp và `TOCTRL`); [firmware/src/imu.c](firmware/src/imu.c) ghi đúng bảng A.1 rồi **đọc lại 7 thanh ghi**, báo số thanh ghi sai lúc khởi động; INT trên P2.2 qua ngắt cổng P2. Chờ board để đo chu kỳ INT
- [ ] **FW-05** (G1·1) Hiệu chuẩn offset gyro: trung bình 200 mẫu lúc khởi động, làm lại nếu mũ đang rung — *Pass:* trung bình 500 mẫu trong ±2 LSB
  - **Cách kiểm trên board (16/10):** [tools/gyro_residual.py](tools/gyro_residual.py) đọc file LOG của `logger.py` (gyro đã trừ offset), in trung bình 500 mẫu đầu mỗi trục (Pass ±2 LSB) và 500 mẫu lệch nhất trên cả file (độ trôi); bước B5.4 của `docs/huong_dan_dot_B.md`. Thử trên dữ liệu giả: offset dư −1,0 → PASS, −3,0 → FAIL
  - **Mã xong 14/10:** [firmware/src/gyro_cal.c](firmware/src/gyro_cal.c), C thuần: 200 mẫu, làm lại khi max − min của trục gyro nào > 100 LSB (≈ 6 °/s), làm tròn đối xứng. Unicorn: chuỗi có rung lúc đầu → làm lại 2 lần, offset trùng tham chiếu Python. Pass (±2 LSB trên 500 mẫu) đo ở board
- [ ] **FW-06** (G1·1) `uart_log.c` (buffer vòng + ngắt TX) và chế độ LOG theo A.9 — *Pass:* file 10 phút, 0 lần mất mẫu
  - **Mã xong 14/10 (chỉ biên dịch):** UART0 trong [firmware/src/board.c](firmware/src/board.c) có buffer vòng TX 512 B và RX 1.024 B, cả hai bằng ngắt; LOG khi giữ SW6 lúc khởi động hoặc lệnh `LOG`; đếm mất mẫu (khoảng cách ngắt ≥ 15 ms) trong lệnh `STAT`. Ghi file bằng `tools/logger.py`
- [x] **FW-07** (G2·1) `preprocess.c`: bộ lọc giảm mẫu + lượng tử + `ring` theo A.2 — *Pass:* 10.000 mẫu từ `tv/pre_in.csv` cho ra đúng `tv/pre_out.csv` của Python ✅ 14/10
  - [firmware/src/preprocess.c](firmware/src/preprocess.c), C thuần, chạy theo từng mẫu. Vector do [tools/gen_tv_pre.py](tools/gen_tv_pre.py) sinh từ golden model: đứng yên, đi bộ, va chạm bão hòa, ngẫu nhiên toàn dải INT16, các hằng số đúng biên làm tròn của A.2, sườn dốc
  - **Cách đo:** máy không có trình biên dịch C cho PC, nên [tools/m0_test.py](tools/m0_test.py) chạy **mã máy Cortex-M0 do chính armclang sinh ra** trong trình giả lập Unicorn (khóa ở tập lệnh ARMv6-M). 10.000 mẫu → 5.000 mẫu khớp từng byte; 305 cửa sổ đúng bước 16. Phép âm: 12 lỗi cài cố ý (làm tròn, hệ số lọc, kẹp, bước cửa sổ, CRC, SEQ, các ngưỡng FSM) đều bị bắt
  - Giới hạn: Keil build với mức tối ưu khác `build.sh`; phép kiểm trên chip là FW-10 (CRC của khung MCU so với Python)
- [ ] **FW-08** (G2·1) `spi_fpga.c` theo A.7 và E.2: CS của FPGA bằng GPIO P2.8, P1.8 luôn ra mức cao (giữ flash SPI trên EVK không được chọn), CRC-16 bằng khối CRC phần cứng (hàm phần mềm ở Phụ lục B giữ để đối chiếu), gửi thẳng từ `ring`, đọc 7 hoặc 20 byte, timeout 50 ms; hỗ trợ cả `PROTO = 1` (khung CRC-8 hiện có) để thông mạch lần đầu — *Pass:* khung `spi_00.bin` ra đúng từng byte trên logic analyzer
  - **Phần máy xong 14/10:** [firmware/src/spi_frame.c](firmware/src/spi_frame.c) (C thuần) dựng khung và kiểm khung đọc; [firmware/src/spi_fpga.c](firmware/src/spi_fpga.c) lái SPI0, CS, IRQ, RST_N, CRC phần cứng. Trong Unicorn: 305 khung v3 và 305 khung PROTO 1 khớp golden từng byte; 92 ca khung đọc (hợp lệ, SEQ lệch, CRC sai, STATUS, CLASS, đuôi HIL) cho đúng mã lỗi
  - Khung PROTO 1 cũng đã qua **RTL thật**: `rtl/tb/tb_top_spi.v` đưa đúng các byte đó vào chân SPI của `fpga_top` ở 4 MHz, đọc lại 7 byte khớp golden, khung sai CRC không bật IRQ (xem RB-01)
  - Datasheet 19.3.2: `CRC_DATA` **chỉ nhận ghi 8 bit**, mã ghi bằng con trỏ `uint8_t`. Còn lại (đợt B): lệnh `c` cho `0x29B1`, rồi logic analyzer
- [ ] **FW-09** (G2·1) Thử nấc với RA-04: (a) thông mạch bằng RTL hiện có, `PROTO = 1`, SCK 1 MHz, 100 vòng ghi → IRQ → đọc; (b) giao thức v3, khung đúng và sai CRC 100 lần; (c) 1.000 vòng ở SCK 4 MHz; (d) rút dây IRQ — *Pass:* (a)(b)(c) 0 lỗi; (d) bỏ cửa sổ, không treo
- [ ] **FW-10** (G2·1) Chế độ TRC: in mẫu thô và `F,seq,crc` của mỗi khung; `tools/check_frames.py` dựng lại khung từ mẫu thô — *Pass:* 1.000 khung, CRC của MCU trùng CRC của Python 100 %
  - **Phần máy xong 14/10:** lệnh `TRC` trong [firmware/src/app_main.c](firmware/src/app_main.c) in mẫu (gyro đã trừ offset), `F,seq,crc` cho khung đã gửi, `X,seq` cho cửa sổ bị bỏ khi FPGA còn bận. [tools/check_frames.py](tools/check_frames.py) ghi luồng từ cổng nối tiếp và dựng lại khung bằng golden. Thử bằng luồng giả có CRC do mã C (Unicorn) sinh: 298/298 khớp với cả PROTO 1 và 3; sửa 1 mẫu thô → đúng 8 khung báo sai
  - **15/10:** luồng TRC dựng từ khung do **mã máy firmware** sinh (`preprocess.c` + `spi_frame.c`, 1.283 khung trên 413 s dữ liệu ngã thật) → `check_frames.py` **PASS 1.283/1.283**; phép âm CRC sai, mất 1 mẫu → FAIL. Sửa: mất mẫu nay là FAIL (trước in "chưa đủ", mã 0). Bằng chứng: [docs/bao_cao/2026-10-15_verify_sau_don/](docs/bao_cao/2026-10-15_verify_sau_don/README.md). Pass còn chờ board
- [x] **FW-11** (G3·1) `blocks.c` (A.8) và `safety.c` là C thuần không gọi phần cứng; chương trình phát lại trên PC — *Pass:* mỗi dòng trong bảng chuyển trạng thái A.8 có một ca test ✅ 14/10
  - [firmware/src/blocks.c](firmware/src/blocks.c), [firmware/src/safety.c](firmware/src/safety.c); 49 ca trong [firmware/test/host_main.c](firmware/test/host_main.c), chạy bằng `tools/m0_test.py`: đủ 9 dòng của bảng A.8, biên của từng ngưỡng (2,99 s / 3 s, 299 / 300 LSB, ...), thứ tự ưu tiên CANCEL > timeout > phiếu > khối, bỏ qua WEAR từ SUSPECT, bíp IMPACT, tràn bộ đếm ms
  - Ba quy ước A.8 chưa nói, đã chọn và có ca test: (1) lần nhấn CANCEL đã gây chuyển trạng thái thì "đã dùng" tới khi nhả, nên giữ SOS 3 s rồi giữ tiếp không tự tắt ALARM; (2) lịch sử phiếu xóa khi vào SUSPECT và khi về MONITOR; (3) bíp IMPACT chỉ ở MONITOR, cần SCORE ≥ `T_SCORE`
  - Chưa có: phát lại file dữ liệu thật qua golden + FSM (AI-10)
- [ ] **FW-12** (G4·1) Giao diện: OLED vẽ từng trang (chưa có OLED thì dùng LED 7 đoạn của EVK), còi PWM trên P3.0, LED D6, CANCEL = phím SW3 chống dội 20 ms — *Pass:* bật hết giao diện, 10 phút không mất mẫu
  - **Một phần 14/10:** còi P3.0 đảo trong SysTick (âm 500 Hz, chạy được với còi thụ động lẫn chủ động; `BUZZER_ACTIVE_HIGH` để đổi cực tính khi thử), mẫu còi và LED theo trạng thái trong `app_core.c` (PRE_ALARM bíp ngắn mỗi giây, ALARM hú liên tục, IMPACT bíp 100 ms), CANCEL = SW3 chống dội 20 ms. **15/10: LED 7 đoạn của EVK** hiện trạng thái (`oFF`, `rUn`, `SUS`, `P 10`→`P 00` đếm ngược PRE_ALARM, `ALr`, `CL`, `Err`), quét trong SysTick; logic hiển thị (`app_display`) có ca test trong Unicorn. Chưa có OLED; chưa thử trên board
- [ ] **FW-13** (G2·1) Chế độ HIL: 768 byte payload vào `ring`, 4 byte đầu/cuối giữ riêng — *Pass:* 20 vector hiện có đi trọn vòng PC → MCU → FPGA → PC, khớp golden. Cổng G2 cần việc này (trước đây xếp nhầm ở G4)
  - **Phần máy xong 14/10:** lệnh `HIL`: MCU nhận khung 772 byte (kiểm CRC khung PC gửi), chuyển sang FPGA, trả nguyên 20 byte. Bộ đệm riêng 772 byte thay vì dùng lại `ring` (RAM còn đủ: 5,4 KB / 8 KB). PC: [tools/hil_test.py](tools/hil_test.py)
- [ ] **FW-14** (G6·2) WEAR, SOS, tự kiểm khi bật nguồn (A.10), watchdog, RST_N sau 3 lỗi liên tiếp — *Pass:* rút dây SPI → hiện ERR, cắm lại tự hồi phục; nạp bitstream sai weight → tự kiểm báo FAIL
  - **Một phần 14/10 (chỉ biên dịch):** tự kiểm A.10 lúc khởi động so với [firmware/src/selftest_expect.h](firmware/src/selftest_expect.h) (sinh bởi `export_mem.py` cho đúng weight trong bitstream), watchdog ≈ 1 s (khóa 0x5AFA, nạp 0x55AA; WDTPRE reset = chia 1 theo datasheet 3.4.2, tần số ILRC [CẦN XÁC MINH – nguồn: lệnh `w`, X16]), RST_N sau 3 lỗi liên tiếp (`spi_fpga.c`), WEAR qua `WEAR_PRESENT`. SOS đã có trong Safety FSM
  - **16/10, một nút (nhóm chọn):** [firmware/src/pwr_btn.c](firmware/src/pwr_btn.c) ngoài FSM tạo WEAR từ nút. 9 ca mới trong `host_main.c` (mode 4) chạy mã máy Cortex-M0 trong Unicorn, tất cả PASS: cấp nguồn, tắt, bật, giữ 6 s khi bật không thành SOS, SOS, hai lần nhấn cách xa, nhấn rồi giữ, CANCEL ở PRE_ALARM, ngã ngay sau khi tắt. Phép âm `BTN_POWER=0`: 4 ca bật/tắt FAIL. Keil 0 lỗi 0 cảnh báo, Code 16.092 (+732 B). Lõi firmware vẫn trùng golden (402 kết quả). Chưa thử trên board (bước B9)
- [ ] **FW-15** (G6·2) Bản đối chứng `cnn_mcu.c` (project riêng): golden model bằng C số nguyên — *Pass:* khớp golden trên 50 vector; có số ms mỗi lần đo bằng GPIO
  - **Phần máy xong 14/10:** [firmware/src/cnn_mcu.c](firmware/src/cnn_mcu.c) chạy N1, N2, N2-S, N2-L. Trong Unicorn: **khớp golden 50/50 trên 5 mô hình** (lớp, SCORE, 4 logit). Đếm lệnh Cortex-M0 một lần suy luận (`-O3`): N1 2,39 triệu lệnh → **74,6 ms** nếu nhân 1 chu kỳ, **232,7 ms** nếu nhân 32 chu kỳ (X7), cộng tới ≈ 26 ms nếu Flash 1 wait-state; N2 2,37 triệu lệnh → 73,9–232,3 ms (đề cương làm tròn "khoảng 2,4 triệu lệnh, 74–232 ms"); N2-S 39,3–118,9 ms. Là dự toán từ số lệnh thật, chưa đo GPIO trên chip. Bằng chứng: [docs/bao_cao/2026-10-14_fw15_mcu_only/](docs/bao_cao/2026-10-14_fw15_mcu_only/)
- [ ] **FW-16** (·3) Ghi sự kiện vào Flash; `GATE_EN` bỏ qua cửa sổ khi 8 khối gần nhất đều bất động

### AI — dữ liệu và mô hình

- [x] **AI-01** (G0·1) Đưa notebook Colab và `fpga_export/` vào repo; chốt `conv1_shift` bằng số liệu (H5: shift 7 cho recall FALL 97,8 %, shift 8 cho 96,7 % trên tập test) — *Pass:* một `quant_params.json` duy nhất; golden và RTL cùng đọc ✅ 14/10
  - **Chốt shift (8, 8)**, giữ nguyên json của nhóm AI. Golden trên SisFall: validation 95,66 % / Macro-F1 0,8892 / recall FALL 96,89 % (shift 7: 96,26 % / 0,9034 / 97,51 %); test 94,39 % / 0,8446 / 96,71 % (shift 7: 94,59 % / 0,8308 / 97,78 %). Chênh ≤ 1,1 điểm và Macro-F1 đổi chiều giữa hai tập, nên không có bằng chứng 7 tốt hơn; 8 là giá trị bước xuất tính ra và đã sinh `golden_vectors.npz`; shift 7 làm kích hoạt chạm 127 tăng từ 0,035 % lên 0,475 % (l1, validation)
  - Một nguồn: `tools/gen_cnn_params.py` (RTL), `tools/verify_spec_v3.py` (golden) cùng đọc `quant_params.json`. Bằng chứng: [docs/bao_cao/2026-10-14_ra01_conv1_shift/](docs/bao_cao/2026-10-14_ra01_conv1_shift/README.md)
  - Notebook Colab vẫn chưa có; phần đó chuyển sang AI-07 (viết lại script huấn luyện) và X4
- [x] **AI-02** (G0·1) Đưa `golden_model.py` (Phụ lục B) và script kiểm vào `ml/src/`, `tools/` — *Pass:* in "TẤT CẢ PASS" ✅ 14/10: `python tools/verify_spec_v3.py ml/src <thư mục fpga_export>`; log ở `docs/bao_cao/2026-10-14_cong_cu/`
- [ ] **AI-03** (G1·1) [tools/logger.py](tools/logger.py) (đã có, chưa chạy với board); thu thử 1–2 người (mỗi kiểu ngã, rơi mũ, va mũ, tháo/đội × 3); thống kê tỉ lệ mẫu vượt 8 g và 500 °/s, thời lượng sự kiện — *Pass:* có bảng số liệu; chốt `ACC_SHIFT`, `GYR_SHIFT`, `DECIM`, ghi vào lịch sử SPEC. Các cú ngã thu ở đây là phần đầu của D3
- [x] **AI-04** (G2·1) `export_mem.py`: bố trí ROM của E1 và E2 (`--P`), `cnn_params.vh`, ≥ 50 test vector gồm FALL, bão hòa ±127, toàn 0, khung LFSR; `spi_XX.bin`, `res_XX.mem`, `selftest_expect.h` — *Pass:* golden đọc ngược `.mem` ra đúng lớp; biên `|acc|` < 2^31 cho mọi kênh ra ✅ 14/10
  - [tools/export_mem.py](tools/export_mem.py) nhận `params_int8.npz` của `ml/train_cnn.py` hoặc thư mục xuất E1 của nhóm. Bố trí ROM ở [ml/src/rom_layout.py](ml/src/rom_layout.py), cùng nguồn với mô hình địa chỉ E2 trong `verify_spec_v3.py`
  - E1 với weight SisFall: `weights.mem`, `bias.mem` xuất ra **trùng từng byte** file của nhóm. 50 vector (10 FALL + 10 NORMAL của D1, LFSR, toàn +127 / −128 / 0, xen kẽ, bậc thang, gyro bão hòa, ngẫu nhiên): đọc ngược khớp golden 50/50; biên |acc| [172.430, 295.566, 140.083] < 2^31
  - E2 cho N2-S (P = 1 và 4): đọc ngược 50/50; mô hình địa chỉ chạy trên ROM đã xuất == golden. Bằng chứng: [docs/bao_cao/2026-10-14_ai04_ai09/](docs/bao_cao/2026-10-14_ai04_ai09/README.md)
  - `res_XX.mem` của E2 để CYCLES = 0 vì E2 chưa có
- [ ] **AI-05** (G3·1) `docs/data_protocol.md`; buổi thử nhỏ đầu tiên trên mũ (v2.1) — *Pass:* NORMAL khi đội mũ ≥ 30 phút từ ≥ 2 người; ≥ 10 cú ngã trên đệm; 10 va mũ khi đang đội, 10 rơi mũ; có video; không file nào mất mẫu. (Trước v2.1: ≥ 100 IMPACT để huấn luyện, không ai phải ngã)
  - Mỗi file ghi một chuỗi 5–6 sự kiện cùng loại, bấm nút đánh dấu quanh từng sự kiện: khoảng 14 file mỗi người thay vì hơn 80
  - Va đập khi **không** đội mũ (rơi mũ, đặt mạnh mũ) không cần người tham gia: một thành viên thu hàng loạt, gán `subject = h0`, chỉ dùng để huấn luyện. Lớp IMPACT được đánh giá trên các va đập khi đang đội
  - **15/10:** [docs/data_protocol.md](docs/data_protocol.md): an toàn và giấy đồng ý (TH-06), kiểm tra thiết bị, đặt tên file, **19 hoạt động có mã cố định** (5 IMPACT, 8 NORMAL khi đội mũ, 6 kiểu ngã D3), cách bấm SW6 quanh từng va đập, chỉ tiêu số lượng. Ưu tiên `nam_xuong`, `cui_nhat`, `suyt_nga` vì đó là nguồn báo giả khi phát lại D1 (AI-10)
- [ ] **AI-06** (G3·1) `windowing.py`: giảm mẫu cả hai pha, lượng tử, bước 16, vùng nhãn A.4 → `dataset.npz`; nhận cả D1 (đã ở 50 Hz, điểm va chạm lấy tự động) lẫn D2, D3 (100 Hz, theo nút đánh dấu); mỗi cửa sổ mang mã nguồn và mã người — *Pass:* đối chiếu bằng mắt 20 cửa sổ mỗi lớp với video (D2, D3) hoặc với biểu đồ bản ghi gốc (D1)
  - **Công cụ xong 15/10:** [tools/windowing.py](tools/windowing.py): điểm sự kiện theo A.4 (trong đoạn bấm nút, hoặc trên cả file với D3), giảm mẫu và lượng tử bằng đúng hàm golden, cắt cửa sổ và gán nhãn, loại file mất mẫu hoặc sai tên, `--plot` vẽ từng sự kiện; ra npz cùng khóa với D1 nên `train_cnn.py --extra` dùng thẳng. Thử bằng file LOG giả dựng từ D1 nội suy 100 Hz: 10/10 sự kiện đúng vị trí (lệch 0 mẫu), mỗi sự kiện đúng 3 cửa sổ dương. Bằng chứng: [docs/bao_cao/2026-10-15_ai05_ai06_thu_du_lieu/](docs/bao_cao/2026-10-15_ai05_ai06_thu_du_lieu/). Pass (đối chiếu 20 cửa sổ mỗi lớp với video) chờ dữ liệu thật
- [ ] **AI-07** (G3·1) Huấn luyện mô hình tầng 1 trên D1 (v2.1: không cần D2; notebook gốc không có nên dùng `ml/train_cnn.py`), xuất INT8 — *Pass:* golden trùng nhãn với mô hình lượng tử của notebook ≥ 99,5 % cửa sổ
  - **Phần chuẩn bị xong 14/10, chỉ trên D1:** notebook gốc vẫn chưa có nên **viết lại** bằng numpy thuần (bản đầu `ml/train_n1.py` + `ml/src/n1_numpy.py`; từ 15/10 thay bằng [ml/train_cnn.py](ml/train_cnn.py) `--arch n1` + [ml/src/cnn_numpy.py](ml/src/cnn_numpy.py), cho đúng từng số). Không cần TensorFlow; chạy trên máy nhóm và Colab; `--extra` để thêm D2 khi có. Mô hình lượng tử của script trùng golden **100 %** (lớp, SCORE, 4 logit) trên 2.000 cửa sổ
  - LOSO 6 người, INT8, `T_SCORE = 0`: **recall sự kiện 515/604 = 85,3 %** (theo người 75,0–99,0 %), Macro-F1 0,861, accuracy 97,9 %, FP32 → INT8 trùng nhãn 99,77 %; phiếu 2/3 nhầm trên bản ghi sinh hoạt 20,6 lần/giờ **trước** Safety FSM
  - Weight xuất ở `ml/out/n1_d1/fpga_export/` chạy trên RTL: `run_all.sh --export` cho 20/20 (10 FALL + 10 NORMAL) và `tb_top_spi` PASS. Bằng chứng: [docs/bao_cao/2026-10-14_ai07_n1_d1/](docs/bao_cao/2026-10-14_ai07_n1_d1/README.md)
  - v2.1: không còn cần D2. Còn lại cho Pass: chạy lại trên D1 8 người và lưu bằng chứng (16/10 đang chạy N1 × 3 seed). Lượng tử hiện là PTQ, chưa phải QAT
- [ ] **AI-08** (G5·2) Buổi thử chính trên mũ (v2.1) — *Pass:* NORMAL khi đội mũ ≥ 2 giờ tổng từ ≥ 2 người, có cúi nhặt, nằm xuống, vấp; ≥ 20 cú ngã trên đệm từ ≥ 2 người; 20 va mũ khi đang đội, 20 rơi mũ. (Trước v2.1: ≥ 250 IMPACT; NORMAL ≥ 2 giờ từ ≥ 4 người; ≥ 40 cú ngã từ ≥ 3 người)
- [ ] **AI-09** (G5·2) N2 với mô phỏng lượng tử đúng A.5; LOSO theo người của D1, mỗi lượt để riêng một buổi thu của D2; so N1 / N2 / N2-S (8-16-16) / N2-L (16-24-32); so có và không có dữ liệu ở thân người (kênh ngực, thắt lưng của D1; SisFall) trên cùng tập kiểm tra — *Pass:* chọn mô hình nhỏ nhất đạt recall sự kiện ≥ 95 % và Macro-F1 ≥ 0,90 trong LOSO, và recall ≥ 90 % trên D3; FP32 → INT8 giảm ≤ 2 điểm %; dữ liệu thân chỉ được giữ nếu không làm tăng báo nhầm trên bản ghi thường ngày
  - **Sơ bộ 14/10, chỉ trên D1 (6 người, chưa có D2/D3):** [ml/train_cnn.py](ml/train_cnn.py) + [ml/src/cnn_numpy.py](ml/src/cnn_numpy.py) huấn luyện cả họ A.4, LOSO, INT8 PTQ, kiểm golden từng bit. Macro-F1 INT8: N1 0,861 · N2 0,958 · **N2-S 0,975** · N2-L 0,976; recall sự kiện (T_SCORE 0): 85,3 % · 98,8 % · **98,7 %** · 98,0 %; FP32 → INT8 trùng nhãn ≥ 99,77 %. Chọn sơ bộ ban đầu là N2-S (mô hình nhỏ nhất đạt ≥ 95 % và ≥ 0,90; 3.184 weight, 113.664 MAC). Bằng chứng: [docs/bao_cao/2026-10-14_ai04_ai09/](docs/bao_cao/2026-10-14_ai04_ai09/README.md)
  - **Sửa 15/10 sau khi lặp 3 seed** (`nhieu_seed/`): Macro-F1 INT8 N2-S 0,975 / 0,916 / 0,945 (TB 0,945), **N2 0,958 / 0,969 / 0,977 (TB 0,968)**, N2-L 0,976 / 0,960 / 0,941 (TB 0,959); phiếu 2/3 nhầm/giờ ở T_SCORE 8 TB: N2-S 21,2, **N2 8,0**, N2-L 6,5. Seed đầu của N2-S là seed may; chênh lệch do seed lớn hơn chênh lệch giữa mô hình. **Chọn sơ bộ đổi thành N2** (ổn định nhất; vẫn ≤ 6 ms trên E2: 5,15 ms), N2-S giữ làm phương án nhỏ. Chốt khi có D2/D3, đánh giá nhiều seed
  - **Dữ liệu thân, 15/10** (`--train-only` ngực 340539 + thắt lưng 340535 của D1; tập kiểm LOSO vẫn chỉ là cửa sổ đầu; 3 seed): Macro-F1 INT8 TB 0,9707 (chỉ đầu 0,9683); recall sự kiện T_SCORE 8: **98,3 %** (95,8 %); cặp phiếu nhầm trước FSM tăng 8,0 → 9,9/giờ nhưng **sau FSM v3.1 PRE_ALARM giả giảm 1,26 → 0,88/giờ**, ngã nằm → PRE_ALARM 95,5 → **96,4 %**; gộp 3 seed 96,2 % / 0,38 giả/giờ; T_SCORE 16 TB 95,4 % / 0,38. **Đề nghị giữ dữ liệu thân (chỉ huấn luyện)** và ghi rõ trong Pass rằng "báo nhầm" tính ở mức PRE_ALARM. Mô hình `ml/out/n2t_d1`, xuất E2 `ml/out/e2_matrix/n2t_p1` (tb_e2 50/50). Chưa thử SisFall: file `sisfall_eventcenter_128x6_4class.npz` của nhóm đã lượng tử theo thang khác (trọng lực ≈ 9,3 mức trên Y), cần SisFall gốc. Bằng chứng: [docs/bao_cao/2026-10-15_ai09_du_lieu_than/](docs/bao_cao/2026-10-15_ai09_du_lieu_than/README.md)
  - **D1 8 người, 16/10** (thêm 107, 108; N2 chỉ đầu, 3 seed, máy thứ hai): Macro-F1 INT8 TB **0,9772** (0,9707 / 0,9803 / 0,9806); trên cùng người kiểm 101–106: 0,9762 so với 0,9683 khi chỉ huấn luyện 6 người (so có cặp); recall sự kiện T_SCORE 0 / 8: **99,6 % / 97,7 %**; phiếu 2/3 nhầm T_SCORE 8 TB 4,15/giờ (6 người: 8,0). Người 105 vẫn yếu nhất (0,86–0,95). N2 + dữ liệu thân trên 8 người: đang chạy. Tái lập `n2_d1` trên máy thứ hai: 0,9591 so với 0,9584 (không trùng từng bit, chênh ≪ phương sai seed). [ai09_8_nguoi](docs/bao_cao/2026-10-16_ai09_8_nguoi/README.md)
  - **Chốt 16/10 (8 người, chỉ đầu, 3 seed): N2 cho phần cứng.** N1 Macro-F1 0,842, recall sự kiện T0 / T8 87,0 / 83,2 %, phiếu nhầm 15,3/giờ, so với N2 0,977, 99,6 / 97,7 %, 4,15/giờ. Đầu + thân: 0,970, 99,2 % ở T8 nhưng phiếu nhầm 8,21/giờ (gấp đôi), nên bỏ dữ liệu thân, đúng như nhóm đã quyết. [ai09_8_nguoi](docs/bao_cao/2026-10-16_ai09_8_nguoi/README.md)
  - **D1 11 người, 16/10 tối** (N2 chỉ đầu, 3 seed, máy gốc): Macro-F1 INT8 TB **0,9828** (0,9823 / 0,9813 / 0,9847); recall sự kiện T_SCORE 0 / 8: **99,6 % / 97,7 %**; phiếu nhầm T_SCORE 8 TB 3,10/giờ; người 105 vẫn yếu nhất (0,924–0,964), người 109 lọt 1–5/119. Mô hình cuối seed 20261014 (chọn trước) vào bitstream 3. [n2_11_nguoi](docs/bao_cao/2026-10-16_n2_11_nguoi/README.md)
- [ ] **AI-10** (G5·2) Chốt `T_SCORE`, `VOTE_K`; phát lại toàn bộ dữ liệu qua golden + FSM để chốt `T_STILL_A`, `T_STILL_G`, `T_TILT` — *Pass:* ≥ 95 % cú ngã tới PRE_ALARM; 0 PRE_ALARM trên file NORMAL; ≤ 10 % sự kiện IMPACT gây PRE_ALARM
  - **Sơ bộ 14/10 trên D1:** [tools/playback_d1.py](tools/playback_d1.py) phát lại 604 cú ngã + 2,65 giờ sinh hoạt qua mô hình LOSO + `safety_model.py` (trùng `safety.c` trên 240.000 tick). N2-S với tham số A.8 hiện tại: ngã → SUSPECT 98,7 %, trễ trung vị **0,84 s** (p90 1,03 s); ngã **kết thúc nằm** → PRE_ALARM **97,0 %**; ngã rồi đứng dậy → PRE_ALARM 0/120 (đúng); trễ PRE_ALARM 4,08 s (p90 5,32 s); **PRE_ALARM giả 5,66/giờ**. Quét 36 cấu hình: chưa cấu hình nào đạt cùng lúc ≥ 95 % và ≤ 1/giờ; ứng viên 3/3 phiếu, T_SCORE 8: 92,1 % và 1,13/giờ. Các số này dùng mô hình N2-S seed 20261014 (seed may).
  - **Sửa 15/10, trung bình 3 seed:** mọi cấu hình đều có **5,8–10 PRE_ALARM giả/giờ**; N2, 2/3 phiếu, T_SCORE 8: ngã nằm → PRE_ALARM 95,5 %, đứng dậy 0/360, 5,91 giả/giờ, trễ 4,08 / 5,25 s. ⚠️ Chỉ tiêu ≤ 1/giờ có rủi ro thật nếu chỉ dùng D1. Đường giảm: D2 NORMAL đội mũ (nằm, cúi, vấp) → WEAR → STILL_BLOCKS 10–12 → gộp 2–3 mô hình (E2 P = 4 chạy 3 lần vẫn < 5 ms). Đã thử gộp 3 seed N2: T_SCORE 8 → 95,7 % ngã nằm, 4,91 giả/giờ (giảm ≈ 17 %), chưa đủ
  - **SPEC v3.1 (15/10): điều kiện nghiêng hai phía `|az_tb| < T_TILT`.** 15/22 báo giả có đầu lộn ngược (cúi gập, `az_tb` ≈ −2040); 375/375 cú ngã nằm có `az_tb` ≥ −1074. Sau v3.1 (3 seed): N2, T_SCORE 8: ngã nằm 95,5 %, **1,26 giả/giờ** (trước 5,91); **gộp 3 seed N2: 95,7 %, 0,75 giả/giờ**, lần đầu đạt cả hai ngưỡng trên D1. Còn lại: 815 (nằm giường), 805 (cúi 90°). Giữ T_TILT 45° (60° mất 10–13 điểm). Bằng chứng: [docs/bao_cao/2026-10-14_ai10_playback/](docs/bao_cao/2026-10-14_ai10_playback/README.md), mục v3.1
  - Pass hiện ghi "≥ 95 % cú ngã tới PRE_ALARM" mâu thuẫn với định nghĩa hệ thống (chỉ báo động khi người **nằm** bất động): 4 kiểu ngã của D1 có đứng dậy và không được báo. Đề nghị sửa thành "≥ 95 % cú ngã kết thúc nằm tới PRE_ALARM; 0 cú ngã có đứng dậy tới ALARM" — chờ nhóm duyệt (X15)
  - **X15 đã đo 15/10** (`playback_d1.py --still-upright N`, chỉ là thí nghiệm, SPEC không đổi): thêm nhánh "bất động ≥ N khối dù đầu thẳng" bắt ngã quỳ/ngồi 85 / 76 / 53 % (N = 12 / 16 / 20) nhưng cũng báo **69 / 36 / 3 % cú ngã đã đứng dậy** và tăng PRE_ALARM giả lên 3,78 / 2,14 / 1,76 lần/giờ (từ 1,26). Đề nghị giữ v3.1, ngã ngồi dùng SOS. Bằng chứng: [docs/bao_cao/2026-10-15_x15_nga_ngoi/](docs/bao_cao/2026-10-15_x15_nga_ngoi/README.md)
  - **D1 8 người, 16/10** (N2 chỉ đầu, 3 seed, SPEC v3.1, 840 cú ngã, 3,88 giờ sinh hoạt): T_SCORE 8: ngã nằm → PRE_ALARM **96,2 / 96,4 / 96,2 % (TB 96,3 %)**, PRE_ALARM giả **0,77 / 0,77 / 0,51/giờ (TB 0,68)**, gộp 3 seed 95,3 % / 0,26; đứng dậy 0/166; trễ SUSPECT trung vị 0,86–0,88 s; trễ PRE_ALARM trung vị 4,12 s, **p90 5,92 s** (6 người: 5,21 s). Lần đầu trung bình 3 seed đạt cả ≥ 95 % và ≤ 1/giờ trên D1, nhưng chỉ 2–3 lần báo giả nên khoảng tin cậy rộng; vẫn phải đo trên mũ. Theo đúng điều kiện của đề cương ("≤ 5 s khi người nằm yên trong 2 s sau va chạm"): 366 cú ngã nằm đạt điều kiện → PRE_ALARM 355/366, trễ trung vị 3,83 s, **p90 4,36 s, lớn nhất 4,56 s, 0 cú > 5 s** (cả 3 seed); p90 5,92 s đến từ những cú ngã còn cử động quá 2 s. [ai09_8_nguoi](docs/bao_cao/2026-10-16_ai09_8_nguoi/README.md)
  - **D1 11 người, 16/10 tối** (SPEC v3.1, 1.180 cú ngã, 5,43 giờ sinh hoạt): T_SCORE 8: ngã nằm → PRE_ALARM **96,4 / 95,8 / 96,4 % (TB 96,2 %)**, PRE_ALARM giả **0,92 / 0,74 / 1,66/giờ (TB 1,11)**, gộp 3 seed 95,6 % / 0,74; đứng dậy 0/234; mọi báo giả từ 815 (nằm xuống giường). T_SCORE 16: 0 / 0,37 / 0,92 giả/giờ nhưng ngã nằm 93,8 / 91,9 / 93,1 %. Trễ khi nằm yên trong 2 s: p90 4,32 s, lớn nhất 4,56 s, 0 cú > 5 s. Đề nghị giữ T_SCORE 8, chốt sau buổi thử đội mũ (≥ 2 giờ). [n2_11_nguoi](docs/bao_cao/2026-10-16_n2_11_nguoi/README.md)
- [ ] **AI-11** (G6·2) Bảng FP32 / INT8 / RTL; recall sự kiện; báo giả mỗi giờ tính trên bản ghi — *Pass:* có bảng và confusion matrix trong `docs/bao_cao/`
  - **Bản cho mô hình lên chip, 16/10** (N2 11 người): FP32 → INT8 mất ≤ 0,0001 Macro-F1; ma trận nhầm lẫn cộng 3 seed: NORMAL → FALL 658 / 318.641 (0,21 %), FALL lọt 92 / 10.611; RTL `tb_e2` 50/50, netlist sau P&R PASS, mô phỏng ghép firmware ↔ RTL 423/423. Bằng chứng: [n2_11_nguoi](docs/bao_cao/2026-10-16_n2_11_nguoi/README.md) mục 5. Pass vẫn cần số trên buổi thử đội mũ
  - **Bảng sơ bộ 15/10 trên D1** (N2, N2-S × 3 seed): FP32 → INT8 mất ≤ 0,15 điểm Macro-F1; INT8 → RTL mất 0 (trùng từng bit, kể cả netlist sau P&R); ma trận nhầm lẫn N2 cộng 3 seed: FALL lọt 111/5.436, NORMAL → FALL 698/154.059 (0,45 %). Phương sai theo seed lớn gấp > 40 lần sai số lượng tử. Bằng chứng: [docs/bao_cao/2026-10-15_ai11_bang_so_bo/](docs/bao_cao/2026-10-15_ai11_bang_so_bo/README.md). Pass cần mô hình cuối trên D1 + D2 + D3
- [ ] **AI-12** (·3) Lớp thứ tư (suýt ngã); thử huấn luyện trước bằng bộ ở cổ (FallAllD) hoặc ở thắt lưng (SisFall)
- [ ] **AI-13** (G1·1) Nguồn D1: bộ "Simulated Falls and Daily Living Activities" của Özdemir và Barshan (UCI, số 455; 1,24 GB; CC BY 4.0) — bộ công khai duy nhất tìm được có cảm biến ở **đầu** (Xsens MTw, 25 Hz, gia tốc m/s², gyro rad/s). [tools/convert_d1.py](tools/convert_d1.py) lấy kênh đầu, xoay trục về quy ước của mũ cho từng người, nội suy 25 → 50 Hz, đổi về thang INT8 của A.2, cắt cửa sổ và gán nhãn theo A.4; [tools/plot_d1.py](tools/plot_d1.py) vẽ 20 kiểu ngã — *Pass:* đủ 17 người; mỗi người qua ba phép kiểm vị trí đầu; kênh Z khi đi bộ đọc 16 ± 2 mức; có biểu đồ mỗi kiểu ngã
  - **Đã xong 13/10 cho 6/17 người** (101–106): 604 cú ngã + 499 hoạt động thường ngày; kênh Z đọc 15,2–16,0 mức; 604/604 cú ngã có đủ 3 cửa sổ dương; chỉ 0,003 % mẫu vượt 7,94 g và 0,05 % vượt 496 °/s nên thang INT8 hiện tại vừa. Bằng chứng: [docs/bao_cao/2026-10-13_d1_dau/](docs/bao_cao/2026-10-13_d1_dau/)
  - **Mã cảm biến ở đầu là 340540.** `Information.pdf` đi kèm ghi 340506 là đầu, nhưng trên cả 6 người thì 340506 quay 1,63–2,20 rad/s khi đi bộ, chỉ nghiêng 13–19° khi cúi và không đổi độ cao khi ngã (dấu hiệu của cổ chân); 340540 thì 0,16–0,39 rad/s, 71–106° và đổi độ cao nhiều nhất
  - **16/10: lên 8/17 người** (thêm 107, 108; máy thứ hai, [tools/fetch_d1.sh](tools/fetch_d1.sh) giải các người đã tải trọn từ file zip 643 MB tải dở). 840 cú ngã, 840/840 đủ 3 cửa sổ dương; 107 và 108 qua đủ ba phép kiểm vị trí đầu (340540: 0,28 / 0,31 rad/s, 82° / 110°, +0,080 / +0,099 hPa; kênh Z 15,3 mức). Phần 101–106 trùng từng byte bản cũ ở cả 3 cảm biến. Bản sao Kaggle thiếu nhiều file, không dùng. Bằng chứng: [docs/bao_cao/2026-10-16_d1_8_nguoi/](docs/bao_cao/2026-10-16_d1_8_nguoi/README.md)
  - **16/10 trưa: lên 11/17 người** (thêm 109, 110, 203 từ một lượt tải 840 MB). 203 lệch ở gyro và độ nghiêng khi cúi, nhưng Δp khi ngã của 340540 lớn nhất trong 6 cảm biến của chính người đó, nên vẫn là đầu. [d1_11_nguoi](docs/bao_cao/2026-10-16_d1_11_nguoi/README.md)
  - Còn lại: 6 người, cần một kết nối tới UCI giữ được khoảng 35–50 phút (mỗi kết nối 0,4–0,6 MB/s, không nhận Range, bị cắt sau 16–25 phút) rồi chạy `tools/fetch_d1.sh`; xác nhận độc lập mã cảm biến (X14)
- [ ] **AI-14** (G3·1) Đo độ chênh giữa D1 và dữ liệu trên mũ, rẻ trước: (1) so phổ lúc đi bộ của D1 với D2 ở băng 12,5–25 Hz; (2) cho mô hình của AI-07 chạy trên các cú ngã thu thử của AI-03 và lập bảng nhầm lẫn — *Pass:* recall sự kiện ≥ 80 % và ≤ 10 % cú ngã bị gọi là IMPACT. *Không đạt thì lần lượt:* (a) lọc thêm `[1,2,1]/4` ở 50 Hz trên cả MCU lẫn pipeline để hai nguồn cùng băng tần (−6 dB ở 12,5 Hz, −20 dB ở 20 Hz; phải nâng SPEC lên v3.1 và sinh lại vector); (b) thêm SisFall đã giảm về 50 Hz để mạng thấy cú ngã có đủ băng tần tới 25 Hz; (c) tinh chỉnh bằng một nửa D3, đánh giá trên nửa kia, tách người; (d) quay về kế hoạch cũ: tự thu ≥ 250 cú ngã từ ≥ 8 người, mất khoảng 1 tuần
  - **Chuẩn bị bước (1), 15/10:** [tools/spectrum_check.py](tools/spectrum_check.py) đo tỉ lệ công suất 12,5–25 Hz / 0,5–25 Hz của tín hiệu vào mạng lúc đi bộ. **D1 (32 bản ghi đi bộ): 0,06–0,49 % tùy trục**, tức băng này gần như trống như dự đoán; đối chứng thêm sóng 15 Hz thì 3–15 %. Khi có D2: `--log ml/data/raw/*_di_bo_*.csv` in tỉ số mũ / D1 theo trục. Bằng chứng: [docs/bao_cao/2026-10-15_ai14_pho_d1/](docs/bao_cao/2026-10-15_ai14_pho_d1/pho_d1_di_bo.log)

### RTL-A — giao tiếp và lên chip

- [x] **RA-00** (G0·1) RTL P = 1 đầy đủ, tổng hợp và P&R xong — *Pass:* có bitstream và báo cáo ✅
- [x] **RA-01** (G0·1) Sửa R1, R8: `cnn_params.vh` sinh từ `quant_params.json`; testbench 20 vector thay cho 1 vector; sửa giá trị mong đợi cũ trong testbench, README, `.bat` — *Pass:* 20/20 ✅ 14/10
  - `python -I tools/gen_cnn_params.py` ghi `src/cnn_params.vh`, `tb/vec_in.mem`, `tb/vec_exp.mem`; `fpga_top.v` và `tb_cnn_core_golden.v` include `cnn_params.vh`; `run_golden_sim.bat` gọi script rồi chạy `iverilog -g2001 -I src`. Project không có README nên không phải sửa
  - Kết quả trên bản sao: 20/20 khớp, 699.800 chu kỳ. Phép âm: ép `.vh` về shift 7 → 0/20; sửa json thành 7 mà không xuất lại vector → script dừng, mã thoát 1. P&R: Logic 913, Register 589, BSRAM 6/46, DSP 1,25/24, Fmax 108,49 MHz, sáu cổng đúng ball. Bằng chứng: [docs/bao_cao/2026-10-14_ra01_conv1_shift/](docs/bao_cao/2026-10-14_ra01_conv1_shift/README.md)
  - Bitstream trong `impl/` của đồng đội **chưa** được build lại (không ghi đè). Người giữ project mở Gowin, Run All để có bitstream shift 8 trước RA-04. **15/10:** đã có sẵn ở [bitstreams/1_e1_proto1_sisfall/](bitstreams/README.md), dựng từ cùng mã nguồn (108,49 MHz lúc dựng đầu; dựng lại chiều 15/10 sau khi sửa `conv_start`: Logic 907, 105,20 MHz)
- [ ] **RA-02** (G2·1) Sửa R2, R10: chân SPI/IRQ trên J1 theo Phụ lục E.3 (đã ghi vào `fpga_top.cst`, pin report đúng chân và đúng 3,3 V ngày 13/10). Còn lại: dò 6 chân trên board bằng `rtl/pin_probe`; thêm cổng `rst_n` và `top.sdc` — *Pass:* 6 chân đo đúng vị trí trên J1; P&R không cảnh báo thiếu ràng buộc clock
  - **14/10:** `rtl/v3/top.sdc` (cho `fpga_top`) và `rtl/v3/fpga_top_v3.sdc` + `.cst` (thêm `rst_n` ở J11) đã qua P&R: không còn cảnh báo về clock; `fpga_top` giữ đúng Logic 913, Fmax 108,49 MHz. Còn lại: dò 6 chân trên board
- [x] **RA-03** (G2·1) Giao thức v3 (A.7) trong `packet_parser` và `spi_result_tx`: CRC-16, SEQ, STATUS, đuôi 13 byte; sửa R3, R4, R5 — *Pass:* `tb_proto`: 50 khung đúng; CRC sai; khung thiếu byte; khung khi đang bận; hai khung sát nhau ✅ 14/10 (mô phỏng)
  - Top mới [rtl/v3/fpga_top_v3.v](rtl/v3/fpga_top_v3.v) với `packet_parser_v3`, `result_frame_v3`, `spi_result_tx_v3`, `crc16_ccitt`, cổng `rst_n`, bộ đếm `CYCLES`; `fpga_top` (PROTO 1) giữ nguyên cho RA-04. `cnn_core` thêm 4 cổng ra logit
  - `bash rtl/v3/run_tb_proto.sh --ng 50`: 50/50 khung đúng (4 lớp, có LFSR và cực trị), CYCLES = 699.800; CRC sai → STATUS 0x00; thiếu byte → 0x04; khung đến khi bận → 0x07 và khung trước vẫn đúng; byte đầu sai → bỏ qua; RUN 7 byte; RST_N. Phép âm 5/5 bị bắt
  - P&R `fpga_top_v3`: Logic 1.522 (8 %), Register 952, BSRAM 6/46, DSP 1,25/24, **Fmax 102,74 MHz**, 0 cảnh báo. Bằng chứng: [docs/bao_cao/2026-10-14_ra03_proto_v3/](docs/bao_cao/2026-10-14_ra03_proto_v3/README.md)
  - Người giữ project Gowin thêm các file `rtl/v3/` và chọn top `fpga_top_v3` sau khi RA-04 thông mạch bằng PROTO 1
- [ ] **RA-04** (G2·1) Thông mạch lần đầu bằng **RTL hiện có** (chỉ cần RA-01 và RA-02, làm **trước** RA-03), rồi thử nấc với FW-09 ở SCK 1 MHz và 4 MHz — *Pass:* như FW-09, có ảnh logic analyzer. Không cần viết `top_link.v`
- [ ] **RA-05** (G2·1) Nạp E1 đầy đủ với weight hiện có — *Pass:* 20 vector qua HIL khớp golden; `CYCLES` ≈ 700.000
  - **Chuẩn bị 15/10 (mô phỏng ghép, không thay HIL):** [tools/cosim.py](tools/cosim.py) nối mã máy firmware (Unicorn) với RTL top v3 + E2 (Icarus) qua chân SPI trên 137,7 s dữ liệu ngã thật của D1: **423/423 khung khớp golden từng byte** theo cả hai chiều, Safety FSM của firmware trùng chuỗi golden. Bằng chứng: [docs/bao_cao/2026-10-15_cosim_fw_rtl/](docs/bao_cao/2026-10-15_cosim_fw_rtl/README.md)
- [ ] **RA-06** (G4·1) Tổng hợp bản tầng 1 với weight huấn luyện trên D1 (v2.1) — *Pass:* RAM/ROM thành BSRAM, không vi phạm timing; lưu báo cáo
- [x] **RA-07** (G5·2) Đưa E2 vào top qua tham số `ENGINE`; `argmax_score` (thêm SCORE = top1 − top2 vào `argmax4` đã 2 tầng); RST_N — *Pass:* `tb_top` 50/50; Fmax ≥ 55 MHz ✅ 14/10 (mô phỏng)
  - `rtl/v3/fpga_top_v3.v` chọn E1 hoặc E2 bằng macro `CNN_ENGINE_E2` trong `cnn_params.vh` (do `export_mem.py` sinh, một nguồn); SCORE = top1 − top2 ở `result_frame_v3`; RST_N. `run_tb_proto.sh --e2 ... --ng 50`: N2-S P = 1 và P = 4 đều 50/50 + 7 kịch bản lỗi. P&R: **105,58 MHz** (P = 1), 91,25 MHz (P = 4), 0 cảnh báo. Bằng chứng: [docs/bao_cao/2026-10-14_rb03_rb04_e2/](docs/bao_cao/2026-10-14_rb03_rb04_e2/README.md)
  - Phát hiện khi chạy P = 4: suy luận (0,8 ms) ngắn hơn một khung ghi (1,54 ms), nên hai khung gửi sát nhau làm kết quả khung trước bị khung lỗi BUSY thay thế. Ghi thành quy ước ở A.7 (một bộ đệm kết quả, bản mới nhất thắng; MCU chờ kết quả rồi mới gửi khung mới — firmware đã làm vậy)
- [x] **RA-08** (G5·2) Báo cáo tài nguyên, timing, công suất bản tầng 2 — *Pass:* Logic ≤ 20 %, BSRAM ≤ 25 %, DSP ≤ 25 % ✅ 14/10 (mô phỏng)
  - Top v3 + E2 N2-S: P = 1 Logic 1.476 (8 %), BSRAM 6/46 (14 %), DSP 2,25/24 (10 %), 105,58 MHz, 156,7 mW (ước lượng công cụ, tĩnh 122,8 + động 33,9); P = 4 Logic 1.870 (10 %), 6/46, 2,25/24, 91,25 MHz, 156,9 mW. Chưa đo dòng thật (TH-10)
- [ ] **RA-09** (·3) Cập nhật weight qua SPI (lệnh 0xA6, ROM → RAM); BIST bằng nút BTN1 trên Kiwi (ball A12)

### RTL-B — khối tính toán

- [x] **RB-01** (G0·1) `rtl/tb/run_all` chạy mọi testbench và in bảng PASS/FAIL — *Pass:* chạy được trên cả Icarus 0.9.7 và bản mới
  - **Nửa Icarus 12.0 xong 15/10** (máy thứ hai, clone từ GitHub): 7/7 PASS, ≈ 9,7 phút; 7 cảnh báo `$readmemh … Too many words` vô hại (file 50 vector, `TB_NV=10`). Bằng chứng: [docs/bao_cao/2026-10-15_may2_icarus12/](docs/bao_cao/2026-10-15_may2_icarus12/README.md)
  - **Nửa trên Icarus 0.9.7 xong 14/10:** [rtl/tb/run_all.sh](rtl/tb/run_all.sh) chép project sang thư mục tạm (không đụng `impl/`, `src/` của đồng đội), sinh tham số bằng `gen_cnn_params.py`, chạy 3 testbench: `tb_pin_probe` PASS, **`tb_top_spi` PASS** (mới, xem dưới), `tb_cnn_core_golden` PASS 20/20; tổng ≈ 2,5 phút. `--export <thư mục>` chạy cùng bộ test với weight khác. Bằng chứng: [docs/bao_cao/2026-10-14_rb01_run_all/](docs/bao_cao/2026-10-14_rb01_run_all/)
  - `rtl/tb/tb_top_spi.v`: lần đầu kiểm `fpga_top` **qua chân SPI** (tầng kiểm 3). Đưa vào đúng khung PROTO 1 mà firmware sinh, SCK 4 MHz mode 0, chờ IRQ, đọc 7 byte: 4/4 khung khớp golden từng byte, IRQ về 0 sau khi đọc; khung sai CRC-8 không bật IRQ, khung đúng ngay sau vẫn chạy. rPLL của Gowin thay bằng `rtl/tb/pll_50m_sim.v` (`clkout = clkin`) khi mô phỏng
  - 15/10: `run_all.sh` chạy thêm `tb_e1_layers` (RB-02), `tb_proto` (giao thức v3, E1) và `tb_e2` (P = 1 và 4, so từng tầng); **7/7 PASS** trên Icarus 0.9.7, ≈ 4,5 phút. Log ở cùng thư mục bằng chứng
  - Còn lại: chạy trên một bản Icarus mới (11 hoặc 12), máy này chỉ có 0.9.7
- [x] **RB-02** (G2·1) Testbench từng tầng cho E1: so `l1`, `l2`, `feat`, `logit` — *Pass:* 50/50 ở mỗi tầng ✅ 15/10 (mô phỏng)
  - [rtl/tb/tb_e1_layers.v](rtl/tb/tb_e1_layers.v) chụp RAM B khi `stage` sang CONV2 (l1) và GAP (l2), `gap_buffer` khi sang DENSE (feat), rồi so logit + lớp. 50 vector của `export_mem.py` (FALL/NORMAL, LFSR, cực trị): **50/50 ở mọi tầng** với weight SisFall của nhóm và với N1 huấn luyện trên D1. Chạy trong `rtl/tb/run_all.sh`. Bằng chứng: [docs/bao_cao/2026-10-15_rb02_e1_tung_tang/](docs/bao_cao/2026-10-15_rb02_e1_tung_tang/)
- [ ] **RB-02b** (G5·2) E1 mở rộng cho N2 (mục 4.1): tổng quát hóa `conv1d_engine`, `maxpool1d_engine`, `cnn_controller`, `dense_engine` và hai ROM — *Pass:* 50/50 ở mọi tầng với N2; N1 vẫn khớp 20/20; `CYCLES` ≈ 702.000
- [x] **RB-03** (G3·2) E2: `mac_lane`, `conv_engine2` chạy lớp C1 với P = 1 — *Pass:* 50/50 với `l1` ✅ 14/10 (mô phỏng)
  - [rtl/e2/cnn_e2.v](rtl/e2/cnn_e2.v): một module gồm đường MAC `LANES` làn, bộ điều khiển và hai RAM đặc trưng thay cho `mac_lane` + `conv_engine2` tách rời. `tb_e2` so l1 50/50 (và mọi tầng sau). Bằng chứng: [docs/bao_cao/2026-10-14_rb03_rb04_e2/](docs/bao_cao/2026-10-14_rb03_rb04_e2/README.md)
- [x] **RB-04** (G5·2) E2 đủ C1–C3, Dense trên flatten, GAP tùy chọn, `argmax_score`, `CYCLES` — *Pass:* 50/50 ở mọi tầng cho cả N1 và N2; `CYCLES` ≤ 300.000 ✅ 14/10 (mô phỏng)
  - `bash rtl/e2/run_tb_e2.sh <thư mục export_mem.py --engine e2> 50`: so **từng tầng** (l1, l2, l3 chụp từ RAM A/B) và 4 logit. N1 SisFall (GAP) và N2, N2-S, N2-L (Flatten) với P = 1, 2, 4: **12/12 cấu hình 50/50 ở mọi tầng**; mô hình kiểm hòa cho đúng lớp 0. Chạy lại 15/10 sau khi dọn: 14/14 (cả 2 bản kiểm hòa) PASS. N2, P = 1: **258.080 chu kỳ = 5,15 ms**; N2-S, P = 1: 132.896 = 2,65 ms. Phép âm 6/6. Bằng chứng: [docs/bao_cao/2026-10-14_rb03_rb04_e2/](docs/bao_cao/2026-10-14_rb03_rb04_e2/README.md)
- [ ] **RB-05** (·3) P = 4 — *Pass:* khớp như RB-04; `CYCLES` ≤ 100.000
  - Đạt trong mô phỏng 14/10 như sản phẩm phụ của tham số `LANES`: N2, P = 4: 75.284 chu kỳ = 1,50 ms ≤ 100.000; N2-S, P = 4: 39.956 = 0,80 ms. Tầng 3 nên không tính vào % cho tới khi G6 qua
- [ ] **RB-06** (·3) Thêm tầng pipeline để Fmax ≥ 100 MHz
  - Top v3 + E2 N2-S, P = 1 đạt 105,58 MHz trong P&R 14/10 mà chưa cần thêm tầng; P = 4 đạt 91,25 MHz. Tầng 3, không tính

### TH — tích hợp, đo đạc, tài liệu

- [ ] **TH-01** (G0·1) Repo Git; cấu trúc `docs/ firmware/ rtl/ ml/ tools/`; chép Phụ lục A thành `docs/spec.md`; tạo `docs/bao_cao/` — *Pass:* cả nhóm clone được
  - 15/10: repo GitHub private `danhle396/fpga2026gowin`; cấu trúc và `docs/bao_cao/` có sẵn. `docs/spec.md` sinh bằng `tools/sync_spec.py` từ Phụ lục A (bản gốc vẫn là Phụ lục A; `--check` báo lệch). Máy thứ hai đã clone và chạy được cả chuỗi kiểm ([may2_icarus12](docs/bao_cao/2026-10-15_may2_icarus12/README.md)). **Còn thiếu:** từng thành viên tự clone được (mời vào repo private)
- [ ] **TH-02** (G0·1) Xác nhận Phụ lục E trên board thật: tìm sơ đồ `32F407 EVK V1.0.pdf` và chép vào `docs/datasheet/` (sơ đồ Kiwi và datasheet MCU đã chép 14/10); tám chân MCU mới chọn ở E.1 có ra header và còn trống không; dò 6 chân J1 của Kiwi theo E.4 — *Pass:* mọi dòng ở E.1 có dấu "đã kiểm"; không chân nào trùng chân nạp; đo I/O hai board đều 3,3 V
- [ ] **TH-03** (G0·1) Vật tư: logic analyzer 8 kênh, mũ bảo hộ, một nút nhấn (v2.1, nối song song SW3: P2.4 xuống GND), đệm ≥ 10 cm, power bank, cáp 4 lõi ≤ 50 cm — *Pass:* đủ đồ
- [ ] **TH-04** (G1·1) Gắn IMU lên mũ theo A.1; ghi `AZ_dung_yen` — *Pass:* lắc mạnh không lỏng; giá trị ≈ +2048
- [ ] **TH-05** (G2·1) Ảnh logic analyzer một giao dịch ghi, một giao dịch đọc — *Pass:* lưu trong `docs/bao_cao/`
- [ ] **TH-06** (G3·1) An toàn và tổ chức buổi thu: đệm, bảo hộ, người đứng cạnh, giấy đồng ý — *Pass:* mọi người tham gia đã ký
- [ ] **TH-07** (G4·1) `tools/hil_test.py`; chạy HIL — *Pass:* ≥ 500 cửa sổ, 0 sai lệch CLASS, SCORE, 4 LOGIT
  - **Công cụ xong 14/10:** [tools/hil_test.py](tools/hil_test.py): cửa sổ D1 thật + LFSR + cực trị + ngẫu nhiên, đáp án từ golden, PROTO 1 hoặc 3. Thử bằng `--mock`: 500/500; cài 1 lỗi logit → bắt được ở cả hai giao thức
- [ ] **TH-08** (G4·1) Mũ bản 1: hộp hai board + pin, đầu nối chắc, thử tầng 1 — *Pass:* điều kiện cổng G4
- [ ] **TH-09** (G5·2) HIL với E2 — *Pass:* ≥ 2.000 cửa sổ, 0 sai lệch
- [ ] **TH-10** (G6·2) Thử thực địa — *Pass:* ≥ 2 người lạ, ≥ 18/20 cú ngã vào PRE_ALARM; ≥ 2 giờ tổng từ ≥ 2 người ≤ 1 báo giả/giờ; va mũ khi đang đội 20 lần ≥ 18 lần không vào PRE_ALARM; rơi mũ 20 lần: đếm số lần vào PRE_ALARM, mọi lần hủy được bằng CANCEL (v2.1); SUSPECT ≤ 1,5 s, PRE_ALARM ≤ 5 s; đo dòng 5 V từng board
  - **Công cụ chấm sẵn 16/10:** [tools/playback_log.py](tools/playback_log.py) phát lại file LOG của buổi thử qua đúng chuỗi của thiết bị (trùng mã máy `app_core.c` 15/15 lần đổi trạng thái) và in Pass: ngã kết thúc nằm → PRE_ALARM, ngã rồi đứng dậy phải 0, báo giả/giờ trên file đội mũ (tự hủy sau 2 s để đếm đủ), va mũ → PRE_ALARM (đường lùi IMPACT). [playback_log](docs/bao_cao/2026-10-16_playback_log/README.md)
- [ ] **TH-11** (G7·2) Báo cáo, slide, video dự phòng, README build, gắn tag — *Pass:* giảng viên hướng dẫn duyệt
- [ ] **TH-12** (G1 · tùy chọn; nhóm có ESP32) Mạch ghi dữ liệu: `test_sensor/esp32/mpu6050_test.py` đổi sang thang A.1 (dòng 22–23 và 157: `0x18`; ngưỡng dòng 224–229), thêm một chân nút đánh dấu — *Pass:* T1..T7 PASS; 10 phút không mất mẫu; file đọc được bằng `tools/logger.py`. Thay được FW-04..06 trong điều kiện của G1; firmware SN32 vẫn phải có trước G2
- [ ] **TH-13** (G2 · tùy chọn; nhóm có ESP32) Đồ gá SPI: ESP32 làm master (3,3 V), PC điều khiển qua cổng nối tiếp, gửi khung và đọc kết quả — *Pass:* 20 vector khớp golden. Cho phép kiểm FPGA trên chip (RA-05, TH-07, TH-09) mà không chờ `spi_fpga.c` của SN32. Cách khác không cần nối dây: thêm `uart_rx`/`uart_tx` vào RTL và đi qua CH340N có sẵn trên Kiwi (FPGA nhận ở C4, phát ở B5)

---

## 7. Chiến lược kiểm chứng

Tầng dưới đúng thì tầng trên mới có nghĩa. Tầng trên báo lỗi thì **lùi xuống tầng dưới** mà tìm.

| Tầng kiểm | Nội dung | Việc |
|---|---|---|
| 8 | Thử thực địa trên người | TH-10 |
| 7 | Phát lại dữ liệu qua golden + FSM trên PC | FW-11, AI-10 |
| 6 | Tiền xử lý của MCU: CRC khung so với Python | FW-10 |
| 5 | HIL: PC → MCU → FPGA → PC, so từng bit (trước khi có board: mô phỏng ghép `tools/cosim.py`) | TH-07, TH-09 |
| 4 | Tự kiểm khi bật nguồn bằng khung LFSR | FW-14 |
| 3 | Testbench `tb_top` qua chân SPI | RA-03, RA-07 |
| 2 | Testbench từng tầng so test vector | RB-02..04 |
| 1 | Python: golden model, tiền xử lý, CRC | AI-02 |

Quy tắc testbench: đọc file bằng `$readmemh`, tự so, in `PASS` hoặc `FAIL tại phần tử i: mong đợi X, nhận Y`. Không kết luận "đúng" bằng cách nhìn dạng sóng.

---

## 8. Sổ tay gỡ lỗi

| Triệu chứng | Nguyên nhân hay gặp | Phép thử, từ rẻ đến đắt |
|---|---|---|
| RTL ra logit khác golden ở mọi vector | Sai shift (R1) hoặc sai file `.mem` | So `cnn_params.vh` với `quant_params.json`; chạy testbench 20 vector |
| Lệch ở vài phần tử đầu/cuối mỗi lớp | Padding sai | So phần tử `t` = 0, 1, L−2, L−1 của `l1` |
| Kết quả lệch đúng một nhịp hoặc lặp giá trị cũ | `valid` không trễ theo BSRAM | Xem dạng sóng địa chỉ – dữ liệu – valid quanh một dải |
| Số âm thành số dương rất lớn | Thiếu `signed` hoặc dùng `>>` thay `>>>` | Testbench `mac` với −128 × −127 |
| Mô phỏng đúng, chip sai | ROM chưa khởi tạo, timing vi phạm, sai chân | Tự kiểm LFSR; báo cáo timing; GAO đọc ROM |
| MCU nhận toàn 0x00 | Đọc khi chưa có kết quả, hoặc sai chân MISO | Xem IRQ trước khi đọc; logic analyzer |
| SPI lệch 1 bit | Sai mode, hoặc SCK quá nhanh so với trễ MISO ≈ 68 ns | Hạ SCK xuống 1 MHz |
| SPI lúc được lúc không | Thiếu GND chung, dây dài, I/O 1,8 V | Thêm GND cạnh SCK; kiểm `IO_TYPE` |
| SPI không có tín hiệu nào dù firmware đúng | Cắm lệch hàng chân chẵn/lẻ của J1 | Nạp `rtl/pin_probe`, đo lại 6 chân (E.4) |
| CRC luôn sai | Khác phạm vi tính hoặc thứ tự byte | `"123456789"` phải ra 0x29B1 ở C, Python, Verilog |
| Mọi khung sau một khung lỗi đều sai | Parser không đồng bộ lại theo CS (R3) | Gửi một khung thiếu byte rồi một khung đúng |
| Đọc MPU6050 toàn 0 | Chưa thoát sleep | `PWR_MGMT_1 = 0x01` |
| `|a|` ≈ 4096 thay vì 2048 | Còn thang ±8 g | `ACCEL_CONFIG = 0x18` |
| Mất mẫu | Một khe vượt 10 ms | Bật/tắt GPIO quanh từng việc, đo bằng logic analyzer |
| Khung MCU khác khung Python | Sai pha giảm mẫu hoặc sai thứ tự `ring` | So 6 mẫu đầu và 6 mẫu cuối của một khung ở chế độ TRC |
| I²C treo sau reset | Slave giữ SDA | 9 xung SCL bằng GPIO lúc khởi động |
| MCU hoặc FPGA nóng, đọc sai | VDD của EVK đang là 5 V (SW1 hoặc jumper J1 sai) | Đặt theo E.4 bước 1, đo VDD trước khi cắm dây |
| Khung SPI đọc về sai lẻ tẻ, MISO có hai mức lạ | Flash SPI của EVK cũng đang được chọn | Giữ P1.8 mức cao; làm phép thử E.4 bước 2 |
| Huấn luyện 99 % nhưng thử thật kém | Chia ngẫu nhiên theo cửa sổ; mũ gắn lệch chiều | Dùng LOSO; kiểm `AZ_dung_yen` |
| Báo giả khi đặt mũ xuống bàn | Quên tắt hệ thống; mũ nằm nghiêng và bất động | Nhấn nhanh 2 lần để tắt trước khi tháo mũ; CANCEL trong 10 s; đường lùi: lớp IMPACT hoặc quy tắc rơi tự do |
| HIL lệch vài cửa sổ hiếm | Giá trị biên, bão hòa | Lấy đúng cửa sổ đó làm test vector, so từng tầng |

---

## 9. Công tắc tầng và bảng cắt giảm

Mọi tính năng tầng 2–3 tắt được mà không hỏng tầng 1.

| Công tắc | Nơi đặt | Tầng 1 | Tầng 2 | Tắt thì |
|---|---|---|---|---|
| `ENGINE` | tham số top | 1 | 2 | Về E1; sau RB-02b thì E1 vẫn chạy được N2 |
| `P` | tham số E2 | — | 1 | — (4 là tầng 3) |
| `DECIM` | `config.h` + `windowing.py` | 2 | 2 | 1 = mạng nhận 100 Hz, cửa sổ 1,28 s. Chỉ dùng được khi mọi nguồn huấn luyện có ≥ 100 Hz; D1 chỉ có 25 Hz nên hiện không dùng được |
| `VOTE_K` | `config.h` | 1 | 2 | Một cửa sổ FALL là đủ |
| `TILT_EN` | `config.h` | 0 | 1 | Chỉ cần bất động |
| `WEAR_PRESENT` | `firmware/src/board.h` | 0 | 0 (v2.1 bật/tắt bằng nút; chỉ đặt 1 nếu có cảm biến đội mũ trên P2.3) | Coi như luôn đội |
| `BTN_POWER` | `firmware/src/fw_config.h` | 1 | 1 | Nút chỉ còn CANCEL/SOS, hệ thống luôn bật |
| `SOS_EN`, `SELFTEST_EN` | `config.h` | 0 | 1 | Bỏ tính năng |
| `PROTO` | `config.h` + RTL | 3 | 3 | 1 = khung CRC-8 hiện có |
| `GATE_EN` | `config.h` | 0 | 0 | (tầng 3) |

| Nếu… | Thì… | Mất gì |
|---|---|---|
| D1 không dùng được trên mũ (AI-14 không đạt sau các bước a, b, c) | Tự thu ≥ 250 cú ngã từ ≥ 8 người như kế hoạch cũ | Khoảng 1 tuần; phải sửa lại mục dữ liệu của đề cương |
| D2 ít | **Đã áp dụng ở v2.1 (16/10):** gộp IMPACT vào NORMAL (2 lớp), dựa vào nút bật/tắt và FSM; đề cương đã sửa | Macro-F1 thành 2 lớp |
| N2 không hơn N1 | Giữ N1 | Không mất gì |
| E2 chưa xong | Chạy N2 trên E1 mở rộng, ≈ 14 ms | Chỉ mất chỉ tiêu ≤ 6 ms; mô hình và các chỉ tiêu nhận dạng không bị ảnh hưởng |
| Giao thức v3 chậm | `PROTO = 1` | SEQ, STATUS, CRC-16 |
| Timing không đạt 50 MHz | Chạy 27 MHz không PLL, SCK ≤ 2 MHz | Thời gian suy luận gấp 1,86 lần |
| I²C phần cứng trục trặc | `i2c_soft.c` | ≈ 1,2 ms mỗi mẫu |
| Không làm được cảm biến đội mũ | **Đã áp dụng ở v2.1:** một nút bấm bật/tắt (`pwr_btn.c`, `BTN_POWER = 1`) | Không phát hiện được mũ văng khi chưa SUSPECT (vốn cũng không xét sau SUSPECT) |
| Chưa có OLED | Hiện trạng thái bằng LED 7 đoạn 4 số trên EVK (P0.0–P0.7, P1.9–P1.12), quét bằng ngắt timer | Chữ hiển thị rút gọn; đề cương ghi OLED nên phải nêu trong báo cáo |
| Hỏng phần cứng lúc demo | Video dự phòng + HIL trên PC | — |

---

## 10. Metrics theo tầng

> Cập nhật 2026-10-14. Cột "Hiện tại" chỉ ghi số đã đo.

| Chỉ tiêu | Tầng 1 | **Tầng 2 (cam kết)** | Tầng 3 | Hiện tại |
|---|---|---|---|---|
| Chạy độc lập trên mũ | Có | Có, kèm tự kiểm khi bật nguồn | — | Chưa |
| Số lớp | 2 (NORMAL, FALL) | **2 lớp NORMAL / FALL** (v2.1) | + IMPACT, suýt ngã | 2 lớp trên D1 |
| Recall FALL mức sự kiện, LOSO trên D1 | ≥ 85 % | **≥ 95 %** | ≥ 98 % | INT8, 6/17 người, chưa có D2: N1 85,3 % (1 seed) · **N2 98,7 %** · N2-S 98,6 % (trung bình 3 seed, 15/10) · 8/17 người (16/10): N2 99,6 % · **11/17 người (16/10): N2 99,6 %** (TB 3 seed) |
| Recall FALL mức sự kiện trên D3 (ngã khi đội mũ, chạy lại bản ghi) | ≥ 80 % | ≥ 90 % (≥ 18/20) | ≥ 95 % | chưa đo |
| Macro-F1 2 lớp mức cửa sổ, LOSO trên D1 (v2.1) | — | **≥ 0,90** | ≥ 0,93 | trung bình 3 seed trên D1: N2 0,968, N2-S 0,945 (N1 0,861); 8 người (16/10): N2 0,977; **11 người (16/10): N2 0,983** |
| Thử trực tiếp trên mũ | ≥ 8/10 | **≥ 18/20 với ≥ 2 người, dữ liệu của họ không dùng để huấn luyện** | — | chưa |
| Báo giả sau Safety FSM | — | **≤ 1 PRE_ALARM giả/giờ** (≥ 2 giờ tổng từ ≥ 2 người; v2.1) | 0 trong 3 giờ | phát lại sinh hoạt D1 (không đội mũ, 2,65 giờ), trung bình 3 seed, SPEC v3.1: N2 T_SCORE 8: 1,26/giờ; gộp 3 seed N2: 0,75/giờ (trước v3.1: 5,91 / 4,91) (15/10) · 8 người, 3,88 giờ (16/10): N2 T_SCORE 8: TB 0,68/giờ; gộp 0,26/giờ (2–3 lần mỗi seed) · **11 người, 5,43 giờ (16/10): T_SCORE 8 TB 1,11/giờ (0,92 / 0,74 / 1,66; toàn bộ từ 815 nằm xuống giường), gộp 0,74/giờ** — vượt nhẹ, chốt trên buổi thử đội mũ |
| Va mũ khi đang đội không gây PRE_ALARM | — | **≥ 18/20** | 20/20 | chưa |
| Rơi mũ khi hệ thống đang bật (v2.1) | — | **báo cáo số lần PRE_ALARM; 100 % hủy được trước ALARM** | 0 lần PRE_ALARM | chưa |
| Va chạm → SUSPECT / PRE_ALARM | ≤ 2 s / ≤ 6 s | **≤ 1,5 s / ≤ 5 s** | trung vị ≤ 1,0 s | phát lại D1 (N2-S): trung vị 0,84 s / 4,08 s; p90 1,03 s / 5,32 s (14/10) · 8 người, N2 (16/10): trung vị 0,88 s / 4,12 s; p90 1,04 s / 5,92 s trên mọi cú ngã; **chỉ tính ngã nằm yên trong 2 s như đề cương: PRE_ALARM trung vị 3,83 s, p90 4,36 s, lớn nhất 4,56 s** |
| Suy luận FPGA | ≤ 15 ms | **≤ 6 ms** | ≤ 2 ms (P = 4) | E1: 13,96 ms · E2: N2 5,15 ms, **N2-S 2,65 ms**; P = 4: 1,50 / 0,80 ms (mô phỏng 14/10) |
| So với MCU-only | — | **có số đo; FPGA nhanh hơn ≥ 5 lần** | ≥ 20 lần | dự toán bằng đếm lệnh (chưa đo chip): MCU N2-S 39–119 ms → E2 nhanh hơn 14,8–44,9 lần; E1 so N1: 5,3–16,7 lần |
| RTL = golden qua HIL | ≥ 500 cửa sổ | **≥ 2.000 cửa sổ, 0 sai lệch** | — | Mô phỏng (chưa HIL): E1 50/50 có bão hòa; E2 50/50 ở mọi tầng trên 12 cấu hình; qua chân SPI giao thức v3 50/50 (E1, E2 P = 1 và 4) |
| FP32 → INT8 | — | **giảm ≤ 2 điểm %** | ≤ 1 | −2,05 recall FALL trên SisFall với shift 8 đã chốt (shift 7: −0,98); N1 trên D1 (14/10): Macro-F1 FP32 0,860 → INT8 0,861, trùng nhãn 99,77 %; N2-S: 0,975 → 0,975, trùng 99,98 % |
| Logic / BSRAM / DSP | — | **≤ 20 % / ≤ 25 % / ≤ 25 %** | — | E1: 5 % / 14 % / 5 % · top v3 + E2 N2-S P = 1: 8 % / 14 % / 10 % |
| Timing | Đạt ở 50,143 MHz | **Fmax ≥ 55 MHz** | ≥ 100 MHz | E1 105,20 MHz (15/10) · top v3 + E1 103,01 MHz · top v3 + E2 + N2 11 người 98,12 MHz (16/10; N2 6 người: 107,25) · top v3 + E2 N2-S 105,58 MHz (P = 1), 91,25 MHz (P = 4) (14/10) |
| Công suất | — | **Báo cáo Gowin + đo dòng hai board** | năng lượng mỗi lần suy luận | 156,5 mW (ước lượng công cụ) |

---

## 11. Lịch 5 tuần

Tạm tính từ 13/10/2026; phải chỉnh theo lịch BTC.

| Tuần | FW | AI | RTL-A | RTL-B | TH | Cổng |
|---|---|---|---|---|---|---|
| 1 (13–19/10) | FW-02..06 | AI-01..03, AI-13 | RA-01, RA-02 (khi có sơ đồ) | RB-01, RB-02 | TH-01..04, (TH-12) | G0, G1 |
| 2 (20–26/10) | FW-07..10, FW-13 | AI-04, AI-05, AI-06 | RA-04 → RA-03 → RA-05 | RB-02b, RB-03 | TH-05, TH-06, (TH-13) | G2 |
| 3 (27/10–02/11) | FW-11, FW-12 | AI-07, AI-14, AI-08 | RA-06 | RB-04 | TH-07, TH-08 | G3, **G4** |
| 4 (03–09/11) | FW-14, FW-15 | AI-08..10 | RA-07, RA-08 | RB-04, hỗ trợ HIL | TH-09 | G5 |
| 5 (10–16/11) | Chỉnh ngưỡng, sửa lỗi | AI-11 | Hỗ trợ đo | (RB-05 nếu G6 đã qua) | TH-10, TH-11 | G6, G7 |

Không có tuần đệm. Cuối tuần 3 phải có mũ tầng 1; nếu trễ thì cắt theo mục 9, không kéo dài.

---

## 12. Kịch bản demo (3–5 phút)

1. Bật nguồn: tự kiểm FPGA, LED 7 đoạn hiện trạng thái MONITOR. Đội mũ, đi lại, cúi, quay đầu.
2. Nhấn nhanh 2 lần (bíp dài) → `STANDBY`, tháo mũ, thả rơi mũ → không báo động.
3. Đội lại, giữ nút 2 s (2 bíp ngắn) để bật, va mũ vào xà → không báo động (người vẫn đứng, không bất động).
4. Ngã trên đệm, nằm yên → `SUSPECT` → `PRE_ALARM`, đếm ngược → bấm CANCEL.
5. Ngã lần nữa, không bấm → `ALARM`.
6. Đứng dậy, giữ nút 3 s → báo động SOS.
7. Màn hình PC: HIL khớp 100 %; bảng E1 → E2 → MCU-only; bảng tài nguyên và timing.

Luôn có video dự phòng.

---

## 13. Câu hỏi phản biện

| Câu hỏi | Trả lời dựa vào |
|---|---|
| Mạng nhỏ thế, MCU chạy được, cần FPGA làm gì? | Số đo MCU-only (FW-15) so với FPGA; bước 0,32 s khiến MCU phải dành phần lớn CPU cho suy luận trong khi vẫn lấy mẫu 100 Hz và lái giao diện; FPGA cho thời gian cố định đếm được từng chu kỳ. Thừa nhận: với mạng cỡ này MCU-only khả thi, lợi ích là dư địa và tính xác định |
| Ngã giả lập có giống ngã thật? | Không hoàn toàn. Cả D1 lẫn D3 đều là ngã giả lập của người tình nguyện; phạm vi đề tài ghi rõ điều này; báo cáo kèm số ca tuyệt đối; đánh giá tách người |
| Huấn luyện bằng dữ liệu người khác thu, cảm biến buộc ở đầu chứ không nằm trên mũ, thì có đúng với mũ không? | Không mặc nhiên đúng, nên nhóm đo: AI-14 đo độ chênh ở tuần 3, và mọi mô hình đều phải qua D3 (≥ 20 cú ngã khi đội mũ, v2.1) cùng thử trực tiếp ≥ 18/20. Lý do chọn cách này: đã có sẵn 604 cú ngã của 6 người (bộ đầy đủ là 17 người) thay cho 250 cú phải tự thu, và người tình nguyện chỉ phải ngã ≥ 40 lần |
| Người ngã còn tỉnh nhưng không dậy được? | Nút SOS giữ 3 s; trạng thái SUSPECT vẫn được ghi log |
| Mũ văng khỏi đầu khi ngã? | Từ SUSPECT trở đi bỏ qua trạng thái bật/tắt (WEAR); mũ nằm yên và nghiêng vẫn dẫn tới báo động — cố ý thiên về an toàn |
| Lượng tử hóa mất bao nhiêu? | Bảng FP32 / INT8 / RTL; trên SisFall đã đo −1 đến −2 điểm recall FALL |
| Làm sao biết phần cứng tính đúng? | HIL ≥ 2.000 cửa sổ khớp từng bit; tự kiểm LFSR mỗi lần bật nguồn |
| Số ≤ 6 ms lấy từ đâu? | E2 đã có trong mô phỏng (14/10): N2 5,15 ms, N2-S 2,65 ms với 1 làn, khớp golden ở mọi tầng 50/50; bản E1 đo được 13,96 ms. Chưa đo trên chip |
| 50 Hz có bắt được xung va chạm? | Cảm biến chạy 100 Hz, mạng nhận 50 Hz. Thừa nhận: các cú ngã huấn luyện (D1) chỉ có 25 Hz, nên mạng không học được thành phần trên 12,5 Hz của cú ngã; va đập mũ (D2) thì có đủ tới 25 Hz. AI-14 đo xem điều này có gây nhầm không |
| ±8 g có bão hòa khi va mũ? | Ghi thô ±16 g; tỉ lệ vượt 8 g được đo ở AI-03 trước khi chốt |
| Không ai ở gần thì còi có ích gì? | Hướng mở rộng: truyền không dây; ngoài phạm vi cam kết |
| Ba cửa sổ chồng nhau 87,5 % thì bỏ phiếu có thêm thông tin gì? | Ba cửa sổ nhìn sự kiện ở ba vị trí khác nhau và với lượng dữ liệu sau va chạm khác nhau (0,48–1,42 s). Lợi ích thật được đo ở AI-10: so `VOTE_K = 1` với `VOTE_K = 2` trên cùng dữ liệu |
| Số người ít thì kết luận được gì? | D1 có 17 người theo tài liệu đi kèm (đã tải 8), buổi thử có ≥ 2 người. Vẫn ít, nên báo cáo số ca tuyệt đối, tách người, ghi rõ nguồn của từng con số, và có thử trực tiếp với người ngoài tập huấn luyện |
| Sao không tính lũy tiến khi hai cửa sổ liền nhau trùng 87,5 %? | Khung độc lập thì kiểm chứng từng bit được qua HIL và không mất đồng bộ khi rớt một khung; FPGA còn dư thời gian hơn 20 lần |

---

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

Còi xác nhận: BẬT = 2 bíp 100 ms, TẮT = 1 bíp 600 ms.

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

### Lịch sử thay đổi SPEC

| Ngày | Nội dung |
|---|---|
| 2026-10-03 | v1: đeo thắt lưng, 100 Hz, 3 lớp Conv |
| 2026-10-12 | v2: mũ, 50 Hz, 2 lớp Conv, kênh trước, UINT8 |
| 2026-10-12 | v3: lấy RTL hiện có làm gốc (vị trí trước, 0..127, dịch sàn); cảm biến 100 Hz ±16 g ±2000 °/s, MCU giảm còn 50 Hz; bước 0,32 s + bỏ phiếu; N1/N2; E1/E2; lớp 0 NORMAL, 1 IMPACT, 3 FALL; giao thức v3; bỏ CONFIRM, thêm SOS và tự kiểm |
| 2026-10-16 | **v3.2** (đi cùng đề cương v2.1): A.4 chỉ huấn luyện 2 lớp 0 NORMAL và 3 FALL, lớp 1 IMPACT để dành; A.8 đầu vào WEAR là trạng thái bật/tắt do một nút bấm tạo (`pwr_btn.c`), thêm quy ước nút. Không đổi khung, số học, FSM hay vector; mô hình đã có vốn là 2 lớp vì D1 không có IMPACT |
| 2026-10-15 | **v3.1**: A.8 điều kiện nghiêng thành hai phía `\|az_tb\| < T_TILT` (trước: `az_tb < T_TILT`). Lý do: phát lại D1 cho thấy 15/22 PRE_ALARM giả có `az_tb` ≈ −2040 (đầu lộn ngược khi cúi gập sau khi vấp, nhặt đồ), còn 375/375 cú ngã nằm tới PRE_ALARM có `az_tb` ≥ −1074. Không đổi khung, số học hay vector |
| 2026-10-14 | v3 (làm rõ, không đổi số học hay khung): A.7 thêm quy ước một bộ đệm kết quả và giá trị `STATUS` cho từng lỗi; `cnn_params.vh` thêm `CNN_SCORE_SHIFT` (lấy từ `score_shift` trong json) |

---

## PHỤ LỤC B – GOLDEN MODEL

Đã chạy ngày 2026-10-12: N1 khớp 20/20 vector của nhóm; mô hình địa chỉ E2 với P = 1, 2, 4 khớp golden cho cả N1 và N2; tiền xử lý, CRC và khung đều PASS.

```python
# ml/src/golden_model.py — SPEC v3. Chỉ dùng số nguyên. Mảng xếp "vị trí trước": (L, C).
import numpy as np

K, PAD, AMAX = 5, 2, 127


def conv1d(x, w, b):
    """x: (L, IC); w: (OC, IC, K) int8; b: (OC,) int32 -> acc (L, OC) int64."""
    L = x.shape[0]
    xp = np.pad(x.astype(np.int64), ((PAD, PAD), (0, 0)))
    acc = np.zeros((L, w.shape[0]), np.int64)
    for k in range(K):
        acc += xp[k:k + L] @ w[:, :, k].astype(np.int64).T
    return acc + b.astype(np.int64)


def requant_relu(acc, n):
    """A.5: acc <= 0 -> 0; ngược lại min(acc >> n, 127). Dịch số học, không làm tròn."""
    return np.where(acc <= 0, 0, np.minimum(acc >> n, AMAX))


def maxpool2(a):
    L, C = a.shape
    return a.reshape(L // 2, 2, C).max(axis=1)


def forward(x, P, trace=None):
    """x: (128, 6) int8, hàng = mẫu (đúng thứ tự byte trong khung SPI).
    P: w1,b1,w2,b2[,w3,b3], wd (4, F), bd (4,), n [n1, n2, ...], head "gap" hoặc "flatten", score_shift."""
    a = x.astype(np.int64)
    for i, n in enumerate(P["n"], start=1):
        acc = conv1d(a, P[f"w{i}"], P[f"b{i}"])
        assert np.abs(acc).max() < 2**31, f"tràn accumulator lớp C{i}"
        a = maxpool2(requant_relu(acc, n))
        if trace is not None:
            trace[f"l{i}"] = a.copy()
    if P["head"] == "gap":
        f = a.sum(axis=0) >> (a.shape[0].bit_length() - 1)      # chia 32 bằng dịch, lấy sàn
    else:
        f = a.reshape(-1)                                       # flatten: i = t*C + c
    logits = P["wd"].astype(np.int64) @ f + P["bd"].astype(np.int64)
    assert np.abs(logits).max() < 2**31
    cls = int(np.argmax(logits))                                # bằng nhau -> chỉ số nhỏ
    top2 = int(np.max(np.delete(logits, cls)))
    score = int(np.clip((int(logits[cls]) - top2) >> P["score_shift"], 0, 127))
    if trace is not None:
        trace["feat"], trace["logit"] = f, logits
    return cls, score, logits


# ---------- tiền xử lý trên MCU (A.2) ----------
def decimate(raw):
    """raw: (M, 6) int16 ở 100 Hz -> (M//2, 6) ở 50 Hz."""
    r = raw.astype(np.int64)
    r = np.vstack([r[:1], r[:1], r])                            # r[-2] = r[-1] = r[0]
    i = 2 * np.arange(len(raw) // 2)
    return (r[i] + 3 * r[i + 1] + 3 * r[i + 2] + r[i + 3] + 4) >> 3


def q8(d, shifts=(7, 7, 7, 6, 6, 6)):
    s = np.array(shifts, np.int64)
    return np.clip((d + (1 << (s - 1))) >> s, -128, 127).astype(np.int8)


# ---------- khung SPI (A.7) ----------
def crc16(data, c=0xFFFF):
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c


def write_frame(seq, x):
    body = bytes([0xA5, seq & 0xFF]) + x.astype(np.int8).tobytes()
    c = crc16(body)
    return body + bytes([c >> 8, c & 0xFF])


def result_frame(seq, status, cls, score, logits, cycles, logit_shift=0):
    head = bytes([0x5A, seq & 0xFF, status, cls & 0xFF, score])
    c = crc16(head)
    head += bytes([c >> 8, c & 0xFF])
    tail = b"".join(int(np.clip(int(v) >> logit_shift, -32768, 32767)).to_bytes(2, "big", signed=True) for v in logits)
    tail += int(cycles).to_bytes(3, "big")
    c = crc16(tail)
    return head + tail + bytes([c >> 8, c & 0xFF])


def selftest_payload():
    """A.10: 768 byte từ LFSR Galois 16 bit, đa thức 0xB400, mầm 0xACE1."""
    s, out = 0xACE1, []
    for _ in range(768):
        lsb = s & 1
        s >>= 1
        if lsb:
            s ^= 0xB400
        out.append(s & 0xFF)
    return np.frombuffer(bytes(out), np.int8).reshape(128, 6)
```

Nạp weight hiện có của nhóm (bố trí E1): `w1 = W[0:480].reshape(16, 6, 5)`, `w2 = W[480:3040].reshape(32, 16, 5)`, `wd = W[3040:3168].reshape(4, 32)`, `n = [8, 8]`, `head = "gap"`.

CRC-16 cho firmware, cùng thuật toán với hàm `crc16` Python ở trên (chưa biên dịch thử trên máy này vì không có trình biên dịch C):

```c
// firmware/src/crc16.c — CRC-16/CCITT-FALSE (A.7)
uint16_t crc16_ccitt(const uint8_t *p, uint32_t n)
{
    uint16_t c = 0xFFFF;
    while (n--) {
        c ^= (uint16_t)(*p++) << 8;
        for (int i = 0; i < 8; i++)
            c = (c & 0x8000) ? (uint16_t)((c << 1) ^ 0x1021) : (uint16_t)(c << 1);
    }
    return c;   /* crc16_ccitt("123456789", 9) phải bằng 0x29B1 */
}
```

---

## PHỤ LỤC C – DANH MỤC [CẦN XÁC MINH]

| # | Nội dung | Nguồn cần tra | Ảnh hưởng |
|---|---|---|---|
| X1 | **Gần đóng.** Chân và điện áp bank đã có từ sơ đồ Kiwi rev v1.0 nhận ngày 12/10 (Phụ lục E.3). Còn lại: số thứ tự chân trên header J1 đọc từ hình sơ đồ, chưa đo | Đo trên board bằng `rtl/pin_probe`. File sơ đồ mới nhận qua chat, chưa nằm trong thư mục | RA-02, TH-02 |
| X2 | **Thu hẹp tiếp 14/10** bằng hướng dẫn EVK của SONiX. Đã rõ: mọi chân E.1 cần nối dây đều ra header (J7, J10, J12, J13); VDD = 3,3 V từ LDO khi SW1 ON và jumper J1/J3 đúng; nạp qua SN-Link trên board. Còn mở: (a) flash SPI của EVK dùng chân chọn nào; (b) J7 có chân nào nối sẵn LED RGB hay linh kiện khác; (c) lấy 3,3 V cho MPU6050 ở đâu vì header không có chân 3,3 V | Thư mục `CIRCUIT_32F407_EVK_V1.0` trong gói tải của SONiX (mục 3.2.1 của hướng dẫn, chưa có trên máy); phép thử E.4 bước 2; đồng hồ đo | FW-03, FW-08, TH-02 |
| X3 | **Đã đóng 14/10 bằng số liệu:** chốt 8 (AI-01). Nguồn gốc của số 7 vẫn chưa rõ vì không có notebook; dấu thời gian không phân xử được (`fpga_top.v` shift 7 lưu 20:21, `golden_vectors.npz` shift 8 lưu 20:32, cùng tối 05/10) | Notebook Colab, nếu tìm được thì chỉ để đối chiếu | Không còn chặn việc nào |
| X4 | Thang lượng tử đầu vào của mô hình SisFall | Notebook Colab | Chỉ ảnh hưởng nếu dùng SisFall để pretrain |
| X5 | **Đã đóng 14/10 (datasheet mục 19).** Khối CRC có chế độ CRC-16-CCITT: đa thức 0x1021, mầm 0xFFFF, không đảo bit, không XOR cuối, đúng CRC của A.7. Chưa thử trên board | Thử `"123456789"` → 0x29B1 ở FW-08: lệnh `c` của `firmware/` (đã viết 14/10; ghi `CRC_DATA` 8 bit theo datasheet 19.3.2) | Dùng CRC phần cứng; hàm phần mềm giữ để đối chiếu |
| X6 | **Đã đóng 14/10 (datasheet mục 14).** SCK = PCLK / (2·DIV + 2): từ 48 MHz, DIV = 23 cho 1 MHz và DIV = 5 cho 4 MHz. FIFO 8 khung mỗi chiều. SELDIS = 1 thì chân SEL là GPIO | — | FW-08 |
| X7 | Lõi Cortex-M0 của SN32F407 có bộ nhân 1 chu kỳ hay 32 chu kỳ. Datasheet V2.2 không ghi (đã tra 14/10) | Đo ở FW-15 (GPIO + logic analyzer) | **Thu hẹp 14/10:** đếm lệnh `cnn_mcu.c` trong Unicorn cho N1 74,6 ms (nhân 1 chu kỳ) đến 232,7 ms (nhân 32 chu kỳ), N2-S 39,3–118,9 ms, cộng tới ≈ 26 ms nếu Flash 1 wait-state; chưa đo trên chip |
| X8 | Dòng tiêu thụ của MCU ở 48 MHz. Datasheet mục 23.2: 6 mA điển hình ở 3,3 V với ngoại vi tắt; chưa đo | Đo dòng thật ở TH-10 | Năng lượng mỗi lần suy luận (tầng 3) |
| X9 | Ghi Flash của SN32F407. Datasheet mục 20 có các thanh ghi FMC (trang 512 byte, xóa trang 4–5 ms, ghi 2 từ mất 48–60 µs); pack không có hàm sẵn | Tự viết theo datasheet mục 20.8 | FW-16 (tầng 3) |
| X10 | Chế độ bề rộng của BSRAM và cách suy ra MULT9X9 cho P = 4 | Gowin UG285, UG287 | RB-05 (tầng 3) |
| X11 | Thể lệ cuộc thi: định dạng, độ dài đề cương, hạn nộp lại, ngày chung kết | BTC | Lịch mục 11; `DE_CUONG_v2.md` |
| X12 | Mã SN32F407 đã đọc được cảm biến dùng chân nào, tần số và thang đo nào; đã thử 10 phút không mất mẫu chưa. (Đã rõ ngày 12/10: bài test PASS trên cả ESP32 và SN32F407, nhưng bằng mã riêng của một thành viên. Ngày 14/10 tìm thấy trên máy dự án vòng 1 có `i2c0.c` cho I2C0 trên P0.10/P0.11, nhưng vẫn chưa có mã đọc MPU6050 của thành viên đó) | Mã và log của thành viên đó, chép vào thư mục | FW-01, FW-02, cột MCU của E.1 |
| X13 | **Đã đóng 12/10:** nhóm có board ESP32 | — | TH-12, TH-13 dùng được |
| X14 | Bộ D1. **Đã rõ 13/10:** định dạng, đơn vị, hướng trục, danh sách 36 hoạt động (có 808 vấp rồi đứng lại được và 809 vấp chân); tài liệu đi kèm ghi 17 người, bài báo dùng 14 trong số đó. **Còn mở:** (1) tài liệu ghi 340506 là cảm biến ở đầu, số liệu 6 người cho thấy 340540 mới là đầu — cần một xác nhận độc lập; (2) 11 người chưa tải được | (1) Hình 1 của bài báo [4] hoặc hỏi tác giả; (2) tải lại bằng mạng nhanh hơn | AI-13; nếu (1) sai thì toàn bộ D1 phải chuyển đổi lại |
| X15 | **Mới 14/10.** Ngã kết thúc **quỳ hoặc ngồi** (D1: 903, 909, 920) có phải báo động không? Với A.8 hiện tại (đầu nghiêng > 45°) chỉ 8/90 tới PRE_ALARM. Đồng thời Pass của AI-10 ("≥ 95 % cú ngã tới PRE_ALARM") đang tính cả 4 kiểu ngã có đứng dậy, vốn không được báo | Nhóm quyết theo mục tiêu "ngã và nằm bất động" (mục 1); nếu cần báo cả ngồi bất động thì thêm nhánh "bất động ≥ N khối dù đầu thẳng" và đo lại báo giả. **Đã đo 15/10** ([x15_nga_ngoi](docs/bao_cao/2026-10-15_x15_nga_ngoi/README.md)): nhánh đó báo nhầm 3–69 % cú ngã đã đứng dậy và tăng báo giả lên 1,76–3,78/giờ; đề nghị giữ v3.1 + SOS. **Chờ nhóm quyết** | AI-10, Safety FSM, chỉ tiêu thử trực tiếp |
| X16 | **Mới 14/10.** Hệ số chia mặc định của clock WDT (`APBCP1.WDTPRE`) và nguồn ILRC: thời gian tràn với TC = 0xFF là 1 s nếu không chia, tới 32 s nếu chia 32. **15/10:** datasheet 3.4.2 ghi WDTPRE reset = 0 (chia 1); còn mở tần số ILRC — 32 kHz theo 3.2.1 (≈ 1.024 ms) nhưng sơ đồ clock trang 19 ghi 256 kHz (≈ 128 ms) | Đo trên board bằng lệnh `w` của menu chẩn đoán (ngừng feed, số in cuối = chu kỳ WDT), bước B2. Vòng chờ IMU lỗi đã đổi sang feed mỗi 250 ms | FW-14 |

---

## PHỤ LỤC D – NHẬT KÝ KẾ HOẠCH

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 2026-10-12 | Bản đầu của file này | — |
| 2026-10-12 | Bỏ hai tài liệu SPEC v1, v2 và các file trùng; thêm `tools/logger.py` | Dọn thư mục |
| 2026-10-12 | Thêm **E1 mở rộng** (RB-02b) giữa E1 và E2 | Để N2 không phụ thuộc vào tiến độ của E2 |
| 2026-10-12 | RA-04 thông mạch bằng RTL hiện có; bỏ `top_link.v` | RTL hiện có đã trả kết quả thật |
| 2026-10-12 | FW-13 (HIL) chuyển từ G4 về G2; RA-02 (chân FPGA) chuyển từ G0 sang G2 | G2 cần HIL; chân FPGA không chặn việc thu dữ liệu |
| 2026-10-12 | Thêm TH-12, TH-13 (ESP32, tùy chọn); gộp sự kiện theo file và thu hàng loạt va đập không đội mũ | Rút ngắn đường găng dữ liệu |
| 2026-10-12 | Gom phần chân vào Phụ lục E, thêm giá trị thanh ghi tra từ SVD và mẫu file ràng buộc FPGA | Trước đó chỉ có bảng đề xuất chân MCU nằm lẫn trong mục 4.3 |
| 2026-10-13 | Chọn 6 chân FPGA trên J1 (K12, K14, J12, J13, H12, J11), ghi vào `fpga_top.cst`, chạy P&R; thêm `rtl/pin_probe` | Đã có sơ đồ Kiwi rev v1.0; Gowin EDA có trên máy nên kiểm được bằng công cụ |
| 2026-10-13 | `argmax4` thành 2 tầng thanh ghi, `inference_done` trễ 2 chu kỳ (sửa R6 sớm, trước RA-07) | Fmax tụt còn 53,60 MHz khi chân cố định, dưới mức cam kết 55 MHz; sau sửa là 101,86 MHz, vẫn khớp 20/20 |
| 2026-10-13 | Số đo E1 đổi: 699.800 chu kỳ, Logic 923, FF 590, 156,5 mW | Hệ quả của hai dòng trên |
| 2026-10-13 | **Chiến lược dữ liệu lai:** FALL và NORMAL huấn luyện bằng D1 (bộ công khai, cảm biến ở đầu); nhóm chỉ tự thu D2 (IMPACT, NORMAL khi đội mũ) và D3 (≥ 40 cú ngã để kiểm tra). AI-13 thành việc bắt buộc, thêm AI-14, sửa AI-05..09, G1, G3, G5 | Nhóm chấp nhận dùng dữ liệu thu ở vị trí khác. Số cú ngã phải tự thực hiện giảm từ ≥ 250 xuống ≥ 40; bộ D1 đầy đủ có 17 người theo tài liệu đi kèm. Kiểm bằng AI-14 và D3; lùi về kế hoạch tự thu cũ nếu không đạt |
| 2026-10-13 | D1: tải và chuyển đổi được 6/17 người (604 cú ngã, 53.165 cửa sổ) vào `ml/data/public/`; thêm `tools/convert_d1.py`, `tools/plot_d1.py`; ghi nhận mã cảm biến ở đầu là 340540 chứ không phải 340506 như tài liệu đi kèm | Máy chủ UCI ngắt sau 20 phút nên chưa lấy đủ. Mã cảm biến xác định bằng ba dấu hiệu vật lý trên từng người |
| 2026-10-13 | Dữ liệu ở thân người (ngực, thắt lưng) thành nguồn bổ sung, quyết ở AI-09; SisFall thêm vào đường lùi của AI-14 | Nhóm chấp nhận dùng dữ liệu ở thân. Phép đo trên 6 người: recall ngang nhau (93,9–95,0 % so với 94,0 %) nhưng báo nhầm trên bản ghi thường ngày tăng từ 51 lên 79–87 trên 499 |
| 2026-10-13 | Ghi nhận từ D1 cho Safety FSM: sau va chạm 4–5 s, đầu nghiêng quá 45° ở 87–100 % số lần của 13 kiểu ngã kết thúc nằm, và ở 0–20 % số lần của 7 kiểu kết thúc ngồi, quỳ hoặc đứng dậy | Ủng hộ `T_TILT` = 45°; số chốt vẫn ở AI-10 |
| 2026-10-13 | Máy có MDK-ARM Lite 5.43 (Arm Compiler 6.24) tại `%LOCALAPPDATA%\Keil_v5`, pack SONiX.SN32F4_DFP 1.1.1 và CMSIS 6.3.0; build thử cho Cortex-M0 qua đủ ba bước biên dịch, hợp dịch, liên kết. Datasheet "SN32F400 Series User's Manual" V2.2 (253 trang) chép vào `docs/datasheet/` | Nhánh firmware hết bị chặn về công cụ. X5–X9 giờ tra được trong datasheet nhưng chưa tra. Bản Lite giới hạn 32 KB mã, bằng đúng Flash của SN32F407 |
| 2026-10-14 | **Làm lại bảng chân MCU (E.1, E.2).** SPI: P1.0 / P1.1 / P1.2, CS P1.8; IRQ P2.0; RST_N P2.1; INT cảm biến P2.2; WEAR P2.3; I²C P0.10 / P0.11; UART0 P3.1 / P3.2; còi P3.0; LED P3.8; CANCEL = phím SW3. Phía FPGA không đổi | Tìm thấy dự án vòng 1 của nhóm trên máy: board thật là "32F407 EVK V1.0", trên đó P0.0–P0.7 là LED 7 đoạn nên bảng cũ (theo sơ đồ Start-Kit) đụng chân. Chân mới chọn theo bảng PFPA của datasheet; chưa thử trên board; lùi: mỗi tín hiệu còn lựa chọn PFPA khác và ba chân dự trữ |
| 2026-10-14 | Đóng X5, X6 bằng datasheet; cập nhật X2, X7, X8, X9, X12. CRC khung dùng khối CRC phần cứng | Datasheet V2.2 đã có trong `docs/datasheet/` cùng sơ đồ Kiwi |
| 2026-10-14 | FW-02: bộ test cảm biến chuyển sang ±16 g / ±2000 °/s, gắn trên mũ, chân của EVK; thêm `build.sh` và biên dịch ra `.hex`. AI-02 xong: `ml/src/golden_model.py`, `tools/verify_spec_v3.py` in "TẤT CẢ PASS" | Có trình biên dịch nên kiểm được mã bằng công cụ thay vì chỉ đọc. Cả hai chưa chạm tới board |
| 2026-10-14 | **CS của FPGA P1.8 → P2.8, IRQ P2.0 → P2.9**; P1.8 giữ mức cao. Thêm nhãn header, thiết lập jumper và nguồn của EVK vào E.1, E.2, E.4. Thêm project Keil `test_sensor/firmware/keil/` (0 lỗi) | Hướng dẫn EVK (V1.0) user gửi: ảnh board cho thấy P2.0 không ra header, và có flash SPI có thể dùng chung SPI0 với chân chọn P1.8. Đổi chân an toàn cả khi flash không dùng P1.8; kiểm bằng E.4 bước 2. Lùi: J7 còn P2.1, P2.3 nếu P2.8 hoặc P2.9 vướng linh kiện (RST_N và WEAR đều thuộc tầng sau) |
| 2026-10-13 | Thêm AI-13 (bộ dữ liệu công khai có cảm biến ở đầu); đề cương thay UMAFall bằng Özdemir–Barshan | Tìm trên mạng: không có bộ dữ liệu ngã nào đo trên mũ. UMAFall không có vị trí đầu, câu cũ trong đề cương là sai |
| 2026-10-13 | Hạ trạng thái các chân MCU từ "đã chạy" về "tra cứu"; viết lại FW-01, H7, X12 | Bài test cảm biến đã PASS bằng mã khác, không phải `test_sensor` trong thư mục |
| 2026-10-14 | **AI-01, RA-01 xong; X3, R1, R8 đóng.** Chốt `conv1_shift = 8`; thêm `tools/gen_cnn_params.py` sinh `src/cnn_params.vh` và vector testbench từ `quant_params.json`; `fpga_top.v`, testbench 20 vector, `run_golden_sim.bat` (`-g2001`), `verify_spec_v3.py` cùng đọc một nguồn. Số P&R mới: Logic 913, Register 589, Fmax 108,49 MHz (sửa ở H3, mục 10, khung trạng thái, đề cương mục III.2, dòng 12 của bảng thay đổi) | Golden trên SisFall: shift 7 và 8 chênh ≤ 1,1 điểm, Macro-F1 đổi chiều giữa validation và test; 8 khớp file xuất và `golden_vectors.npz`, ít bão hòa hơn 13 lần. Đường lùi: sửa một số trong json, xuất lại vector, chạy lại script. RTL 20/20, phép âm 0/20 |
| 2026-10-14 | **Đợt A firmware: FW-07, FW-11 xong; FW-03, FW-08 xong phần máy.** Thêm `firmware/` (8 file nguồn, project Keil `fw.uvprojx` 0 lỗi 0 cảnh báo, 7,5 KB Flash, 1,3 KB RAM), `firmware/tv/` (vector FW-07), `tools/gen_tv_pre.py`, `tools/m0_test.py` | Máy không có trình biên dịch C cho PC, nên kiểm mã máy Cortex-M0 do armclang sinh trong Unicorn: khớp golden từng byte; 12/12 lỗi cài cố ý bị bắt. Phần chạm ngoại vi chờ đợt B. Datasheet 19.3.2: `CRC_DATA` chỉ nhận ghi 8 bit |
| 2026-10-14 | **AI-07 phần chuẩn bị:** viết lại chuỗi huấn luyện N1 bằng numpy (`ml/train_n1.py`, `ml/src/n1_numpy.py`), chạy LOSO trên D1 6 người, xuất `ml/out/n1_d1/fpga_export/` | Notebook gốc chưa có, máy không có TensorFlow; N1 nhỏ nên numpy đủ (≈ 9 phút cho 7 lần huấn luyện). Recall sự kiện 85,3 %, Macro-F1 0,861: mốc tầng 1, còn thiếu 9,7 điểm recall so với chỉ tiêu tầng 2. Weight mới khớp RTL 20/20 |
| 2026-10-14 | **RB-01 xong nửa Icarus 0.9.7**; thêm `rtl/tb/tb_top_spi.v`, `rtl/tb/run_all.sh`, `tools/gen_tb_top.py` | Lần đầu kiểm `fpga_top` qua chân SPI bằng đúng khung firmware sinh: 4/4 khung khớp, khung sai CRC không bật IRQ. Máy chỉ có Icarus 0.9.7 |
| 2026-10-14 | **AI-04 xong**: `tools/export_mem.py`, `ml/src/rom_layout.py` (một nguồn bố trí ROM E1/E2, `verify_spec_v3.py` dùng chung); `tb_cnn_core_golden.v` nhận `TB_NV`. **R9 đóng cho E1**: 50 vector có bão hòa, RTL 50/50 | Pass của AI-04 cần ≥ 50 vector gồm cực trị; E1 export trùng từng byte file của nhóm |
| 2026-10-14 | **RA-03 xong (mô phỏng + P&R)**: `rtl/v3/` (top v3, parser CRC-16, khung đọc 20 byte, RST_N, CYCLES), `tb_proto` 50 khung + 7 kịch bản lỗi, phép âm 5/5. `cnn_core.v` thêm 4 cổng logit; `top.sdc`; R3, R4, R5, R10 đóng ở mức RTL | `fpga_top` (PROTO 1) giữ nguyên cho RA-04; v3 thêm 609 Logic, Fmax 102,74 MHz |
| 2026-10-14 | **AI-09 sơ bộ: chọn N2-S** (8-16-16, 3.184 weight, 113.664 MAC). `ml/train_cnn.py`, `ml/src/cnn_numpy.py` huấn luyện cả họ A.4 | LOSO trên D1: N2-S Macro-F1 0,975, recall sự kiện 98,7 % so với N1 0,861 / 85,3 %; nhỏ nhất trong các mô hình đạt cả hai ngưỡng. Chưa có D2/D3, một seed |
| 2026-10-14 | **AI-10 sơ bộ**: `tools/playback_d1.py`, `ml/src/safety_model.py` (trùng `safety.c` trên 240.000 tick); quét 36 cấu hình FSM. Thêm X15 | Ngã nằm → PRE_ALARM 97,0 %, đứng dậy → 0/120, nhưng PRE_ALARM giả 5,66/giờ trên sinh hoạt D1; chưa cấu hình nào đạt ≥ 95 % và ≤ 1/giờ cùng lúc. Giữ mặc định A.8 tới khi có D2/D3 |
| 2026-10-14 | **Firmware đủ chức năng tầng 1 (chỉ biên dịch)**: `app_main.c`, `app_core.c`, `i2c0.c`, `imu.c`, `gyro_cal.c`, UART ngắt, còi, WDT, `diag.c`; `tools/check_frames.py` (FW-10), `tools/hil_test.py` (TH-07). Keil 0 lỗi, 16 KB / 32 KB, 5,4 KB / 8 KB RAM | `app_core.c` chạy 131 s dữ liệu D1 trong Unicorn, trùng chuỗi golden từng kết quả và từng lần đổi trạng thái; `spi_fpga` thành không chặn để không mất mẫu khi chờ IRQ |
| 2026-10-14 | FW-15 phần máy: `cnn_mcu.c` khớp golden 50/50 trên 5 mô hình; đếm lệnh cho dự toán MCU-only: N1 74,6–232,7 ms, N2-S 39,3–118,9 ms. Đề cương thay câu "ước tính 47–190 ms" bằng số đếm lệnh | Thu hẹp X7; vẫn phải đo GPIO trên chip |
| 2026-10-14 | **RB-03, RB-04, RA-07, RA-08 xong (mô phỏng + P&R)**: `rtl/e2/cnn_e2.v` 1 chu kỳ/MAC, `LANES` làn; 12 cấu hình 50/50 ở mọi tầng; top v3 chọn engine bằng `CNN_ENGINE_E2`; 105,58 MHz, Logic 8 %. A.7 thêm quy ước một bộ đệm kết quả | N2 5,15 ms ≤ 6 ms cam kết; N2-S 2,65 ms. Đề cương và bảng thay đổi đổi "dự toán ≈ 4,9 ms / 1,3 ms" thành số mô phỏng 5,15 / 1,50 ms. Chưa chạy trên chip |
| 2026-10-15 | Thêm `docs/huong_dan_dot_B.md` (8 bước trên board, Pass và thứ cần gửi lại), `docs/data_protocol.md` (AI-05), `tools/windowing.py` (AI-06); `rtl/tb/run_all.sh` chạy thêm `tb_proto` và `tb_e2` (6/6 PASS; thêm `tb_e1_layers` sau đó: 7/7) | Chuẩn bị để nhóm cầm board làm đợt B và thu D2 ngay; AI-09/AI-10 chỉ chốt được khi có dữ liệu đội mũ |
| 2026-10-15 | **RB-02 xong (mô phỏng)**: `rtl/tb/tb_e1_layers.v`, E1 50/50 ở l1, l2, feat, logit với hai bộ weight; `export_mem.py` thêm `vec_feat.mem` | Pass của G2 cần testbench từng tầng cho E1; trước đó mới so logit |
| 2026-10-15 | Mô phỏng ghép firmware ↔ RTL (`tools/cosim.py`, `rtl/v3/tb_stream.v`, chế độ 10 của harness): 423/423 khung khớp; LED 7 đoạn hiện trạng thái (FW-12 một phần, 51 ca test); thêm `README.md` gốc | Nối các mắt xích đã kiểm riêng thành một chuỗi trước khi có board; LED 7 đoạn thay OLED cho demo tầng 1 |
| 2026-10-15 | **AI-09: chọn sơ bộ đổi từ N2-S sang N2**; thêm `tools/spectrum_check.py` (AI-14 bước 1: D1 đi bộ chỉ 0,06–0,49 % công suất ở 12,5–25 Hz) | Lặp LOSO với 2 seed nữa: Macro-F1 trung bình N2 0,968 so với N2-S 0,945; phiếu nhầm ở T_SCORE 8 là 8,0 so với 21,2 lần/giờ. Kết quả một seed ban đầu của N2-S là may. Không đổi phần cứng: E2 chạy cả hai |
| 2026-10-15 | AI-10 phát lại lại với 3 seed: báo giả trung bình 5,8–10/giờ ở mọi cấu hình (số 1,13/giờ trước đó là seed may); ghi rủi ro chỉ tiêu ≤ 1/giờ và đường giảm | Báo cáo trung thực; ưu tiên thu D2 NORMAL khi đội mũ |
| 2026-10-15 | **SPEC v3.1: A.8 điều kiện nghiêng hai phía `\|az_tb\| < T_TILT`** (`safety.c`, `safety_model.py`, 2 ca test; đề cương bảng Safety FSM và dòng 9 bảng thay đổi đổi "đầu nghiêng quá 45°" thành "đầu nằm ngang, lệch 45°–135°") | Phân tích PRE_ALARM giả: 15/22 có đầu lộn ngược khi cúi gập, không cú ngã nằm nào như vậy. Báo giả trung bình giảm từ 5,91 xuống 1,26/giờ (N2), 0,75/giờ khi gộp 3 seed; recall ngã nằm giữ nguyên |
| 2026-10-15 | Thêm `bitstreams/` với 3 bitstream dựng sẵn (PROTO 1 + E1 SisFall shift 8; v3 + E1; v3 + E2 + N2) kèm SHA-256; firmware chọn giao thức và đáp án tự kiểm bằng `FW_BITSTREAM` | Bước B7 không còn phụ thuộc vào việc người giữ project chạy lại Run All; ba nấc lên dần từ RTL đã có tới tầng 2 |
| 2026-10-15 | **Dọn thư mục**: xóa sản phẩm build (`firmware/build`, `keil/Objects`, `Listings`, kể cả của `test_sensor`), `__pycache__`, `ml/train_n1.py` + `ml/src/n1_numpy.py` (đã bị `train_cnn.py` / `cnn_numpy.py` thay thế), `ml/out/export_e1_n1d1`, `ml/out/n2l_d1`, bản xuất trùng `ml/out/n2s_d1/mem_e2_*`, file `.vvp`, và 3 file cũ không dùng trong `src/` của project Gowin (`golden_input_0.mem`, `golden_input_0_expected.txt`, `golden_vectors.npz`); thêm `.gitignore` | Tất cả đều tái tạo được bằng lệnh có sẵn hoặc không còn được tham chiếu; giữ nguyên tài sản gốc của nhóm (`sdk/`, mô hình SisFall, `.docx`, `impl/`) |
| 2026-10-15 | **Verify toàn dự án sau khi dọn** + **mô phỏng netlist sau P&R** (`rtl/gl/run_gl.sh`, `rtl/gl/rpll_stub.v`, `SIM_NETLIST=1` trong `pnr_v3.sh`); sửa `convert_d1.py`, `logger.py` (cp1252), `plot_d1.py` (argparse), `check_frames.py` (mất mẫu → FAIL, báo đúng khung sai), `gen_tb_proto.py`; chạy lại `gen_cnn_params.py` cho `src/cnn_params.vh` của project nhóm (thêm `CNN_SCORE_SHIFT 0`) | Mọi bộ kiểm PASS: SPEC, m0_test, run_all 7/7, tb_e2 14/14, tb_proto E1 50 + E2 20, cosim N2 423/423, check_frames trên mã máy firmware 1.283/1.283; bitstream 3 tái tạo được (chỉ khác dấu thời gian); **netlist sau P&R của bitstream 3 PASS**, phép âm lật 1 bit weight → FAIL. [verify_sau_don](docs/bao_cao/2026-10-15_verify_sau_don/README.md) |
| 2026-10-15 | `ml/train_cnn.py --train-only`; lưu `ml/data/public/d1_windows_nguc_340539.npz`, `d1_windows_that_lung_340535.npz` (bản thô D1 chỉ còn trong thư mục tạm); mô hình `ml/out/n2t_d1` + xuất `ml/out/e2_matrix/n2t_p1` (tb_e2 50/50) | AI-09: dữ liệu thân chỉ để huấn luyện → ngã nằm 96,4 %, PRE_ALARM giả 0,88/giờ (chỉ đầu: 95,5 %, 1,26); đề nghị giữ. [ai09_du_lieu_than](docs/bao_cao/2026-10-15_ai09_du_lieu_than/README.md) |
| 2026-10-15 | `tools/playback_d1.py --still-upright N` (thí nghiệm X15, không vào SPEC) | Nhánh "bất động dù đầu thẳng" báo nhầm cú ngã đã đứng dậy (3–69 %) và tăng báo giả → đề nghị giữ SPEC v3.1. [x15_nga_ngoi](docs/bao_cao/2026-10-15_x15_nga_ngoi/README.md) |
| 2026-10-15 | Bảng AI-11 sơ bộ trên D1 | FP32 → INT8 mất ≤ 0,15 điểm; INT8 → RTL mất 0; phương sai theo seed là rủi ro chính. [ai11_bang_so_bo](docs/bao_cao/2026-10-15_ai11_bang_so_bo/README.md) |
| 2026-10-15 | **Sửa lỗi RTL tìm bằng mô phỏng netlist:** `conv_start` của `cnn_controller.v` không có giá trị khởi tạo, Gowin chọn INIT = 1 → engine conv tự chạy khi nạp cấu hình, **khung đầu tiên sau khi bật nguồn sai** (bitstream 1 và 2; đó là khung tự kiểm A.10 ở B8). Khởi tạo 0 mọi thanh ghi điều khiển trong `src/` của project nhóm (không đụng `impl/`) và `packet_parser_v3.v`; dựng lại bitstream 1 (Logic 907, 105,20 MHz) và 2 (1.521, 103,01 MHz), cập nhật SHA256; bitstream 3 không đổi. `run_gl.sh` thêm chế độ `p1`, `v3` và in danh sách FF INIT = 1. Số Fmax của E1 trong DE_CUONG_v2 / THAY_DOI đổi 108,49 → 105,20 MHz | Netlist mới: bitstream 1 `tb_top_spi` 5/5, bitstream 2 và 3 `tb_proto` PASS; RTL run_all 7/7. [loi_init_conv_start](docs/bao_cao/2026-10-15_loi_init_conv_start/README.md) |
| 2026-10-15 | `tools/svd_decode.py`: giải mã mọi lệnh ghi thanh ghi hằng của firmware theo SVD (bit dự trữ, trường chỉ đọc, vượt độ rộng); đối chiếu nghĩa với datasheet (SPI mode 0 / master / MSB, CLKDIV, UART FD, PCLK, I2C, WDT). Sửa `i2c0.c` (SCLHT = half, tránh 406,8 kHz), `app_main.c` (feed mỗi 250 ms khi chờ IMU), thêm lệnh `w` đo chu kỳ WDT trong `diag.c`, cập nhật B2 và X16; vòng hiệu chuẩn gyro in nhắc mỗi 2 s khi không có ngắt INT (trước đây đứng im), cập nhật B5 | 39 + 12 lệnh ghi hằng, 0 cảnh báo; Keil 0 lỗi 0 cảnh báo, Code 15.360 + RO 1.680; m0_test PASS. [ra_soat_thanh_ghi](docs/bao_cao/2026-10-15_ra_soat_thanh_ghi/README.md) |
| 2026-10-15 | `ml/train_cnn.py --ema` (trung bình trượt mũ trọng số, mặc định tắt); thử trên N2 + dữ liệu thân, 3 seed, so có cặp | Không có tác dụng (Macro-F1 chênh ≤ 0,0004, PRE_ALARM giả trùng hoàn toàn): phương sai theo seed đến từ quỹ đạo huấn luyện, chỉ gộp nhiều seed mới giảm được. [ai09_du_lieu_than/ema](docs/bao_cao/2026-10-15_ai09_du_lieu_than/README.md) |
| 2026-10-15 | Thêm `CLAUDE.md` (Claude Code tự đọc trên mọi máy: bắt đầu phiên, luật, thay phiên nhiều tài khoản, môi trường); `params_src.txt` ghi đường dẫn tương đối với gốc dự án (`export_mem.py`, `gen_tb_proto.py`, `cosim.py`), viết lại 4 file có sẵn; `.gitignore` thêm log Keil | Để nhiều máy và nhiều tài khoản Claude thay phiên chạy dự án qua Git mà không hỏng đường dẫn; xuất lại `n2_p1` vẫn trùng từng byte |
| 2026-10-15 | Repo GitHub private `danhle396/fpga2026gowin`; `.gitattributes` (LF cho script/mã/`.txt`, `.fs` nhị phân); hook Claude Code `.claude/settings.json`: SessionStart tự `git pull` + báo trạng thái, Stop chặn khi còn thay đổi chưa commit/push và yêu cầu Chốt phiên | Để nhiều máy và nhiều tài khoản Claude thay phiên mà không mất việc; bản clone từ GitHub: SHA256 3 bitstream OK, `verify_spec_v3.py` TẤT CẢ PASS |
| 2026-10-15 | **RB-01 xong**: `run_all` 7/7 PASS trên Icarus 12.0 ở máy thứ hai (DESKTOP-A00FJKC, clone từ GitHub; cài Python 3.12.10 + Icarus 12 bằng winget). Cùng máy: `verify_spec_v3` và `m0_test` TẤT CẢ PASS, Keil `fw.uvprojx` 0 lỗi (15.360 + 1.680, trùng), **dựng lại bitstream 1 trùng từng dòng `.fs`** trừ dấu thời gian (Logic 907, 105,196 MHz) | Pass của RB-01 cần cả bản Icarus mới; bitstream của đợt B không còn phụ thuộc máy gốc. [may2_icarus12](docs/bao_cao/2026-10-15_may2_icarus12/README.md) |
| 2026-10-15 | TH-01 phần máy: `docs/spec.md` sinh từ Phụ lục A bằng `tools/sync_spec.py` (`--check` vào bộ kiểm nhanh của CLAUDE.md) | TH-01 yêu cầu bản SPEC riêng; sinh tự động để không thành nguồn thứ hai lệch luật. Chưa [x]: cần từng thành viên clone được |
| 2026-10-16 | **D1 lên 8/17 người** (thêm 107, 108: 840 cú ngã, 79.111 cửa sổ đầu; ngực, thắt lưng cùng người) vào `ml/data/public/`; thêm `tools/fetch_d1.sh`; `tools/playback_d1.py` chỉ phát lại người có lượt LOSO. Sửa số D1 trong DE_CUONG_v2 mục dữ liệu (i) và dòng 18 của bảng thay đổi (6 người / 604 cú ngã → 8 người / 840 cú ngã, ngày 16/10) | Máy chủ UCI cắt mỗi kết nối sau 16–25 phút; file 643 MB tải dở đủ trọn 101–108. Phần 6 người cũ trùng từng byte nên mô hình và báo cáo cũ vẫn đúng (chúng là số trên 6 người); 107, 108 qua ba phép kiểm vị trí đầu. [d1_8_nguoi](docs/bao_cao/2026-10-16_d1_8_nguoi/README.md) |
| 2026-10-16 | Rà chéo số giữa 3 file: H3 (mục 2) và RA-01 còn ghi bitstream 1 / E1 là Logic 913, 108,49 MHz như ngày 14/10 → sửa thành số hiện tại Logic 907, 105,20 MHz (giữ diễn biến) | Sau khi sửa `conv_start` 15/10 số đã đổi ở khung trạng thái, mục 10, DE_CUONG_v2 và THAY_DOI, nhưng sót hai chỗ này. Các số khác (Fmax, ms, Macro-F1, báo giả/giờ) khớp giữa 3 file |
| 2026-10-16 | Phản biện `docs/huong_dan_dot_B.md` đối chiếu mã firmware: mọi chuỗi "Mong đợi", lệnh menu, mã `rc`, tham số script và điện áp `pin_probe` khớp, trừ B5.4 → sửa B5.4, thêm `tools/gyro_residual.py` | B5.4 bảo đọc offset gyro dư bằng `STAT`, nhưng `STAT` chỉ in bộ đếm; người cầm board sẽ không kiểm được Pass của FW-05 |
| 2026-10-16 | Phản biện `docs/data_protocol.md` với `logger.py` / `windowing.py`: `windowing.py` từ chối `s00` (trùng mã người 200 với `h0`; `s00` chỉ dành cho file thử B5), tên file ghi rõ `<nn>` hai chữ số; hai script trong `docs/bao_cao/` (`test_windowing.py`, `phan_tich_do_nghieng.py`) bỏ đường dẫn cứng của máy gốc và chỉ phân tích người có lượt LOSO | Dùng nhầm `s00` cho dữ liệu thật sẽ gộp nó với `h0` khi chia LOSO. Hai script chạy lại trên máy thứ hai ra trùng log đã lưu (`test_windowing` TẤT CẢ PASS) |
| 2026-10-16 | `ml/train_cnn.py --subjects …` (chọn người, cả `--train-only`); README ghi rõ `ml/out/*_d1` là mô hình 6 người 101–106 và lệnh mặc định ghi đè thư mục đó | Dữ liệu đã lên 8 người nên không còn lệnh nào chọn lại đúng tập của các mô hình đã lưu. Thử tái lập `n2_d1` trên máy thứ hai: dữ liệu vào trùng (53.165 cửa sổ) nhưng lượt 101 ra Macro-F1 0,9816 / 97 sự kiện so với 0,9806 / 95, tức huấn luyện **không tái lập từng bit giữa các máy** (số thực, BLAS); weight INT8 đã lưu mới là nguồn cố định |
| 2026-10-16 | **AI-09/AI-10 trên D1 8 người** (N2 chỉ đầu, 3 seed): Macro-F1 0,977, recall sự kiện 99,6 %; FSM v3.1 T_SCORE 8: ngã nằm 96,3 %, PRE_ALARM giả 0,68/giờ, p90 trễ PRE_ALARM 5,92 s. Cập nhật TRẠNG THÁI, AI-09, AI-10, mục 10 (4 hàng) | Trên cùng người kiểm 101–106, thêm 2 người huấn luyện nâng Macro-F1 0,9683 → 0,9762. Lần đầu trung bình 3 seed đạt ≥ 95 % và ≤ 1/giờ trên D1, nhưng chỉ 2–3 lần báo giả; p90 trễ PRE_ALARM vượt 5 s là rủi ro mới. Chưa đổi mô hình của bitstream 3. [ai09_8_nguoi](docs/bao_cao/2026-10-16_ai09_8_nguoi/README.md) |
| 2026-10-16 | Độ trễ va chạm → PRE_ALARM tính đúng điều kiện của đề cương (`docs/bao_cao/2026-10-16_ai09_8_nguoi/tre_nam_yen_2s.py`): ngã nằm yên trong 2 s → p90 4,36 s, lớn nhất 4,56 s, 0/355 vượt 5 s (3 seed) | Dòng trước báo p90 5,92 s là rủi ro, nhưng số đó tính trên mọi cú ngã, kể cả người còn cử động lâu sau va chạm, nằm ngoài chỉ tiêu. Rủi ro đóng trên D1; vẫn phải đo trên mũ |
| 2026-10-16 | **Đề cương v2.1 + SPEC v3.2: gọn đề tài.** Mạng 2 lớp NORMAL / FALL (IMPACT để dành); công tắc bật/tắt thay cảm biến đội mũ; huấn luyện chỉ bằng D1; D2 + D3 thành một buổi thử nhỏ chỉ để kiểm tra; chỉ tiêu rơi mũ đổi thành "đếm và hủy được"; LED 7 đoạn thay OLED. Sửa DE_CUONG_v2 (23 chỗ + ghi chú phiên bản), THAY_DOI (dòng 5, 9, 14, 18, mục Điều chỉnh v2.1, đoạn giải trình), file này (tóm tắt, 4.4, G3, G5, G6, AI-05, AI-07, AI-08, RA-06, TH-03, TH-10, mục 9, mục 10, demo, A.4, A.8, E.1) | Nhóm yêu cầu làm ở mức vừa sức, gần hướng tham khảo (2 lớp, ESP32 → MCU + FPGA). Số liệu cho phép: trên D1 8 người, mạng 2 lớp + FSM v3.1 cho ngã nằm → PRE_ALARM 96,3 %, 0,68 báo giả/giờ, trễ p90 4,36 s với ngã nằm yên trong 2 s ([ai09_8_nguoi](docs/bao_cao/2026-10-16_ai09_8_nguoi/README.md)). Firmware đã có đầu vào WEAR trên P2.3 nên công tắc không cần sửa mã. Đường lùi: bật lại lớp IMPACT (đầu ra 4 logit sẵn) hoặc quy tắc rơi tự do nếu buổi thử có > 2/20 va mũ vào PRE_ALARM |
| 2026-10-16 | **D1 lên 11/17 người** (101–110, 203; 1.180 cú ngã); **nhóm quyết chỉ dùng kênh đầu** (AI-09: bỏ dữ liệu thân); thiết kế hộp trên đỉnh mũ (hai board + MPU6050 + nút + pin). `playback_d1.py`, `spectrum_check.py` nạp `.npz` một lần (phát lại 15–20 phút → 80 s, kết quả trùng) | Một lượt tải UCI giữ được 87 phút. Nạp lười làm mỗi bản ghi giải nén lại cả mảng 12 MB, và làm hỏng lượt phát lại N2 + dữ liệu thân khi file bị chép đè. Hộp trên đỉnh mũ đặt cảm biến ở đỉnh đầu, giống vị trí cảm biến đầu của D1. [d1_11_nguoi](docs/bao_cao/2026-10-16_d1_11_nguoi/README.md) |
| 2026-10-16 | **Chốt mô hình phần cứng: N2 chỉ dữ liệu đầu trên E2 (bitstream 3)**; N1/E1 chỉ để thông mạch SPI (B7). Tiến trình dài chuyển sang Task Scheduler (tác vụ `fpga2026_jobs`) | N1 trên 8 người: Macro-F1 0,842, recall 87,0 %, không đạt ≥ 95 % và ≤ 6 ms; N2: 0,977, 99,6 %, 5,15 ms. Tiến trình chạy tách qua WMI bị tắt im lặng sau vài phút (lô N2 11 người, chuỗi phần cứng, tải). [ai09_8_nguoi](docs/bao_cao/2026-10-16_ai09_8_nguoi/README.md) |
| 2026-10-16 | **Một nút cho bật/tắt + CANCEL + SOS** (nhóm chọn cách 2): `firmware/src/pwr_btn.c/.h`, `BTN_POWER` trong `fw_config.h`, ghép vào `app_tick`; SPEC v3.2 thêm quy ước nút ở A.8; E.1 nút ngoài nối song song SW3 (P2.4); thay mọi chỗ "công tắc bật/tắt" ở DE_CUONG_v2, THAY_DOI và file này; B9 của hướng dẫn đợt B viết lại | Hộp trên đỉnh mũ chỉ có 1 nút. Không sửa Safety FSM, nên FSM vẫn trùng `safety_model.py` (240.000 tick). 9/9 ca nút PASS trên mã máy, phép âm bắt được; giữ 2 s để bật không vô tình thành SOS; ngã ngay sau khi tắt vẫn báo động và vẫn CANCEL được |
| 2026-10-16 | **(đã xong, xem dòng N2 11 người)** LOSO N2 chỉ đầu trên D1 **11 người**, 3 seed (20261014, 7, 99) + phát lại FSM từng seed và gộp 3 seed; sau đó huấn luyện mô hình cuối 11 người, xuất E2, dựng lại bitstream 3, kiểm `tb_e2` + netlist (`run_gl.sh`), cập nhật `selftest_expect` cho `FW_BITSTREAM 3`. Đồng thời sửa khung TRẠNG THÁI (gạch AI: bỏ câu "đề nghị giữ" dữ liệu thân, số mới nhất lên trước) và CLAUDE.md mục 5 | Bitstream 3 vẫn mang N2 6 người trong khi đã chốt N2 chỉ đầu và D1 có 11 người. Kết quả chạy để ngoài repo cho tới khi xong |
| 2026-10-16 | Sửa `pwr_btn.c`: vừa TẮT mà FSM còn MONITOR / SUSPECT (3 s chờ `WEAR_OFF_MS`) thì lần nhấn chỉ là cử chỉ BẬT, không chuyển cho FSM; thêm ca test | Trước đó giữ nút để bật lại trong 3 s đó sẽ thành SOS → ALARM khi đang tắt (phép âm: mã cũ FAIL ca mới). Sau sửa 63/63 PASS trên mã máy M0, 10/10 ca của nút; Keil 0 lỗi 0 cảnh báo. [pwr_btn_sos_gia](docs/bao_cao/2026-10-16_pwr_btn_sos_gia/README.md) |
| 2026-10-16 | **N2 chỉ đầu trên D1 11 người** (3 seed) + phát lại FSM; **bitstream 3 dựng lại với N2 11 người** (`ml/out/n2_11_d1`, `ml/out/e2_matrix/n2_11_p1`, seed 20261014 chọn trước); `firmware/src/selftest_expect_v3_e2_n2.h` mới; sửa số ở TRẠNG THÁI, AI-09, AI-10, mục 10 (Recall, Macro-F1, báo giả, Timing), THAY_DOI dòng a và đoạn Bổ sung v2.1, bitstreams/README, README, CLAUDE.md | Macro-F1 0,983, recall 99,6 %; FSM T8 ngã nằm 96,2 %, báo giả 1,11/giờ (vượt nhẹ, toàn bộ từ 815); trễ p90 4,32 s. `tb_e2` 50/50, `tb_proto` PASS, netlist PASS, Fmax 98,12 MHz (từ 107,25), Keil 0 lỗi. [n2_11_nguoi](docs/bao_cao/2026-10-16_n2_11_nguoi/README.md) |
| 2026-10-16 | Phân tích báo giả 815 (nằm xuống giường) trên 11 người: đỉnh \|a\| 3 s trước SUSPECT của báo giả 1,69–2,50 g, ngã nằm thật trung vị 4,7 g nhưng p5 ≈ 2,56 g (`phan_tich_815.py`) | Ngưỡng 2,5 g loại 75–89 % báo giả nhưng kéo ngã nằm → PRE_ALARM xuống ≈ 92 % (< 95 %); 2,0 g gần như không loại được. Chưa đổi SPEC; ghi "cổng va chạm" là ứng viên, đo ngưỡng trên buổi thử đội mũ (D1 25 Hz làm đỉnh thấp hơn thật). [n2_11_nguoi](docs/bao_cao/2026-10-16_n2_11_nguoi/README.md) mục 4 |
| 2026-10-16 | README, `tools/hil_test.py`, `bitstreams/README.md`: chỉ rõ mô hình của bitstream 3 là `ml/out/n2_11_d1` và lệnh HIL cho bitstream 3 (`--proto 3 --params ml/out/n2_11_d1/params_int8.npz`) | HIL so với sai mô hình sẽ báo sai lệch mọi cửa sổ dù chip đúng; trước đó tài liệu còn trỏ `n2_d1` / `n2s_d1`. Thử `--mock` với mô hình mới: 50/50 khớp |
| 2026-10-16 | Mô phỏng ghép firmware ↔ RTL với N2 11 người (`cosim.py --e2 ml/out/e2_matrix/n2_11_p1`) và bảng FP32 / INT8 / RTL cho mô hình lên chip (AI-11) | 423/423 khung khớp golden, CYCLES 258.080, FSM trùng golden; chuỗi đầy đủ được kiểm đúng với bitstream 3 sẽ nạp |
| 2026-10-16 | `tools/playback_log.py`: chấm buổi thử trên mũ theo Pass của đề cương v2.1; thêm vào `docs/data_protocol.md` mục 6 | Chưa có công cụ tính ngã → PRE_ALARM / báo giả/giờ / va mũ trên file LOG. Trùng mã máy `app_core.c` 15/15 lần đổi trạng thái; buổi thử giả từ D1: ngã nằm 24/24, đứng dậy 0/8, file lỗi bị bỏ đúng. [playback_log](docs/bao_cao/2026-10-16_playback_log/README.md) |

---

## PHỤ LỤC E – CHÂN VÀ NỐI DÂY

Cột "Trạng thái" dùng ba mức, chưa dòng nào ở mức "đã chạy trên board":

- **P&R** = đọc từ sơ đồ Kiwi Primer 20K rev v1.0 ([docs/datasheet/](docs/datasheet/fpga-kiwi-primer-20k.pdf)) và đã qua Place & Route của Gowin EDA, chưa đo trên board. TH-02 có nhiệm vụ đo.
- **datasheet** = chức năng chân theo "SN32F400 Series User's Manual" V2.2 ([docs/datasheet/](docs/datasheet/SN32F407_V2.2_EN.pdf)), chương 1.4 (sơ đồ chân LQFP48) và chương 6 (PFPA).
- **EVK** = theo ghi chú phần cứng của dự án vòng 1 (`D:\hoctap\fpga\thi_fpga\MCU\docs\PIN_MAPPING.md`, `HARDWARE_FINDINGS.md`), đọc từ sơ đồ `32F407 EVK V1.0.pdf`. File sơ đồ đó chưa có trong thư mục này.
- **header** = nhãn in trên board cạnh header, đọc từ ảnh board (hình 16) trong "Hướng dẫn sử dụng bo mạch SONiX SN32F407 EVK" V1.0 ([docs/datasheet/](docs/datasheet/SONiX_32F407_EVK_Guide_Ver1.0_VN.pdf)). Ảnh chỉ cho biết chân nào ra header, không cho biết chân đó còn nối linh kiện nào khác.

**Sửa lớn ngày 14/10.** Bảng chân MCU trước đây dựa trên sơ đồ Start-Kit trong `sdk/`, không phải board của nhóm. Board thật là "32F407 EVK V1.0": P0.0–P0.7 là LED 7 đoạn, P0.10/P0.11 là I²C đã có EEPROM, P2.4–P2.7 là cột phím. Vì vậy SPI, I²C, UART, nút, LED, còi đều đổi chân so với bản trước. Phía FPGA không đổi.

Vỏ LQFP48 của SN32F407F chỉ đưa ra các chân: P0.0–P0.7, P0.10, P0.11 · P1.0–P1.12 · P2.0–P2.10 · P3.0–P3.2, P3.5–P3.13. Không có P0.8, P0.9, P3.3, P3.4.

### E.1 Bảng nối dây

| Tín hiệu | Chân MCU (chân vỏ) | Nối tới | Chân FPGA: ball · header | Trạng thái |
|---|---|---|---|---|
| GND | VSS (47) | GND của Kiwi | J1-1, J1-2 | nối trước tiên |
| SPI SCK | P1.0 (39), SCK0 lựa chọn 2 · header J12 `SCK_P10` | `spi_sclk` | K14 · J1-4 | MCU: datasheet + header · FPGA: P&R |
| SPI MISO | P1.1 (40), MISO0 lựa chọn 2 · J12 `MISO_P11` | `spi_miso` | J13 · J1-6 | như trên |
| SPI MOSI | P1.2 (41), MOSI0 lựa chọn 2 · J12 `MOSI_P12` | `spi_mosi` | J12 · J1-5 | như trên |
| SPI CS | **P2.8 (19)** · header J7 `P28`, GPIO ra, mặc định mức cao | `spi_cs_n` | K12 · J1-3 | như trên |
| IRQ | **P2.9 (20)** · J7 `P29`, vào, kéo xuống, ngắt cạnh lên | `irq` | H12 · J1-7 | như trên |
| RST_N | P2.1 (12) · J7 `P21`, ra, mặc định mức cao | `rst_n` (chỉ top v3: bitstream 2, 3; `fpga_top` PROTO 1 không có) | J11 · J1-8 | pin report 15/10: J11, LVCMOS33, kéo lên |
| Giữ flash SPI của EVK im lặng | P1.8 (34) · J12 `SEL_P18`, GPIO ra, **luôn mức cao**; không cắm dây | — | — | datasheet + header; lý do ở dưới bảng |
| Clock FPGA | — | Dao động 27 MHz trên board | H11 | P&R |
| I²C SCL | P0.10 (42), SCL0 lựa chọn 2 · header J13 `SCL_P010` | MPU6050 SCL, OLED SCL | — | datasheet + EVK + header |
| I²C SDA | P0.11 (43), SDA0 lựa chọn 2 · J13 `SDA_P011` | MPU6050 SDA, OLED SDA | — | datasheet + EVK + header |
| INT cảm biến | P2.2 (13) · J7 `P22`, vào, kéo xuống, ngắt cạnh lên | MPU6050 INT | — | datasheet + header |
| WEAR | P2.3 (14) · J7 `P23`, vào, kéo lên | Không dùng ở v2.1 (bật/tắt bằng nút, `pwr_btn.c`); dự trữ cho cảm biến đội mũ, khi đó đặt `WEAR_PRESENT 1` | — | datasheet + header |
| UART0 TX / RX | P3.1 (30) / P3.2 (31), lựa chọn 2 · header J10 `UTX_P31` / `URX_P32` | Mạch USB-UART (RX / TX) | — | datasheet + EVK + header |
| Nút duy nhất: BẬT/TẮT + CANCEL + SOS (v2.1) | Phím SW3: ROW0 = P1.4 (45) ra mức 0, COL0 = P2.4 (15) vào kéo lên, nhấn = 0. Nút ngoài trên hộp nối song song SW3 (P2.4 xuống GND) | Phím ma trận trên EVK; P2.4 ra header hay không **[CẦN XÁC MINH trên board]**, nếu không thì hàn song song vào SW3 | — | EVK |
| Nút đánh dấu, cũng là nút chọn chế độ LOG lúc khởi động | Phím SW6: ROW0 = P1.4, COL3 = P2.7 (18) vào kéo lên | Phím ma trận trên EVK | — | EVK |
| LED báo | P3.8 (1), mức thấp = sáng | LED D6 trên EVK | — | EVK |
| Còi | P3.0 (29), CT16B0_PWM0 lựa chọn 1 | Còi trên EVK | — | datasheet + EVK; cực tính chưa thử |
| Dự trữ | P2.0 (11), P3.9 (2): không thấy trên header nào trong ảnh, phải hàn dây nếu cần | — | — | datasheet |
| Không dùng làm I/O | P3.5 / P3.6 (SWDIO / SWCLK, nối mạch nạp SN-Link trên EVK qua jumper J5 / J4), P3.7 (RESET), P1.3 (BOOT: mức thấp lúc khởi động thì vào bootloader), P3.10–P3.13 (thạch anh) | — | — | datasheet |

J1 là header 2 × 20 của Kiwi. Số thứ tự chân trên header được đọc từ hình sơ đồ, nên phải dò lại bằng `rtl/pin_probe` (E.4) trước khi nối dây.

**Chân EVK đã có linh kiện (theo ghi chú vòng 1):**

| Chân | Trên EVK |
|---|---|
| P0.0–P0.7 | LED 7 đoạn, đoạn A..G và DP, mức cao = sáng |
| P1.9–P1.12 | COM0..COM3 của LED 7 đoạn, qua transistor NPN, mức cao = bật |
| P1.4–P1.7 / P2.4–P2.7 | Hàng / cột phím ma trận 4 × 4 |
| P2.10 | Đường ngắt chung của phím |
| P0.10 / P0.11 | I²C0, điện trở kéo lên 10 kΩ, EEPROM 24C05 ở địa chỉ 0x50 |
| P3.0 · P3.8 | Còi · LED D6 |
| P3.1 / P3.2 | UART0 |
| P3.10–P3.13 | Thạch anh 32,768 kHz và 16 MHz |

**Header của EVK (đọc từ ảnh trong hướng dẫn EVK):** J7 = `P21, P22, P23, P28, P29` · J8 = `P310, P311, P312, P313` (chân thạch anh, không dùng) · J10 = `UTX_P31, URX_P32, GND` · J12 = `SEL_P18, SCK_P10, MISO_P11, MOSI_P12, GND` · J13 = `SCL_P010, SDA_P011, GND`. Mọi tín hiệu E.1 cần nối dây đều nằm trên năm header này. **Không header nào có chân 3,3 V**; P2.0 và P3.9 không ra header.

**Vì sao CS chuyển từ P1.8 sang P2.8 (sửa 14/10).** EVK có một chip flash SPI (hình 13 của hướng dẫn, chip 8 chân cạnh EEPROM) và header J12 đưa SPI0 ra kèm `SEL_P18`. Rất có thể flash nằm trên chính SCK/MISO/MOSI này với chân chọn là P1.8. Nếu đúng vậy mà vẫn dùng P1.8 làm CS của FPGA thì mỗi lần MCU gọi FPGA, flash cũng được chọn và hai chip cùng đẩy MISO. Đặt CS của FPGA ở P2.8 và giữ P1.8 mức cao thì an toàn trong cả hai trường hợp, không tốn gì. Flash dùng chân chọn nào thì **[CẦN XÁC MINH – nguồn: sơ đồ trong thư mục `CIRCUIT_32F407_EVK_V1.0` của SONiX, hoặc phép thử ở E.4 bước 2]**. IRQ chuyển từ P2.0 sang P2.9 vì P2.0 không ra header.

Chân nào trong J7 còn nối sẵn linh kiện khác trên EVK (LED RGB trong sơ đồ khối của SONiX, biến trở ADC) thì ảnh không cho biết **[CẦN XÁC MINH – nguồn: sơ đồ `CIRCUIT_32F407_EVK_V1.0`; thử nhanh: đặt từng chân làm ra, đổi mức, xem trên board có gì sáng hay kêu]** (X2).

MPU6050: VCC = 3,3 V (lấy từ đâu trên EVK thì chưa rõ vì header không có chân 3,3 V; tìm trên sơ đồ hoặc đo, không lấy từ chân 5 V của USB nếu module không có ổn áp), AD0 nối GND (địa chỉ 0x68, không trùng EEPROM 0x50), XDA và XCL để trống. Bus I²C của EVK kéo lên bằng 10 kΩ; nếu sườn lên quá chậm ở 400 kHz với cáp dài tới mũ thì hạ xuống 100 kHz (đọc 14 byte mất khoảng 1,7 ms, vẫn lọt chu kỳ 10 ms).

Chưa có OLED thì tầng 1 có thể hiện trạng thái bằng LED 7 đoạn sẵn có trên EVK (mục 9).

### E.2 Thiết lập phía MCU

Giá trị lấy từ datasheet V2.2; tên thanh ghi theo `SN32F400.h` của pack.

| Thanh ghi | Giá trị | Ý nghĩa |
|---|---|---|
| `SN_PFPA->SPI0` | 0x2A, giữ SEL0 = 0 | MISO0 = P1.1 (bit 1:0 = 2), MOSI0 = P1.2 (bit 3:2 = 2), SCK0 = P1.0 (bit 5:4 = 2). SEL0 (bit 7:6) không dùng vì CS là GPIO |
| `SN_PFPA->I2C0` | 0x0A | SDA0 = P0.11 (bit 1:0 = 2), SCL0 = P0.10 (bit 3:2 = 2) |
| `SN_PFPA->UART0` | 0x0A | UTXD0 = P3.1 (bit 1:0 = 2), URXD0 = P3.2 (bit 3:2 = 2) |
| `SN_PFPA->CT16B0` | PWM0 (bit 1:0) = 1 | CT16B0_PWM0 ra P3.0 |
| `SN_SPI0->CTRL0` | SELDIS = 1 (mặc định), DL = 7, MS = 0, SPIEN = 1 | SELDIS = 1 thì phần cứng không đụng tới chân SEL, CS do GPIO điều khiển. DL = 7 là khung 8 bit. Sau mỗi lần đổi cấu hình khi SPIEN = 1 phải ghi FRESET = 3 |
| `SN_SPI0->CTRL1` | 0 | CPOL = 0, CPHA = 0 (mode 0), MSB trước |
| `SN_SPI0->CLKDIV` | 23 khi thử, 5 khi chạy | SCK = PCLK / (2·DIV + 2). Với PCLK 48 MHz: 1 MHz và 4 MHz |
| `SN_CRC->CTRL` | CRC[1:0] = 0; bit RESET (2) = 1 trước mỗi khung | CRC-16-CCITT: đa thức 0x1021, mầm 0xFFFF, không đảo bit, không XOR cuối, tức đúng CRC của A.7. Ghi từng byte vào `SN_CRC->DATA`, đọc kết quả ở chính thanh ghi đó |
| `SN_FLASH->LPCTRL` | 0x5AFA0019 trước khi lên 48 MHz | Mức chờ Flash cho 24 MHz < HCLK ≤ 48 MHz. File `system_SN32F400.c` của pack tự đặt |

SPI0 có FIFO 8 khung cho mỗi chiều. Thời gian CS: giữ CS thấp trước cạnh SCK đầu ≥ 2 chu kỳ SCK và sau cạnh cuối ≥ 1,5 chu kỳ.

| Bật clock trong `SN_SYS1->AHBCLKEN` | Bit |
|---|---|
| CT16B0 (còi) | 5 |
| SPI0 | 12 |
| UART0 | 16 |
| I2C0 | 21 |
| CRC | 27 |

GPIO (mỗi cổng một bộ thanh ghi `DATA, MODE, CFG, IS, IBS, IEV, IE, RIS, IC, BSET, BCLR`):

| Việc | Cách đặt |
|---|---|
| Chân ra | `MODE` bit = 1; ghi mức bằng `BSET` / `BCLR` |
| Chân vào | `MODE` bit = 0; `CFG` 2 bit mỗi chân: 0 = kéo lên, 1 = kéo xuống, 2 = không kéo (mặc định sau reset), 3 = không kéo và tắt Schmitt. Điện trở kéo lên trong chip 60–100 kΩ ở 3,3 V |
| Ngắt cạnh lên (P2.9, P2.2) | `IS` = 0 (cạnh), `IBS` = 0, `IEV` = 0 (lên), `IE` = 1; xóa cờ bằng `IC` |
| Số ngắt NVIC (theo SVD) | Cổng P0 = 31, P1 = 30, P2 = 29; SPI0 = 6; I2C0 = 10; UART0 = 13; CT16B1 = 16; WDT = 25 |

IRQ của FPGA và INT của cảm biến cùng nằm trên cổng P2 nên dùng chung một trình phục vụ ngắt; trong đó đọc `RIS` để biết chân nào vừa kích. Phím CANCEL đọc bằng cách quét, không dùng ngắt.

Clock: IHRC 48 MHz trong chip (47,76–48,24 MHz ở 25 °C) đủ cho UART và SPI. EVK còn có thạch anh 16 MHz nếu cần chính xác hơn.

**VDD của board MCU phải là 3,3 V trước khi nối FPGA hay cảm biến.** Chip chạy được từ 1,8 đến 5,5 V và mức ra bằng VDD; nếu MCU chạy 5 V thì chân MCU sẽ đưa 5 V vào FPGA (bank 3,3 V) và MPU6050. Ngược lại, mức cao 3,3 V của FPGA cũng thấp hơn ngưỡng VIH = 0,7·VDD = 3,5 V của MCU chạy 5 V. Theo mục 4.2.1 của hướng dẫn EVK: công tắc SW1 ở ON thì LDO 3,3 V cấp cho MCU, cùng với jumper J1 nối `SW_ON_3.3V`–`32F407_VDD` và J3 nối `T_VDD`–`32F407_VDD`. Đây là thiết lập mặc định của SONiX, nhưng vẫn đo bằng đồng hồ (E.4 bước 1).

### E.3 Thiết lập phía FPGA

Nguồn: sơ đồ nguyên lý Kiwi Primer 20K rev v1.0, trang 4, 5, 6, 10 và 12.

**Điện áp bank.** Bank 0, 1, 2, 3, 6, 7 cấp 3,3 V; bank 4 và 5 cấp 1,5 V cho DDR3. Mọi chân tín hiệu trên các header J1, J2, J5 đều thuộc bank 3,3 V.

**Lý do chọn J1-3 .. J1-8.** Sáu chân liền nhau, sát hai chân GND (J1-1, J1-2), thuộc bank 0 và 1, chỉ đi ra header và không mang chức năng cấu hình.

**Các chân phải tránh**

| Chân | Lý do |
|---|---|
| J1-35, J1-36 | `PMIC_SDA`, `PMIC_SCL`: bus I²C của IC nguồn MP5479. Tín hiệu lạ trên hai chân này có thể đổi điện áp các đường nguồn của board |
| J1-37, J1-38 và J2-37, J2-38 | Chân nguồn `P3V3_EXT` và `P5V0`, không phải I/O |
| Ball R9, T10, T9, P9, N9, M8 (trên J2) và C10 (J1-18) | Chân bank 3 có chức năng thứ hai dùng lúc cấu hình: D0–D3, DIN, DOUT, SCLK |

**File ràng buộc.** Năm cổng đang có trong `fpga_top.v` đã được ghi vào `src/fpga_top.cst` của project Gowin:

```
IO_LOC "clk" H11;
IO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=NONE;
IO_LOC "spi_cs_n" K12;
IO_PORT "spi_cs_n" IO_TYPE=LVCMOS33 PULL_MODE=UP;
IO_LOC "spi_sclk" K14;
IO_PORT "spi_sclk" IO_TYPE=LVCMOS33 PULL_MODE=DOWN;
IO_LOC "spi_mosi" J12;
IO_PORT "spi_mosi" IO_TYPE=LVCMOS33 PULL_MODE=DOWN;
IO_LOC "spi_miso" J13;
IO_PORT "spi_miso" IO_TYPE=LVCMOS33 PULL_MODE=NONE DRIVE=8;
IO_LOC "irq" H12;
IO_PORT "irq" IO_TYPE=LVCMOS33 PULL_MODE=NONE DRIVE=8;
```

Thêm hai dòng sau khi `fpga_top.v` có cổng `rst_n` (RA-07):

```
IO_LOC "rst_n" J11;
IO_PORT "rst_n" IO_TYPE=LVCMOS33 PULL_MODE=UP;
```

Kết quả P&R ngày 13/10 (Gowin EDA V1.9.11.03): cả năm cổng vào đúng ball, `IO Type` = LVCMOS33, `BankVccio` = 3,3. Báo cáo lưu ở `docs/bao_cao/2026-10-13_pnr_e1_chan_j1/`. Chạy lại ngày 14/10 sau RA-01: chân không đổi; báo cáo ở `docs/bao_cao/2026-10-14_ra01_conv1_shift/`.

Lý do chọn điện trở kéo: CS kéo lên để FPGA không bị chọn khi MCU chưa lái chân; SCK và MOSI kéo xuống cho đúng mức nghỉ của mode 0.

**Tài nguyên có sẵn trên Kiwi, dùng được cho gỡ lỗi**

| Tài nguyên | Ball | Ghi chú |
|---|---|---|
| LED1 .. LED8 | D15, C16, H14, H13, G15, G14, G13, F13 | Mức thấp = sáng |
| Nút BTN1, BTN2, BTN3 | A12, B12, A11 | Nhấn = mức thấp; có điện trở kéo lên 100 kΩ |
| Nút RST (S1) | B11 | Mức thấp khi nhấn và lúc mới cấp nguồn |
| UART qua CH340N (cổng USB-C) | FPGA nhận ở C4, phát ở B5 | PC nói chuyện thẳng với FPGA, không cần MCU |

### E.4 Kiểm tra trước khi cấp nguồn lần đầu

1. Thiết lập EVK theo mục 4.2.1 của hướng dẫn: J5 `T_DATA`–`SWDIO_P35`, J4 `T_CLK`–`SWCLK_P36`, J3 `T_VDD`–`32F407_VDD`, J1 `SW_ON_3.3V`–`32F407_VDD`, SW1 ở ON. Cắm USB: LED D4 xanh (PC thấy SN-Link), D5 xanh (SN-Link thấy MCU). Đo VDD của MCU = 3,3 V.
2. Chưa nối FPGA: nạp `firmware/keil/fw.uvprojx`, gõ lệnh `f` trên UART (460800 8N1). Mã đó kéo P1.8 xuống thấp và gửi lệnh đọc mã JEDEC 0x9F qua SPI0 (1 MHz). Nhận được 3 byte khác 0x00 và 0xFF thì flash của EVK đúng là dùng P1.8 làm chân chọn, giữ quyết định ở E.1. Nhận toàn 0xFF thì kéo lần lượt P2.8 và P2.9 xuống và thử lại: nếu flash trả lời ở một trong hai chân đó thì phải đổi CS và IRQ sang chân khác trước khi nối FPGA.
3. Chưa nối dây: nạp `rtl/pin_probe/pin_probe.fs` vào Kiwi. LED1 nháy chậm là bitstream đang chạy. Chân thứ k (k = 1..6, từ J1-3 đến J1-8) phát k xung 1 kHz mỗi 8 ms: đếm bằng logic analyzer, hoặc đo điện áp DC sẽ thấy khoảng 0,21 / 0,41 / 0,62 / 0,83 / 1,03 / 1,24 V. Sai vị trí nào thì sửa E.1 trước khi nối dây.
4. Nạp bitstream chính, vẫn chưa nối dây: đo `spi_miso` (J1-6) và `irq` (J1-7), phải ≤ 3,3 V.
5. Nối GND trước, rồi mới nối dây tín hiệu; dây ≤ 15 cm.
6. Bắt đầu ở SCK 1 MHz (việc RA-04, FW-09).
