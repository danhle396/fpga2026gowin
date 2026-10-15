# MẪU ĐĂNG KÝ ĐỀ TÀI VÒNG CHUNG KẾT
## CUỘC THI THIẾT KẾ FPGA VÀ MCU MỞ RỘNG KHU VỰC MIỀN TRUNG 2026

*Bản cập nhật (v2), ngày 12/10/2026 — thay cho bản đã nộp. Các điểm thay đổi được liệt kê trong tài liệu kèm theo "Thay đổi so với bản v1".*

---

## I. THÔNG TIN CHUNG

- **Tên đội thi:** VKU - NewBie
- **Trường / Viện:** Trường Đại học Công nghệ thông tin và Truyền thông Việt Hàn
- **Tên đề tài:** Mũ bảo hộ thông minh phát hiện té ngã thời gian thực sử dụng cảm biến IMU và mạng 1D-CNN INT8 tăng tốc trên FPGA–MCU
- **Trưởng nhóm (Họ tên - SĐT - Email):** Nguyễn Bá Thiện – 0766758551 – thiennb.23ce@vku.udn.vn
- **Thành viên & Giảng viên hướng dẫn:**
  - Thầy Dương Ngọc Pháp (Giảng viên hướng dẫn)
  - Nguyễn Bá Thiện
  - Đặng Văn Rin
  - Lê Thành Danh
  - Trần Phan Minh Tiến
  - Bùi Quốc Khánh

---

## II. TỔNG QUAN GIẢI PHÁP & MỤC TIÊU

### 1. Mục tiêu đề tài

**Đặt vấn đề.** Công nhân công trường, nhà máy và người làm việc một mình có nguy cơ té ngã kèm chấn thương đầu mà không có người phát hiện kịp. Mũ bảo hộ là vật bắt buộc phải đội, có vị trí cố định trên cơ thể và ở gần đầu, nên là nơi phù hợp để gắn cảm biến quán tính. Khó khăn riêng của mũ là các va đập không phải ngã: rơi mũ, va mũ vào vật cản, tháo và đội mũ. Một cú ngã gồm ba pha nối tiếp nhau — mất thăng bằng, va chạm, nằm yên [1], [2] — nên muốn phân biệt ngã với một cú va mũ thì phải xét được trình tự trước và sau va chạm, không chỉ riêng xung va chạm.

**Giải pháp.** Nhóm xây dựng một mũ bảo hộ gắn MPU6050. Vi điều khiển SN32F407 đọc cảm biến ở 100 Hz, lọc và giảm mẫu còn 50 Hz, lượng tử hóa về INT8 và giữ cửa sổ 128 mẫu (2,56 s). Cứ 0,32 s, MCU gửi một cửa sổ sang FPGA Gowin qua SPI. Mạng 1D-CNN INT8 do nhóm tự viết bằng RTL phân loại cửa sổ thành NORMAL, IMPACT hoặc FALL và báo cho MCU bằng chân ngắt. MCU kết hợp kết quả của ba cửa sổ liên tiếp với phép đo bất động và độ nghiêng của đầu để quyết định cảnh báo tại chỗ bằng màn hình, còi và LED. Thiết bị chạy độc lập, không cần PC hay Internet.

**Tính mới so với hướng tham khảo.** Đề tài tham khảo hướng mũ bảo hộ thông minh của nhóm EDL_AIOT (Cuộc thi Thiết kế điện tử Việt Nam 2025; mô hình học sâu chạy trên ESP32-S3, hai lớp ngã / không ngã). Các điểm khác của nhóm:

1. Toàn bộ suy luận chạy trên **bộ tăng tốc 1D-CNN INT8 viết bằng RTL**, không dùng IP tăng tốc AI đóng gói sẵn. Kết quả phần cứng được yêu cầu **khớp từng bit** với mô hình tham chiếu số nguyên.
2. **Suy luận dày**: mỗi sự kiện được mạng nhìn ba lần ở ba vị trí khác nhau trong cửa sổ, rồi bỏ phiếu 2 trên 3. Cách làm này tương tự làm mượt kết quả trên cửa sổ trượt trong nhận dạng từ khóa [7].
3. Lớp **IMPACT** dành riêng cho va đập đặc thù của mũ, cùng cảm biến phát hiện mũ đang được đội.
4. Mạng **giữ thứ tự thời gian** đến lớp cuối, để phân biệt được trình tự "đứng → va chạm → nằm" của một cú ngã với "va chạm rồi tiếp tục hoạt động" của một cú va mũ.

**Các lớp nhận diện**

| Lớp | Gồm các hành vi | Vai trò trong Safety FSM |
|---|---|---|
| 0 – NORMAL | Đứng, đi, chạy, ngồi–đứng, cúi nhặt đồ, quay đầu, lên xuống cầu thang, nằm xuống có chủ ý, vấp rồi tự lấy lại thăng bằng | Không cảnh báo |
| 1 – IMPACT | Rơi mũ, va mũ vào vật, gõ vào mũ, đội và tháo mũ, đặt mạnh mũ xuống | Loại trừ; nếu đang đội thì bíp một tiếng và ghi log |
| 3 – FALL | Ngã tới trước, ngã ngửa, ngã nghiêng trái/phải, trượt ngã, ngã khi đang đi | Kích hoạt chuỗi xác nhận |

Chỉ số lớp 2 được để dành cho lớp "suýt ngã" ở mục tiêu mở rộng. Tư thế nằm sau ngã không phải một lớp; Safety FSM suy ra từ độ bất động và độ nghiêng của đầu.

**Phạm vi.** Đây là nguyên mẫu hỗ trợ cảnh báo, không phải thiết bị y tế. Các cú ngã dùng để huấn luyện lấy từ bộ dữ liệu công khai [4] (ngã giả lập của người tình nguyện, cảm biến gắn ở đầu); các cú ngã dùng để thử thiết bị là ngã giả lập trên đệm khi đội mũ. Cả hai có thể khác ngã thật của công nhân.

### 2. Sơ đồ khối hệ thống

```
        MŨ BẢO HỘ                    SN32F407 (Cortex-M0)                      KIWI PRIMER 20K (GW2A-18)
 ┌──────────────────┐   I²C   ┌────────────────────────────┐  SPI 772 byte  ┌──────────────────────────────┐
 │ MPU6050 (6 trục) │────────►│ Đọc 100 Hz theo ngắt       │───────────────►│ SPI Slave + Parser + CRC-16  │
 │ ±16 g, ±2000 °/s │  INT    │ Lọc [1,3,3,1]/8, ↓2 → 50 Hz│  mỗi 0,32 s    │ Bộ đệm cửa sổ (BSRAM)        │
 └──────────────────┘────────►│ Lượng tử INT8, ring 128×6  │                │ 1D-CNN INT8 (RTL tự viết)    │
 ┌──────────────────┐         │                            │◄───────────────│  Conv → Pool → … → Dense     │
 │ Cảm biến đội mũ  │────────►│ Khối bất động + độ nghiêng │  IRQ + 7 byte  │ Argmax + Score               │
 │ Nút CANCEL / SOS │────────►│ Bỏ phiếu 2/3 → Safety FSM  │───────────────►│ Thanh ghi kết quả, IRQ       │
 └──────────────────┘         │ OLED · còi · LED · UART log│     RST_N      └──────────────────────────────┘
                              └────────────────────────────┘
                 PC chỉ dùng khi phát triển: thu dữ liệu, huấn luyện, kiểm thử HIL
```

**Luồng hoạt động.** (1) MPU6050 phát ngắt data-ready ở 100 Hz; MCU đọc 14 byte qua I²C. (2) MCU lọc, giảm mẫu còn 50 Hz, lượng tử hóa INT8 và ghi vào buffer vòng 128 mẫu. (3) Mỗi 16 mẫu mới (0,32 s), MCU gửi khung 772 byte gồm cả cửa sổ và CRC-16. (4) FPGA kiểm CRC, chạy 1D-CNN, lưu lớp và điểm tin cậy, kéo IRQ lên mức cao. (5) MCU đọc khung kết quả 7 byte; IRQ trở về mức thấp. (6) Safety FSM yêu cầu 2 trong 3 cửa sổ gần nhất báo FALL, sau đó chờ người nằm bất động 2,56 s với đầu nghiêng quá 45°, rồi đếm ngược 10 s và báo động; nút CANCEL hủy cảnh báo.

---

## III. CẤU HÌNH PHẦN CỨNG

### 1. Bo mạch chính sử dụng

- [X] Gowin FPGA Board: Kiwi Primer 20K – GW2A-LV18PG256C8/I7 (20.736 LUT4, 15.552 FF, 46 khối BSRAM 18 Kbit, 24 khối DSP, 4 PLL).
- [X] Sonix MCU Board: SN32F407 – Cortex-M0, Flash 32 KB, RAM 8 KB.
- [X] Phối hợp FPGA Gowin + MCU Sonix (Hybrid System).

### 2. Dự toán tài nguyên Gowin FPGA

Nhóm đã viết, mô phỏng và tổng hợp phiên bản RTL đầu tiên (mạng 2 lớp Conv, một làn tính). Bảng dưới ghi số liệu của phiên bản đó, lấy từ báo cáo Place & Route của Gowin EDA V1.9.11.03 ngày 15/10/2026 với các chân I/O đã cố định trên header của board, và mục tiêu cho bản cuối. Bản này đã sửa một lỗi giá trị khởi tạo thanh ghi mà nhóm phát hiện bằng mô phỏng netlist sau Place & Route.

| Hạng mục | Phiên bản đầu (đã tổng hợp) | Mục tiêu bản cuối | Tài nguyên chip |
|---|---|---|---|
| Logic (LUT + ALU) | 907 (5 %) | ≤ 20 % | 20.736 |
| Flip-flop | 589 (4 %) | báo cáo số thực | 15.552 |
| BSRAM | 6 khối (14 %) | ≤ 25 % | 46 khối |
| DSP | 1,25 khối (5 %) | ≤ 25 % | 24 khối |
| Clock hệ thống | 50,143 MHz từ rPLL (dao động 27 MHz) | giữ nguyên | 4 PLL |
| Fmax | 105,20 MHz | ≥ 55 MHz với bộ tính mới; mục tiêu mở rộng ≥ 100 MHz | — |
| I/O | 6 chân | 7 chân: SCK, MOSI, MISO, CS, IRQ, RST_N, clk | 207 |
| Công suất (ước lượng của công cụ) | 156,5 mW, trong đó động 33,7 mW | báo cáo kèm đo dòng thực | — |

**Mô hình 1D-CNN.** Đầu vào 128 × 6 (INT8) → Conv1D 6→16 (kernel 5) + ReLU + MaxPool 2 → Conv1D 16→16 + ReLU + MaxPool 2 → Conv1D 16→32 + ReLU + MaxPool 2 → Flatten (16 vị trí × 32 kênh) → Dense 512→4 → Argmax. Tổng cộng 6.368 trọng số, 68 bias và 227.328 phép nhân–cộng (MAC) mỗi cửa sổ. Mỗi vị trí ở lớp cuối nhìn 36 mẫu (0,72 s) và lớp Dense nhìn cả 16 vị trí theo đúng thứ tự thời gian, nên mạng thấy toàn bộ 2,56 s. Số học: trọng số và đầu vào INT8, bias và bộ cộng dồn INT32, tái lượng tử hóa sau mỗi lớp Conv bằng dịch phải và kẹp về 0…127; tỉ lệ là lũy thừa của 2 nên không cần bộ nhân thứ hai.

Mô hình trên sẽ được so sánh với mô hình 2 lớp Conv + Global Average Pooling của phiên bản đầu (3.168 trọng số, 225.408 MAC) trên dữ liệu của nhóm theo cách tách người; nhóm dùng mô hình nhỏ nhất đạt chỉ tiêu.

**Thời gian suy luận** (clock 50,143 MHz):

| Bộ tính | Chu kỳ mỗi lần suy luận | Thời gian | Trạng thái |
|---|---|---|---|
| Phiên bản đầu: 3 chu kỳ mỗi MAC, 1 làn | 699.800 | 13,96 ms | Đã đo trong mô phỏng |
| Bản cam kết: 1 chu kỳ mỗi MAC, 1 làn | 258.080 | 5,15 ms; cam kết ≤ 6 ms | Đo trong mô phỏng với mạng 3 lớp (227.328 MAC); chưa chạy trên chip |
| Mục tiêu mở rộng: 4 làn | 75.284 | 1,50 ms; mục tiêu ≤ 2 ms | Đo trong mô phỏng; chưa chạy trên chip |

**Vai trò của FPGA.** Với bước suy luận 0,32 s, một lần suy luận thuần phần mềm trên Cortex-M0 cần khoảng 2,4 triệu lệnh với mạng 3 lớp (đếm trên trình giả lập lõi Cortex-M0), tức 74–232 ms tùy loại bộ nhân của lõi (chưa đo trên chip), chiếm 23–73 % thời gian CPU trong khi MCU vẫn phải đọc cảm biến 100 lần mỗi giây, chạy Safety FSM và cập nhật màn hình. Trên FPGA, thời gian suy luận cố định và đếm được từng chu kỳ. Nhóm sẽ viết thêm bản suy luận chạy hoàn toàn trên MCU với cùng trọng số, đo thời gian thực tế và báo cáo cạnh số đo của FPGA. Nhóm thừa nhận với mạng cỡ này bản MCU thuần là khả thi; lợi ích của FPGA được trình bày bằng số đo chứ không bằng khẳng định.

### 3. Danh sách ngoại vi & cổng giao tiếp

| Thiết bị / Ngoại vi | Chuẩn giao tiếp | Kết nối với | Yêu cầu nguồn |
|---|---|---|---|
| MPU6050 (gắn cố định trên mũ) | I²C 400 kHz, ngắt data-ready 100 Hz | Sonix MCU | 3,3 V |
| Kiwi Primer 20K | SPI mode 0, MSB trước, SCK ≤ 4 MHz | MCU ↔ FPGA | Board 5 V; I/O 3,3 V |
| IRQ (Data Ready) | GPIO ngắt ngoài, mức cao tích cực | FPGA → MCU | 3,3 V |
| RST_N | GPIO, mức thấp tích cực | MCU → FPGA | 3,3 V |
| OLED SSD1306 0,96" | I²C dùng chung, cập nhật từng trang 128 byte | Sonix MCU | 3,3 V |
| Còi | PWM qua transistor | Sonix MCU | 3,3 V / 5 V |
| LED đỏ / xanh | GPIO | Sonix MCU | 3,3 V |
| Nút CANCEL (giữ 3 s = SOS) | GPIO, chống dội bằng phần mềm | Sonix MCU | 3,3 V |
| Cảm biến đội mũ | GPIO (micro-switch hoặc module hồng ngoại phản xạ) | Sonix MCU | 3,3 V |
| PC gỡ lỗi / thu dữ liệu | UART 460800 baud | Sonix MCU | USB 5 V |

**Lưu ý thiết kế.** (i) MCU chạy được từ 1,8 V đến 5,5 V và mức logic theo VDD [10]; nhóm cấp VDD = 3,3 V cho board MCU bằng bộ ổn áp 3,3 V có sẵn trên board [12] và đo lại trước khi nối với FPGA và cảm biến. (ii) Chân SPI và IRQ phía FPGA đặt trên header J1 của board, thuộc bank 0 và 1 cấp 3,3 V, ràng buộc ở chuẩn LVCMOS33 [11]. (iii) Một lần làm tươi toàn bộ OLED mất khoảng 25 ms, dài hơn chu kỳ lấy mẫu 10 ms, nên OLED chỉ cập nhật từng trang xen giữa các lần đọc cảm biến. (iv) Cáp I²C từ mũ tới hộp mạch không dài quá 50 cm.

### 4. Thiết bị & linh kiện đề nghị BTC hỗ trợ

- **Bo mạch / mạch nạp:** 01 Kiwi Primer 20K; 01 SN32F407_EVK; 01 SN-LINK-V3 (nếu BTC chưa cấp cho đội).
- **Cảm biến / module:** 01 MPU6050; 01 OLED SSD1306 I²C; còi, LED, nút nhấn, dây nối.
- **Nhóm tự chuẩn bị:** mũ bảo hộ, cảm biến đội mũ, hộp và đai gắn mạch, pin dự phòng 5 V, đệm tập.

---

## IV. PHÂN CHIA KIẾN TRÚC PHẦN MỀM & RTL

### 1. Phân chia nhiệm vụ xử lý

**Gowin FPGA (RTL).** SPI Slave đồng bộ SCK, CS, MOSI vào miền clock hệ thống bằng chuỗi flip-flop; bộ phân tích khung kiểm CRC-16 và ghi cửa sổ vào BSRAM; bộ tăng tốc 1D-CNN gồm một khối nhân–cộng dồn dùng chung chạy tuần tự qua các lớp, hai RAM đặc trưng dùng luân phiên, ROM trọng số và ROM bias khởi tạo từ file `.mem`; khối Argmax tính lớp thắng và điểm tin cậy (hiệu giữa logit lớn nhất và lớn nhì, bão hòa về 0…127); thanh ghi kết quả và chân IRQ. Dữ liệu trong RAM được xếp theo thứ tự thời gian nên cửa sổ tích chập là một dải địa chỉ liên tiếp, bộ sinh địa chỉ chỉ cần bộ đếm. Bộ đếm chu kỳ trong RTL ghi lại thời gian của từng lần suy luận.

**Sonix MCU (firmware).** Cấu hình MPU6050 ở 100 Hz, bộ lọc số 44 Hz, dải ±16 g và ±2000 °/s; đọc 14 byte theo ngắt data-ready (ISR chỉ đặt cờ); hiệu chuẩn độ lệch con quay khi khởi động. Bộ lọc giảm mẫu số nguyên `(r₀ + 3r₁ + 3r₂ + r₃ + 4) >> 3` đưa tín hiệu về 50 Hz, suy giảm 13,8 dB ở 30 Hz và 30,6 dB ở 40 Hz để hạn chế chồng phổ. Lượng tử hóa về INT8 bằng dịch phải có làm tròn và bão hòa: một mức bằng 1/16 g hoặc 3,9 °/s. MCU không trích đặc trưng thủ công cho mạng. Cùng một đoạn mã tiền xử lý được dùng khi tạo dữ liệu huấn luyện và khi chạy trên thiết bị. Ngoài ra MCU chạy Safety FSM, điều khiển OLED, còi, LED, đọc nút và cảm biến đội mũ, ghi log qua UART, có watchdog.

**Giao tiếp FPGA–MCU.** SPI mode 0, MCU làm master, kèm chân IRQ và RST_N.

| Hướng | Cấu trúc khung | Kích thước |
|---|---|---|
| MCU → FPGA | `0xA5` · SEQ · 768 byte (128 mẫu × 6 kênh INT8, theo thứ tự thời gian) · CRC-16 | 772 byte, truyền ≈ 1,5 ms ở 4 MHz |
| FPGA → MCU | `0x5A` · SEQ · STATUS · CLASS · SCORE · CRC-16 | 7 byte |
| FPGA → MCU (chỉ khi kiểm thử) | tiếp theo khung trên: 4 logit INT16 · số chu kỳ 24 bit · CRC-16 | thêm 13 byte |

CRC-16/CCITT (đa thức 0x1021, khởi tạo 0xFFFF). Nếu CRC sai, trường SEQ không khớp hoặc IRQ không lên trong 50 ms, MCU bỏ cửa sổ đó và làm tiếp cửa sổ sau; sau 3 lỗi liên tiếp MCU reset FPGA qua RST_N và hiển thị lỗi. Khi bật nguồn, MCU gửi một khung thử sinh bằng LFSR và so kết quả với giá trị tính sẵn, để tự kiểm toàn bộ chuỗi SPI, FPGA và trọng số.

**Safety FSM (trên MCU).**

| Trạng thái | Điều kiện vào | Hành động |
|---|---|---|
| STANDBY | Cảm biến báo mũ không được đội liên tục 3 s | Không xét cảnh báo |
| MONITOR | Mặc định khi mũ được đội | OLED hiển thị lớp hiện tại |
| SUSPECT | Ít nhất 2 trong 3 cửa sổ gần nhất là FALL với điểm tin cậy vượt ngưỡng | Theo dõi bất động; từ đây không xét cảm biến đội mũ nữa, vì mũ có thể văng ra khi ngã |
| PRE-ALARM | Bất động liên tục 2,56 s và đầu nằm ngang (lệch 45°–135° so với phương thẳng đứng) trong vòng 8 s kể từ SUSPECT | Còi ngắt quãng, LED đỏ nháy, đếm ngược 10 s; CANCEL → MONITOR |
| ALARM | Hết đếm ngược; hoặc người dùng giữ nút 3 s (SOS) | Còi liên tục, LED đỏ, ghi log; giữ CANCEL 1 s để tắt, chờ 30 s |

Độ bất động được tính trên mẫu thô 100 Hz theo từng khối 0,32 s: khối là bất động khi biên độ dao động của cả ba trục gia tốc và ba trục con quay đều dưới ngưỡng. Các ngưỡng được chọn từ dữ liệu thu được.

### 2. Công cụ & môi trường phát triển

- **Gowin EDA** V1.9.11.03 Education; RTL Verilog; IP rPLL. BSRAM và DSP được suy ra từ RTL.
- **Keil MDK-ARM** với gói thiết bị SONiX SN32F4 và mạch nạp SN-LINK-V3.
- **Huấn luyện:** Python, NumPy, TensorFlow/Keras hoặc PyTorch; huấn luyện có mô phỏng lượng tử hóa [5], [6] theo đúng phép dịch và kẹp của phần cứng.
- **Kiểm chứng:** mô hình tham chiếu Python chỉ dùng số nguyên làm chuẩn. (i) Testbench Verilog (Icarus Verilog) cho từng lớp và cho toàn hệ thống qua chân SPI, tự so với vector sinh từ mô hình tham chiếu, kèm các ca lỗi: CRC sai, khung thiếu byte, khung đến khi đang bận. (ii) Kiểm thử phần cứng trong vòng lặp: PC gửi cửa sổ thật qua MCU sang FPGA và so từng bit lớp, điểm tin cậy và bốn logit. (iii) Kiểm tra tiền xử lý của MCU bằng cách so CRC của khung MCU gửi với khung PC dựng lại từ mẫu thô. Phiên bản RTL đầu đã khớp mô hình tham chiếu trên 20/20 vector trong mô phỏng.

### 3. Dữ liệu, huấn luyện & lượng tử hóa

- **Gắn cảm biến:** cố định ở đỉnh hoặc phía sau mũ, trục Z hướng lên, trục X hướng về trước, có đệm giảm rung; vị trí được giữ nguyên từ lúc thu dữ liệu đến lúc trình diễn.
- **Nguồn dữ liệu:** ba nguồn, mỗi nguồn một vai trò.
  - *(i) Ngã và hoạt động thường ngày, dùng để huấn luyện:* bộ dữ liệu công khai của Özdemir và Barshan [4], có một cảm biến gắn ở đầu. Theo tài liệu đi kèm, bộ này gồm 17 người (bài báo [4] dùng 14 người trong số đó), 20 kiểu ngã và 16 hoạt động thường ngày, mỗi thứ lặp khoảng 5 lần, lấy mẫu 25 Hz; theo [4], dải đo là ±120 m/s² và ±1200 °/s. Đến ngày 13/10 nhóm đã chuyển đổi xong 6 người, gồm 604 cú ngã. Nhóm chỉ lấy kênh ở đầu, xoay trục về quy ước của mũ, nội suy lên 50 Hz và đổi về thang INT8 của thiết bị. Nhờ đó người tình nguyện không phải ngã hàng trăm lần.
  - *(ii) Va đập mũ và hoạt động bình thường khi đội mũ, nhóm tự thu:* không bộ công khai nào có các sự kiện này. Nhóm ghi mẫu thô 100 Hz ở dải ±16 g, ±2000 °/s bằng mạch ghi của nhóm, dùng đúng cảm biến và cấu hình thanh ghi của thiết bị, có video và nút đánh dấu sự kiện. Mục tiêu: ≥ 250 va đập mũ (rơi, va, đặt mạnh, tháo và đội); hoạt động bình thường ≥ 2 giờ từ ≥ 4 người, trong đó ≥ 50 tình huống suýt ngã (gán nhãn NORMAL).
  - *(iii) Ngã khi đội mũ, nhóm tự thu, chỉ để kiểm tra:* ≥ 40 cú ngã trên đệm của ≥ 3 người, không đưa vào huấn luyện. Ngã thực hiện trên đệm dày, có bảo hộ, có người hỗ trợ; người tham gia ký giấy đồng ý.
  - *Hạn chế đã biết:* bộ [4] lấy mẫu 25 Hz trong khi thiết bị chạy 50 Hz, và cảm biến của [4] buộc vào đầu chứ không nằm trên vỏ mũ. Nhóm đo độ chênh này bằng nguồn (iii) ở tuần 3, trước khi chốt mô hình. Cả ba nguồn đều có dải đo rộng hơn dải ±8 g mà mạng dùng, nên đổi thang lượng tử không cần thu lại.
- **Gán nhãn:** một cửa sổ mang nhãn của sự kiện khi điểm va chạm nằm trong khoảng mẫu 56–103, tức mạng có 0,48–1,42 s dữ liệu sau va chạm; cửa sổ có điểm va chạm ở sát hai biên bị loại khỏi tập huấn luyện. Với bước 16 mẫu, mỗi sự kiện có đúng ba cửa sổ mang nhãn.
- **Đánh giá:** tách theo người (leave-one-subject-out) trên bộ [4], không trộn cửa sổ của cùng một người; va đập mũ tách theo buổi thu. Chỉ số chính là độ nhạy mức sự kiện: một cú ngã được tính là phát hiện khi ít nhất 2 trong 3 cửa sổ của nó được phân loại FALL. Mô hình sau đó được thử trên các cú ngã khi đội mũ của nguồn (iii). Kết quả báo cáo kèm số ca tuyệt đối và ghi rõ nguồn dữ liệu của từng con số.
- **Tăng cường dữ liệu:** nhiễu, co giãn biên độ ±10 %, dịch thời gian, xoay trục ±10° để giả lập mũ đội lệch; trọng số lớp cho lớp ít mẫu.
- **Bộ dữ liệu ở vị trí khác:** SisFall [3] (cảm biến ở thắt lưng) đã được nhóm dùng để thông chuỗi huấn luyện → lượng tử hóa → RTL: mô hình thử nghiệm INT8 đạt độ chính xác 94,4 % và độ nhạy lớp ngã 96,7 % trên 6 người không có trong tập huấn luyện. Các số này **không phải kết quả của đề tài** vì khác vị trí đeo. Nhóm chọn [4] làm nguồn huấn luyện chính vì đây là bộ công khai duy nhất nhóm tìm được có cảm biến ở đầu; dữ liệu thu ở thân người (kênh ngực và thắt lưng của chính bộ [4], và SisFall) là nguồn bổ sung, chỉ được giữ nếu so sánh có và không có trên cùng tập kiểm tra cho thấy không làm tăng báo nhầm.

---

## V. KẾ HOẠCH TRIỂN KHAI & TIẾN ĐỘ

**Hiện trạng (14/10/2026).** Đã có: MPU6050 đã được đọc và kiểm tra trên SN32F407; phiên bản RTL đầu của toàn bộ đường suy luận, khớp mô hình tham chiếu trong mô phỏng (cả khi đưa khung dữ liệu vào qua chân SPI), đã tổng hợp và P&R; chuỗi huấn luyện – lượng tử hóa – xuất trọng số chạy trên SisFall và trên 6 người đầu của bộ [4]; các module firmware tiền xử lý, khung SPI và Safety FSM khớp mô hình tham chiếu khi chạy mã máy Cortex-M0 trên trình giả lập. Chưa có: dữ liệu trên mũ, kết nối SPI thật giữa hai board, firmware chạy trên board.

**Cách tổ chức.** Công việc chia ba tầng, tầng dưới chạy được rồi mới làm tầng trên. Tầng 1 là hệ thống tối thiểu chạy trên mũ, dùng phiên bản RTL đầu. Tầng 2 là các chỉ tiêu cam kết dưới đây. Tầng 3 là mục tiêu mở rộng, không cam kết. Mỗi tính năng của tầng 2 và 3 có công tắc tắt mà không ảnh hưởng tầng 1.

| Tuần | Nội dung | Mốc kiểm chứng |
|---|---|---|
| 1 | Chốt đặc tả và sơ đồ chân; firmware ghi dữ liệu 100 Hz; gắn cảm biến lên mũ; thu thử 1–2 người; chuyển bộ dữ liệu [4] về định dạng của thiết bị; sửa giao thức SPI trong RTL | Log 10 phút không mất mẫu; RTL khớp mô hình tham chiếu |
| 2 | Kết nối SPI thật; tiền xử lý trên MCU; phiên bản RTL đầu chạy trên chip; thu va đập mũ và hoạt động bình thường đợt 1 | 1.000 vòng gửi – ngắt – đọc không lỗi; kết quả trên chip khớp mô hình tham chiếu |
| 3 | Huấn luyện mô hình đầu tiên trên [4] cộng dữ liệu mũ; đo độ chênh giữa [4] và dữ liệu mũ; Safety FSM và giao diện; lắp mũ bản 1; bộ tính mới ở mức mô phỏng | **Tầng 1: mũ chạy độc lập**, ngã trên đệm 10 lần có ≥ 8 lần vào PRE-ALARM |
| 4 | Thu dữ liệu mũ đợt 2 (≥ 4 người) và các cú ngã kiểm tra; mô hình cuối và lượng tử hóa; bộ tính mới lên chip; kiểm thử phần cứng trong vòng lặp; bản đối chứng trên MCU | Đánh giá tách người đạt chỉ tiêu; phần cứng khớp 100 % trên ≥ 2.000 cửa sổ |
| 5 | Thử với người mới, đếm báo giả, đo độ trễ và công suất; chỉnh ngưỡng; báo cáo, video, slide | Đủ các chỉ tiêu cam kết |

**Phân công**

| Nhánh | Nội dung | Phụ trách |
|---|---|---|
| Firmware | Cảm biến, tiền xử lý, SPI, Safety FSM, giao diện, bản đối chứng trên MCU | Lê Thành Danh |
| Dữ liệu và mô hình | Thu và gán nhãn dữ liệu, huấn luyện, lượng tử hóa, mô hình tham chiếu, xuất trọng số | *(nhóm chốt)* |
| RTL giao tiếp và lên chip | SPI, giao thức, ràng buộc chân, tổng hợp, timing | *(nhóm chốt)* |
| RTL khối tính toán | Bộ tính tích chập, testbench từng lớp | Bùi Quốc Khánh |
| Tích hợp và tài liệu | Cơ khí mũ, kiểm thử phần cứng trong vòng lặp, đo đạc, báo cáo | Nguyễn Bá Thiện |

**Rủi ro và phương án dự phòng**

| Rủi ro | Phương án |
|---|---|
| Mô hình huấn luyện trên [4] kém đi khi chạy trên mũ (khác tần số lấy mẫu, khác cách gắn cảm biến) | Đo sớm ở tuần 3 bằng các cú ngã khi đội mũ; lọc thêm trên MCU để hai nguồn cùng băng tần; tinh chỉnh bằng một phần cú ngã tự thu; cuối cùng là tự thu ≥ 250 cú ngã từ ≥ 8 người |
| Dữ liệu va đập mũ ít | Thu thêm (không cần ai ngã); tăng cường dữ liệu; nếu vẫn thiếu thì gộp IMPACT vào NORMAL và dựa vào cảm biến đội mũ cùng Safety FSM |
| Mô hình 3 lớp không tốt hơn mô hình 2 lớp | Dùng mô hình 2 lớp đã có RTL |
| Bộ tính mới chậm tiến độ | Mở rộng phiên bản đầu để chạy mạng 3 lớp (≈ 14 ms, vẫn nhỏ hơn bước 0,32 s hơn 20 lần); chỉ chỉ tiêu thời gian suy luận bị ảnh hưởng, các chỉ tiêu nhận dạng thì không |
| Sai lệch giữa mô hình Python và phần cứng | So từng lớp bằng vector kiểm; tham số lượng tử sinh tự động từ một file duy nhất |
| Lỗi truyền SPI, FPGA treo | CRC-16, timeout, bỏ cửa sổ lỗi, reset qua RST_N |
| Cảm biến bão hòa khi va đập mạnh | Dữ liệu thô đã ghi ở ±16 g; đổi thang lượng tử rồi huấn luyện lại |
| Báo giả do rơi và va mũ | Lớp IMPACT, cảm biến đội mũ, bỏ phiếu, điều kiện bất động và độ nghiêng |

**Chỉ tiêu cam kết.** Các số dưới đây là mục tiêu, sẽ được đo và báo cáo ở vòng chung kết.

| Chỉ tiêu | Mục tiêu | Cách đo |
|---|---|---|
| Hoạt động độc lập | Không cần PC, Internet; tự kiểm khi bật nguồn | Trình diễn trực tiếp |
| Độ nhạy lớp FALL mức sự kiện / Macro-F1 ba lớp | ≥ 95 % / ≥ 0,90 | Tách theo người trên bộ [4] (FALL, NORMAL) cộng va đập mũ tự thu |
| Thử trực tiếp trên mũ | ≥ 18 trên 20 cú ngã vào PRE-ALARM | ≥ 2 người; dữ liệu của họ không dùng để huấn luyện |
| Báo giả sau Safety FSM | ≤ 1 lần mỗi giờ | Đội mũ hoạt động bình thường, 3 người × 60 phút |
| Loại trừ rơi mũ và va mũ | ≥ 18 trên 20 lần không gây PRE-ALARM | Thử trực tiếp |
| Độ trễ phát hiện | Va chạm → SUSPECT ≤ 1,5 s; → PRE-ALARM ≤ 5 s khi người nằm yên trong 2 s sau va chạm | Mốc thời gian trong log của MCU |
| Thời gian suy luận trên FPGA | ≤ 6 ms; nhanh hơn bản chạy trên MCU ≥ 5 lần | Bộ đếm chu kỳ trong RTL; đo bản MCU bằng GPIO |
| Khớp phần cứng – phần mềm | 0 sai lệch trên ≥ 2.000 cửa sổ; FP32 → INT8 giảm ≤ 2 điểm % | Kiểm thử phần cứng trong vòng lặp; bảng FP32 / INT8 / RTL |
| Tài nguyên và timing | Logic ≤ 20 %, BSRAM ≤ 25 %, DSP ≤ 25 %; Fmax ≥ 55 MHz | Báo cáo Gowin EDA |
| Công suất | Báo cáo ước lượng của công cụ và dòng đo ở nguồn 5 V của từng board | Gowin EDA; đồng hồ đo dòng |

**Mục tiêu mở rộng (không cam kết).** Bộ tính 4 làn song song với thời gian suy luận ≤ 2 ms và Fmax ≥ 100 MHz; năng lượng cho mỗi lần suy luận của FPGA so với MCU; lớp thứ tư "suýt ngã"; nạp trọng số qua SPI để cập nhật mô hình không cần tổng hợp lại; lưu sự kiện vào Flash của MCU; chỉ suy luận khi có chuyển động.

**Hướng phát triển.** Truyền cảnh báo từ mũ về trạm giám sát qua BLE hoặc LoRa; thu dữ liệu với người lao động thật dưới sự giám sát an toàn; thiết kế mạch in tích hợp dùng FPGA công suất thấp thay cho hai board phát triển.

---

## TÀI LIỆU THAM KHẢO

[1] N. Noury và cộng sự, "Fall detection – Principles and Methods," *Proc. 29th Annual International Conference of the IEEE EMBS*, 2007.
[2] A. K. Bourke, J. V. O'Brien, G. M. Lyons, "Evaluation of a threshold-based tri-axial accelerometer fall detection algorithm," *Gait & Posture*, tập 26, số 2, tr. 194–199, 2007.
[3] A. Sucerquia, J. D. López, J. F. Vargas-Bonilla, "SisFall: A Fall and Movement Dataset," *Sensors*, tập 17, số 1, 198, 2017.
[4] A. T. Özdemir, B. Barshan, "Detecting Falls with Wearable Sensors Using Machine Learning Techniques," *Sensors*, tập 14, số 6, tr. 10691–10708, 2014. Bộ dữ liệu: UCI Machine Learning Repository, DOI 10.24432/C52028.
[5] B. Jacob và cộng sự, "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference," *CVPR*, 2018 (arXiv:1712.05877).
[6] Y. Bengio, N. Léonard, A. Courville, "Estimating or Propagating Gradients Through Stochastic Neurons for Conditional Computation," arXiv:1308.3432, 2013.
[7] G. Chen, C. Parada, G. Heigold, "Small-footprint keyword spotting using deep neural networks," *ICASSP*, 2014.
[8] InvenSense, *MPU-6000 and MPU-6050 Product Specification* và *Register Map and Descriptions*.
[9] Gowin Semiconductor, *GW2A series of FPGA Products Data Sheet (DS102)*; *Gowin BSRAM & SSRAM User Guide (UG285)*; *Gowin DSP User Guide (UG287)*.
[10] SONiX Technology, *SN32F400 Series User's Manual (SN32F407/405/403)*, phiên bản 2.2; gói thiết bị *SN32F4_DFP*.
[11] OneKiwi Technology, sơ đồ nguyên lý *Kiwi Primer 20K*, rev v1.0, 28/09/2024.
[12] SONiX Technology, *Hướng dẫn sử dụng bo mạch SONiX SN32F407 EVK*, phiên bản 1.0.
