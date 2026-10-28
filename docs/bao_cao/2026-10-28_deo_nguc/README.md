# 2026-10-28 — Đeo thiết bị ở ngực: đo hướng cảm biến, đổi trục trên ESP32

Nhóm làm xong phần cứng đeo bằng dây ở **ngực**, chạy bằng pin. Mọi phần xử lý sau MCU dùng quy ước trục người: X hướng trước, Y sang trái, Z lên trời. Các phần đó gồm CNN (dữ liệu D1 đã xoay về quy ước này), khối A.8 (`|az_tb| < T_TILT` là nằm) và tư thế A.11. Khi đeo ở ngực, MPU6050 không còn nằm theo trục người nữa, nên phải đo hướng thật rồi đổi trục.

## Đo

Lệnh đo: `ghi_uart.py --tcp 192.168.88.97 --lenh LOG --buoc truc_nguc --tu-the`, chạy bằng pin, đọc qua WiFi. Lệnh nhắc lần lượt 5 tư thế, mỗi tư thế 5 s để đổi + 10 s giữ yên.

| File | Ghi chú |
|---|---|
| [truc_nguc_20261028_143948.txt](truc_nguc_20261028_143948.txt) | Lần 1, chưa có lời nhắc. Chỉ ghi được 23 s, một tư thế (trọng lực theo −Y), nên không dùng được. Sau đó thêm `--tu-the` vào `ghi_uart.py`. Giữa hai lần đo MPU6050 có lúc không trả lời I²C (`i2c=2`, hết thời gian chờ); nhóm ấn lại dây thì chạy lại |
| [truc_nguc_20261028_151551.txt](truc_nguc_20261028_151551.txt) | Lần 2: đủ 5 mốc, 7.940 mẫu. ESP32 `mat=0`, `khung_hong=0`, `ok = gui = 529`, `timeout=0`; MCU `i2c_loi=0`, `cau_hinh_lai=0` |

## Kết quả ([truc_cam_bien.txt](truc_cam_bien.txt), `python -I tools/truc_cam_bien.py <log>`)

Trọng lực trung bình lúc giữ yên, đơn vị LSB (2048 = 1 g):

| Tư thế | x | y | z |
|---|---|---|---|
| đứng thẳng | −142 | **−2038** | 250 |
| nằm ngửa | −263 | −4 | **2240** |
| nằm nghiêng phải | **−2029** | −36 | 131 |
| nằm nghiêng trái | **2021** | 138 | 366 |
| cúi về trước | −73 | −592 | **−1760** |

**Bảng đổi trục cho vị trí ngực:** X_người = +Z, Y_người = −X, Z_người = −Y của MPU6050.
- Mỗi trục mang 99–100 % trọng lực ở tư thế tương ứng.
- Định thức +1, tức là phép xoay đúng, không bị lật gương.
- Kiểm chéo: nằm nghiêng trái cho +X, ngược dấu với nghiêng phải, khớp với bảng.

**Kiểm bằng `posture_model`** trên chính log này:

| Đoạn giữ yên | Trước khi đổi trục | Sau khi đổi trục |
|---|---|---|
| đứng thẳng | NGHIENG_TRAI ✗ | DUNG ✓ |
| nằm ngửa | DUNG ✗ | NAM_NGUA ✓ |
| nằm nghiêng phải | NAM_SAP ✗ | NGHIENG_PHAI ✓ |
| nằm nghiêng trái | NAM_NGUA ✗ | NGHIENG_TRAI ✓ |
| cúi về trước | NGHIENG_TRAI ✗ | NAM_SAP ✗ |

Ở tư thế cúi, ngực ngả 73° so với phương thẳng đứng (z_người = 592 ≈ 0,29 g), gần nằm ngang. Chỉ dựa vào trọng lực thì cúi sâu ở ngực không phân biệt được với nằm sấp. Đây là giới hạn của vị trí ngực, ghi lại để báo cáo.

Trước khi đổi trục, lúc đứng `z_người` ≈ 250, tức Safety FSM thấy "nằm ngang" ngay cả khi người đứng. Một cú lắc rồi đứng yên là đủ vào PRE_ALARM giả. Đổi trục xong thì lúc đứng `z_người` = 2038.

## Mã

- `fw_config.h`: `FW_VI_TRI_DEO` (0 = mũ, **1 = ngực, mặc định từ 28/10**) chọn `TRUC_X/Y/Z`.
- `hub.c`: `hub_doi_truc()` đổi trục cả gia tốc lẫn gyro. Đổi dấu −32768 thì kẹp về 32767. `hub_sample` đổi trục trước app_core và posture; mẫu đã đổi lưu ở `h->r`.
- ESP32: lệnh `LOG` in mẫu **đã đổi trục**, nên dữ liệu thu sau này cùng quy ước với D1. Lúc khởi động in `# vi tri deo: NGUC ...`.
- MCU không đổi (vẫn gửi trục cảm biến), không cần nạp lại.
- `m0_test` `test_hub`: luồng MCU dựng ở trục cảm biến ngực (phép ngược của bảng). hub.c vẫn trùng golden + safety_model, 402/402 khung và 11 lần đổi trạng thái. Như vậy phép đổi trục cũng đã được kiểm. Toàn bộ m0_test: TẤT CẢ PASS.
- Build ESP32 (core 3.0.7): 967.021 B flash, 0 cảnh báo. **Chưa nạp**: ESP32 chạy pin, không cắm USB vào máy.

## Còn mở

- **Mô hình CNN trên FPGA vẫn học từ cảm biến ở đầu.** Theo đo AI-09 (13/10, 6 người), tín hiệu ngực gần với đầu: đỉnh |a| khi ngã 4,11 g so với 4,44 g; góc nằm sau ngã 65° so với 67°. Nhưng mô hình chưa được kiểm trên kênh ngực. Đề nghị: train N2 bằng `d1_windows_nguc_340539.npz` (8 người) và kiểm LOSO trên ngực. Để phát lại qua FSM cần bản ghi liền của kênh ngực, dữ liệu thô đó đang ở máy thứ hai [CẦN XÁC MINH – nguồn: đo LOSO trên ngực].
- Đề cương v2.1/v2.2 vẫn ghi "mũ bảo hộ, cảm biến ở đầu". Nhóm cần quyết có cập nhật đề cương (v2.3) không; nếu có thì ba file sửa cùng lúc.
- Chỉ tiêu va mũ / rơi mũ không còn áp dụng nguyên văn khi đeo ngực.
