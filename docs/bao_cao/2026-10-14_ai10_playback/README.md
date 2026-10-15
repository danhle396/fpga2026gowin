# 2026-10-14 — AI-10 (sơ bộ): phát lại D1 qua chuỗi đầy đủ của thiết bị

`tools/playback_d1.py` phát lại 604 bản ghi ngã và 499 bản ghi sinh hoạt (2,65 giờ) của 6 người D1 qua chuỗi sau:
1. Cửa sổ 128 mẫu, bước 16.
2. Mô hình INT8 của **lượt LOSO mà người đó được để riêng** (`ml/out/<mô hình>_d1/loso_params.npz`).
3. Bỏ phiếu.
4. Khối bất động + độ nghiêng.
5. Safety FSM (`ml/src/safety_model.py`). Bản Python này **trùng mã C `safety.c`/`blocks.c` trên 240.000 tick ngẫu nhiên** (`tools/m0_test.py`).

Mỗi bản ghi chạy một FSM mới, WEAR = 1, không bấm CANCEL. Kết quả CNN đến trễ 40 ms sau khi cửa sổ kết thúc.

**Khác thiết bị thật:**
- D1 chỉ có 50 Hz (vốn 25 Hz nội suy), nên khối = 16 mẫu 50 Hz thay cho 32 mẫu 100 Hz; ngưỡng giữ nguyên LSB.
- Người D1 không đội mũ.
- Sinh hoạt của D1 là chuỗi động tác "khó" dồn liền nhau (vấp, nhặt đồ, nằm xuống giường), không phải một giờ đội mũ làm việc bình thường.

## Ba nhóm kiểu ngã (theo `Information.pdf`)

Hệ thống chỉ báo động khi người ngã **và nằm** bất động (mục 1, A.8). Vì vậy tách D1 thành ba nhóm:
- **Kết thúc nằm**, 13 kiểu, 394 lần: phải tới PRE_ALARM.
- **Ngã rồi đứng dậy**, 905/906/914/916, 120 lần: không được tới PRE_ALARM.
- **Kết thúc quỳ/ngồi**, 903/909/920, 90 lần: đầu thẳng; tới hay không là câu hỏi yêu cầu, ghi ở Phụ lục C (X15).

## Kết quả chính (`pb_*.log`, `n2s_k2_s8_t1450_co_nhom.log`)

| Mô hình, tham số A.8 hiện tại (2/3 phiếu, 8 khối, 45°) | Ngã → SUSPECT | Trễ va chạm → SUSPECT, trung vị / p90 | Ngã nằm → PRE_ALARM | Đứng dậy → PRE_ALARM | Trễ → PRE_ALARM, trung vị / p90 | PRE_ALARM giả/giờ |
|---|---|---|---|---|---|---|
| N2-S, T_SCORE 0 | 98,7 % | **0,84 / 1,03 s** | **97,0 %** | **0/120** | 4,08 / 5,32 s | 5,66 |
| N2-S, T_SCORE 8 | 95,9 % | 0,88 / 1,04 s | 94,4 % | 0/120 | 4,08 / 5,24 s | 3,77 |
| N1, T_SCORE 0 | 87,1 % | 0,56 / 0,74 s | — | — | 4,00 / 5,16 s | 3,77 |
| N2-S **không** xét nghiêng | 98,7 % | 0,84 / 1,03 s | — | (đứng dậy cũng báo) | 4,20 / 6,46 s | 11,32 |

Xét nghiêng là cần thiết: bỏ nó thì báo giả tăng gấp đôi, và ngã có đứng dậy cũng thành báo động.

## Quét tham số với N2-S (`quet/`)

VOTE_K 2 hoặc 3 × STILL_BLOCKS 8 / 10 / 12 × T_TILT 45° (1450) hoặc 60° (1024) × T_SCORE 0 / 8 / 16.

| Cấu hình | Ngã nằm → PRE_ALARM | PRE_ALARM giả/giờ | Trễ PRE_ALARM trung vị / p90 |
|---|---|---|---|
| 2/3, 8 khối, 45°, T 0 (A.8 hiện tại) | 97,0 % | 5,66 | 4,08 / 5,32 s |
| 3/3, 8 khối, 45°, T 0 | 95,4 % | 3,40 | 4,08 / 5,32 s |
| **3/3, 8 khối, 45°, T 8** | 92,1 % | **1,13** | 4,04 / 5,18 s |
| 3/3, 12 khối, 45°, T 8 | 91,4 % | 0,38 | 5,32 / 6,42 s |
| 60° thay 45° | giảm 10–13 điểm ở mọi cấu hình | | |

**Kết luận sơ bộ:**
- Chưa cấu hình nào đạt cùng lúc ≥ 95 % ngã nằm tới PRE_ALARM và ≤ 1 PRE_ALARM giả mỗi giờ trên sinh hoạt của D1.
- Giữ T_TILT 45°.
- Ứng viên cần thử trên D2/D3: 3/3 phiếu, 8 khối, T_SCORE 8.
- Firmware giữ mặc định A.8 cho tới khi AI-10 chốt bằng dữ liệu đội mũ.

Báo giả đến từ 806 (nhặt đồ), 808 (vấp rồi đứng lại), 809 (vấp chân) và 815 (nằm xuống giường).

Pass của AI-10 ("≥ 95 % cú ngã tới PRE_ALARM; 0 PRE_ALARM trên file NORMAL") chưa đạt. Câu chữ của nó cũng cần sửa: phải tính trên ngã kết thúc nằm, vì ngã có đứng dậy không được tới PRE_ALARM.

## Bổ sung 15/10: phát lại với 3 seed của N2 và N2-S (`nhieu_seed/`)

| Mô hình | Phiếu | T_SCORE | Ngã nằm → PRE_ALARM (3 seed) | TB | Đứng dậy → PRE_ALARM | PRE_ALARM giả/giờ (3 seed) | TB | Trễ PRE_ALARM tv / p90 |
|---|---|---|---|---|---|---|---|---|
| N2 | 2/3 | 0 | 96.7 / 96.7 / 97.2 % | 96.9 % | 0/360 | 10.19 / 8.68 / 4.91 | 7.93 | 4.08 / 5.29 s |
| N2 | 2/3 | 8 | 95.2 / 94.9 / 96.4 % | 95.5 % | 0/360 | 8.30 / 5.66 / 3.77 | 5.91 | 4.08 / 5.25 s |
| N2 | 3/3 | 0 | 95.7 / 96.7 / 96.7 % | 96.4 % | 0/360 | 9.44 / 7.93 / 4.15 | 7.17 | 4.08 / 5.26 s |
| N2 | 3/3 | 8 | 92.9 / 92.4 / 94.7 % | 93.3 % | 0/360 | 7.93 / 5.28 / 4.15 | 5.79 | 4.08 / 5.22 s |
| N2-S | 2/3 | 0 | 97.0 / 94.7 / 96.4 % | 96.0 % | 0/360 | 5.66 / 13.97 / 10.19 | 9.94 | 4.07 / 5.31 s |
| N2-S | 2/3 | 8 | 94.4 / 92.9 / 95.2 % | 94.2 % | 0/360 | 3.77 / 11.70 / 9.06 | 8.18 | 4.07 / 5.25 s |
| N2-S | 3/3 | 0 | 95.4 / 94.4 / 95.2 % | 95.0 % | 0/360 | 3.40 / 12.46 / 9.44 | 8.43 | 4.07 / 5.29 s |
| N2-S | 3/3 | 8 | 92.1 / 90.4 / 91.4 % | 91.3 % | 0/360 | 1.13 / 11.70 / 7.93 | 6.92 | 4.05 / 5.19 s |

**Sửa kết luận:**
- Con số 1,13 PRE_ALARM giả/giờ ở trên là của một seed may (N2-S seed 20261014). Tính trung bình 3 seed, mọi cấu hình đều ở **5,8–10 PRE_ALARM giả/giờ** trên sinh hoạt D1, khoảng gấp 6 lần chỉ tiêu ≤ 1/giờ.
- Ngã nằm → PRE_ALARM ổn định qua seed: N2, 2/3 phiếu: 96,9 % (T_SCORE 0), 95,5 % (T_SCORE 8). Ngã có đứng dậy: 0/360 ở mọi cấu hình.
- Cấu hình nên dùng khi thử D2/D3: **N2, 2/3 phiếu, T_SCORE 8**: 95,5 % ngã nằm, 5,91 giả/giờ, trễ 4,08 / 5,25 s.

**Rủi ro:** chỉ tiêu báo giả của đề cương khó đạt nếu chỉ huấn luyện bằng D1. Đường giảm theo thứ tự rẻ trước:
1. Thu D2 NORMAL khi đội mũ, đặc biệt nằm xuống, cúi nhặt, vấp, rồi huấn luyện lại. Đây là nguồn báo giả chính.
2. Cảm biến đội mũ (WEAR) loại các tình huống tháo mũ.
3. Tăng STILL_BLOCKS lên 10–12, đổi lại PRE_ALARM trễ hơn (trung vị 4,7–5,4 s).
4. Gộp 2–3 mô hình (cộng logit): E2 với P = 4 chạy 3 lần vẫn dưới 5 ms.

Phép thử thật là 3 người × 60 phút đội mũ (TH-10). Sinh hoạt của D1 dồn liền các động tác khó nên có thể bi quan hơn thực tế, nhưng không được dựa vào điều đó.

## Thử 15/10: gộp 3 seed N2 (cộng logit INT8; `gop_mo_hinh/`, `playback_d1.py --model A B C`)

| N2 × 3, 2/3 phiếu | Ngã nằm → PRE_ALARM | Đứng dậy → PRE_ALARM | PRE_ALARM giả/giờ |
|---|---|---|---|
| T_SCORE 0 | 97,0 % | 0/120 | 8,68 |
| T_SCORE 8 | 95,7 % | 0/120 | **4,91** (một mô hình, trung bình 3 seed: 5,91) |
| T_SCORE 16 | 91,9 % | 0/120 | 3,40 |

Gộp giảm khoảng 17 % báo giả ở cùng mức recall, với giá 3 lần suy luận (E2 N2 P = 4: 3 × 1,50 ms). Có ích nhưng không đủ đưa về ≤ 1/giờ. Đòn bẩy chính vẫn là dữ liệu NORMAL khi đội mũ (D2). Bản một mô hình chạy lại qua mã gộp cho đúng 10,19/giờ như trước, nên phần sửa mã không đổi kết quả cũ.

## 15/10: SPEC v3.1 — điều kiện nghiêng hai phía `|az_tb| < T_TILT` (`v31/`)

**Phân tích (`v31/phan_tich_do_nghieng_truoc_v31.log`, N2 seed 20261014, T_SCORE 8, quy tắc cũ):**
- 22 PRE_ALARM giả, trong đó **15 có `az_tb` ≈ −1882 đến −2040**, tức đầu lộn ngược: cúi gập khi nhặt đồ (806) và tư thế cúi sau khi vấp (807–809).
- 375 cú ngã nằm tới PRE_ALARM đều có `az_tb` ≥ −1074.
- Điều kiện một phía cũ `az_tb < T_TILT` coi "lộn ngược" là "nghiêng". Đổi sang hai phía (đầu lệch 45°–135° khỏi phương thẳng đứng) giữ 100 % cú ngã nằm và loại 15/22 báo giả. Đây là thay đổi theo nghĩa vật lý của "nằm", không phải chỉnh ngưỡng cho khớp dữ liệu.

**Phát lại lại với v3.1 (3 seed):**

| Mô hình | T_SCORE | Ngã nằm → PRE_ALARM | TB | Đứng dậy → PRE_ALARM | PRE_ALARM giả/giờ | TB | Trễ PRE tv / p90 |
|---|---|---|---|---|---|---|---|
| N2 | 0 | 96.7 / 96.7 / 97.2 % | 96.9 % | 0/360 | 3.40 / 3.02 / 1.13 | 2.52 | 4.08 / 5.25 s |
| N2 | 8 | 95.2 / 94.9 / 96.4 % | 95.5 % | 0/360 | 2.64 / 0.75 / 0.38 | 1.26 | 4.07 / 5.21 s |
| N2-S | 0 | 97.0 / 95.2 / 96.4 % | 96.2 % | 0/360 | 1.13 / 3.40 / 3.77 | 2.77 | 4.07 / 5.28 s |
| N2-S | 8 | 94.4 / 93.1 / 95.2 % | 94.2 % | 0/360 | 0.75 / 1.13 / 1.51 | 1.13 | 4.05 / 5.23 s |
| N2x3 (gộp) | 0 | 97.0 % | 97.0 % | 0/120 | 2.64 | 2.64 | 4.08 / 5.25 s |
| N2x3 (gộp) | 8 | 95.7 % | 95.7 % | 0/120 | 0.75 | 0.75 | 4.08 / 5.24 s |
| N2x3 (gộp) | 16 | 91.9 % | 91.9 % | 0/120 | 0.00 | 0.00 | 4.04 / 5.16 s |

**Kết luận v3.1:**
- **N2, 2/3 phiếu, T_SCORE 8:** ngã nằm → PRE_ALARM 95,5 %, đứng dậy 0/360, PRE_ALARM giả trung bình **1,26/giờ** (trước 5,91), trễ 4,07 / 5,21 s.
- **Gộp 3 seed N2, T_SCORE 8:** 95,7 %, **0,75 giả/giờ**. Đây là cấu hình đầu tiên đạt cả ≥ 95 % ngã nằm lẫn ≤ 1 giả/giờ trên sinh hoạt D1.
- Báo giả còn lại chỉ từ 815 (chủ động nằm xuống giường) và 805 (cúi gập đúng khoảng 90°). D2 `nam_xuong`, `cui_nhat` nhắm đúng hai nguồn này.
- Firmware (`safety.c`) và `safety_model.py` đã sửa và vẫn trùng nhau trên 240.000 tick ngẫu nhiên, có giá trị `az_tb` âm ở biên; thêm 2 ca test (53/53 PASS).
