# Quy trình thu dữ liệu khi đeo ngực

Dữ liệu nhóm tự thu **chỉ để kiểm tra thiết bị**, không dùng để huấn luyện CNN (CNN học từ bộ công khai D1, mục 4.4 của `PROJECT_MASTER.md`). Ngày 28/10 nhóm dùng dữ liệu này để:
- đo hướng cảm biến (đổi trục, SPEC A.1);
- kiểm tư thế (A.11);
- chọn ngưỡng tầng xác nhận ngã thật (A.12).

## 1. An toàn và đồng ý — bắt buộc trước buổi có ngã

- Đệm hoặc nệm dày ≥ 10 cm, rộng ít nhất 2 × 2 m, đặt trên sàn phẳng; dọn vật cứng trong bán kính 1,5 m.
- Người ngã mặc đồ dài, có bảo vệ khuỷu tay và đầu gối.
- Luôn có **một người đứng cạnh đệm**, sẵn sàng đỡ. Ngã chậm, có kiểm soát; không ngã từ trên cao, không ngã đầu xuống trước.
- Người tham gia ký giấy đồng ý, gồm: mục đích; rủi ro; quyền dừng bất cứ lúc nào; dữ liệu chỉ dùng cho đề tài và được ẩn danh (mã `s01`, `s02`…).
- Người có bệnh về cột sống, tim mạch hoặc đang đau không tham gia.
- Dừng buổi thu ngay khi có ai đau hoặc chóng mặt.

## 2. Thiết bị và kiểm tra trước mỗi buổi

1. Module MPU6050 trên dây đeo ngực, cố định chắc. Hướng gắn phải giống lúc đo đổi trục (A.1). Đổi cách gắn thì đo lại theo mục 4.
2. Ba board đã nạp theo `docs/huong_dan_nap_chay.md`, chạy pin.
3. Laptop cùng mạng WiFi với ESP32. Trang web `http://<IP ESP32>/` hiện ĐANG THEO DÕI, "Mẫu mất" và "Khung hỏng" không tăng khi đứng yên.
4. Lúc khởi động, đứng yên khoảng 3 s để MCU hiệu chuẩn gyro.
5. Quay video toàn bộ buổi, để khớp từng bước với log khi cần xem lại.

## 3. Thu log

`tools/ghi_uart.py` nối tới ESP32 qua WiFi (TCP 3333), gửi lệnh `LOG`, đọc to lời nhắc từng bước theo kịch bản và ghi mốc vào file. Mốc có dạng `# >>> TU THE <mã> doi` lúc chuẩn bị và `... giu` lúc bắt đầu làm. File lưu ở `ket_qua_board/<bước>_<ngày giờ>.txt`. Mất kết nối thì công cụ tự nối lại và gửi lại `LOG`.

```bash
python -I tools/ghi_uart.py --tcp <IP ESP32> --lenh LOG --buoc tu_the   --kich-ban tu_the     # 9 tư thế, ≈ 2,5 phút
python -I tools/ghi_uart.py --tcp <IP ESP32> --lenh LOG --buoc dong_tac --kich-ban dong_tac   # động tác dễ nhầm, ≈ 7–9 phút
python -I tools/ghi_uart.py --tcp <IP ESP32> --lenh LOG --buoc nga      --kich-ban nga        # ngã lên nệm, ≈ 4–5 phút
```

| Kịch bản | Các bước (số lần) | Cần |
|---|---|---|
| `tu_the` | đứng; ngồi ghế lưng thẳng; đứng dậy; cúi về trước; đứng lại; nằm ngửa; nằm nghiêng phải; nằm nghiêng trái; nằm sấp. Mỗi bước 6 s đổi + 10 s giữ yên | ghế, chỗ nằm |
| `dong_tac` | đứng yên; ngồi phịch xuống ghế thật mạnh rồi đứng lên (×10); cúi nhặt đồ (×5); đi lại 30 s; nằm xuống giường (×5); ngồi dậy (×5); đang nằm lăn người thật mạnh (×10) | ghế, giường / nệm |
| `nga` | đứng yên; ngã xuống nệm rồi nằm yên (×10); ngã nhẹ xuống nệm rồi ngồi dậy ngay (×5) | nệm dày, người đỡ (mục 1) |

Mỗi dòng mẫu trong log là `t_ms,ax,ay,az,gx,gy,gz,…`, đã đổi về trục người và trừ `ACC_OFF`. Log còn có các dòng trạng thái của ESP32:
- `F,` — trạng thái FSM thô;
- `N,` — mỗi lần xét ngã;
- `S,` — trạng thái hiển thị;
- `STAT,` — thống kê.

## 4. Chấm log

```bash
python -I tools/truc_cam_bien.py ket_qua_board/tu_the_<giờ>.txt --da-doi     # hướng cảm biến: bảng đổi trục đúng phải là (+1, +2, +3); kiểm tư thế
python -I tools/nga_tren_log.py  ket_qua_board/dong_tac_<giờ>.txt            # chạy lại lõi ESP32: CNN nghi / nga.c loại / báo ngã, theo từng bước
python -I tools/nga_tren_log.py  ket_qua_board/nga_<giờ>.txt
```

`nga_tren_log.py` chạy nguyên lõi ESP32 dạng mã máy Cortex-M0 trong Unicorn, với CNN tham chiếu thay cho FPGA. Với mỗi lần CNN nghi, công cụ in ra:
- đang ở bước nào;
- `nga.c` xác nhận hay loại, và vì sao;
- đỉnh va chạm, tốc độ quay, có nghiêng hay không.

Log ghi bằng bản ESP32 trước 28/10 17:16 (đã đổi trục, chưa trừ offset) thì thêm `--chua-tru-offset`.

## 5. Chỉ tiêu

| Việc | Chỉ tiêu (Pass) | Đã có (28/10, một người, một buổi) |
|---|---|---|
| Tư thế giữ yên | 9/9 đoạn đúng | 9/9 |
| Động tác dễ nhầm | 0 lần báo ngã | 0 (CNN nghi 22 lần, `nga.c` loại cả 22) |
| Ngã lên nệm | ≥ 18/20 cú được báo | 14/15 |
| Đeo dài (đi lại, ngồi, làm việc, nằm nghỉ) | ≤ 1 lần báo nhầm mỗi giờ, ≥ 2 giờ tổng từ ≥ 2 người | **[CHỜ ĐO]** |
| Ngã từ người khác (không có trong log chọn ngưỡng) | ≥ 18/20, ≥ 2 người | **[CHỜ ĐO]** |

Bằng chứng: `docs/bao_cao/2026-10-28_tu_the_nguc/`, `docs/bao_cao/2026-10-28_nga_that/`.

## 6. Định dạng cũ (thiết kế ban đầu trên mũ)

`tools/logger.py`, `tools/windowing.py` và `tools/playback_log.py` đọc file CSV do MCU ghi ở chế độ LOG khi MCU làm hết phần xử lý (A.9). Trên phần cứng hiện tại, MCU chạy `FW_NODE` nên không dùng các công cụ này. Chúng vẫn được giữ lại để chấm các file cùng định dạng.
