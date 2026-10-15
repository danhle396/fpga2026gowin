# 2026-10-16 — D1: từ 6 lên 8 người (thêm 107, 108)

## Lấy dữ liệu

- Nguồn: UCI #455, gói zip 1,24 GB. Chỉ có một mục `Tests.rar`, lưu nguyên (method 0); mỗi người là một file `Tests/<mã>.rar` (57–73 MB).
- Máy chủ UCI giới hạn tốc độ từng kết nối ở khoảng 0,4–0,6 MB/s, không nhận `Range`, và cắt kết nối sau một lúc:
  - lượt 15/10: 643 MB sau 25 phút, dừng vì phiên Claude kết thúc;
  - lượt 16/10: 572 MB sau 16 phút, `server closed abruptly`.
- Đường dẫn cũ `ml/machine-learning-databases/00455/Tests.rar` cũng không nhận Range, khoảng 0,26 MB/s.
- Đường mạng của máy không phải nút cổ chai: bản sao Kaggle tải được ở 6,8 MB/s.
- Từ file 643 MB, [tools/fetch_d1.sh](../../../tools/fetch_d1.sh) giải được trọn **101–108**; 109 bị cắt cụt nên bỏ.

**Bản sao Kaggle (`eblerim/simulated-falls-and-daily-living-activities`, 764 MB, tải không cần đăng nhập) không dùng được:**
- chỉ có 6.370 file của 10 người (101–110);
- thiếu rất nhiều: ví dụ người 101 chỉ có 42 file cảm biến 340540, trong khi UCI có 197 bản ghi; người 103 có 14 file.

## Kiểm tra

1. **6 người cũ trùng từng byte.** `convert_d1.py` chạy trên 8 người. Phần 101–106 của cả 3 file cửa sổ (đầu 340540, ngực 340539, thắt lưng 340535) trùng từng phần tử `X, y, subject, act, p` với bản cũ trong repo; `d1_trials_50hz.npz` cũng vậy. Các mô hình, `loso.npz` và báo cáo đã có vẫn đúng cho phần dữ liệu đó.
2. **Mã cảm biến đầu 340540 cũng đúng với 107 và 108**, đủ ba dấu hiệu như 6 người cũ:

   | Người | 340540 (đầu): gyro đi bộ / nghiêng khi cúi / Δp khi ngã | 340506 (tài liệu ghi "đầu"): cùng ba số |
   |---|---|---|
   | 107 | 0,28 rad/s / 82° / +0,080 hPa | 1,77 rad/s / 16° / −0,007 hPa |
   | 108 | 0,31 rad/s / 110° / +0,099 hPa | 1,69 rad/s / 6° / +0,005 hPa |
   | 101–106 (cũ) | 0,16–0,39 / 71–106° / +0,084…+0,089 | 1,63–2,20 / 13–19° / ≈ 0 |

   Kênh Z khi đi bộ: 15,3 mức với cả hai người (yêu cầu 16 ± 2). Báo cáo đầy đủ: `d1_report_340540.txt`, `d1_report_340506_tai_lieu_ghi_la_dau.txt`.
3. `tools/m0_test.py` TẤT CẢ PASS với dữ liệu mới (bộ test chọn cửa sổ ngẫu nhiên trên toàn bộ file). `tools/playback_d1.py` (đã sửa 16/10 để chỉ phát lại người có lượt LOSO) cho mô hình 6 người ra đúng bảng cũ, thêm dòng "bỏ 2 người … [107, 108]".

## Bộ dữ liệu mới (`ml/data/public/`)

| | 6 người (13/10) | **8 người (16/10)** |
|---|---|---|
| Bản ghi (đầu) | 1.103 = 604 ngã + 499 sinh hoạt | **1.529 = 840 ngã + 689 sinh hoạt** |
| Thời lượng | 5,65 giờ | **8,31 giờ** |
| Cửa sổ đầu | 53.165 (FALL 1.812) | **79.111 (FALL 2.520)** |
| Cửa sổ ngực / thắt lưng | 53.172 / 53.131 | 79.124 / 79.085 |
| Cú ngã có đủ 3 cửa sổ dương | 604/604 | 840/840 |
| Mẫu vượt 7,94 g / 496 °/s | 0,003 % / 0,05 % | 0,0029 % / 0,038 % |

Mọi số AI-09, AI-10, AI-11 ghi trước 16/10 vẫn là số **trên 6 người**. Lượt LOSO trên 8 người đang chạy.

## Còn lại (AI-13)

Còn 9 người (109–117). Cách lấy:
- cần một kết nối tới UCI giữ được khoảng 35–50 phút; hoặc
- tải bằng trình duyệt hay trình quản lý tải ở mạng khác, rồi chạy `bash tools/fetch_d1.sh <thư mục> <file zip>`.
