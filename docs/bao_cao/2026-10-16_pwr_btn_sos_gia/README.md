# 2026-10-16 — Sửa `pwr_btn.c`: giữ nút để bật lại ngay sau khi tắt có thể thành SOS giả

**Lỗi.**
- Nhấn nhanh 2 lần thì hệ thống TẮT, nhưng Safety FSM còn ở MONITOR thêm `WEAR_OFF_MS` = 3 s rồi mới về STANDBY.
- Trong 3 s đó, `mask` chỉ được bật khi FSM ở STANDBY. Vì vậy một lần **giữ nút để BẬT lại** không được hiểu là cử chỉ bật, mà được chuyển thẳng cho FSM.
- Giữ tới 3 s thì FSM coi là **SOS → ALARM** (còi hú) trong khi hệ thống đang tắt.

**Sửa.**
- Lần nhấn cũng được che (chỉ là cử chỉ BẬT, giữ 2 s) khi hệ thống đã TẮT mà FSM còn ở MONITOR hoặc SUSPECT.
- Ở PRE_ALARM và ALARM nút vẫn chuyển cho FSM như cũ. Nhờ vậy ca nhóm cố ý giữ vẫn đúng: "vừa TẮT mà ngã trong 3 s → vẫn PRE_ALARM, nút vẫn CANCEL được".

**Kiểm** (mã máy Cortex-M0 trong Unicorn, `tools/m0_test.py`):

| | Ca mới "vừa TẮT, giữ 3,5 s trong lúc FSM còn MONITOR → BẬT lại, không SOS" | Tổng |
|---|---|---|
| Mã cũ (phép âm) | **FAIL** | 62 PASS, 1 FAIL |
| Mã đã sửa | PASS | **63 PASS, 0 FAIL**; cả 10 ca của nút đều PASS (`m0_test_sau_sua.log`) |

Keil `fw.uvprojx`: 0 lỗi, 0 cảnh báo, Code 16.160 + RO 1.680 byte (`keil_fw.log`). Chưa chạy trên board.
