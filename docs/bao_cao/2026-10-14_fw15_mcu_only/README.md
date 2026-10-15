# 2026-10-14 — FW-15: CNN thuần trên MCU (bản đối chứng), đúng và dự toán thời gian

`firmware/src/cnn_mcu.c`, C số nguyên, chạy N1, N2, N2-S, N2-L. RAM: hai bộ đệm 1.024 byte.

## Đúng (`m0_test.log`)

Ảnh test chạy mã máy Cortex-M0 trong Unicorn (`tools/m0_test.py`, chế độ 7). Mỗi mô hình 50 cửa sổ: 15 FALL + 15 NORMAL của D1, LFSR, toàn +127 / −128 / 0, 16 ngẫu nhiên. Lớp, SCORE và 4 logit **khớp golden 50/50** cho cả 5 mô hình: N1 SisFall của nhóm, N1 / N2-S / N2 / N2-L huấn luyện trên D1.

## Dự toán thời gian (`dem_lenh_cnn_mcu.log`)

Đếm lệnh thực thi một lần suy luận (khung LFSR) trong Unicorn rồi quy ra chu kỳ theo TRM Cortex-M0: LDR/STR 2, nhánh lấy 3, BL 4, PUSH/POP 1 + N, MULS 1 hoặc 32 tùy bộ nhân. SN32F407 dùng loại nào thì chưa biết (X7).

| Mô hình | Bản build | Lệnh | Nhân 1 chu kỳ | Nhân 32 chu kỳ | Flash 1 wait-state (thêm) |
|---|---|---|---|---|---|
| N1 | `-O3` | 2,39 triệu | 74,6 ms | 232,7 ms | ≈ 26,5 ms |
| N2-S | `-O3` | 1,25 triệu | 39,3 ms | 118,9 ms | ≈ 13,9 ms |
| N2 | `-O3` | 2,37 triệu | 73,9 ms | 232,3 ms | ≈ 26,3 ms |
| N2-L | `-O3` | 3,07 triệu | 95,5 ms | 305,5 ms | ≈ 34,1 ms |
| N1 | `-Oz` | 3,11 triệu | 90,9 ms | 234,2 ms | ≈ 38,3 ms |

So sánh:
- E1 trên FPGA cần 13,96 ms cho N1, nên FPGA nhanh hơn MCU **5,3–16,7 lần**. Cam kết là "≥ 5 lần".
- Bước suy luận là 0,32 s. MCU-only N1 chiếm 23–81 % thời gian mỗi bước, so với 4,4 % của E1.

Số MULS (244.791) lớn hơn số MAC (225.408) vì có cả phép nhân tính địa chỉ.

**Giới hạn:** đây là dự toán từ số lệnh thật, chưa đo trên chip. Còn thiếu hai thứ: số đo bằng GPIO + logic analyzer trên SN32F407 (Pass của FW-15), và thông tin bộ nhân có 1 hay 32 chu kỳ.
