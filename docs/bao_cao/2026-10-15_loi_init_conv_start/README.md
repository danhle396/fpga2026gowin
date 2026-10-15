# 2026-10-15 — Lỗi: engine conv tự chạy lúc bật nguồn (`conv_start` có INIT = 1). Tìm bằng mô phỏng netlist, đã sửa

## Triệu chứng

Mô phỏng netlist sau P&R của **bitstream 1** (`fpga_top`, PROTO 1, E1) bằng `tb_top_spi` (`gl_bitstream1_cu_FAIL.log`):

```
khung 0: IRQ sau 622607 chu ky; doc 5a 00 00 00 01 6d 11; mong doi 5a 00 00 00 02 73 74  FAIL
khung 1, 3, 4: IRQ sau 699781 chu ky, khớp golden                                        PASS
khung 2 (CRC sai): không IRQ                                                              PASS
```

Bitstream 2 (`fpga_top_v3` + E1) cũng hỏng tương tự: khung đầu ra CYCLES 621.708 thay vì 699.800, sai 6 byte. Mô phỏng RTL thì PASS ở cả hai.

Hai con số khớp nhau đúng từng chu kỳ:
- 622.607 + 77.174 = 699.781, tức đúng một lần suy luận E1.
- 77.174 chu kỳ ≈ thời gian ghi một khung 771 byte ở SCK 4 MHz.

Nghĩa là engine **đã bắt đầu suy luận từ lúc bật nguồn**, trước khi khung 0 tới. Kết quả của khung đầu vì thế tính trên bộ đệm còn đang được ghi dở.

## Nguyên nhân

`probe_tb_top_spi.v` dò netlist (`probe_trang_thai_luc_bat_nguon.log`): FSM của `conv1d_engine` đi CLEAR → ISSUE → WAIT → MAC ngay từ chu kỳ đầu, trong khi `cnn_controller` vẫn ở IDLE.

Trong netlist (`netlist_cu_conv_start_DFFS_INIT1.txt`):

```
DFFS \u_cnn_core/u_controller/conv_start_s1 ( ... .Q(\u_cnn_core/conv_start_Z ) );
defparam \u_cnn_core/u_controller/conv_start_s1 .INIT=1'b1;
```

- `cnn_controller.v` khai báo `output reg conv_start` **không có giá trị khởi tạo**. GowinSynthesis được phép tự chọn INIT, và đã chọn FF loại set với `INIT = 1`.
- Trên chip, mọi FF nhận giá trị INIT khi nạp cấu hình (GSR). Vậy vừa cấu hình xong, `conv_start = 1` trong một chu kỳ, đủ để kích engine conv.
- Mô phỏng RTL không thấy lỗi: ở đó `conv_start` mang giá trị `X`, và `if (start)` với `X` được coi là sai.

**Ảnh hưởng nếu nạp lên board:**
- Khung đầu tiên sau mỗi lần cấp nguồn hoặc nạp lại FPGA cho kết quả sai.
- Đó chính là khung **tự kiểm A.10** lúc firmware khởi động. Ở bước B8, firmware sẽ báo FAIL dù mọi thứ khác đúng.
- Ở B7, thống kê sẽ là 99/100.
- Bitstream 3 (E2) không bị: netlist của nó không có FF điều khiển nào mang INIT = 1 ngoài các khởi tạo cố ý.

## Sửa

Khởi tạo 0 cho mọi thanh ghi điều khiển. Danh sách trong `sua_src_nhom.diff`.

**Project nhóm** (`src/`, không đụng `impl/`):

| File | Thanh ghi |
|---|---|
| `cnn_controller.v` | `conv/pool/gap/dense_start`, `conv/pool_layer_sel`, `busy`, `inference_done`, `stage` |
| `conv1d_engine.v`, `gap_engine.v`, `maxpool1d_engine.v` | `busy`, `done`, `output_valid` |
| `dense_engine.v` | `busy`, `done` |
| `packet_parser.v` | `data_we`, `payload_done`, `crc_error` |
| `spi_result_tx.v` | `read_done` |
| `spi_slave.v` | `rx_valid` |

Cú pháp là `output reg x = 0`: Verilog-2001, Icarus 0.9.7 và GowinSynthesis đều nhận.

**`rtl/v3/packet_parser_v3.v`:** `data_we`, `payload_done`, `frame_err`. Bản dựng lần này Gowin đã tự chọn 0 cho các thanh ghi này, nhưng không có gì bảo đảm lần dựng sau cũng vậy.

## Kiểm sau khi sửa

| Kiểm | Kết quả |
|---|---|
| `rtl/tb/run_all.sh` (RTL) | 7/7 PASS |
| `run_tb_proto.sh --e2 n2_p1 --ng 10` (RTL) | PASS |
| `cosim.py --e2 n2_p1`: firmware → RTL (parser v3 đã sửa) → firmware, 6 bản ghi D1 (`cosim_n2_sau_sua.log`) | 423/423, FSM trùng golden |
| Netlist bitstream 1, `tb_top_spi` (`gl_bitstream1_da_sua_PASS.log`) | **5/5 PASS**, khung 0: 699.781 chu kỳ, khớp golden |
| Netlist bitstream 2, `tb_proto` 1 khung + 7 kịch bản | PASS, CYCLES 699.800 |
| Netlist bitstream 3, `tb_proto` 3 khung + 7 kịch bản | PASS, CYCLES 258.080 |
| FF có INIT = 1 trong netlist mới | Chỉ còn khởi tạo cố ý: `cs_sync = 111`, CRC-16 `= FFFF`, `rst_sync = 111`, trạng thái đầu `S_IGNORE` của parser v3, `L = 128` của E2. Riêng `top2[31]`, `f[2]` của `result_frame_v3` luôn được gán trước khi dùng (kịch bản "đọc khi chưa có kết quả" PASS) |
| Dựng bản phát hành (không có tùy chọn netlist) so với bản đã mô phỏng | `.fs` trùng bit, trừ dòng `Created Time` |

Bitstream mới:
- **1:** Logic 907 (5 %), 105,20 MHz.
- **2:** Logic 1.521 (8 %), 103,01 MHz.
- **3:** không đổi, file giữ nguyên.

`bitstreams/*/SHA256.txt` đã cập nhật. Công suất ước lượng không đổi (156,5 / 157,2 mW).

## Phòng lặp lại

- `rtl/gl/run_gl.sh` nay in danh sách FF có INIT = 1 sau mỗi lần dựng. Mỗi dòng phải ứng với một khởi tạo cố ý trong RTL.
- Quy tắc cho RTL mới: mọi thanh ghi phát xung (start, done, valid, we, irq) phải có giá trị khởi tạo, hoặc có reset.
