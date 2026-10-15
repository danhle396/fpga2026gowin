# 2026-10-14 — AI-07 (phần chuẩn bị): N1 huấn luyện trên D1, xuất INT8, chạy trên RTL

Notebook Colab gốc của nhóm AI vẫn chưa có, nên tôi viết lại chuỗi huấn luyện. Máy không có TensorFlow, và N1 chỉ có 3.168 weight, nên viết bằng numpy thuần: `ml/src/n1_numpy.py` (mạng, lan truyền ngược, Adam, lượng tử, suy luận số nguyên theo lô) và `ml/train_n1.py` (LOSO, đánh giá, xuất). Chạy được trên máy nhóm và trên Colab.

- Gradient giải tích khớp sai phân hữu hạn, sai tương đối ≤ 3·10⁻⁷.
- Lệnh: `python ml/train_n1.py` (30 epoch, seed 20261014; 520 s trên máy nhóm, khi CPU đang chia cho việc khác).
- Dữ liệu: `ml/data/public/d1_windows.npz`, 6 người, 53.165 cửa sổ (1.812 FALL). Chưa có D2, nên **chưa có lớp IMPACT**.
- Lượng tử: sau huấn luyện (PTQ). Thang kích hoạt lấy theo phân vị 99,99 %; shift là lũy thừa 2; bias cộng sẵn 2^(n−1) để requant làm tròn (A.5); bù phần lấy sàn của GAP vào bias Dense. Lớp 2: weight 0, bias −2^30.

## Kết quả LOSO (`train_n1_report.txt`)

Huấn luyện trên 5 người, thử trên người thứ 6, lặp 6 lần. Số là của mô hình INT8 đúng như sẽ chạy trên FPGA. `T_SCORE = 0`.

| Chỉ số | Giá trị | Chỉ tiêu tầng 2 (để so) |
|---|---|---|
| Recall FALL mức sự kiện (≥ 2/3 cửa sổ dương báo FALL) | **515/604 = 85,3 %** (theo người: 75,0–99,0 %) | ≥ 95 % |
| Macro-F1 mức cửa sổ (NORMAL, FALL), trung bình 6 lượt | 0,861 (FP32 0,860) | ≥ 0,90 |
| Accuracy mức cửa sổ | 97,9 % | — |
| Số lần đạt 2/3 phiếu FALL trên bản ghi sinh hoạt, **trước Safety FSM** | 54 lần / 2,63 giờ = 20,6 lần/giờ | ≤ 1 báo giả/giờ **sau** FSM |
| FP32 → INT8 trùng nhãn | 99,77 % | FP32 → INT8 giảm ≤ 2 điểm: giảm 0 |

Ma trận nhầm lẫn INT8 cộng 6 lượt (hàng = thật, cột = dự đoán): NORMAL → NORMAL 50.490, NORMAL → FALL 863; FALL → NORMAL 282, FALL → FALL 1.530.

Đọc số này thế nào:
- Đây là N1 (GAP xóa thứ tự thời gian), chỉ 6 người, chưa có D2 và chưa tinh chỉnh. Nó là mốc tầng 1, không phải con số cam kết.
- Số phiếu nhầm trên sinh hoạt chưa qua bộ lọc "bất động ≥ 2,56 s + đầu nghiêng > 45°" của FSM. AI-10 sẽ phát lại cả chuỗi qua FSM để có số báo giả thật.

## Kiểm từng bit

- `int_forward` theo lô (dùng để tính mọi số ở trên) trùng `golden_model.forward` ở lớp, SCORE và 4 logit trên 2.000/2.000 cửa sổ ngẫu nhiên.
- Thư mục xuất `ml/out/n1_d1/fpga_export/` cùng định dạng với thư mục xuất của nhóm AI. `bash rtl/tb/run_all.sh --export ml/out/n1_d1/fpga_export` cho kết quả:
  - `tb_cnn_core_golden` 20/20, gồm 10 cửa sổ FALL và 10 NORMAL (bộ vector cũ toàn NORMAL, R9), 699.800 chu kỳ;
  - `tb_top_spi` PASS.
  - Log: `tb_cnn_core_golden_n1_d1.log`, `tb_top_spi_n1_d1.log`.
- `quant_params.json`: `conv1_shift` 8, `conv2_shift` 8, `score_shift` 5. Riêng lượt LOSO thử người 106 tự chọn được (7, 8).

## Chưa làm

Huấn luyện có mô phỏng lượng tử (QAT, để dành cho N2 ở AI-09); thêm D2 (`--extra`); chốt `T_SCORE`. Bitstream của nhóm vẫn dùng weight SisFall; đổi sang weight này là quyết định của nhóm (RA-06).
