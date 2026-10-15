# 2026-10-14 — Engine E2 (RB-03, RB-04; RB-05 trong mô phỏng), đưa vào top v3 (RA-07), P&R (RA-08)

## RTL

`rtl/e2/cnn_e2.v`: 1 chu kỳ mỗi MAC, `LANES` làn. Chạy N1 (2 Conv + GAP) và họ N2 (3 Conv + Flatten) theo bảng lớp trong `cnn_params.vh` do `tools/export_mem.py --engine e2` sinh.
- Hai con trỏ (dữ liệu, weight) chỉ tăng 1, đúng mô hình địa chỉ `ml/src/rom_layout.engine()`.
- Pipeline: phát địa chỉ → BSRAM → thanh ghi tích → cộng dồn.
- Bias nạp 3 nhịp mỗi làn; requant sau max-pool; argmax 2 tầng, bằng nhau thì chọn chỉ số nhỏ.

`rtl/v3/fpga_top_v3.v` chọn engine bằng macro `CNN_ENGINE_E2` trong `cnn_params.vh`, nên chỉ có một nguồn tham số.

## Mô phỏng `bash rtl/e2/run_tb_e2.sh <thư mục xuất> 50` (`tb_e2_*.log`)

`tb_e2` so **từng tầng**: l1 lấy từ RAM A khi lớp 0 xong, l2 từ RAM B, l3 từ RAM A lúc xong; rồi so 4 logit và lớp. Mỗi cấu hình 50 vector của `export_mem.py`: FALL/NORMAL D1, LFSR, cực trị, ngẫu nhiên.

| Mô hình | P = 1 | P = 2 | P = 4 |
|---|---|---|---|
| N1 SisFall của nhóm (GAP) | 50/50, 257.280 chu kỳ | 50/50, 136.376 | 50/50, 75.924 |
| N2 | 50/50, **258.080** | 50/50, 136.216 | 50/50, **75.284** |
| **N2-S** | 50/50, **132.896 (2,65 ms)** | 50/50, 70.936 | 50/50, **39.956 (0,80 ms)** |
| N2-L | 50/50, 343.840 | 50/50, 179.992 | 50/50, 98.068 |
| Mô hình kiểm hòa (lớp 0, 1, 3 bằng nhau) | 10/10 → lớp 0 | — | 10/10 |

So với mục tiêu:
- **RB-04:** N1 và N2 khớp ở mọi tầng; CYCLES 258.080 ≤ 300.000. Đạt.
- **RB-05 (tầng 3):** N2, P = 4: 75.284 ≤ 100.000. Đạt trong mô phỏng.
- E1 cần 699.800 chu kỳ = 13,96 ms. E2 với N2-S, P = 1 nhanh hơn **5,3 lần**.

Phép âm (`tb_e2_phep_am.log`): 6/6 lỗi cài vào RTL bị bắt (làm tròn requant, biên đệm, max-pool, độ trễ pipeline, GAP, quy tắc hòa của argmax). Quy tắc hòa lúc đầu lọt vì dữ liệu thật không bao giờ hòa; đã thêm mô hình kiểm hòa.

## Qua chân SPI: `run_tb_proto.sh --e2 ... --ng 50` (`tb_proto_v3_e2_*.log`)

Top v3 + E2 N2-S, P = 1 và P = 4: 50/50 khung đúng, đủ 7 kịch bản lỗi; CYCLES 132.896 và 39.956. SCORE với `score_shift` 9 khớp golden.

**Quy ước mới cho A.7, phát hiện ở bước này:** chỉ có một bộ đệm kết quả, bản mới nhất thắng. Với P = 4, một lần suy luận (0,8 ms) ngắn hơn thời gian gửi một khung (1,54 ms). Nếu MCU gửi hai khung sát nhau, kết quả khung trước xong trong lúc khung sau còn truyền, rồi bị khung lỗi BUSY của khung sau thay thế. Firmware luôn chờ kết quả rồi mới gửi khung mới (`spi_fpga_busy()`), nên không gặp trường hợp này. `tb_proto` tự nhận biết engine nhanh để kỳ vọng đúng.

## P&R top v3 + E2 (`pnr_v3_e2_n2s_*`), Gowin EDA V1.9.11.03

| | Logic | Register | BSRAM | DSP | Fmax (mục tiêu 50,143 MHz) | Cảnh báo |
|---|---|---|---|---|---|---|
| N2-S, P = 1 | 1.476 (8 %) | 1.082 | 6/46 (14 %) | 2,25/24 (10 %) | **105,58 MHz** | 0 |
| N2-S, P = 4 | 1.870 (10 %) | 1.272 | 6/46 (14 %) | 2,25/24 (10 %) | **91,25 MHz** | 0 |

So với mục tiêu:
- **RA-07:** Fmax ≥ 55 MHz. Đạt.
- **RA-08:** Logic ≤ 20 %, BSRAM ≤ 25 %, DSP ≤ 25 %. Đạt.
- **RB-06 (tầng 3):** Fmax ≥ 100 MHz. Đạt với P = 1, chưa đạt với P = 4.

Chưa nạp lên chip.
