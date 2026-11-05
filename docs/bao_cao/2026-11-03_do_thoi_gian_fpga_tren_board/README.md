# Đo thời gian suy luận FPGA trên board — 2026-11-03

**Kết luận:** bộ đếm `CYCLES` trên chip GW2A-18 đọc được **258.080 chu kỳ ở 12.000/12.000 khung**, trùng số mô phỏng. Đổi ra thời gian ở clock danh định 50,143 MHz là **5,147 ms (làm tròn 5,15 ms)**. Đồng hồ ESP32 đo độc lập được **≈ 5,139 ms**, chênh 8 µs (0,15 %).

## Cách đo

- Sketch tạm [`do_thoi_gian_fpga.ino`](do_thoi_gian_fpga.ino) trên ESP32, SPI 1 MHz, cùng dây và bitstream đang dùng. FPGA và MCU không nạp lại.
- Mỗi khung: ghi 772 byte, đọc thăm 1 byte đến khi thấy `0x5A`, rồi đọc đủ 20 byte, kiểm cả hai CRC, STATUS, SEQ, CLASS.
- `CYCLES` là bộ đếm trong RTL (`fpga_top_v3.v`), đếm từ `payload_done` tới `inference_done`, đọc ở byte 15..17.
- Hai lần chạy, mỗi lần 3 chế độ × 2.000 khung:

| Chế độ | Dữ liệu | Đọc thăm khi FPGA đang tính |
|---|---|---|
| A | Khung tự kiểm A.10, kiểm thêm 7 byte đầu đúng đáp án | Có |
| B | Giả ngẫu nhiên, mỗi khung một mầm | Có |
| C | Khung tự kiểm A.10, kiểm thêm 7 byte đầu đúng đáp án | Không, chờ 6 ms rồi mới đọc, giống `hub.c` |

## Kết quả

| | Lần 1 | Lần 2 |
|---|---|---|
| Khung OK, A / B / C | 2.000 / 2.000 / 2.000 | 2.000 / 2.000 / 2.000 |
| `CYCLES`, A / B / C | luôn 258.080 | luôn 258.080 |
| Lớp ở chế độ B | lớp 0: 269, lớp 3: 1.731 | lớp 0: 269, lớp 3: 1.731 |
| `max(t_lo)`, A / B (µs) | 5139 / 5138 | 5137 / 5139 |
| `min(t_hi)`, A / B (µs) | 5139 / 5139 | 5139 / 5139 |
| Ghi 772 byte, trung vị (µs) | 6223 | 6223 |

- `t_lo` là lần đọc thăm cuối còn thấy `0x00`, `t_hi` là lần đầu thấy `0x5A`, tính từ lúc ghi xong. Kết quả sẵn sàng nằm giữa hai mốc này. Chu kỳ đọc thăm trung vị 23 µs.
- Số `clock suy ra` mà `phan_tich.py` in ra dùng điểm giữa `t_lo`, `t_hi` nên bị lệch theo pha đọc thăm. Không dùng số đó. Mốc đáng tin là biên 5139 µs ở trên.
- Tính cả gửi khung, một lần suy luận mất ≈ 6,22 ms ghi + 5,15 ms tính ≈ 11,4 ms, chưa tính đọc kết quả.

## So với golden trên 2.000 cửa sổ khác nhau

`so_golden_che_do_b.py` dựng lại 2.000 cửa sổ của chế độ B từ mầm và so với `golden_model.forward`, không cần board:

- Lần 1: **2.000/2.000** khung trùng lớp và SCORE. Lần 2: **2.000/2.000**.
- Golden có lớp 0: 269, lớp 3: 1.731 và đủ 128 giá trị SCORE, nên phép so có khả năng phát hiện sai khác.
- Chỉ so lớp và SCORE, vì log không ghi logit từng khung. Dữ liệu là giả ngẫu nhiên, không phải cửa sổ thật. Vì vậy phần này **chưa đủ Pass của TH-09** (so từng bit qua HIL).

## Giới hạn của phép đo

- 50,143 MHz là clock danh định của PLL, không đo bằng thiết bị. Kiểm chéo duy nhất là đồng hồ ESP32.
- Chênh 8 µs chưa được tách nguyên nhân. `t_cs` lấy trước khi CS xuống và `t0` lấy sau khi ghi xong, đều làm số đo nhỏ đi vài µs. Chưa đủ thiết bị để tách riêng.
- Chế độ B là dữ liệu giả ngẫu nhiên, chỉ để xem `CYCLES` có đổi theo dữ liệu không. Lớp ra ở chế độ này không có ý nghĩa nhận dạng.
- Đợt đo FPGA chạy lúc board MCU chưa bật nguồn. Đường đo chỉ gồm ESP32 và FPGA nên `CYCLES` không phụ thuộc MCU. Thời gian trên MCU đo riêng ở [`2026-11-03_do_thoi_gian_cnn_mcu_tren_chip`](../2026-11-03_do_thoi_gian_cnn_mcu_tren_chip/README.md).
- Mỗi log có 1 đoạn 64 byte rác trên đường Serial (lần 1 làm mất dòng `MODE,C`, lần 2 nằm trước `MODE,A`). Mọi dòng `F,` đều đọc được, đủ 2.000 dòng mỗi chế độ.

## Khôi phục ESP32

Chỉ ghi vùng app ở `0x10000`, trước và sau khi đo.

- Trước khi nạp: `verify-flash` cho thấy bootloader, bảng phân vùng, `boot_app0`, app trùng MD5 với bản dựng 31/10.
- Sau khi khôi phục: 4/4 vùng vẫn trùng MD5, tự kiểm A.10 PASS, 61/61 khung OK ở lần đọc đầu.
- NVS khác bản sao lưu 1.988 byte (`0x9020–0xA03F`). Sketch đo không dùng WiFi và không ghi NVS, còn firmware gốc dùng WiFi lúc khởi động, nên đây nhiều khả năng là phần WiFi/PHY tự ghi. 40 chuỗi đầu trong NVS giống nhau; chưa so nội dung từng khóa.
- `read-flash` toàn bộ 4 MB lỗi đúng ở `0x6D000` ở cả 921600 và 230400 baud, chưa rõ nguyên nhân. Vì vậy nguồn khôi phục là bản dựng 31/10 đã xác minh MD5, không phải bản đọc toàn flash.

## Mất mẫu UART khi chưa bật nguồn board MCU

Trong đợt đo, người đo cho biết board MCU **chưa bật nguồn**. Bật nguồn xong thì hết lỗi, không cần sửa dây hay code:

| Khi để yên, 35 s | Chưa bật nguồn MCU (`uart_sau_khoi_phuc.txt`) | Đã bật nguồn MCU (`uart_sau_bat_nguon_mcu.txt`) |
|---|---|---|
| Mẫu nhận được | 45,1 /s | 100,0 /s |
| Mẫu mất | 55,0 /s | 0 |
| Khung hỏng | 25,2 /s | 0 |
| Byte nhận ở GPIO16 | 6.421,6 /s | 2.114,7 /s |

Dòng "mất mẫu 0" trên poster khớp với trạng thái đã bật nguồn. MCU vẫn gửi được một phần mẫu lúc chưa bật nguồn; cơ chế cấp điện lúc đó chưa được kiểm chứng.

## Tệp

- `do_thoi_gian_fpga.ino`, `phan_tich.py`: sketch và bộ tổng hợp.
- `do_lan1.log`, `do_lan2.log`: log thô từng khung.
- `truoc_khi_nap.log`, `sau_khi_khoi_phuc.log`, `uart_sau_khoi_phuc.txt`: trạng thái board trước và sau, lúc MCU chưa bật nguồn.
- `sau_bat_nguon_mcu.log`, `uart_sau_bat_nguon_mcu.txt`: trạng thái sau khi bật nguồn MCU.
