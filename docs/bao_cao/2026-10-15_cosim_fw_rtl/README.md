# 2026-10-15 — Mô phỏng ghép firmware ↔ RTL trên dữ liệu ngã thật

`tools/cosim.py --e2 ml/out/e2_matrix/n2s_p1 --trials 6` (`cosim_n2s_p1_6_ban_ghi.log`). Đây là bước gần HIL nhất có thể làm khi chưa có board.

**Dữ liệu:** 6 bản ghi D1 của người 104, nội suy lên 100 Hz rồi nối với nhau: ngã nằm sấp 901, ngã nằm ngửa 910, ngã rồi đứng dậy 905, đi bộ 801, nằm xuống giường 815, nhặt đồ 806. Tổng 137,7 s.

1. **Lượt 1, mã máy Cortex-M0 của firmware (Unicorn):** `preprocess.c` + `spi_frame.c` dựng 423 khung ghi v3 từ mẫu thô.
2. **Lượt 2, RTL (Icarus):** đúng các byte đó đi qua chân SPI (4 MHz, mode 0) vào `rtl/v3/fpga_top_v3.v` + `rtl/e2/cnn_e2.v`, mô hình N2-S, P = 1. RTL trả 423 khung đọc 20 byte (`rtl/v3/tb_stream.v`).
3. **Lượt 3, mã máy Cortex-M0 của firmware:** `app_core.c` kiểm từng khung đọc của RTL bằng `spi_parse_v3`, bỏ phiếu, chạy Safety FSM (trễ kết quả 30 ms, WEAR = 1, không bấm CANCEL).

| Kiểm | Kết quả |
|---|---|
| Khung ghi của firmware == `write_frame()` golden | 423/423 |
| Khung đọc của RTL == `result_frame()` golden (SEQ, STATUS, CLASS, SCORE, CRC, 4 logit) và CRC đuôi đúng | 423/423; CYCLES = 132.896 ở mọi khung |
| Firmware đọc được khung RTL (`spi_parse_v3` = OK) và kết quả == golden | 423/423 |
| Các lần đổi trạng thái của firmware == chuỗi golden Python (`decimate`, `q8`, `forward`, `safety_model`) | trùng: MONITOR → SUSPECT → PRE_ALARM → ALARM |

Lớp golden: 409 NORMAL, 14 FALL. FSM dừng ở ALARM sau cú ngã đầu vì không ai bấm CANCEL. Các bản ghi sau vẫn được kiểm ở mức khung và kết quả, nhưng không đi qua các nhánh FSM khác; các nhánh đó đã được kiểm riêng (49 ca, chuỗi 131 s có lịch bấm CANCEL).

**Ý nghĩa:**
- Mỗi mắt xích trước đó đã khớp golden riêng lẻ. Đây là lần đầu chúng nối thành **một chuỗi duy nhất**: đúng byte firmware gửi, đúng khung RTL trả, đúng cách firmware đọc khung. Vì vậy khi lên board, lỗi chỉ còn có thể đến từ điện, chân, thời gian thật hoặc ngoại vi.
- Không thay được HIL trên chip (TH-07: ≥ 500 cửa sổ trên board).
- 15/10, sau SPEC v3.1: `cosim_n2s_p1_6_ban_ghi_v31.log` vẫn PASS 423/423, FSM trùng golden.
- 15/10, mô hình N2 (chọn sơ bộ): `cosim_n2_p1_6_ban_ghi_v31.log` PASS 423/423, CYCLES 258.080, FSM trùng golden.
