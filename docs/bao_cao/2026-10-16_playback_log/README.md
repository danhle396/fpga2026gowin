# 2026-10-16 — `tools/playback_log.py`: chấm buổi thử trên mũ theo đúng chuỗi của thiết bị

**Vì sao cần.** `windowing.py` cắt được cửa sổ, nhưng chưa công cụ nào tính các chỉ tiêu Pass của buổi thử theo đề cương v2.1:
- ngã → PRE_ALARM, cần ≥ 18/20;
- PRE_ALARM giả mỗi giờ khi đội mũ, cần ≤ 1 trên ≥ 2 giờ từ ≥ 2 người;
- va mũ / rơi mũ → PRE_ALARM; nếu va mũ quá 2/20 thì phải thu dữ liệu IMPACT.

Viết sẵn từ bây giờ để có dữ liệu là có kết quả ngay.

**Chuỗi xử lý.** Dùng lại vòng lặp tham chiếu Python mà `tools/m0_test.py` đã kiểm trùng `firmware/src/app_core.c`:
- giảm mẫu và lượng tử bằng `decimate` + `q8`;
- cửa sổ 128 mẫu, bước 16;
- mô hình INT8, mặc định `ml/out/n2_11_d1` của bitstream 3;
- kết quả đến trễ 30 ms;
- khối bất động 32 mẫu ở 100 Hz;
- Safety FSM tick 10 ms.

Mỗi file chạy một FSM mới, hệ thống BẬT suốt file. Cột `btn` là SW6 đánh dấu sự kiện, không đưa vào FSM. File ngã: không ai bấm hủy. File NORMAL và file va đập: mỗi lần vào PRE_ALARM, giả lập người đội nhấn hủy sau 2 s (`--auto-cancel-ms`). Nếu không hủy, FSM kẹt ở ALARM tới hết file và **đếm thiếu** các lần báo nhầm sau đó; lỗi này lộ ra ngay ở bản đầu của công cụ.

## Kiểm

| Kiểm | Kết quả | Log |
|---|---|---|
| So với **mã máy `app_core.c`** (Unicorn, chế độ 8): 133 s gồm 6 bản ghi D1 của người 109 (901, 815, 910, 806, 905, 815), mô hình N2 11 người, T_SCORE 8, cùng chuỗi nhấn hủy | **15/15 lần đổi trạng thái trùng**, gồm 4 lần tự hủy; hai lần vào PRE_ALARM ở 36,15 s và 124,15 s thuộc đoạn 815 | `so_voi_firmware.log` (`chk_playback_log.py`, cần `unicorn`) |
| "Buổi thử giả" dựng từ D1 (người 105 → s01, 109 → s02), 48 file đặt tên đúng quy ước, có file va mũ chèn 3 xung 4 g với SW6 bấm quanh mỗi xung | Ngã kết thúc nằm 24/24 vào PRE_ALARM (trễ trung vị 3,95 s, lớn nhất 4,67 s); ngã rồi đứng dậy 0/8 (đúng); ngã kết thúc ngồi 0/8 (X15); NORMAL 0,18 giờ, 2 báo giả, đều từ `nam_xuong`; va mũ 0/6 | `buoi_thu_gia.log` (`mk_session.py`) |
| File lỗi: tên `s00_*`, hoạt động lạ, mất 1 mẫu | Cả ba bị bỏ, kèm lý do | `file_loi.log` |

Số của "buổi thử giả" chỉ để kiểm công cụ: dữ liệu là D1 nội suy, không phải mũ thật.

## Dùng sau buổi thử

```
python -I tools/playback_log.py ml/data/raw --detail
```
