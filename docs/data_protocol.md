# Quy trình thu dữ liệu trên mũ — D2 và D3 (việc AI-05, AI-08, TH-06)

Theo chiến lược dữ liệu ở mục 4.4 của `PROJECT_MASTER.md`:
- **D2** = va đập mũ (lớp IMPACT) + sinh hoạt khi đội mũ (NORMAL); không ai phải ngã.
- **D3** = ngã thật trên đệm khi đội mũ; **chỉ để kiểm tra**, không đưa vào huấn luyện.

## 1. An toàn và đồng ý (TH-06) — bắt buộc trước buổi D3

- Đệm dày ≥ 10 cm, rộng ít nhất 2 × 2 m, đặt trên sàn phẳng; dọn vật cứng trong bán kính 1,5 m.
- Người ngã đội mũ bảo hộ cài quai, mặc đồ dài, có bảo vệ khuỷu tay và đầu gối.
- Luôn có **một người đứng cạnh đệm** sẵn sàng đỡ; ngã chậm, có kiểm soát; không ngã từ trên cao, không ngã đầu xuống trước.
- Người tham gia ký giấy đồng ý: mục đích, rủi ro, quyền dừng bất cứ lúc nào, dữ liệu chỉ dùng cho đề tài và được ẩn danh (mã `s01`, `s02`…). Người có bệnh về cột sống, tim mạch hoặc đang đau không tham gia.
- Dừng buổi thu ngay khi có ai đau hoặc chóng mặt.

## 2. Thiết bị và kiểm tra trước mỗi buổi

1. Cảm biến gắn trên mũ theo A.1: Z hướng lên trời, X hướng về trước khi đội và đứng thẳng; đệm xốp mỏng; cố định chắc (TH-04).
2. Firmware chính, chế độ LOG: giữ SW6 lúc khởi động, hoặc gửi `LOG`. Để mũ đứng yên 3 s lúc khởi động cho hiệu chuẩn gyro.
3. Ghi bằng `tools/logger.py`. Mỗi file kết thúc phải in `mất 0 mẫu -> PASS`; file có mất mẫu thì **thu lại**.
4. Quay video toàn bộ buổi; mở đầu mỗi file bằng câu đọc to "<người> <hoạt động> lần <n>" để khớp video với file.
5. Kiểm nhanh: đội mũ đứng yên 5 s thì cột `az` ≈ +2048 (±10 %).

## 3. Đặt tên file

```
python tools/logger.py --port COMx --subject <người> --activity <hoạt động> --trial <n>
→ ml/data/raw/<người>_<hoạt động>_<nn>.csv        (<nn> = số lần, hai chữ số: 01, 02, …)
```
- `<người>` là `s01`, `s02`… Riêng **`h0`** dành cho va đập khi *không* đội mũ: một người thu hàng loạt, chỉ dùng để huấn luyện. **`s00`** chỉ dùng cho file thử trên bàn ở đợt B (B5); `windowing.py` bỏ qua mọi file `s00_*`.
- `<hoạt động>` phải nằm trong bảng dưới; `tools/windowing.py` từ chối tên lạ.

| `<hoạt động>` | Nguồn | Lớp | Mô tả | Nút đánh dấu SW6 |
|---|---|---|---|---|
| `roi_mu` | D2, h0 | IMPACT | thả mũ rơi từ 1–1,5 m xuống sàn | bấm giữ quanh mỗi lần rơi |
| `dat_manh` | D2, h0 | IMPACT | đặt mạnh mũ xuống bàn hoặc sàn | như trên |
| `va_mu` | D2 | IMPACT | đang đội, va mũ vào vật (cửa, khung) ở tốc độ đi bộ | như trên |
| `go_mu` | D2 | IMPACT | đang đội, gõ mạnh lên mũ bằng tay hoặc vật mềm | như trên |
| `thao_doi` | D2 | IMPACT | tháo mũ ra rồi đội lại | như trên |
| `di_bo` | D2 | NORMAL | đi bộ, rẽ, đi nhanh | không |
| `cau_thang` | D2 | NORMAL | lên xuống cầu thang | không |
| `cui_nhat` | D2 | NORMAL | cúi nhặt đồ dưới sàn, đứng lên | không |
| `ngoi_dung` | D2 | NORMAL | ngồi xuống ghế, đứng lên | không |
| `nam_xuong` | D2 | NORMAL | chủ động nằm xuống đệm hoặc giường, nằm yên 10 s, ngồi dậy | không |
| `lam_viec` | D2 | NORMAL | thao tác làm việc: khuân vác nhẹ, với tay lên cao, gõ búa | không |
| `chay` | D2 | NORMAL | chạy chậm | không |
| `suyt_nga` | D2 | NORMAL (lớp 2 dự trữ ở tầng 3) | vấp rồi lấy lại thăng bằng, trượt chân nhẹ | không |
| `nga_truoc`, `nga_sau`, `nga_trai`, `nga_phai` | D3 | FALL | ngã trên đệm theo hướng, **nằm yên 10 s** sau ngã | không (mỗi file 1 lần ngã) |
| `nga_dung_day` | D3 | FALL | ngã trên đệm rồi tự đứng dậy sau 2–3 s | không |
| `nga_ngoi` | D3 | FALL | ngã ngồi, giữ tư thế ngồi 10 s | không |

## 4. Cách bấm nút đánh dấu (D2, lớp IMPACT)

- Mỗi file gom **5–6 sự kiện cùng loại**, cách nhau ≥ 5 s, để giảm số file (mục 6, AI-05).
- Người phụ **bấm giữ SW6 khoảng 1–2 s bao quanh từng va đập**: bấm ngay trước, nhả ngay sau. Cột `btn` của file LOG ghi lại.
- `windowing.py` lấy điểm sự kiện là mẫu có |a| lệch khỏi 1 g nhiều nhất **trong đoạn đang bấm** (A.4). Không cần bấm đúng thời điểm, chỉ cần đoạn bấm chứa va đập và không chứa va đập khác.
- D3 không dùng nút: mỗi file một lần ngã, điểm sự kiện tìm trên cả file (như D1). File ngã phải dài ≥ 15 s và có ≥ 10 s sau ngã.

## 5. Chỉ tiêu số lượng

| Đợt | Việc | Chỉ tiêu (Pass) |
|---|---|---|
| D2 đợt 1 (AI-05, G3) | IMPACT | ≥ 100 sự kiện (rơi, va, đặt mạnh, tháo/đội) |
| | NORMAL khi đội mũ | ≥ 30 phút từ ≥ 2 người |
| D2 đợt 2 (AI-08, G5) | IMPACT | ≥ 250, trong đó ≥ 80 va đập khi đang đội |
| | NORMAL khi đội mũ | ≥ 2 giờ từ ≥ 4 người, có ≥ 50 tình huống `suyt_nga` |
| D3 (AI-03, AI-08) | ngã trên đệm | ≥ 40 cú từ ≥ 3 người; ≥ 2 người không có dữ liệu trong huấn luyện |

Ưu tiên thu `nam_xuong`, `cui_nhat` và `suyt_nga`. Phát lại D1 (AI-10) cho thấy báo giả đến chủ yếu từ nằm xuống giường, nhặt đồ và vấp.

## 6. Sau mỗi buổi

```
python -I tools/windowing.py ml/data/raw --out ml/data/d2/d2_windows.npz       # D2 (bỏ qua file nga_*)
python -I tools/windowing.py ml/data/raw --only-falls --out ml/data/d3/d3_windows.npz
```
Script in số sự kiện tìm được theo file. Số sự kiện phải bằng số lần thực hiện; lệch thì xem lại đoạn bấm nút trong video. Cuối cùng đối chiếu bằng mắt 20 cửa sổ mỗi lớp với video (Pass của AI-06): `--plot <thư mục>` vẽ từng sự kiện.
