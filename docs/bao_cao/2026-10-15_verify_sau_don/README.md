# 2026-10-15 — Verify toàn dự án sau khi dọn thư mục, và mô phỏng netlist sau P&R

Chạy lại mọi bộ kiểm có thể chạy không cần board, sau khi xóa sản phẩm build và các file thừa (Phụ lục D, dòng "Dọn thư mục"). Mọi lệnh chạy trên bản sao trong thư mục tạm, không ghi `.vvp` hay log vào cây dự án.

## 1. Kiểm tĩnh

| Kiểm | Kết quả |
|---|---|
| `py_compile` 24 file Python | 0 lỗi |
| `--help` của mọi công cụ trong `tools/`, `ml/`, `test_sensor/tools/` | 3 công cụ lỗi rồi đã sửa (mục 4); sau sửa, tất cả chạy |
| `iverilog -g2001 -Wall`: top v3 + E1, `cnn_e2.v` | 0 cảnh báo |
| `armclang` (`build.sh`, `build.sh test`, `test_sensor`) | 0 lỗi; 1 cảnh báo, nằm trong `system_SN32F400.c` của gói DFP SONiX, không phải mã của nhóm |
| Keil `UV4 -r` `fw.uvprojx` / `mpu6050_test.uvprojx` (`keil_*.log`) | 0 lỗi, 0 cảnh báo; Code 15.184 + RO 1.480 / Code 14.756 + RO 2.028 byte |

## 2. Kiểm động

| Kiểm | Kết quả | Log |
|---|---|---|
| `verify_spec_v3.py` (golden SPEC v3.1) | TẤT CẢ PASS | `verify_spec_v3.log` |
| `m0_test.py`: firmware C chạy bằng mã máy Cortex-M0 trong Unicorn | TẤT CẢ PASS | `m0_test.log` |
| `rtl/tb/run_all.sh`, 7 testbench, Icarus 0.9.7 | 7/7 PASS | `run_all.log` |
| `tb_e2` trên **cả 14** bản xuất `ml/out/e2_matrix/` (N1 nhóm, N2, N2-S, N2-L × P = 1/2/4; tie × P = 1/4), so từng tầng | 14/14 PASS | `tb_e2_ma_tran_14.log` |
| `tb_proto` v3, E1, 50 khung + 7 kịch bản | PASS, CYCLES 699.800 | `tb_proto_v3_e1_50.log` |
| `tb_proto` v3, E2 + N2, 20 khung + 7 kịch bản | PASS | `tb_proto_v3_e2_n2_20.log` |
| `cosim.py --e2 n2_p1`: firmware → RTL → firmware trên 6 bản ghi D1 | 423/423, FSM trùng golden | `cosim_n2_p1_6_ban_ghi.log` |
| `hil_test.py --mock`, PROTO 1 và 3; phép âm `--mock-error 7` | 200/200 khớp; phép âm FAIL đúng chỗ | — |
| `check_frames.py --file` trên luồng TRC dựng từ **mã máy firmware** (`mk_trc.py`) | 1.283/1.283 → PASS; phép âm CRC sai → FAIL; phép âm mất 1 mẫu → FAIL | `check_frames_*.log` |

## 3. Khả năng tái tạo

| Kiểm | Kết quả |
|---|---|
| `export_mem.py` xuất lại `n2_p1`, `n2s_p1`, `n2s_p4` từ `params_int8.npz` | trùng từng byte với bản lưu |
| `convert_d1.py` chuyển lại D1 (cảm biến 340540) từ file gốc | `d1_windows.npz` trùng từng byte |
| `gen_cnn_params.py` cho project nhóm | weights / bias / vector trùng byte. Chỉ `src/cnn_params.vh` có thêm dòng `CNN_SCORE_SHIFT 0` (do script sinh từ 15/10). Nay trùng file của bitstream 1 |
| Dựng lại bitstream 3 (`pnr_v3.sh e2 n2_p1`) | Logic 1.474, BSRAM 8, DSP 2,25, Fmax 107,253 MHz như bản lưu. `.fs` chỉ khác dòng `Created Time` |
| `sha256sum -c` cả 3 bitstream | OK |
| `cnn_params.vh` của bitstream 3 với `e2_matrix/n2_p1` | trùng |

## 4. Mô phỏng netlist sau P&R (mới)

Trước đây mọi kiểm RTL đều chạy trên mã Verilog nguồn. Lần này kiểm **netlist mà Gowin thật sự đặt lên chip**. Phép kiểm này bắt được những lỗi mà mô phỏng RTL không thấy được:
- `$readmemh` không được nạp vào ROM;
- suy luận BSRAM/DSP sai;
- tổng hợp bỏ mất logic.

- Netlist `.vg` của bản Education bị mã hóa (`pragma protect`). Tùy chọn `set_option -gen_verilog_sim_netlist 1` thì cho `impl/pnr/fpga_project.vo` **không mã hóa**. Nay bật bằng `SIM_NETLIST=1` trong `rtl/v3/pnr_v3.sh`.
- Netlist có 5 khối `pROM` mang `INIT_RAM_xx`, nghĩa là Gowin **đã nhúng weight/bias** vào ROM. Ngoài ra có 3 `SDPB`, 4 `RAM16SDP4`, 2 `MULTADDALU18X18`, 1 `rPLL`.
- Mô hình `rPLL` trong `prim_sim.v` dùng mảng `real` mà Icarus 0.9.7 không dịch được. Thay bằng `rtl/gl/rpll_stub.v` (CLKOUT = CLKIN, đủ tham số), giống cách mô phỏng RTL dùng `pll_50m_sim.v`.
- **Bitstream 3 (E2 + N2), `tb_proto` gate-level, 3 khung + 7 kịch bản: PASS.** CYCLES = 258.080 (`gl_proto_netlist_e2_n2_ng3.log`, 1.815 s).
- **Phép âm:** lật 1 bit của một weight trong `INIT_RAM_00` của `.vo` → **FAIL, 2 byte logit sai** (`gl_proto_phep_am_lat_1_bit_weight.log`). Phép kiểm netlist so tới từng bit của nội dung ROM.
- Chạy lại: `bash rtl/gl/run_gl.sh <thư mục> ml/out/e2_matrix/n2_p1 [NG]`. Đã chạy trọn script với NG = 1: PASS, 562 s gồm cả P&R (`run_gl_sh_ng1.log`). Netlist chạy khoảng 2.000–5.000 chu kỳ/s.
- **Bitstream 1, 2 (làm tiếp cùng ngày):** netlist của cả hai **FAIL ở khung đầu tiên sau khi bật nguồn**, vì `conv_start` có INIT = 1. Đã sửa RTL và dựng lại hai bitstream; netlist mới PASS. Xem [`../2026-10-15_loi_init_conv_start/`](../2026-10-15_loi_init_conv_start/README.md).
- **Chưa làm:** mô phỏng có thời gian (SDF).

## 5. Lỗi tìm thấy và đã sửa

| File | Lỗi | Sửa |
|---|---|---|
| `tools/convert_d1.py`, `tools/logger.py` | `--help` (và mọi dòng in tiếng Việt trước khi gọi `reconfigure`) chết vì console cp1252 | gọi `sys.stdout.reconfigure` ở đầu `main()` |
| `tools/plot_d1.py` | đọc thẳng `sys.argv`, nên `--help` bị coi là tên file | dùng argparse |
| `tools/check_frames.py` | (a) mất mẫu mà CRC đúng thì in "chưa đủ…" và trả mã 0, dù Pass của FW-10 đòi 0 mất mẫu; (b) khung không tìm được cửa sổ thì không được ghi là "khung sai đầu tiên", nên báo sai chỗ | (a) FAIL, mã 1; (b) ghi lại, in "không có cửa sổ tương ứng" |
| `tools/gen_tb_proto.py` | in `np.int64(3)` | in số thường |
| `Kiwi20K_FallDetection_FPGA/src/cnn_params.vh` | thiếu dòng `CNN_SCORE_SHIFT` so với bitstream 1. Không ảnh hưởng chức năng: chỉ `fpga_top_v3` dùng macro này, và mặc định là 0 | chạy lại `gen_cnn_params.py` |
