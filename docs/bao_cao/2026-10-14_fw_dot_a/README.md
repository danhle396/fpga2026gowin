# 2026-10-14 — firmware đợt A: FW-03 (phần máy), FW-07, FW-08 (phần máy), FW-11

Chưa chạm board. Mọi số dưới đây đo trên máy của nhóm (Keil MDK 5.43, Arm Compiler 6.24, pack SONiX.SN32F4_DFP 1.1.1).

| File | Nội dung |
|---|---|
| `keil_uv4_build.log`, `keil_uv4_rebuild.log` | `UV4 -b` / `UV4 -r firmware/keil/fw.uvprojx`: 0 lỗi, 0 cảnh báo; Code 6.716, RO 948, RW 4, ZI 1.344 byte |
| `build_fw.log` | `bash firmware/build.sh` (`-Oz`): RO 4.736 byte, RW + ZI 1.344 byte. Cảnh báo duy nhất nằm trong `system_SN32F400.c` của pack |
| `build_test.log` | `bash firmware/build.sh test`: ảnh Cortex-M0 cho trình giả lập |
| `m0_test.log` | `python tools/m0_test.py`: TẤT CẢ PASS |
| `m0_test_phep_am.sh`, `.log` | 12 lỗi cài cố ý vào bản sao mã nguồn; cả 12 đều làm `m0_test.py` báo FAIL |

## Cách kiểm và vì sao tin được

Máy không có gcc hay trình biên dịch C nào cho PC. `tools/m0_test.py` nạp ảnh do **chính armclang** sinh cho Cortex-M0 vào Unicorn 2.1.4, với CPU đặt là Cortex-M0 (chỉ nhận tập lệnh ARMv6-M). Ảnh chỉ gồm các module C thuần (`crc`, `preprocess`, `spi_frame`, `blocks`, `safety`) cộng `firmware/test/host_main.c`; dữ liệu đi vào và ra qua vùng nhớ chỉ có trong trình giả lập. Python so kết quả với `ml/src/golden_model.py`.

| Kiểm | Kết quả |
|---|---|
| A.10 payload LFSR 768 byte; CRC-16 `"123456789"`; CRC-8 của RTL | khớp; 0x29B1; 0xF4 |
| A.2 `q8` trên 2.627 giá trị, gồm bảng tự kiểm A.2 | khớp |
| FW-07: 10.000 mẫu `firmware/tv/pre_in.csv` → `pre_out.csv` | 5.000/5.000 mẫu khớp từng byte |
| FW-08: khung ghi v3 (772 B) và PROTO 1 (771 B) cho 305 cửa sổ | 0 byte sai |
| FW-08: kiểm khung đọc, 92 ca | đúng mã lỗi ở mọi ca |
| FW-11: khối + Safety FSM | 49/49 ca |

Phép âm (`m0_test_phep_am.log`): làm tròn `+4 → +3`, hệ số lọc `3 → 2`, kẹp `127 → 126`, bước cửa sổ `16 → 15`, đa thức CRC, CRC-8 tính cả 0xA5, bỏ kiểm SEQ, SOS dùng `>`, quên đánh dấu nút đã dùng, không bỏ qua WEAR ở SUSPECT, nới `T_TILT`, ngưỡng khối dùng `>`. Lần chạy đầu, lỗi bước cửa sổ làm trình chạy dừng vì lỗi chỉ số chứ không báo FAIL; đã sửa để báo FAIL rõ ràng.

## Chưa kiểm được ở đây

`board.c`, `spi_fpga.c`, `main.c` chạm ngoại vi nên chỉ biên dịch được. Chúng chờ đợt B: nạp EVK, lệnh `c` (CRC phần cứng), `f` (E.4 bước 2), `s` (FW-09 a).
