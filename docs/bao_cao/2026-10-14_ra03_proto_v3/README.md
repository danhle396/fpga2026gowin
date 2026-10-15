# 2026-10-14 — RA-03: giao thức v3 trong RTL (mô phỏng + P&R), kèm `top.sdc` (R10)

## Thay đổi

| File | Nội dung |
|---|---|
| `rtl/v3/fpga_top_v3.v` | Top mới: giao thức v3, cổng `rst_n` (đồng bộ 3 tầng), bộ đếm `CYCLES`. Dùng lại nguyên `spi_slave`, `input_buffer`, `cnn_core` của project |
| `rtl/v3/packet_parser_v3.v` | Khung ghi `[A5][SEQ][768][CRC-16]` trong một lần CS thấp. **R3:** 0xA5 phải là byte đầu sau CS xuống; CS lên giữa khung là lỗi thiếu byte. **R4:** khung đến khi CNN bận thì không ghi vào bộ đệm. **R5:** mọi kết cục đều có khung kết quả và IRQ |
| `rtl/v3/result_frame_v3.v` | Khung đọc 20 byte: SEQ, STATUS, CLASS, SCORE = top1 − top2 (A.4), 4 logit INT16, CYCLES 24 bit, 2 CRC-16. CRC tính tuần tự 16 chu kỳ |
| `rtl/v3/spi_result_tx_v3.v` | Phát 20 byte; IRQ về 0 sau byte thứ 7 (A.7); MISO đổi ngay ở chu kỳ phát hiện cạnh xuống SCK như bản cũ (R11) |
| `rtl/v3/crc16_ccitt.v` | CRC-16/CCITT-FALSE một byte |
| `rtl/v3/fpga_top_v3.cst`, `.sdc`, `rtl/v3/top.sdc` | Thêm `rst_n` ở J11 (E.3); ràng buộc clock 27 MHz + false path cho chân bất đồng bộ (R10) |
| `src/cnn_core.v` (project) | Thêm 4 cổng ra `logit0_out..logit3_out`. `fpga_top.v` nối rỗng tường minh để không thêm cảnh báo |
| `tools/gen_cnn_params.py` | Ghi thêm `` `CNN_SCORE_SHIFT `` (từ `score_shift` trong json, mặc định 0) |

`fpga_top.v` (PROTO 1) giữ nguyên chức năng để thông mạch lần đầu (RA-04).

## Mô phỏng: `bash rtl/v3/run_tb_proto.sh --ng 50` (`tb_proto_50.log`)

Vector do `tools/gen_tb_proto.py` sinh từ golden model với weight SisFall của nhóm. 50 khung đúng gồm 20 cửa sổ của `golden_vectors.npz`, khung tự kiểm LFSR, 5 mẫu cực trị (toàn +127, −128, 0, xen kẽ, bậc thang) và cửa sổ ngẫu nhiên; lớp golden 0/1/2/3 = 16/3/4/27.

| Kịch bản | Kết quả |
|---|---|
| (0) đọc khi chưa có kết quả | MISO toàn 0 |
| (1) 50 khung đúng, đọc 20 byte | 50/50 khớp golden (SEQ, STATUS, CLASS, SCORE, CRC đầu, 4 logit); CRC đuôi đúng; CYCLES = **699.800** ở mọi khung |
| (2) CRC sai | STATUS 0x00, CLASS 0xFF, có IRQ |
| (3) khung thiếu byte (CS lên sau 302 byte) | STATUS 0x04 |
| (4) hai khung sát nhau | khung sau: STATUS 0x07 (CRC_OK + BUSY + ERR), không ghi đè bộ đệm; khung trước vẫn ra kết quả đúng |
| (5) byte đầu không phải 0xA5 | bỏ qua, không IRQ |
| (6) chế độ RUN | sau 6 byte IRQ vẫn cao; sau 7 byte IRQ về 0; đọc lại → toàn 0 |
| (7) RST_N thấp 1 µs | IRQ về 0, MISO toàn 0 |

Phép âm (`tb_proto_phep_am.log`): 5 lỗi cài vào RTL đều bị bắt. Lỗi "IRQ hạ sau byte 6" lúc đầu lọt, nên đã thêm kiểm IRQ vào testbench.

## P&R (Gowin EDA V1.9.11.03, GW2A-LV18PG256C8/I7)

| Top | Logic | Register | BSRAM | DSP | Fmax (mục tiêu 50,143 MHz) | Cảnh báo |
|---|---|---|---|---|---|---|
| `fpga_top_v3` + `fpga_top_v3.sdc` | 1.522 (8 %) | 952 | 6/46 | 1,25/24 | **102,74 MHz** | 0 |
| `fpga_top` (PROTO 1) + `top.sdc` | 913 (5 %) | 589 | 6/46 | 1,25/24 | 108,49 MHz (như 14/10) | 1 (NL0002 `crc8` bị gộp, có từ trước) |

Không còn cảnh báo thiếu ràng buộc clock; `rst_n` vào J11 đúng chuẩn LVCMOS33.

## Chưa làm

Nạp lên chip (RA-04, cần board). Thêm các file `rtl/v3/` vào project Gowin của nhóm là quyết định của người giữ project: thêm file, rồi chọn top `fpga_top_v3`.
