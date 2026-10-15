# 2026-10-15 — AI-11 sơ bộ: bảng FP32 / INT8 / RTL trên D1

**Chưa phải Pass của AI-11.** Pass cần mô hình cuối huấn luyện trên D1 + D2 + D3 (cổng G6). Bảng này gom số đã có để: (1) thấy ngay mắt xích nào làm mất độ chính xác; (2) có sẵn khung bảng cho báo cáo TH-11, khi có D2/D3 chỉ cần thay số.

Nguồn số liệu, không chạy lại:
- LOSO 6 người D1: `docs/bao_cao/2026-10-14_ai04_ai09/loso_n2.txt`, `loso_n2s.txt`, `nhieu_seed/*.log` (seed 20261014, 7, 99).
- Phát lại qua Safety FSM v3.1: `docs/bao_cao/2026-10-14_ai10_playback/v31/`.
- RTL: `docs/bao_cao/2026-10-14_rb03_rb04_e2/`, `2026-10-15_cosim_fw_rtl/`, `2026-10-15_verify_sau_don/`.

## 1. FP32 → INT8 (LOSO, mức cửa sổ)

| Mô hình | Seed | Macro-F1 FP32 | Macro-F1 INT8 | Giảm (điểm %) | Trùng nhãn FP32 / INT8 |
|---|---|---|---|---|---|
| N2 [16,16,32] | 20261014 | 0,9599 | 0,9584 | 0,15 | 99,93 % |
| N2 | 7 | 0,9703 | 0,9691 | 0,12 | 99,96 % |
| N2 | 99 | 0,9767 | 0,9774 | −0,07 | 99,98 % |
| N2-S [8,16,16] | 20261014 | 0,9750 | 0,9747 | 0,03 | 99,98 % |
| N2-S | 7 | 0,9159 | 0,9157 | 0,02 | 99,94 % |
| N2-S | 99 | 0,9466 | 0,9452 | 0,14 | 99,91 % |

Lượng tử PTQ (shift lũy thừa 2, A.5) làm giảm nhiều nhất 0,15 điểm %, trong khi chỉ tiêu AI-09 cho phép 2 điểm. **Độ lệch giữa các seed (đến 6 điểm ở N2-S) lớn hơn 40 lần độ lệch do lượng tử.** Vì vậy chưa cần QAT. Việc cần làm là ổn định huấn luyện.

## 2. INT8 → RTL

| Phép kiểm | Số cửa sổ | Sai lệch (lớp, SCORE, 4 logit) |
|---|---|---|
| `tb_e2`, E2 P = 1/2/4, N2 / N2-S / N2-L / N1, so **từng tầng** với golden | 50 mỗi cấu hình × 14 cấu hình | 0 |
| `tb_cnn_core_golden` + `tb_e1_layers`, E1 (`cnn_core` của nhóm), weight SisFall | 50 | 0 |
| Mô phỏng ghép firmware → RTL (qua chân SPI) → firmware, N2 và N2-S, dữ liệu ngã thật | 423 mỗi mô hình | 0 |
| `tb_proto` v3 qua chân SPI, E1 và E2 | 50 (E1), 20 (E2 N2) | 0 |
| Netlist sau P&R của Gowin (bitstream 3, E2 + N2), `tb_proto` gate-level | 3 + 7 kịch bản | 0 (phép âm lật 1 bit weight → FAIL) |

RTL tính **trùng từng bit** với golden INT8, nên cột RTL trong mọi bảng dưới đây **bằng đúng** cột INT8. Trên chip thật thì chưa đo: TH-07 (≥ 500 cửa sổ) và TH-09 (≥ 2.000 cửa sổ) cần board.

## 3. Ma trận nhầm lẫn INT8 (LOSO, mức cửa sổ, cộng 3 seed)

Hàng là nhãn thật, cột là nhãn dự đoán. D1 không có lớp IMPACT, nên các lớp 1 và 2 trống và không ghi ở đây.

**N2:**

| thật \ đoán | NORMAL | FALL |
|---|---|---|
| NORMAL | 153.361 | 698 |
| FALL | 111 | 5.325 |

Recall cửa sổ FALL 97,96 %, precision 88,41 %, tỉ lệ cửa sổ NORMAL bị gọi FALL 0,453 %. Từng seed: 0,693 / 0,417 / 0,249 %.

**N2-S:**

| thật \ đoán | NORMAL | FALL |
|---|---|---|
| NORMAL | 151.525 | 2.534 |
| FALL | 141 | 5.295 |

Recall 97,41 %, precision 67,63 %, cửa sổ NORMAL bị gọi FALL 1,645 %. Từng seed: 0,275 / **3,673** / 0,987 %. Seed 7 tệ gấp 13 lần seed tốt nhất.

## 4. Mức sự kiện và mức hệ thống

| Mô hình | Recall sự kiện (≥ 2/3 cửa sổ), T_SCORE 0 | T_SCORE 8 | Ngã nằm → PRE_ALARM (FSM v3.1, T_SCORE 8) | Ngã có đứng dậy → PRE_ALARM | PRE_ALARM giả/giờ trên 2,65 giờ sinh hoạt |
|---|---|---|---|---|---|
| N2, 3 seed | 98,8 / 99,0 / 98,3 % | 95,7 / 94,7 / 96,9 % | 95,5 % (TB) | 0/360 | 1,26 (TB; 2,64 / 0,75 / 0,38) |
| N2-S, 3 seed | 98,7 / 98,8 / 98,2 % | 95,4 / 95,9 / 95,9 % | 94,2 % (TB) | 0/360 | 1,13 (TB) |
| Gộp 3 seed N2 | — | — | **95,7 %** | 0/120 | **0,75** |

Chỉ tiêu tham chiếu: AI-10 cần ≥ 95 % ngã nằm tới PRE_ALARM (đề nghị sửa Pass theo X15); TH-10 cần ≤ 1 báo giả/giờ.

## Nhận xét cho báo cáo cuối

1. **Chuỗi FP32 → INT8 → RTL gần như không mất gì:** lượng tử mất ≤ 0,15 điểm; RTL mất 0. Sai số còn lại hoàn toàn nằm ở mô hình và dữ liệu.
2. **Safety FSM gánh phần lớn việc chống báo giả:**
   - Trước FSM: N2 tạo 5,3–11 lần/giờ cặp 2/3 phiếu nhầm (T_SCORE 8).
   - Sau FSM v3.1: còn 0,38–2,64 lần/giờ.
3. **Phương sai theo seed là rủi ro chính:**
   - Khi có D2/D3, phải báo trung bình ± độ lệch trên ≥ 3 seed.
   - Có thể gộp mô hình (E2 P = 4 chạy 3 mô hình vẫn < 5 ms).
4. Thêm dữ liệu ngực + thắt lưng chỉ để huấn luyện: ngã nằm 96,4 %, PRE_ALARM giả 0,88/giờ (gộp 3 seed 96,2 % / 0,38), xem [`2026-10-15_ai09_du_lieu_than/`](../2026-10-15_ai09_du_lieu_than/README.md). Bảng này giữ N2 chỉ đầu, đúng mô hình đang có trong bitstream 3.
5. Số ở đây tính trên D1 (cảm biến buộc ở đầu, 25 Hz nội suy lên 50 Hz). Số trên mũ thật có thể khác (AI-14).
