# 2026-10-16 — D1: từ 8 lên 11 người (thêm 109, 110, 203), chỉ dữ liệu đầu

Từ 16/10 nhóm quyết định **chỉ dùng dữ liệu vùng đầu** (cảm biến 340540) để huấn luyện và kiểm tra. File ngực và thắt lưng trong `ml/data/public/` giữ nguyên bản 8 người để đối chiếu với AI-09, không dùng nữa.

## Lấy dữ liệu

- Một lượt tải UCI giữ được kết nối khoảng 87 phút, đạt 840 MB trước khi bị cắt (09:38).
- `tools/fetch_d1.sh` giải trọn 101–110 và 203; 204 bị cắt cụt nên bỏ.
- Mã người của bộ dữ liệu không liền nhau: sau 110 là 203. Bộ có 17 người theo tài liệu đi kèm; danh sách mã đầy đủ **[CẦN XÁC MINH]**, khi tải trọn sẽ biết.

## Kiểm tra

1. **8 người cũ trùng từng byte.** Phần 101–108 của `d1_windows.npz` (X, y, subject, act, p) và `d1_trials_50hz.npz` trùng bản trước, nên mô hình và số liệu 8 người vẫn đúng.
2. **Vị trí cảm biến đầu.** 109 và 110 nằm trong khoảng của 8 người cũ: gyro khi đi bộ 0,35 / 0,27 rad/s, nghiêng khi cúi 105° / 89°, Δp khi ngã +0,091 / +0,084 hPa.
3. **Người 203 lệch ở 2/3 dấu hiệu** (gyro khi đi bộ 0,63 rad/s, nghiêng khi cúi 57°), nhưng dấu hiệu chắc nhất về vật lý thì rõ. So 6 cảm biến của **chính người 203**:

   | Cảm biến | Gyro đi bộ (rad/s) | Nghiêng khi cúi | Δp khi ngã (hPa) |
   |---|---|---|---|
   | **340540 (đầu)** | 0,63 | 57° | **+0,081 (lớn nhất, tức ở cao nhất)** |
   | 340539 (ngực) | 0,39 | 94° | +0,069 |
   | 340535 (thắt lưng) | 0,32 | 72° | +0,054 |
   | 340537 | 1,10 | 44° | +0,047 |
   | 340527 | 0,82 | 11° | +0,030 |
   | 340506 (cổ chân) | 1,78 | 20° | −0,010 |

   Thứ tự Δp đúng thứ tự độ cao đầu > ngực > thắt lưng > … > cổ chân, như ở mọi người khác. Kết luận: 340540 vẫn là đầu. Người này cúi bằng thân, ít cúi đầu (ngực 94°, đầu 57°) và cử động đầu nhiều hơn khi đi. Giữ 203 trong dữ liệu.
4. 1.179/1.180 cú ngã có đủ 3 cửa sổ dương. Cú còn lại có bản ghi ngắn (bản ghi ngắn nhất 2,6 s).

## Bộ dữ liệu đầu mới (`ml/data/public/d1_windows.npz`, `d1_trials_50hz.npz`)

| | 8 người | **11 người** |
|---|---|---|
| Bản ghi | 1.529 = 840 ngã + 689 sinh hoạt | **2.141 = 1.180 ngã + 961 sinh hoạt** |
| Thời lượng | 8,31 giờ | **11,57 giờ** |
| Cửa sổ | 79.111 (FALL 2.520) | **109.970 (FALL 3.537)** |
| Mẫu vượt 7,94 g / 496 °/s | 0,0029 % / 0,038 % | 0,0027 % / 0,046 % |

Báo cáo đủ 6 cảm biến của 11 người: `d1_report_<mã>.txt`.

## Sửa công cụ đi kèm

`tools/playback_d1.py`, `tools/spectrum_check.py` và `tre_nam_yen_2s.py` nạp file `.npz` một lần vào bộ nhớ (`dict(np.load(...))`).

Trước đây mỗi lần truy cập `D["data"]` lại giải nén cả mảng 12 MB. Hậu quả:
- một lượt phát lại mất 15–20 phút; giờ còn 80 s, kết quả trùng từng dòng;
- lượt phát lại của N2 + dữ liệu thân bị `EOFError`, vì file dữ liệu bị chép đè khi đang đọc.
