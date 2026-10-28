# THIẾT BỊ ĐEO NGỰC PHÁT HIỆN TÉ NGÃ — BÁO CÁO KỸ THUẬT (BẢN NHÁP)

**Đội VKU-NewBie** · Cuộc thi thiết kế FPGA và MCU mở rộng khu vực miền Trung 2026 · Bản nháp cập nhật ngày 28/10/2026

> **Tình trạng bản nháp.** Hệ thống bản cuối đã chạy thông trên board bằng pin, đeo ở ngực. Mỗi con số ghi rõ nguồn:
> - mô phỏng;
> - báo cáo Place & Route của Gowin EDA;
> - phát lại bộ dữ liệu công khai;
> - log đeo ngực do nhóm tự thu, chạy lại nguyên lõi phần mềm ESP32 trên PC.
>
> Mục nào cần buổi thử có số đo (đeo dài, HIL trên chip) được đánh dấu **[CHỜ ĐO]**. Bằng chứng nằm ở thư mục `docs/bao_cao/` của repo.

---

## 1. Tóm tắt

Hệ thống là một thiết bị đeo ở ngực, chạy pin:
- MPU6050 trên dây đeo ngực đo 6 trục ở 100 Hz.
- Vi điều khiển SONiX SN32F407 đọc cảm biến và gửi từng mẫu qua UART cho ESP32.
- ESP32 đổi trục cảm biến về trục người, lọc và lượng tử, cứ 0,32 s gửi một cửa sổ 2,56 s sang FPGA qua SPI.
- FPGA Gowin GW2A-18 (Kiwi Primer 20K) chạy mạng 1D-CNN INT8 bằng **RTL tự viết**, không dùng IP AI đóng gói.
- Trên ESP32:
  - Safety FSM bỏ phiếu 2/3 cửa sổ FALL để **nghi** ngã;
  - tầng xác nhận kiểm thêm 4 dấu hiệu vật lý; đủ thì báo **PHÁT HIỆN NGÃ** (còi + trang web);
  - nếu người nằm bất động, đếm ngược 10 s rồi báo động.

Kết quả chính:

| | Kết quả |
|---|---|
| Mạng N2 (3 lớp Conv + Dense, INT8), tách theo người trên 11 người của bộ công khai (cảm biến ở đầu) | Macro-F1 **0,983**; nhận ra **99,6 %** cú ngã |
| Log đeo ngực của nhóm, sau tầng xác nhận ngã thật | Ngồi phịch xuống ghế: báo nhầm **0/10**; cả log động tác dễ nhầm: báo nhầm **0**; ngã lên nệm: **14/15**; tư thế: **9/9** |
| Thời gian suy luận trên FPGA | **5,15 ms** (258.080 chu kỳ ở 50,143 MHz, mô phỏng) |
| Khớp phần cứng – phần mềm | RTL và netlist sau Place & Route khớp mô hình tham chiếu **từng bit**; phần mềm ESP32 chạy dạng mã máy trên trình giả lập khớp mô hình tham chiếu |
| Tài nguyên | Logic 8 %, BSRAM 18 %, DSP 10 %, Fmax 111,01 MHz |
| Trên board | Chạy pin; tự kiểm FPGA PASS khi khởi động; mẫu đều, mất 0; FPGA trả OK mọi khung |

---

## 2. Kiến trúc hệ thống

```
  DÂY ĐEO NGỰC           SN32F407 (Cortex-M0)          ESP32                                   KIWI PRIMER 20K (GW2A-18)
 ┌──────────────┐ I²C  ┌───────────────────┐ UART  ┌──────────────────────────────────┐ SPI  ┌─────────────────────────────┐
 │ MPU6050      │─────►│ Đọc 100 Hz        │──────►│ Tách khung, chèn bù mẫu mất      │ 772 B│ SPI Slave + Parser + CRC-16 │
 │ ±16 g        │      │ Hiệu chuẩn gyro   │115200 │ Đổi trục ngực → trục người       │─────►│ Bộ đệm cửa sổ (BSRAM)       │
 │ ±2000 °/s    │      │ Gỡ bus I²C        │21 B/  │ Lọc ↓2 → 50 Hz, INT8, ring 128×6 │0,32 s│ 1D-CNN INT8 (RTL tự viết)   │
 └──────────────┘      │ Khung mẫu CRC-16  │ mẫu   │ Bỏ phiếu 2/3 → Safety FSM        │◄─────│ Conv → Pool → … → Dense     │
 ┌──────────────┐      │                   │◄──────│ Xác nhận ngã thật, tư thế        │ 7 B  │ Argmax + Score              │
 │ Nút SW3      │─────►│ Còi PZ1 2 kHz     │ lệnh  │ Trang web, log WiFi TCP 3333     │hỏi   └─────────────────────────────┘
 └──────────────┘      └───────────────────┘ còi   └──────────────────────────────────┘vòng
```

Dây nối của nhóm cố định: MCU chỉ có đường UART TX sang ESP32 (cùng một dây lệnh còi theo chiều ngược lại), còn ESP32 làm master SPI tới FPGA. Vì vậy MCU chỉ làm nút cảm biến, ESP32 chạy toàn bộ phần xử lý của firmware (cùng lõi C với `firmware/src/`).

**Đặc tả chung (SPEC v3.4, Phụ lục A của `PROJECT_MASTER.md`)** là một tài liệu duy nhất mà RTL, firmware và phần mềm Python cùng tuân theo. Nó quy định:
- thang đo, vị trí đeo và đổi trục;
- bộ lọc và lượng tử;
- cửa sổ và gán nhãn;
- số học INT8;
- khung SPI;
- Safety FSM, tư thế, xác nhận ngã thật.

**Mô hình tham chiếu số nguyên** (`ml/src/golden_model.py`) là đáp án. Mọi tầng (RTL, netlist, firmware, công cụ PC) đều được kiểm là khớp nó từng bit.

### 2.1 Mô hình 1D-CNN (N2)

Cấu trúc:
- đầu vào 128 × 6 INT8;
- Conv1D 6→16 (k = 5) + ReLU + MaxPool 2;
- Conv1D 16→16 + ReLU + MaxPool 2;
- Conv1D 16→32 + ReLU + MaxPool 2;
- Flatten (16 × 32) → Dense 512→4 → Argmax.

Mạng có 6.368 trọng số, 68 bias, 227.328 MAC mỗi cửa sổ. Trọng số và đầu vào là INT8, bộ cộng dồn INT32. Sau mỗi lớp, kết quả được tái lượng tử bằng dịch phải và kẹp về 0…127.

Đầu ra có 4 logit. Hệ thống dùng 2 lớp NORMAL và FALL; 2 lớp còn lại để dành cho mở rộng (IMPACT, suýt ngã). Điểm tin cậy SCORE = (logit thắng − logit nhì) dịch phải, bão hòa 0…127.

Mạng N2 được chọn sau khi so trên 8 người. Mạng 2 lớp Conv + Global Average Pooling của phiên bản đầu (N1) chỉ đạt Macro-F1 0,842 và nhận ra 87,0 % cú ngã, không đạt chỉ tiêu.

### 2.2 FPGA

| Khối | Mô tả |
|---|---|
| SPI Slave | Đồng bộ SCK, CS, MOSI vào miền 50,143 MHz bằng chuỗi flip-flop; SPI mode 0, master là ESP32 |
| Parser khung v3 | `0xA5` · SEQ · 768 byte · CRC-16/CCITT. Kiểm CRC, kiểm độ dài, báo trạng thái lỗi trong khung trả về |
| Engine E2 | Một chu kỳ mỗi MAC; ROM trọng số và bias khởi tạo từ `.mem`; hai RAM đặc trưng dùng luân phiên; dữ liệu xếp theo thời gian nên bộ sinh địa chỉ chỉ cần bộ đếm. Có bộ đếm chu kỳ mỗi lần suy luận |
| Khung kết quả | `0x5A` · SEQ · STATUS · CLASS · SCORE · CRC-16. "Có kết quả" chốt lúc CS xuống; đọc sớm trả toàn 0, nên ESP32 hỏi vòng (không dùng IRQ, RST_N) |

### 2.3 Firmware

**MCU SN32F407** (`firmware/keil/fw.uvprojx`, `FW_NODE 1`):
- đọc MPU6050 100 Hz, hiệu chuẩn offset con quay lúc khởi động;
- quá 200 ms không có mẫu mới thì gỡ bus I²C và cấu hình lại cảm biến mỗi giây;
- gửi mỗi mẫu một khung `F1 7E` 21 byte có CRC-16 qua UART 115200;
- nhận lệnh còi từ ESP32 và tạo âm 2 kHz trên PZ1 bằng ngắt timer;
- watchdog.

**ESP32** (`esp32/mu_nga_hub`):
- **Tách khung chịu nhiễu:** chỉ nhận khung đúng độ dài; khung hỏng thì dò lại đầu khung ngay trong các byte của nó, nên mỗi lần nhiễu chỉ mất 1 mẫu. Mẫu mất (khoảng hở ≤ 50 mẫu) được chèn bù bằng mẫu gần nhất.
- **Đổi trục và trừ offset:** đổi trục cảm biến → trục người khi đeo ngực (X trước, Y trái, Z lên), rồi trừ offset gia tốc đo khi đeo.
- **Tiền xử lý và khung SPI:** bộ lọc giảm mẫu `(r₀ + 3r₁ + 3r₂ + r₃ + 4) >> 3`, lượng tử INT8 có làm tròn và bão hòa, khung SPI v3 kèm CRC-16.
- **Tự kiểm khi bật nguồn:** gửi một khung thử cố định, so khung FPGA trả về với đáp án tính sẵn.
- **Ra quyết định:** bỏ phiếu + Safety FSM, xác nhận ngã thật, nhận dạng tư thế.
- **Báo cho người dùng:** MẤT CẢM BIẾN; trang web (trạng thái, tư thế, biểu đồ, thống kê, nút hủy); log USB và WiFi TCP 3333.

### 2.4 Safety FSM và xác nhận ngã thật

| Trạng thái (trên web) | Điều kiện vào | Hành động |
|---|---|---|
| TẮT (STANDBY) | Nhấn nhanh 2 lần khi đang theo dõi, quá 3 s | Không xét cảnh báo; giữ nút 2 s (hoặc "Bật lại hệ thống" trên web) để BẬT |
| ĐANG THEO DÕI (MONITOR) | Hệ thống BẬT | Hiển thị trạng thái, tư thế |
| PHÁT HIỆN NGÃ (SUSPECT) | ≥ 2 trong 3 cửa sổ gần nhất là FALL **và** tầng xác nhận thấy đủ 4 dấu hiệu | Còi bíp 0,4 s mỗi giây; tự về theo dõi sau 8 s nếu người cử động |
| CẢNH BÁO (PRE-ALARM) | Bất động 2,56 s **và** ngực nằm ngang (lệch 45°–135° so với phương thẳng đứng) | Còi 2 bíp mỗi giây, đếm ngược 10 s; nhấn nút → hủy |
| BÁO ĐỘNG (ALARM) | Hết đếm ngược, hoặc giữ nút 3 s (SOS) | Còi hú; giữ nút 1 s để tắt, rồi tạm nghỉ 30 s |
| MẤT CẢM BIẾN | Quá 3 s không có mẫu | Web đỏ, còi 2 bíp mỗi 3 s |

**Xác nhận ngã thật** (`firmware/src/nga.c`, SPEC A.12). Bỏ phiếu CNN chỉ cho biết *nghi* ngã. Một lần nghi chỉ được báo khi có đủ cả bốn dấu hiệu:
1. trong 3,2–10,2 s trước đó, ngực đã ở tư thế **thẳng**;
2. **va chạm** ≥ 2,5 g;
3. ngực **quay nhanh** ≥ 220 °/s trong ±1,6 s quanh va chạm;
4. ngực **nghiêng** ≥ 45° trong 3,84 s sau va chạm.

Thiếu một dấu hiệu thì lần nghi bị bỏ: FSM về theo dõi, còi im, người dùng không thấy gì.

---

## 3. Phương pháp kiểm chứng

Không có board trong phần lớn thời gian phát triển, nên nhóm xây một chuỗi kiểm chứng nhiều tầng. Tầng sau chỉ được tin khi tầng trước đã khớp từng bit:

| Tầng | Cách kiểm | Kết quả |
|---|---|---|
| Đặc tả ↔ mô hình tham chiếu | `tools/verify_spec_v3.py` | TẤT CẢ PASS |
| Huấn luyện ↔ mô hình tham chiếu | Mô hình INT8 sau huấn luyện so với `golden_model.forward` | 1000/1000 cửa sổ trùng lớp, SCORE và 4 logit |
| RTL engine | `tb_e2`: so **từng tầng** (Conv1, Conv2, Conv3, logit) với mô hình tham chiếu | 50/50 cửa sổ, 14 cấu hình mô hình × số làn |
| RTL giao thức | `tb_proto`: khung qua chân SPI và 7 kịch bản lỗi (CRC sai, thiếu byte, hai khung sát nhau, sai header, đọc khi chưa có kết quả…) | PASS |
| **Netlist sau Place & Route** | Mô phỏng netlist mà Gowin xuất cho chính file bitstream sẽ nạp; phép âm: lật 1 bit một trọng số thì phải FAIL | PASS; phép âm FAIL đúng |
| Firmware MCU và ESP32 | Mã máy Cortex-M0 do trình biên dịch Arm sinh từ cùng lõi C, chạy trong trình giả lập Unicorn, so với mô hình tham chiếu Python | TẤT CẢ PASS. Gồm: 70 ca (tiền xử lý, khung, FSM, nút, còi, xác nhận ngã); khung UART MCU → ESP32 khớp từng byte, kể cả khi có nhiễu; ESP32 `hub.c` khớp mô hình tham chiếu + `safety_model` trên 402 khung; tư thế khớp `posture_model` từng mẫu |
| **Ghép firmware ↔ RTL** | Đúng các byte firmware gửi đi qua chân SPI vào RTL; đúng khung RTL trả về được firmware đọc và đưa vào FSM; 6 bản ghi ngã thật | 423/423 khung khớp; chuỗi trạng thái FSM trùng mô hình tham chiếu |
| Lõi ESP32 trên log thật | `tools/nga_tren_log.py`: chạy nguyên lõi ESP32 (CNN tham chiếu thay FPGA) trên log đeo ngực | Mục 5 |
| Trên chip | HIL: PC → FPGA → PC, so với mô hình tham chiếu | **[CHỜ ĐO]**, cần ≥ 2.000 cửa sổ |

**Lỗi mô phỏng netlist tìm ra.**
- *Lỗi:* trong RTL của phiên bản đầu, thanh ghi phát xung khởi động engine (`conv_start`) không có giá trị khởi tạo. Gowin tự chọn giá trị khởi tạo bằng 1, nên vừa nạp cấu hình, engine đã tự chạy.
- *Hậu quả:* **khung đầu tiên sau mỗi lần bật nguồn cho kết quả sai**, mà khung đó lại chính là khung tự kiểm.
- *Vì sao mô phỏng RTL không thấy:* ở đó giá trị chưa khởi tạo là X và được coi là 0.
- *Cách sửa:* khởi tạo 0 mọi thanh ghi điều khiển, và thêm bước liệt kê mọi FF khởi tạo bằng 1 vào quy trình dựng bitstream.

---

## 4. Dữ liệu và huấn luyện

- **Huấn luyện CNN:** bộ công khai của Özdemir và Barshan (UCI #455, cảm biến ở **đầu**). Nhóm đã chuyển đổi 11/17 người (101–110, 203): 1.180 cú ngã thuộc 20 kiểu và 16 hoạt động thường ngày, tổng 109.970 cửa sổ.
- **Chuyển đổi:** lấy kênh đầu, xoay trục về quy ước X trước, Y trái, Z lên; nội suy 25 → 50 Hz; đổi về thang INT8 của thiết bị.
- **Gán nhãn:** cửa sổ là FALL khi điểm va chạm nằm ở mẫu 56–103 (mỗi cú ngã có đúng 3 cửa sổ); cửa sổ có va chạm sát biên thì bị loại.
- **Huấn luyện:** numpy, Adam, lịch lr cosine, tăng cường dữ liệu (lật trái–phải, co giãn biên độ ±10 %, nhiễu ±1 mức). Sau đó lượng tử sau huấn luyện, dùng phép dịch lũy thừa 2.
- **Đánh giá:** tách theo người (leave-one-subject-out), 3 lần huấn luyện với 3 seed. Mô hình đưa lên chip dùng seed chuẩn 20261014, chọn trước khi xem kết quả.
- **Log đeo ngực do nhóm tự thu (28/10), không dùng để huấn luyện CNN:** 9 tư thế giữ yên; động tác dễ nhầm (ngồi phịch xuống ghế ×10, cúi nhặt đồ ×5, đi lại 30 s, nằm xuống giường ×5, ngồi dậy ×5, lăn người khi nằm ×10); ngã lên nệm dày có người đỡ (ngã rồi nằm ×10, ngã nhẹ rồi ngồi dậy ×5). Dùng để đo hướng cảm biến, kiểm tư thế và chọn ngưỡng tầng xác nhận ngã.

Hai kết quả phụ:
- Thêm dữ liệu cảm biến ở ngực và thắt lưng của bộ công khai có lợi khi mới có 6 người, nhưng hết lợi khi có 8 người (Macro-F1 0,970 so với 0,977; phiếu nhầm gấp đôi). Vì vậy CNN chỉ học kênh đầu.
- Trung bình trượt trọng số (EMA) không giảm được độ dao động giữa các seed.

---

## 5. Kết quả

### 5.1 Khi đeo ngực (log của nhóm, chạy lại nguyên lõi ESP32)

**Vì sao cần tầng xác nhận.** Khi đeo ngực, ngồi phịch xuống ghế tạo va chạm 4,3–6,2 g, mạnh hơn cả ngã lên nệm (2,6–5,3 g). Va chạm một mình không phân biệt được hai trường hợp này. Hai đại lượng tách được chúng:

| Động tác | Đỉnh \|a\| | Nghiêng tối đa sau va chạm | Đỉnh \|ω\| |
|---|---|---|---|
| Ngồi phịch xuống ghế ×10 | 4,30–6,17 g | 18–31° | 85–149 °/s |
| Ngã lên nệm rồi nằm ×10 | 2,58–5,29 g | 58–80° | 281–467 °/s |
| Ngã nhẹ rồi ngồi dậy ×4 | 3,33–3,77 g | 68–78° | 258–385 °/s |
| Nằm xuống giường ×5 | 1,03–2,74 g | 85–96° | 12–192 °/s |
| Cúi nhặt đồ ×5 | 1,51–1,68 g | 66–72° | 175–210 °/s |

**Kết quả:**

| Log | CNN nghi | Báo ngã cho người dùng |
|---|---|---|
| Động tác dễ nhầm (không có cú ngã) | 22 lần (ngồi mạnh 19, lăn 3) | **0** |
| Ngã lên nệm, 15 cú | 14 cú | **14/15**; cú sót là ngã nhẹ 1,74 g mà CNN cũng không nghi |
| 9 tư thế giữ yên | 2 lần | **0**; tư thế nhận đúng **9/9** |

Bằng chứng: `2026-10-28_nga_that`, `2026-10-28_tu_the_nguc`.

### 5.2 Theo chỉ tiêu cam kết

| Chỉ tiêu | Mục tiêu | Đã đo | Bằng chứng |
|---|---|---|---|
| Hoạt động độc lập; tự kiểm khi bật nguồn | Không cần PC | **Có:** chạy pin, tự kiểm FPGA PASS mỗi lần khởi động, mẫu đều, mất 0 | `2026-10-28_chot_ket_qua` |
| Độ nhạy FALL mức sự kiện / Macro-F1 hai lớp (CNN) | ≥ 95 % / ≥ 0,90 | **99,6 % / 0,983** (TB 3 seed, 11 người, bộ công khai, kênh đầu) | `2026-10-16_n2_11_nguoi` |
| Ngã được báo khi đeo ngực | ≥ 18/20 | Log nhóm: 14/15 (một người, một buổi). **[CHỜ ĐO]** buổi ≥ 20 cú ngã từ ≥ 2 người | `2026-10-28_nga_that` |
| Không báo nhầm động tác thường | ≤ 1 lần/giờ | Log nhóm: 0 lần trên ≈ 7 phút động tác dễ nhầm. **[CHỜ ĐO]** đeo ≥ 2 giờ | `2026-10-28_nga_that` |
| Độ trễ: va chạm → SUSPECT | ≤ 1,5 s | Bộ công khai: trung vị 0,84–0,88 s. **[CHỜ ĐO]** khi đeo ngực | `2026-10-16_n2_11_nguoi` |
| Độ trễ: → PRE-ALARM khi nằm yên trong 2 s | ≤ 5 s | Bộ công khai: 514 cú ngã thỏa điều kiện, trung vị 3,80 s, p90 4,32 s, 0 cú > 5 s | như trên |
| Thời gian suy luận trên FPGA | ≤ 6 ms; nhanh hơn MCU ≥ 5 lần | **5,15 ms** (258.080 chu kỳ, bộ đếm trong RTL, mô phỏng); MCU ước tính 74–232 ms (đếm lệnh trên trình giả lập) | `2026-10-14_rb03_rb04_e2`, `2026-10-14_fw15_mcu_only` |
| Khớp phần cứng – phần mềm | 0 sai lệch trên ≥ 2.000 cửa sổ; FP32 → INT8 giảm ≤ 2 điểm | RTL và netlist khớp từng bit; FP32 → INT8 giảm ≤ 0,0001 Macro-F1. **[CHỜ ĐO]** HIL ≥ 2.000 cửa sổ | `2026-10-16_n2_11_nguoi` |
| Tài nguyên và timing | Logic ≤ 20 %, BSRAM ≤ 25 %, DSP ≤ 25 %; Fmax ≥ 55 MHz | Logic 1.473/20.736 (8 %), thanh ghi 1.084/16.173 (7 %), BSRAM 8/46 (18 %), DSP 2,25/24 (10 %), **Fmax 111,01 MHz** | `fpga/bitstream/fpga_project.rpt.txt` |
| Công suất | Ước lượng + dòng đo | Ước lượng của Gowin EDA ≈ 157 mW [CẦN XÁC MINH – nguồn: báo cáo Power cho bitstream hiện tại]. **[CHỜ ĐO]** dòng thật | |

**Nhận xét trung thực:**
1. **Ngưỡng tầng xác nhận** (220 °/s, 45°) được chọn trên chính log dùng để chấm, một người, một buổi. Con số 0/10 và 14/15 vì vậy lạc quan hơn thực tế. Cần một buổi đeo với người khác để kiểm.
2. **CNN học từ cảm biến ở đầu**, chưa huấn luyện lại cho ngực. Trên log ngực, CNN nghi cả 19 lần ngồi mạnh; tầng xác nhận là phần loại các lần nghi này.
3. **Không báo theo thiết kế:**
   - ngã kết thúc **ngồi hoặc quỳ** mà thân vẫn thẳng. Với cảm biến ở ngực, kiểu ngã này giống hệt ngồi phịch xuống ghế. Trên bộ công khai (người 102), 15 bản ghi kiểu này đều không báo;
   - ngã va chạm < 2,5 g.

   Người ngã còn tỉnh thì giữ nút 3 s để gọi SOS.
4. **Nằm xuống giường mạnh** (2,74 g, nghiêng 94°) chỉ bị loại nhờ dấu hiệu quay: đo được 192 °/s, ngưỡng là 220 °/s, khoảng cách nhỏ.
5. **MPU6050 đôi lúc treo:** chip không trả lời I²C, bus vẫn rảnh, cấu hình lại không có tác dụng, chỉ cắt nguồn mới hết. Hệ thống không im lặng: quá 3 s không có mẫu thì báo MẤT CẢM BIẾN (web đỏ, còi). Nhóm nghi do sụt áp 3,3 V khi ESP32 phát WiFi [CẦN XÁC MINH – nguồn: dao động ký]. Hiện người dùng rút pin khoảng 5 s để gỡ.

---

## 6. Hạn chế và hướng phát triển

- Chưa có buổi đeo dài (≥ 2 giờ) và ≥ 20 cú ngã từ ≥ 2 người; chưa có HIL ≥ 2.000 cửa sổ trên chip. Xem các ô **[CHỜ ĐO]**.
- Huấn luyện CNN bằng dữ liệu ngực; đưa quy tắc xác nhận ngã vào mô hình tham chiếu Python để kiểm khớp từng bit như các tầng khác.
- Nguồn riêng cho cảm biến, có công tắc để vi điều khiển tắt / bật lại khi cảm biến treo; tụ lọc sát module.
- Mục tiêu mở rộng, không cam kết:
  - bộ tính 4 làn, đã có trong mô phỏng: 75.284 chu kỳ = 1,50 ms;
  - lớp IMPACT / suýt ngã;
  - cập nhật trọng số qua SPI;
  - ghi sự kiện vào Flash;
  - gửi cảnh báo ra ngoài mạng WiFi nội bộ (tin nhắn, ứng dụng).

---

## Phụ lục — Tái lập

Repo của đội có hướng dẫn đầy đủ:
- `README.md`: lệnh kiểm không cần board, thu và chấm log đeo ngực;
- `docs/huong_dan_nap_chay.md`: nạp ba board và chạy;
- `docs/data_protocol.md`: buổi thử khi đeo ngực;
- `tools/ghi_uart.py --kich-ban …` và `tools/nga_tren_log.py`: thu và chấm log.

Bitstream dựng sẵn ở `fpga/bitstream/`, có SHA256.
