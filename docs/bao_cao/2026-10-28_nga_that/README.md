# 2026-10-28 — Chỉ báo ngã thật (nga.c), MẤT CẢM BIẾN, UART chịu nhiễu

Khi đeo ngực, nhóm thấy thiết bị báo ngã cả khi chỉ ngồi xuống hơi mạnh hoặc lăn người lúc đang nằm. Nhóm cũng yêu cầu không còn trạng thái "nghi ngã" hiện ra: chỉ báo ngã thật.

## Thiết kế (bản 3, 28/10 tối)

SUSPECT của Safety FSM (CNN báo 2/3 cửa sổ FALL) giờ chỉ là bước nghi nội bộ. `firmware/src/nga.c` chạy trên ESP32 trong `hub.c` và chỉ xác nhận khi có **đủ bốn** dấu hiệu vật lý:

1. **Trước đó đang thẳng** (đứng / ngồi / đi): trong khoảng 3,2–10,2 s trước SUSPECT có ít nhất một khối 0,32 s mà hướng ngực đã chốt là THẲNG.
2. **Va chạm:** đỉnh |a| trong 3,84 s trước SUSPECT ≥ 2,5 g. Khối có đỉnh đó là *khối va chạm*.
3. **Quay nhanh:** đỉnh |ω| trong ±5 khối (±1,6 s) quanh khối va chạm ≥ 220 °/s.
4. **Ngực nghiêng:** từ khối va chạm tới 12 khối (3,84 s) sau đó, có một khối mà gia tốc trung bình lệch ≥ 45° khỏi phương thẳng đứng.

Hết cửa sổ (hoặc 4 s sau SUSPECT) mà thiếu dấu hiệu 3 hay 4 thì loại. Khi bị loại, `safety_bo_nghi()` đưa FSM về MONITOR với lý do WHY_KHONG_NGA. Còi, web và ô đếm "Số lần phát hiện ngã" không thấy lần nghi đó. Mỗi lần xét, ESP32 ghi một dòng log `N,<ms>,XAC_NHAN|BO,ly_do,dinh,quay,nghieng,dh_cm,truoc_thang`.

Ngưỡng đặt trong `fw_config.h` (`NGA_*`). Quy tắc chưa đưa vào SPEC A.8 và chưa có golden Python (việc B3).

**Các bản trước:**
- **Bản 1:** cần va chạm ≥ 2,5 g, kèm nằm hoặc ngực hạ ≥ 0,5 m. Trên D1 người 102 chỉ xác nhận 73/101 cú ngã ([nga_d1_102_v1.txt](nga_d1_102_v1.txt)). Kiểm thử: [m0_test.txt](m0_test.txt).
- **Bản 2:** va chạm ≥ 3 g thì xác nhận ngay; 2,5–3 g thì cần nằm, hạ ngực hoặc PRE_ALARM.
  - D1 người 102: 94/101 ([nga_d1_102_v2.txt](nga_d1_102_v2.txt)).
  - Log 9 tư thế: báo nhầm 0 ([nga_tren_log_9_tu_the.txt](nga_tren_log_9_tu_the.txt)).
  - Đeo ngực thật, bản 2 báo ngã 9/10 lần **ngồi phịch xuống ghế**: ngồi mạnh va chạm 4,3–6,2 g, mạnh hơn cả ngã lên nệm. Va chạm một mình không phân biệt được ngồi với ngã, nên bản 3 bỏ luật "≥ 3 g xác nhận ngay".

Cùng đợt sửa:
- **MẤT CẢM BIẾN:** quá 3 s không có mẫu thì web đỏ, còi 2 bíp mỗi 3 s, LED nháy nhanh.
- **UART chịu nhiễu:** bộ tách chỉ nhận khung LEN = 14 và dò lại `F1 7E` ngay trong khung hỏng.
  - Kiểm: 6 lần nhiễu (rơi byte, LEN bị nhiễu, đổi bit) trong 200 khung → mất đúng 6 mẫu; bản C khớp đáp án Python `node_rx_py`.
  - Bộ tách cũ, đo trên cùng luồng: mỗi lần rơi byte hoặc LEN nhiễu mất 2 mẫu.
- **ESP32:** bật kéo lên trên GPIO16, bộ đệm nhận 32 KB, gửi log TCP bằng `MSG_DONTWAIT`, chèn bù mẫu mất (khoảng hở ≤ 50 mẫu).
  - Đã thử cấp nguồn MPU6050 qua GPIO25 để tự gỡ treo. Nhóm nối VCC vào GPIO25 thì cảm biến không chạy, nên chốt giữ VCC ở 3,3 V của ESP32 (`MPU_NGUON_GPIO 0`).
  - MPU treo thì rút pin ≈ 5 s.

## Dữ liệu đeo ngực của nhóm (B2, 28/10 tối)

Thu bằng `ghi_uart --kich-ban dong_tac` và `--kich-ban nga`, ESP32 chạy bản 2:
- [dong_tac_20261028_204848.txt](dong_tac_20261028_204848.txt): đứng; ngồi phịch xuống ghế ×10; cúi nhặt đồ ×5; đi lại 30 s; nằm xuống giường ×5; ngồi dậy ×5; lăn người khi đang nằm ×10;
- [nga_20261028_205657.txt](nga_20261028_205657.txt): ngã xuống nệm rồi nằm ×10; ngã nhẹ rồi ngồi dậy ngay ×5.

Đặc trưng từng lần ([dac_trung_b2.txt](dac_trung_b2.txt), [dac_trung.py](dac_trung.py)):
- đỉnh |a|;
- góc nghiêng của ngực (gia tốc lọc 0,5 s), lấy giá trị lớn nhất trong 4 s sau đỉnh;
- đỉnh |ω| trong ±1,5 s quanh đỉnh.

| Động tác | Đỉnh \|a\| | Nghiêng tối đa sau va chạm | Đỉnh \|ω\| |
|---|---|---|---|
| Ngồi phịch xuống ghế ×10 | 4,30–6,17 g | 18–31° | 85–149 °/s |
| Ngã lên nệm rồi nằm ×10 | 2,58–5,29 g | 58–80° | 281–467 °/s |
| Ngã nhẹ rồi ngồi dậy ×4 | 3,33–3,77 g | 68–78° | 258–385 °/s |
| Ngã nhẹ lần 5 | 1,74 g | 22° | 71 °/s |
| Nằm xuống giường ×5 | 1,03–2,74 g | 85–96° | 12–192 °/s |
| Cúi nhặt đồ ×5 | 1,51–1,68 g | 66–72° | 175–210 °/s |

Ngưỡng bản 3 chọn từ bảng này: quay 220 °/s, nghiêng 45°. **Ngưỡng được chọn trên chính dữ liệu dùng để chấm**, một người, một buổi thu.

## Kết quả bản 3

**Phép kiểm trong trình giả lập:** 70/70 PASS. Các ca của `nga.c` bản 3:
- lăn người khi đang nằm: loại;
- ngồi mạnh 5 g, quay chậm: loại;
- ngồi mạnh quay 300 °/s mà thân vẫn thẳng: loại;
- ngã rồi nằm: xác nhận;
- ngã nhẹ 2,6 g, quay sau va chạm, nghiêng rồi ngồi dậy: xác nhận;
- cúi nhặt đồ nhanh 2 g: loại;
- nghiêng xảy ra trước va chạm, hoặc quay nằm ngoài ±5 khối: không tính;
- lăn qua vùng CÚI: loại;
- ngất gục từ từ rồi nằm: xác nhận;
- hết 4 s mà không có khối nghiêng: loại;
- hub: SUSPECT chưa xác nhận thì còi im.

**Chạy lại nguyên lõi ESP32** (`tools/nga_tren_log.py`, CNN golden thay FPGA) trên log của nhóm:

| Log | CNN nghi | Bản 2 báo ngã | **Bản 3 báo ngã** |
|---|---|---|---|
| dong_tac (không có cú ngã) | 22 lần (ngồi mạnh 19, lăn 3) | 9/10 lần ngồi mạnh (trên board) | **0** ([nga_tren_log_dong_tac_v3.txt](nga_tren_log_dong_tac_v3.txt)) |
| nga (15 cú ngã) | 14/15 cú ngã (sót ngã nhẹ lần 5: 1,74 g) | 13/15 (trên board; nga_nam_10 bị loại vì 2,96 g mà không nằm) | **14/15** ([nga_tren_log_nga_v3.txt](nga_tren_log_nga_v3.txt)) |
| 9 tư thế (17:05) | 2 lần | 0 | **0** ([nga_tren_log_9_tu_the_v3.txt](nga_tren_log_9_tu_the_v3.txt)) |

- Trên log dong_tac, mọi lần ngồi mạnh đều bị loại vì cả hai dấu hiệu: quay ≤ 149 °/s và ngực không nghiêng. Lần lăn người bị loại vì trước đó không thẳng.
- Có 5 lần xét bị loại vì đỉnh 2,40–2,49 g. Đó là các khung CNN nghi trước hoặc sau cú ngã nga_nam_2, nga_nam_5 và nga_nhe_4; ba cú ngã này vẫn được xác nhận ở lần nghi kế tiếp.

**D1 người 102** (`tools/nga_d1.py`, mỗi bản ghi chạy riêng qua lõi ESP32):

| Nhóm bản ghi | Số bản ghi | CNN nghi | Bản 1 | Bản 2 | **Bản 3** |
|---|---|---|---|---|---|
| Ngã, tất cả (901–920) | 101 | 101 | 73 | 94 | **70 (69,3 %)** |
| — kết thúc quỳ / ngồi, thân thẳng (903, 909, 920; X15) | 15 | 15 | 1 | 15 | **0** |
| — ngất 917 (đầu nằm ngang từ đầu bản ghi) | 6 | 6 | 0 | 0 | **0** |
| — các kiểu ngã còn lại | 80 | 80 | 72 | 79 | **70** |
| Sinh hoạt (801–816), báo nhầm | 81 | 0 | 0 | 0 | **0** |

Chi tiết từng bản ghi: [nga_d1_102_v3.txt](nga_d1_102_v3.txt), [nga_d1_102_v3.csv](nga_d1_102_v3.csv).
- 903 / 909 / 920 bị loại đúng theo thiết kế bản 3: thân vẫn thẳng sau cú ngã (nghiêng 0); 903 và 909 còn quay chậm, 96–185 °/s. Với cảm biến ở ngực, các kiểu ngã này giống hệt ngồi phịch xuống ghế. Từ 15/10, A.8 cũng không đưa các kiểu ngã này tới PRE_ALARM (X15).
- 10 trong 80 bản ghi còn lại bị loại vì quay 148–218 °/s, thấp hơn ngưỡng 220 °/s một chút. D1 là cảm biến **ở đầu**, lấy mẫu 50 Hz rồi nội suy lên 100 Hz: đỉnh |ω| bị làm tròn xuống, và đầu quay khác ngực. Không hạ ngưỡng theo D1, vì trên ngực thật nằm xuống giường đã quay tới 192 °/s.

## Giới hạn

- Ngưỡng quay và nghiêng chọn trên chính 25 lần thu của một người, một buổi. Cần một buổi thu khác (người khác, nệm khác) để kiểm.
- **Bỏ sót theo thiết kế:** ngã ngồi, ngã quỳ mà thân vẫn thẳng (nghiêng < 45°); ngã chậm hoặc va chạm < 2,5 g (ngã nhẹ lần 5: 1,74 g).
- Nằm xuống giường mạnh (lần 1: 2,74 g, nghiêng 94°) chỉ bị loại nhờ dấu hiệu quay: 192 °/s so với ngưỡng 220 °/s. CNN không nghi lần này, nhưng khoảng cách tới ngưỡng nhỏ.
- D1 là cảm biến ở đầu, người 102 nằm trong tập huấn luyện của N2_11.
- Bản 3 chưa nạp lên ESP32.
