# D1 — dữ liệu công khai, cảm biến ở đầu

Nguồn huấn luyện lớp FALL và NORMAL của đề tài (mục 4.4 và việc AI-13 trong [PROJECT_MASTER.md](../../../PROJECT_MASTER.md)).

## Nguồn gốc

- Bộ "Simulated Falls and Daily Living Activities Data Set", A. T. Özdemir và B. Barshan, UCI Machine Learning Repository, số 455, DOI 10.24432/C52028. Giấy phép CC BY 4.0: dùng được, phải ghi nguồn.
- Bài báo phải trích: A. T. Özdemir, B. Barshan, "Detecting Falls with Wearable Sensors Using Machine Learning Techniques," *Sensors*, 14(6), 10691–10708, 2014.
- Tài liệu gốc đi kèm: [Information.pdf](Information.pdf).
- Cảm biến Xsens MTw, 25 Hz, gia tốc tính bằng m/s² (có trọng lực), gyro tính bằng rad/s. Mỗi lần thực hiện ghi đồng thời 6 cảm biến.

## Hiện có gì (16/10/2026)

**8 trên 17 người** (101–108): 1.529 bản ghi = 840 cú ngã (20 kiểu, mỗi kiểu 41–45 lần) + 689 hoạt động thường ngày (16 loại), tổng 8,31 giờ. Ngày 13/10 có 6 người (101–106); phần 6 người đó trong các file hiện tại trùng từng byte với bản cũ ([2026-10-16_d1_8_nguoi](../../../docs/bao_cao/2026-10-16_d1_8_nguoi/README.md)).

9 người còn lại (109–117) chưa có. File gốc nặng 1,24 GB. Máy chủ UCI không nhận `Range`, giới hạn mỗi kết nối khoảng 0,4–0,6 MB/s và cắt kết nối sau 16–25 phút, nên mỗi lượt chỉ lấy được 477–643 MB đầu. Bản sao trên Kaggle thiếu nhiều file, không dùng được. Cách lấy phần còn lại: tải trọn file zip (cần một kết nối giữ được khoảng 35–50 phút, hoặc mạng nhanh hơn), rồi chạy `bash tools/fetch_d1.sh <thư mục ngoài repo> <file zip>` và các lệnh ở cuối file này. Script giải được cả từ file zip tải dở.

| File | Nội dung |
|---|---|
| `d1_trials_50hz.npz` | Từng bản ghi đầy đủ ở 50 Hz, INT16 theo LSB của MPU6050 ở ±16 g / ±2000 °/s (2048 LSB/g, 16,4 LSB/(°/s)), trục đã xoay về quy ước của mũ. `data[start[i] : start[i] + length[i]]` là bản ghi thứ `i`; `subject`, `act` (801–816 thường ngày, 901–920 ngã), `rep`, `event` (chỉ số mẫu của điểm va chạm, −1 nếu không phải ngã), `flags` (1 = có khoảng trống đã nội suy, 2 = có mẫu ngoài dải đã bỏ) |
| `d1_windows.npz` | 79.111 cửa sổ 128 × 6 INT8, bước 16 mẫu, nhãn theo A.4: `y` = 0 (NORMAL, 76.591 cửa sổ) hoặc 3 (FALL, 2.520 cửa sổ = 840 cú ngã × 3). Kèm `subject`, `act`, `trial`, `p` (vị trí điểm va chạm trong cửa sổ, −1 nếu không có). Cửa sổ thuộc vùng bỏ của A.4 đã được loại |
| `d1_windows_nguc_340539.npz`, `d1_windows_that_lung_340535.npz` | Cùng định dạng với `d1_windows.npz`, lấy từ cảm biến ở **ngực** và **thắt lưng** của cùng các lần thực hiện (thêm 15/10). Chỉ dùng làm dữ liệu huấn luyện bổ sung: `ml/train_cnn.py --train-only <hai file>`. Không bao giờ dùng để kiểm tra, vì thiết bị đeo trên đầu. Kết quả AI-09: `docs/bao_cao/2026-10-15_ai09_du_lieu_than/` |

Thứ tự kênh: `[AX, AY, AZ, GX, GY, GZ]`; X hướng về trước, Y sang trái, Z lên trời. Đứng yên thì AZ ≈ +16 mức INT8.

## Ba điều phải biết trước khi dùng

1. **Mã cảm biến ở đầu là 340540, không phải 340506 như `Information.pdf` ghi.** Số liệu của cả 8 người cho thấy danh sách trong tài liệu bị ngược thứ tự:

   | Dấu hiệu | 340506 (tài liệu ghi "đầu") | 340540 (tài liệu ghi "cổ chân") |
   |---|---|---|
   | Tốc độ quay hiệu dụng khi đi bộ | 1,63–2,20 rad/s | 0,16–0,39 rad/s |
   | Góc nghiêng lớn nhất khi cúi 90° | 13–19° | 71–106° |
   | Đổi áp suất khi ngã (cao xuống thấp) | ≈ 0 hPa | +0,084 đến +0,089 hPa, lớn nhất trong 6 cảm biến |

   Kết luận này dựa trên số liệu, chưa có xác nhận độc lập (Hình 1 của bài báo, hoặc hỏi tác giả). Bảng kiểm của từng người nằm trong `docs/bao_cao/2026-10-13_d1_dau/`.
2. **Chỉ có 25 Hz.** Mẫu 50 Hz ở đây là mẫu gốc xen với mẫu nội suy `(−1, 9, 9, −1)/16`, nên phần phổ 12,5–25 Hz gần như trống, trong khi dữ liệu thu trên mũ có đủ tới 25 Hz. Việc AI-14 đo ảnh hưởng của điều này.
3. **Không có lớp IMPACT** (rơi mũ, va mũ, tháo và đội). Lớp đó nhóm phải tự thu (nguồn D2). Cảm biến ở đây buộc vào đầu chứ không nằm trên vỏ mũ.

Khi tách tập huấn luyện và kiểm tra, tách theo `subject`, không tách ngẫu nhiên theo cửa sổ: các cửa sổ liền nhau trùng nhau 87,5 %.

## Tạo lại

```
python -I tools/convert_d1.py --src <thư mục chứa 101, 102, ...> --out ml/data/public
python tools/plot_d1.py ml/data/public/d1_trials_50hz.npz docs/bao_cao/<thư mục>
```

`--sensor 340539` lấy kênh ngực, `--sensor 340535` lấy kênh thắt lưng (dùng làm nguồn bổ sung; xem `docs/bao_cao/2026-10-13_d1_dau/so_sanh_dau_nguc_that_lung.txt`). Hai file `d1_windows_nguc_340539.npz` / `d1_windows_that_lung_340535.npz` là `d1_windows.npz` của lệnh đó, đổi tên.
