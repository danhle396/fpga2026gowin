# Đo thời gian CNN N2 trên chip SN32F407 — 2026-11-03

**Kết luận:** một lần suy luận N2 bằng `cnn_mcu.c` trên chip mất **≈ 4,40 triệu chu kỳ, tức 91,8 ms ở 48 MHz**, đúng golden 240/240 lần. So với FPGA đo cùng ngày (5,147 ms), **FPGA nhanh gấp ≈ 18 lần**. Đây là số đo thay cho dự toán 74–232 ms của FW-15.

## Cách đo

- Chương trình tạm [`do_cnn_main.c`](do_cnn_main.c), dựng ngoài repo bằng [`build_do.sh`](build_do.sh), `-O3` như dự toán FW-15. `cnn_mcu.c` và `board.c` lấy nguyên từ repo, không sửa.
- Clock giống firmware chính: IHRC 48 MHz, `LPCTRL = 0x19`. Weight trong Flash, cửa sổ vào chép sang RAM như khi chạy thật.
- Tắt ngắt lúc đo, SysTick đếm HCLK, kiểm cờ tràn. Mỗi lần chạy so lớp, SCORE, 4 logit với `golden_model.forward`.
- 6 cửa sổ × 20 lần × 2 vòng. Kết quả đi qua UART và firmware ESP32 hiện có, không nạp lại ESP32. FPGA không tham gia.

Mô hình trong `so_lieu.c` là `ml/out/n2_11_d1/params_int8.npz`, cùng mô hình với bitstream. `sinh_so_lieu.py` kiểm logit của cửa sổ LFSR trùng đáp án tự kiểm của FPGA.

## Kết quả

Hai vòng cho số chu kỳ giống hệt nhau. Mỗi cửa sổ, cả 40 lần cùng một số chu kỳ:

| Cửa sổ | Đúng golden | Chu kỳ | ms ở 48 MHz |
|---|---|---|---|
| LFSR | 40/40 | 4.404.391 | 91,76 |
| Toàn 0 | 40/40 | 4.403.696 | 91,74 |
| Toàn +127 | 40/40 | 4.404.756 | 91,77 |
| Toàn −128 | 40/40 | 4.404.539 | 91,76 |
| D1 FALL | 40/40 | 4.405.446 | 91,78 |
| D1 NORMAL | 40/40 | 4.405.407 | 91,78 |

- **Bộ nhân:** vòng 1.000 `MULS` mất 7.008 chu kỳ, vòng `MOVS` tương ứng 7.014. Vậy `MULS` ≈ 1 chu kỳ, trả lời câu hỏi X7 của FW-15. Số đo 91,8 ms nằm trong khoảng dự toán, gần đầu thấp cộng phần wait-state (73,9 + 26,3 ms).
- **Clock:** 20.000 ms theo clock MCU đo được 20,086 s và 20,060 s trên đồng hồ máy tính (lệch −0,43 % và −0,30 %). Mốc giờ đi qua ESP32 và USB nên sai số phép đối chiếu này chưa được lượng hóa. Nếu tính theo clock đối chiếu thì khoảng 92,0–92,2 ms, kết luận ≈ 18 lần không đổi.

## Giới hạn

- 48 MHz là clock danh định của IHRC, không đo bằng thiết bị.
- Đây là bản đối chứng. Firmware sản phẩm không chạy CNN trên MCU, CNN chạy trên FPGA.
- Số này chỉ tính phần suy luận với ngắt tắt, `-O3`. Khi chạy thật cùng đọc cảm biến và UART thì sẽ lâu hơn; chưa đo.

## Khôi phục MCU

- Trước khi nạp: đọc nguyên 32 KB flash qua SN-Link (`mcu_goc.hex`), chứa bản dựng `Oct 31 2026 12:03:01`, trùng mốc nạp 31/10.
- Sau khi đo: nạp lại đúng bản đọc đó (Verify OK), đọc lại và so: **khác 0 byte**.
- Sau khôi phục: ESP32 nhận mẫu đều, bộ đếm mẫu mất không tăng (`sau_khoi_phuc_mcu.log`, `trang_thai_cuoi.txt`), tự kiểm FPGA PASS.
- Mỗi lần vào debug hoặc nạp, MCU bị reset và mất mẫu tạm thời, nên bộ đếm `mat` tích lũy trên ESP32 có tăng trong lúc đo. Muốn số sạch thì khởi động lại ESP32.

## Tệp

- `do_cnn_main.c`, `so_lieu.h`, `sinh_so_lieu.py`, `build_do.sh`, `phan_tich_mcu.py`: chương trình đo, số liệu, bộ tổng hợp.
- `do_mcu_lan1.log`, `do_mcu_lan2.log`: log thô, có mốc giờ máy tính.
- `mcu_goc.hex`: bản đọc từ chip, dùng để khôi phục.
- `sau_khoi_phuc_mcu.log`, `trang_thai_cuoi.txt`: trạng thái board sau khôi phục.
