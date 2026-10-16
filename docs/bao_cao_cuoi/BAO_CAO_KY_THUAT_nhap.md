# MŨ BẢO HỘ PHÁT HIỆN TÉ NGÃ — BÁO CÁO KỸ THUẬT (BẢN NHÁP)

**Đội VKU-NewBie** · Cuộc thi thiết kế FPGA và MCU mở rộng khu vực miền Trung 2026 · Bản nháp ngày 16/10/2026

> **Tình trạng bản nháp.** Mọi số trong báo cáo đều lấy từ mô phỏng, từ báo cáo Place & Route của Gowin EDA, hoặc từ phát lại bộ dữ liệu công khai. Những mục cần số đo trên chip hoặc trên mũ thật được đánh dấu **[CHỜ ĐO]** và sẽ điền sau đợt thử trên board và buổi thử đội mũ. Nguồn của từng con số ghi ở cột "Bằng chứng" (thư mục `docs/bao_cao/` của repo).

---

## 1. Tóm tắt

Hệ thống là một mũ bảo hộ chạy độc lập:
- MPU6050 trên mũ đo 6 trục ở 100 Hz.
- Vi điều khiển SONiX SN32F407 lọc và lượng tử tín hiệu, cứ 0,32 s gửi một cửa sổ 2,56 s sang FPGA.
- FPGA Gowin GW2A-18 (Kiwi Primer 20K) chạy mạng 1D-CNN INT8 bằng **RTL tự viết**, không dùng IP AI đóng gói.
- Safety FSM trên MCU chỉ báo động khi người đội **ngã rồi nằm bất động**, sau 10 s đếm ngược mà không ai hủy.

Kết quả hiện có (mô phỏng và dữ liệu công khai, chưa đo trên chip):

| | Kết quả |
|---|---|
| Mạng N2, 3 lớp Conv + Dense, INT8; tách theo người trên 11 người của bộ công khai | Macro-F1 **0,983**; nhận ra **99,6 %** cú ngã |
| Sau Safety FSM (phát lại 1.180 cú ngã và 5,43 giờ sinh hoạt) | **96,2 %** cú ngã kết thúc nằm dẫn tới PRE-ALARM; **1,11** lần cảnh báo giả mỗi giờ; 0/234 cú ngã có tự đứng dậy bị báo |
| Thời gian suy luận trên FPGA | **5,15 ms** (258.080 chu kỳ ở 50,143 MHz); bản chạy trên MCU ước tính 74–232 ms |
| Khớp phần cứng – phần mềm | RTL và netlist sau Place & Route khớp mô hình tham chiếu **từng bit**; chuỗi firmware → FPGA → firmware khớp 423/423 khung |
| Tài nguyên | Logic 8 %, BSRAM 18 %, DSP 10 %, Fmax 98,12 MHz |

---

## 2. Kiến trúc hệ thống

```
        MŨ BẢO HỘ                    SN32F407 (Cortex-M0)                      KIWI PRIMER 20K (GW2A-18)
 ┌──────────────────┐   I²C   ┌────────────────────────────┐  SPI 772 byte  ┌──────────────────────────────┐
 │ MPU6050 (6 trục) │────────►│ Đọc 100 Hz theo ngắt       │───────────────►│ SPI Slave + Parser + CRC-16  │
 │ ±16 g, ±2000 °/s │  INT    │ Lọc [1,3,3,1]/8, ↓2 → 50 Hz│  mỗi 0,32 s    │ Bộ đệm cửa sổ (BSRAM)        │
 └──────────────────┘────────►│ Lượng tử INT8, ring 128×6  │                │ 1D-CNN INT8 (RTL tự viết)    │
 ┌──────────────────┐         │                            │◄───────────────│  Conv → Pool → … → Dense     │
 │ Nút bấm (1 nút)  │────────►│ Khối bất động + độ nghiêng │  IRQ + khung   │ Argmax + Score               │
 │ bật/tắt·CANCEL·SOS│        │ Bỏ phiếu 2/3 → Safety FSM  │───────────────►│ Thanh ghi kết quả, IRQ       │
 └──────────────────┘         │ LED 7 đoạn·còi·LED·UART log│     RST_N      └──────────────────────────────┘
                              └────────────────────────────┘
```

**Đặc tả chung (SPEC v3.2)** là một tài liệu duy nhất mà RTL, firmware và phần mềm Python cùng tuân theo. Nó quy định:
- thang đo cảm biến;
- bộ lọc và lượng tử;
- cửa sổ và gán nhãn;
- số học INT8;
- khung SPI;
- Safety FSM.

**Mô hình tham chiếu số nguyên** (`ml/src/golden_model.py`) là đáp án. Mọi tầng (RTL, netlist, firmware, công cụ PC) đều được kiểm là khớp nó từng bit.

### 2.1 Mô hình 1D-CNN (N2)

Cấu trúc:
- đầu vào 128 × 6 INT8;
- Conv1D 6→16 (k = 5) + ReLU + MaxPool 2;
- Conv1D 16→16 + ReLU + MaxPool 2;
- Conv1D 16→32 + ReLU + MaxPool 2;
- Flatten (16 × 32) → Dense 512→4 → Argmax.

Mạng có 6.368 trọng số, 68 bias, 227.328 MAC mỗi cửa sổ. Trọng số và đầu vào là INT8, bộ cộng dồn INT32; sau mỗi lớp tái lượng tử bằng dịch phải và kẹp về 0…127. Đầu ra 4 logit, trong đó dùng 2 lớp là NORMAL và FALL; 2 lớp còn lại để dành cho mở rộng (IMPACT, suýt ngã). Điểm tin cậy SCORE = (logit thắng − logit nhì) dịch phải, bão hòa 0…127.

Mạng N2 được chọn sau khi so trên 8 người. Mạng 2 lớp Conv + Global Average Pooling của phiên bản đầu (N1) chỉ đạt Macro-F1 0,842 và nhận ra 87,0 % cú ngã, không đạt chỉ tiêu.

### 2.2 FPGA

| Khối | Mô tả |
|---|---|
| SPI Slave | Đồng bộ SCK, CS, MOSI vào miền 50,143 MHz bằng chuỗi flip-flop; SPI mode 0, tới 4 MHz |
| Parser khung v3 | `0xA5` · SEQ · 768 byte · CRC-16/CCITT. Kiểm CRC, kiểm độ dài, báo trạng thái lỗi trong khung trả về |
| Engine E2 | Một chu kỳ mỗi MAC; ROM trọng số và bias khởi tạo từ `.mem`; hai RAM đặc trưng dùng luân phiên; dữ liệu xếp theo thời gian nên bộ sinh địa chỉ chỉ cần bộ đếm. Có bộ đếm chu kỳ mỗi lần suy luận |
| Khung kết quả | `0x5A` · SEQ · STATUS · CLASS · SCORE · CRC-16; ở chế độ kiểm thử thêm 4 logit, số chu kỳ, CRC |
| RST_N | MCU reset FPGA sau 3 lỗi liên tiếp |

### 2.3 Firmware (SN32F407)

- Đọc MPU6050 theo ngắt data-ready 100 Hz; hiệu chuẩn offset con quay lúc khởi động.
- Bộ lọc giảm mẫu `(r₀ + 3r₁ + 3r₂ + r₃ + 4) >> 3`, lượng tử INT8 có làm tròn và bão hòa.
- Khung SPI kèm CRC-16 tính bằng khối CRC phần cứng.
- Tự kiểm khi bật nguồn: gửi một khung thử cố định, so khung FPGA trả về với đáp án tính sẵn.
- Watchdog; một nút cho bật/tắt, CANCEL, SOS; LED 7 đoạn, còi, LED; log qua UART.
- Các chế độ RUN / LOG / TRC / HIL / DIAG cho thu dữ liệu và kiểm thử.

### 2.4 Safety FSM

| Trạng thái | Điều kiện vào | Hành động |
|---|---|---|
| STANDBY | Hệ thống TẮT (nhấn nhanh 2 lần khi đang theo dõi) quá 3 s | Không xét cảnh báo; giữ nút 2 s để BẬT |
| MONITOR | Hệ thống BẬT | Hiển thị trạng thái |
| SUSPECT | ≥ 2 trong 3 cửa sổ gần nhất là FALL với SCORE ≥ T_SCORE (= 8) | Theo dõi bất động |
| PRE-ALARM | Bất động 2,56 s **và** đầu nằm ngang (lệch 45°–135° so với phương thẳng đứng) trong vòng 8 s kể từ SUSPECT | Còi ngắt quãng, đếm ngược 10 s; nhấn nút → hủy |
| ALARM | Hết đếm ngược, hoặc giữ nút 3 s (SOS) | Còi liên tục; giữ nút 1 s để tắt |

Va đập mũ (va, rơi, gõ) không phải một lớp của mạng. FSM loại chúng bằng trình tự ba pha: phải có cả **bất động**, **đầu nằm ngang**, và **10 s không ai hủy**.

---

## 3. Phương pháp kiểm chứng

Không có board trong phần lớn thời gian phát triển, nên nhóm xây một chuỗi kiểm chứng nhiều tầng. Tầng sau chỉ được tin khi tầng trước đã khớp từng bit:

| Tầng | Cách kiểm | Kết quả |
|---|---|---|
| Đặc tả ↔ mô hình tham chiếu | `tools/verify_spec_v3.py` | TẤT CẢ PASS |
| Huấn luyện ↔ mô hình tham chiếu | Mô hình INT8 sau huấn luyện so với `golden_model.forward` | 1000/1000 cửa sổ trùng lớp, SCORE và 4 logit |
| RTL engine | `tb_e2`: so **từng tầng** (Conv1, Conv2, Conv3, logit) với mô hình tham chiếu | 50/50 cửa sổ, 14 cấu hình mô hình × số làn |
| RTL giao thức | `tb_proto`: khung qua chân SPI và 7 kịch bản lỗi (CRC sai, thiếu byte, hai khung sát nhau, sai header, đọc khi chưa có kết quả, RST_N…) | PASS |
| **Netlist sau Place & Route** | Mô phỏng netlist mà Gowin xuất cho chính file bitstream sẽ nạp; phép âm: lật 1 bit một trọng số thì phải FAIL | PASS; phép âm FAIL đúng |
| Firmware | Mã máy Cortex-M0 do trình biên dịch Arm sinh, chạy trong trình giả lập Unicorn, so với mô hình tham chiếu Python | 63/63 ca: tiền xử lý, khung, FSM, nút bấm, hiệu chuẩn gyro |
| **Ghép firmware ↔ RTL** | Đúng các byte firmware gửi đi qua chân SPI vào RTL; đúng khung RTL trả về được firmware đọc và đưa vào FSM; 6 bản ghi ngã thật | 423/423 khung khớp; chuỗi trạng thái FSM trùng mô hình tham chiếu |
| Trên chip | HIL: PC → MCU → FPGA → PC, so với mô hình tham chiếu | **[CHỜ ĐO]**, cần ≥ 2.000 cửa sổ |

**Lỗi mô phỏng netlist tìm ra.** Trong RTL của phiên bản đầu, thanh ghi phát xung khởi động engine (`conv_start`) không có giá trị khởi tạo. Gowin tự chọn giá trị khởi tạo bằng 1, nên vừa nạp cấu hình, engine đã tự chạy và **khung đầu tiên sau mỗi lần bật nguồn cho kết quả sai**. Khung đó lại chính là khung tự kiểm. Mô phỏng RTL không thấy lỗi này, vì ở đó giá trị chưa khởi tạo là X và được coi là 0. Nhóm đã sửa bằng cách khởi tạo 0 mọi thanh ghi điều khiển, và thêm bước liệt kê mọi FF khởi tạo bằng 1 vào quy trình dựng bitstream.

---

## 4. Dữ liệu và huấn luyện

- **Huấn luyện:** bộ công khai của Özdemir và Barshan (UCI #455, cảm biến ở **đầu**). Nhóm đã chuyển đổi 11/17 người (101–110, 203): 1.180 cú ngã thuộc 20 kiểu và 16 hoạt động thường ngày, tổng 109.970 cửa sổ.
- **Chuyển đổi:** lấy kênh đầu, xoay trục về quy ước của mũ, nội suy 25 → 50 Hz, đổi về thang INT8 của thiết bị.
- **Gán nhãn:** cửa sổ là FALL khi điểm va chạm nằm ở mẫu 56–103 (mỗi cú ngã có đúng 3 cửa sổ); cửa sổ có va chạm sát biên thì bị loại.
- **Huấn luyện:** numpy, Adam, lịch lr cosine, tăng cường dữ liệu (lật trái–phải, co giãn biên độ ±10 %, nhiễu ±1 mức). Sau đó lượng tử sau huấn luyện, dùng phép dịch lũy thừa 2.
- **Đánh giá:** tách theo người (leave-one-subject-out), 3 lần huấn luyện với 3 seed. Mô hình đưa lên chip dùng seed chuẩn 20261014, chọn trước khi xem kết quả.
- **Dữ liệu đội mũ do nhóm tự thu chỉ để kiểm tra**, không dùng để huấn luyện: buổi thử ≥ 2 giờ đội mũ, ngã trên đệm, va mũ, rơi mũ. **[CHỜ ĐO]**

Hai kết quả phụ:
- Thêm dữ liệu cảm biến ở ngực và thắt lưng có lợi khi mới có 6 người, nhưng hết lợi khi có 8 người (Macro-F1 0,970 so với 0,977; phiếu nhầm gấp đôi). Vì vậy chỉ dùng kênh đầu.
- Trung bình trượt trọng số (EMA) không giảm được độ dao động giữa các seed.

---

## 5. Kết quả theo chỉ tiêu cam kết

| Chỉ tiêu (đề cương v2.1) | Mục tiêu | Đã đo (mô phỏng / dữ liệu công khai) | Trên chip / trên mũ | Bằng chứng |
|---|---|---|---|---|
| Hoạt động độc lập; tự kiểm khi bật nguồn | Không cần PC | Tự kiểm có đáp án tính sẵn từ mô hình tham chiếu, cho đúng trọng số trong bitstream | **[CHỜ ĐO]** | `2026-10-16_n2_11_nguoi` |
| Độ nhạy FALL mức sự kiện / Macro-F1 hai lớp | ≥ 95 % / ≥ 0,90 | **99,6 % / 0,983** (TB 3 seed, 11 người) | không áp dụng | `2026-10-16_n2_11_nguoi` |
| Thử trực tiếp trên mũ | ≥ 18/20 cú ngã vào PRE-ALARM | Phát lại 769 cú ngã kết thúc nằm của bộ công khai: 96,2 % | **[CHỜ ĐO]** | như trên |
| Báo giả sau Safety FSM | ≤ 1 lần/giờ | Phát lại 5,43 giờ sinh hoạt: **1,11/giờ** (0,92 / 0,74 / 1,66), toàn bộ từ "chủ động nằm xuống giường"; gộp 3 mô hình 0,74/giờ | **[CHỜ ĐO]**, đội mũ ≥ 2 giờ | như trên |
| Loại trừ va mũ khi đang đội | ≥ 18/20 không gây PRE-ALARM | Bộ công khai không có va mũ; FSM yêu cầu bất động + đầu nằm ngang | **[CHỜ ĐO]** | |
| Rơi mũ khi hệ thống bật | Đếm; mọi lần hủy được | | **[CHỜ ĐO]** | |
| Độ trễ: va chạm → SUSPECT | ≤ 1,5 s | Trung vị 0,84–0,88 s | **[CHỜ ĐO]** | `2026-10-16_n2_11_nguoi` |
| Độ trễ: → PRE-ALARM khi nằm yên trong 2 s | ≤ 5 s | 514 cú ngã thỏa điều kiện: trung vị 3,80 s, p90 4,32 s, lớn nhất 4,56 s, 0 cú > 5 s | **[CHỜ ĐO]** | như trên |
| Thời gian suy luận trên FPGA | ≤ 6 ms; nhanh hơn MCU ≥ 5 lần | **5,15 ms** (258.080 chu kỳ, bộ đếm trong RTL); MCU ước tính 74–232 ms (đếm lệnh trên trình giả lập) | **[CHỜ ĐO]**: bộ đếm chu kỳ qua HIL; MCU đo bằng GPIO | `2026-10-14_rb03_rb04_e2`, `2026-10-14_fw15_mcu_only` |
| Khớp phần cứng – phần mềm | 0 sai lệch trên ≥ 2.000 cửa sổ; FP32 → INT8 giảm ≤ 2 điểm | RTL và netlist khớp từng bit; FP32 → INT8 giảm ≤ 0,0001 Macro-F1 | **[CHỜ ĐO]**, HIL ≥ 2.000 cửa sổ | `2026-10-16_n2_11_nguoi` mục 5 |
| Tài nguyên và timing | Logic ≤ 20 %, BSRAM ≤ 25 %, DSP ≤ 25 %; Fmax ≥ 55 MHz | Logic 1.473/20.736 (8 %), thanh ghi 1.084/16.173 (7 %), BSRAM 8/46 (18 %), DSP 2,25/24 (10 %), **Fmax 98,12 MHz** | không áp dụng | `bitstreams/3_v3_e2_n2` |
| Công suất | Ước lượng + dòng đo | Ước lượng của Gowin EDA: 157,6 mW (động 34,8 mW) | **[CHỜ ĐO]**, dòng ở nguồn 5 V của từng board | như trên |

**Nhận xét trung thực:**
1. Trên dữ liệu công khai, báo giả **vượt nhẹ** chỉ tiêu (1,11 so với ≤ 1/giờ). Mọi lần báo giả đều đến từ một hoạt động: chủ động nằm xuống giường, tức nằm hẳn xuống, đầu ngang, rồi bất động. Người đội mũ bảo hộ hiếm khi làm vậy. Nhóm sẽ báo con số đo được trên mũ.
   - Nhóm đã thử thêm "cổng va chạm" (đỉnh |a| ≥ 2,5 g trước SUSPECT). Cổng này loại được phần lớn các lần báo giả, nhưng làm mất khoảng 4 % cú ngã, nên chưa đưa vào.
2. Bộ công khai lấy mẫu 25 Hz và cảm biến được buộc vào đầu, không gắn trên vỏ mũ, nên kết quả trên mũ có thể khác. Buổi thử đội mũ là phép đo quyết định.
3. Ngã kết thúc **ngồi hoặc quỳ** không được tự báo động (3 % trên bộ công khai), vì hệ thống chỉ báo khi người nằm. Người ngã ngồi mà còn tỉnh thì giữ nút 3 s để gọi SOS. Nhóm đã thử thêm nhánh "bất động dù đầu thẳng", nhưng nhánh này báo nhầm 3–69 % cú ngã đã đứng dậy, nên không dùng.

---

## 6. Hạn chế và hướng phát triển

- Kết quả trên chip và trên mũ đang chờ đo; xem các ô **[CHỜ ĐO]**.
- Mục tiêu mở rộng, không cam kết:
  - bộ tính 4 làn, đã có trong mô phỏng: 75.284 chu kỳ = 1,50 ms;
  - Fmax ≥ 100 MHz;
  - lớp IMPACT / suýt ngã, nếu buổi thử có quá 2/20 lần va mũ vào PRE-ALARM;
  - cập nhật trọng số qua SPI;
  - ghi sự kiện vào Flash;
  - truyền cảnh báo về trạm giám sát qua BLE hoặc LoRa.

---

## Phụ lục — Tái lập

Repo của đội có hướng dẫn đầy đủ:
- `README.md`: lệnh kiểm không cần board;
- `docs/huong_dan_dot_B.md`: B1–B10 trên board;
- `docs/data_protocol.md`: buổi thử đội mũ;
- `tools/playback_log.py`: chấm buổi thử.

Bitstream dựng sẵn ở `bitstreams/`, có SHA256.
