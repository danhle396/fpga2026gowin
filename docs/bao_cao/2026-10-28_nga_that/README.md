# 2026-10-28 — Chỉ báo ngã thật (nga.c), MẤT CẢM BIẾN, UART chịu nhiễu

Khi đeo ngực, nhóm thấy thiết bị báo ngã cả khi chỉ ngồi xuống hơi mạnh hoặc lăn người lúc đang nằm. Nhóm cũng yêu cầu không còn trạng thái "nghi ngã" hiện ra: chỉ báo ngã thật.

## Thiết kế

SUSPECT của Safety FSM (CNN báo 2/3 cửa sổ FALL) giờ chỉ là bước nghi nội bộ. `firmware/src/nga.c` chạy trên ESP32 trong `hub.c` và xét thêm các dấu hiệu vật lý:

1. **Trước đó đang thẳng** (đứng / ngồi / đi): trong khoảng 3,2–10,2 s trước SUSPECT có ít nhất một khối 0,32 s mà hướng ngực đã chốt là THẲNG.
2. **Va chạm:** lấy đỉnh |a| trong 3,84 s trước SUSPECT:
   - ≥ 3,0 g → **xác nhận ngay**;
   - < 2,5 g → **loại**;
   - 2,5–3,0 g → xét tiếp mục 3.
3. **Bằng chứng thêm** (chỉ khi va chạm 2,5–3,0 g): trong 4 s sau SUSPECT phải có một trong ba: ngực chốt NẰM, một đợt cử động hạ ngực ≥ 0,5 m, hoặc FSM vào PRE_ALARM. Không có thì loại.

Khi bị loại, `safety_bo_nghi()` đưa FSM về MONITOR với lý do WHY_KHONG_NGA. Còi, web và ô đếm "Số lần phát hiện ngã" không thấy lần nghi đó. Mỗi lần xét ghi một dòng log `N,<ms>,XAC_NHAN|BO,ly_do,dinh,dh_cm,truoc_thang` để sau này chỉnh ngưỡng.

Ngưỡng đặt trong `fw_config.h` (`NGA_*`). Đây là bản 2; quy tắc chưa đưa vào SPEC A.8 và chưa có golden Python (việc B3).

Cùng đợt sửa:
- **MẤT CẢM BIẾN:** quá 3 s không có mẫu thì web đỏ, còi 2 bíp mỗi 3 s, LED nháy nhanh.
- **UART chịu nhiễu:** bộ tách chỉ nhận khung LEN = 14 và dò lại `F1 7E` ngay trong khung hỏng.
- **ESP32:** bật kéo lên trên GPIO16, bộ đệm nhận 32 KB, gửi log TCP bằng `MSG_DONTWAIT`, chèn bù mẫu mất (khoảng hở ≤ 50 mẫu), cấp nguồn MPU6050 qua GPIO25 để tự gỡ treo.

## Kết quả

**Phép kiểm trong trình giả lập** ([m0_test.txt](m0_test.txt), bản 1): TẤT CẢ PASS. Bản 2: 71/71 PASS. Các ca của `nga.c`:
- lăn người khi đang nằm, kể cả khi ngực lăn qua vùng CÚI (N → C → N, 2,7 g): loại;
- ngồi xuống mạnh 2 g: loại;
- ngã rồi nằm: xác nhận;
- ngã nhẹ, ngực hạ 0,6 m: xác nhận;
- va chạm 2,7 g, ngực chỉ hạ 0,36 m, vẫn thẳng: loại sau 4 s;
- PRE_ALARM: xác nhận;
- ngã quỳ / ngã ngồi 4 g: xác nhận ngay;
- ngất gục từ từ rồi nằm: xác nhận;
- hub: SUSPECT chưa xác nhận thì còi im, web hiện "đang theo dõi".

**Bộ tách UART:** 6 lần nhiễu (rơi byte, LEN bị nhiễu, đổi bit) trong 200 khung → mất đúng 6 mẫu, bản C khớp đáp án Python `node_rx_py`. Bộ tách cũ, đo trên cùng luồng: rơi byte hoặc LEN nhiễu mất 2 mẫu mỗi lần.

**Log đeo ngực 9 tư thế của nhóm** ([nga_tren_log_9_tu_the.txt](nga_tren_log_9_tu_the.txt), chạy nguyên lõi ESP32 bằng `tools/nga_tren_log.py`). Log có ngồi, đứng, cúi, nằm, lăn, không có cú ngã nào:

| | CNN nghi | Báo ngã |
|---|---|---|
| Không có `nga.c` | 1 lần (nằm ngửa xuống) | 1, tới PRE_ALARM |
| Có `nga.c` | 2 lần (nằm xuống: đỉnh 2,4 g; lăn qua vùng CÚI: 2,7 g) | **0** |

**D1 người 102** (`tools/nga_d1.py`, mỗi bản ghi chạy riêng qua lõi ESP32):

| | Bản ghi | CNN nghi | Bản 1: xác nhận | **Bản 2: xác nhận** |
|---|---|---|---|---|
| Ngã 901–920 | 101 | 101 | 73 (72,3 %) | **94 (93,1 %)** |
| Sinh hoạt 801–816 | 81 | 0 | 0 | **0** |

Chi tiết từng bản ghi kèm lý do loại: [nga_d1_102_v1.txt](nga_d1_102_v1.txt), [nga_d1_102_v2.txt](nga_d1_102_v2.txt).
- Bản 1 loại 903 (ngã quỳ), 909 (ngã ngồi), 920, cùng một phần 905 / 906 / 914 / 916. Các cú ngã này va chạm 3,7–5,0 g nhưng sau đó không nằm, và Δh đo trôi (−0,4 … +3,5 m). Từ đó có bản 2: va chạm ≥ 3 g xác nhận ngay.
- Bản 2 còn sót: 905 một lần (2,87 g, không nằm), và 917 (ngất) 0/6.
- Trong 6 bản ghi 917 của người 102, đầu đã nằm ngang ngay từ đầu bản ghi, và hai bản 358 / 359 trùng nhau từng mẫu. Không thể có "trước đó đang thẳng" nên không chỉnh quy tắc theo các bản ghi này. Không tính 917: 94/95 = 98,9 %.

## Giới hạn

- D1 là **cảm biến ở đầu**, và người 102 nằm trong tập huấn luyện của mô hình N2_11. CNN nghi đúng 101/101 là con số lạc quan. Chưa có bản ghi liền kênh ngực (việc B1).
- Ngồi xuống thật mạnh mà đỉnh ≥ 3 g sẽ bị báo ngã nhầm. Ngất / ngã nhẹ va chạm < 2,5 g sẽ bị bỏ sót. Ngã khi đang cúi sẽ bị loại vì trước đó không thẳng. [CẦN XÁC MINH – nguồn: dữ liệu nhóm tự thu khi đeo ngực, `ghi_uart --kich-ban dong_tac` và `--kich-ban nga`]
- Nằm xuống giường khi đeo có đỉnh 2,4 g, rất sát ngưỡng 2,5 g.
- Chưa nạp lên board.
