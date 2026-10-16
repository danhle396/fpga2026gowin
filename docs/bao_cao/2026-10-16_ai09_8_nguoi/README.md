# 2026-10-16 — AI-09 / AI-10 trên D1 8 người (101–108)

**Cách làm:**
- Dữ liệu: [2026-10-16_d1_8_nguoi](../2026-10-16_d1_8_nguoi/README.md). 840 cú ngã, 689 bản ghi sinh hoạt; khi phát lại là 3,88 giờ.
- Huấn luyện: `ml/train_cnn.py --arch n2`, LOSO 8 lượt cộng mô hình cuối, 3 seed (20261014, 7, 99), cùng mã nguồn với các lần chạy 6 người.
- Phát lại: `tools/playback_d1.py --t-score 0 8 16 32`, SPEC v3.1, 2/3 phiếu.
- Lệnh đầy đủ: `run_ai_8.sh`. Chạy trên máy thứ hai, tách khỏi phiên Claude. Tổng hợp số bằng `tong_hop.py`.
- Mô hình ở `E:\FPGA2026_GOWIN\runs\` (ngoài repo). Repo chỉ giữ `report.txt` và các bảng phát lại. Bitstream 3 và firmware vẫn dùng `ml/out/n2_d1` (6 người).

## N2 chỉ dữ liệu đầu: mức cửa sổ và sự kiện (LOSO, INT8)

| | seed 20261014 | seed 7 | seed 99 | **TB 8 người** | TB 6 người (15/10) |
|---|---|---|---|---|---|
| Macro-F1 INT8, trung bình theo người | 0,9707 | 0,9803 | 0,9806 | **0,9772** | 0,9683 |
| Macro-F1 chỉ tính người 101–106 | 0,9676 | 0,9798 | 0,9813 | **0,9762** | 0,9683 |
| Sự kiện ngã bắt được, người 101–106 (T_SCORE 0) | 603/604 | 603/604 | 601/604 | **99,7 %** | 98,7 % |
| Recall sự kiện, T_SCORE 0 | 99,6 % | 99,9 % | 99,3 % | **99,6 %** | 98,7 % |
| Recall sự kiện, T_SCORE 8 | 97,3 % | 98,3 % | 97,4 % | **97,7 %** | 95,8 % |
| Cặp phiếu 2/3 nhầm/giờ **trước FSM**, T_SCORE 8 | 5,71 | 4,67 | 2,08 | **4,15** | 8,0 |
| FP32 → INT8 trùng nhãn | 99,98 % | 99,98 % | 99,98 % | | ≥ 99,93 % |
| Mô hình cuối: INT8 theo lô trùng `golden_model.forward` | 1000/1000 | 1000/1000 | 1000/1000 | | |

- **Tác dụng của 2 người thêm vào tập huấn luyện:** trên cùng 6 người kiểm tra (101–106), Macro-F1 tăng 0,9683 → 0,9762 (+0,008) và số cú ngã bị lọt giảm từ khoảng 8 xuống 1–3 trên 604. Đây là so sánh có cặp: cùng người kiểm tra, cùng 3 seed.
- **Người 105 vẫn yếu nhất:** Macro-F1 0,86 / 0,92 / 0,95; phiếu nhầm 23–83/giờ trước FSM. Giống lần 6 người.

## Mức hệ thống (Safety FSM v3.1)

| T_SCORE | | Ngã nằm → PRE_ALARM: 3 seed | TB | PRE_ALARM giả/giờ: 3 seed | TB | Gộp 3 seed: nằm / giả/giờ |
|---|---|---|---|---|---|---|
| 0 | 8 người | 96,9 / 96,9 / 96,9 % | 96,9 % | 1,54 / 1,54 / 1,03 | 1,37 | 96,9 % / 1,03 |
| **8** | **8 người** | 96,2 / 96,4 / 96,2 % | **96,3 %** | 0,77 / 0,77 / 0,51 | **0,68** | **95,3 % / 0,26** |
| 8 | 6 người (15/10) | 95,2 / 94,9 / 96,4 % | 95,5 % | 2,64 / 0,75 / 0,38 | 1,26 | 95,7 % / 0,75 |
| 16 | 8 người | 92,3 / 94,5 / 91,8 % | 92,9 % | 0,26 / 0,26 / 0,51 | 0,34 | 87,0 % / 0,00 |
| 32 | 8 người | 78,8 / 85,4 / 76,3 % | 80,2 % | 0 / 0 / 0 | 0 | 67,5 % / 0 |

Cả 3 seed và cả bản gộp:
- ngã có đứng dậy → PRE_ALARM: 0/166;
- ngã quỳ/ngồi → PRE_ALARM: 4,0–4,8 % (X15, giữ SPEC v3.1);
- va chạm → SUSPECT: trung vị 0,84–0,88 s, p90 1,00–1,06 s;
- va chạm → PRE_ALARM: trung vị 4,12 s, **p90 5,92 s**. Trên 6 người p90 là 5,21 s.

PRE_ALARM giả ở T_SCORE 8 chỉ còn đến từ 815 (chủ động nằm xuống giường), cộng 1 lần 805 (cúi gập) ở seed 20261014.

## Kết luận sơ bộ (chỉ trên D1 8 người, chưa đội mũ)

1. **Ở T_SCORE 8, N2 chỉ dữ liệu đầu đạt cả hai chỉ tiêu hệ thống của tầng 2 trên D1:** ngã nằm → PRE_ALARM ≥ 95 % (TB 96,3 %, seed thấp nhất 96,2 %) và ≤ 1 PRE_ALARM giả/giờ (TB 0,68, seed cao nhất 0,77). Với 6 người, trung bình báo giả là 1,26/giờ, chưa đạt.
2. **Số mẫu báo giả rất nhỏ:** 2–3 lần trong 3,88 giờ. Một hay hai lần chênh là đổi kết luận. Chỉ tiêu ≤ 1/giờ vẫn phải xác nhận trên mũ (D2, TH-10).
3. **Thời gian tới PRE_ALARM:** trung vị đạt (4,12 s ≤ 5 s), p90 thì không (5,92 s). DE_CUONG_v2 (bảng chỉ tiêu) ghi "→ PRE-ALARM ≤ 5 s **khi người nằm yên trong 2 s sau va chạm**". Phép phát lại này chưa lọc theo điều kiện đó, nên p90 có thể gồm cả những cú ngã mà người còn cử động lâu hơn 2 s. Việc tiếp theo: tính lại độ trễ chỉ trên các cú ngã có khối bất động đầu tiên trong vòng 2 s sau va chạm. Nếu vẫn vượt 5 s thì xem lại `STILL_BLOCKS` (8 khối = 2,56 s bất động). Ghi thành rủi ro, chưa đổi SPEC.
4. **Tái lập giữa hai máy:** huấn luyện lại `n2_d1` (6 người, seed 20261014) trên máy thứ hai cho Macro-F1 0,9591 so với 0,9584, recall T8 95,5 % so với 95,7 %, phiếu nhầm 11,42 so với 11,04/giờ (`repro_n2_d1_may2.log`). Chênh lệch do khác máy (≈ 0,001) nhỏ hơn nhiều so với chênh lệch giữa các seed (0,958–0,977).

## N2 + dữ liệu thân (ngực, thắt lưng chỉ để huấn luyện)

Đang chạy (`n2t_8_s*`, bắt đầu 16/10 08:59). Kết quả sẽ thêm vào đây.
