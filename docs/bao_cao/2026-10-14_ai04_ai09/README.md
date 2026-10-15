# 2026-10-14 — AI-04 (`export_mem.py`) và AI-09 (so N1 / N2 / N2-S / N2-L trên D1)

## AI-04: `tools/export_mem.py`

| Lần xuất | Kết quả (`export_*.txt`) |
|---|---|
| E1, weight SisFall của nhóm | `weights.mem`, `bias.mem` **trùng từng byte** file của nhóm. 50 vector: 10 FALL + 10 NORMAL của D1, LFSR, toàn +127 / −128 / 0, xen kẽ, bậc thang, gyro bão hòa, ngẫu nhiên. Đọc ngược khớp golden 50/50; biên \|acc\| [172.430, 295.566, 140.083] |
| E2, N2-S, P = 1 và 4 | đọc ngược 50/50; mô hình địa chỉ E2 trên ROM đã xuất == golden; biên \|acc\| [75.399, 120.158, 276.571, 1.073.741.824 (bias −2^30 của lớp dự trữ)] |
| RTL E1 chạy 50 vector của lần xuất E1 (`tb_cnn_core_50vec_e1_sisfall.log`) | **50/50 khớp golden**, 699.800 chu kỳ mỗi lần → đóng R9 cho E1 |

`tb_cnn_core_golden.v` nhận thêm macro `TB_NV` (mặc định 20, như cũ) để chạy được 50 vector.

## AI-09: LOSO 6 người của D1, INT8, cùng seed và 30 epoch (`loso_*.txt`)

| Mô hình | Weight | MAC | Macro-F1 INT8 (FP32) | Recall sự kiện, T_SCORE = 0 | Phiếu 2/3 nhầm/giờ | Recall, T_SCORE = 8 | Phiếu nhầm/giờ |
|---|---|---|---|---|---|---|---|
| N1 | 3.168 | 225.408 | 0,861 (0,860) | 515/604 = 85,3 % | 20,6 | 82,3 % | 13,3 |
| N2 | 6.368 | 227.328 | 0,958 (0,960) | 597/604 = 98,8 % | 24,4 | 95,7 % | 11,0 |
| **N2-S** | **3.184** | **113.664** | **0,975 (0,975)** | **596/604 = 98,7 %** | 12,6 | 95,4 % | 6,1 |
| N2-L | 8.288 | 309.248 | 0,976 (0,978) | 592/604 = 98,0 % | 9,5 | 94,9 % | 6,1 |

- "Phiếu nhầm" là số lần đạt 2/3 phiếu FALL trên 2,63 giờ bản ghi sinh hoạt của D1, **trước** Safety FSM.
- FP32 → INT8 trùng nhãn 99,77–99,98 % ở mọi mô hình; Macro-F1 không giảm. Chỉ tiêu "FP32 → INT8 giảm ≤ 2 điểm" đạt mà chưa cần QAT.
- INT8 theo lô trùng `golden_model.forward` từng bit, 1.000/1.000 cửa sổ ở mỗi mô hình.

**Chọn sơ bộ: N2-S.** Đây là mô hình nhỏ nhất đạt cả recall ≥ 95 % lẫn Macro-F1 ≥ 0,90 trong LOSO trên D1. Nó có ít weight ngang N1 và chỉ cần một nửa số MAC, nên E2 chạy N2-S nhanh hơn N1.

Pass của AI-09 còn ba điều kiện chưa có: D2 (lớp IMPACT, NORMAL khi đội mũ), ≥ 40 cú ngã D3 trên mũ (recall ≥ 90 %), và quy tắc "dữ liệu thân người chỉ giữ nếu không tăng báo nhầm".

Hai giới hạn khác:
- Mới có một seed. Chênh lệch giữa N2, N2-S và N2-L (dưới 2 điểm) có thể chỉ là nhiễu.
- Mới có 6/17 người của D1.

## Bổ sung 15/10: lặp lại với 2 seed nữa (`nhieu_seed/`)

| Mô hình | Macro-F1 INT8, seed 20261014 / 7 / 99 | Trung bình | Recall sự kiện TB (T = 0) | Phiếu nhầm/giờ TB, T = 0 | Recall TB, T = 8 | Phiếu nhầm/giờ TB, T = 8 |
|---|---|---|---|---|---|---|
| N2-S | 0,975 / 0,916 / 0,945 | 0,945 | 98,6 % | 25,0 | 95,7 % | 21,2 |
| **N2** | 0,958 / 0,969 / 0,977 | **0,968** | 98,7 % | 16,7 | 95,8 % | **8,0** |
| N2-L | 0,976 / 0,960 / 0,941 | 0,959 | 98,3 % | 26,3 | 95,3 % | 6,5 |

**Sửa kết luận:**
- Chênh lệch do seed (Macro-F1 lệch tới 0,06; phiếu nhầm lệch gấp 3) lớn hơn chênh lệch giữa ba mô hình. Kết quả N2-S ở bảng trên là một seed may.
- Tính trung bình 3 seed, cả ba đều đạt recall ≥ 95 % và Macro-F1 ≥ 0,90. **N2 ổn định nhất** (Macro-F1 0,958–0,977) và báo nhầm ít hơn N2-S rõ rệt ở T_SCORE 8.
- **Chọn sơ bộ đổi thành N2**, giữ N2-S làm phương án nhỏ. Cả hai chạy trên cùng engine E2: N2 5,15 ms với P = 1, 1,50 ms với P = 4.
- Số phát lại qua FSM ở `2026-10-14_ai10_playback/` dùng N2-S seed 20261014, nên lạc quan về báo giả.
- Cần D2/D3 và nhiều seed (hoặc gộp nhiều lần huấn luyện) mới chốt được. Với 6 người, đánh giá còn rất nhiễu.
