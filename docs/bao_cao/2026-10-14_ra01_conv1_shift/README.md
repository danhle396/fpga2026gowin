# AI-01 + RA-01 (X3, R1, R8): chốt `conv1_shift` = 8, một nguồn tham số — 2026-10-14

## Kết luận

`conv1_shift = 8`, `conv2_shift = 8`, giữ đúng như `quant_params.json` của nhóm AI. Nguồn duy nhất là `quant_params.json`; `tools/gen_cnn_params.py` sinh `src/cnn_params.vh` (RTL) và `tb/vec_*.mem` (testbench). Golden model và `verify_spec_v3.py` cũng đọc shift từ json. RTL khớp golden **20/20**; P&R không vượt số cũ.

## 1. Chọn shift bằng số liệu (`shift_compare.py`, `shift_compare.log`)

Golden model số nguyên, mô hình SisFall của nhóm (4 lớp), tách người. Chỉ đổi `conv1_shift`.

| Tập | shift | Accuracy | Macro-F1 | Recall FALL | Bão hòa 127 ở l1 |
|---|---|---|---|---|---|
| validation (3.479 cửa sổ) | 7 | 96,26 % | 0,9034 | 97,51 % | 0,475 % |
| validation | **8** | 95,66 % | 0,8892 | 96,89 % | 0,035 % |
| test (3.549 cửa sổ) | 7 | 94,59 % | 0,8308 | 97,78 % | 0,367 % |
| test | **8** | 94,39 % | 0,8446 | 96,71 % | 0,022 % |

Hai shift cho cùng nhãn ở 98,02 % (val) và 97,75 % (test) số cửa sổ.

Lý do chọn 8:
1. Chênh lệch về độ chính xác nhỏ (≤ 1,1 điểm) và **không cùng chiều**: Macro-F1 nghiêng về 7 trên validation (+0,014) nhưng về 8 trên test (+0,014). Không có bằng chứng 7 tốt hơn.
2. 8 là giá trị mà bước xuất của nhóm AI tính ra, và `golden_vectors.npz` được sinh với 8. Chọn 7 phải sửa file xuất của đồng đội và sinh lại vector mà không có notebook để biết vì sao.
3. Shift 7 làm tỉ lệ kích hoạt chạm trần 127 tăng 13–17 lần (0,035 % → 0,475 % ở l1).
4. Mô hình SisFall chỉ dùng để thông chuỗi SPI/HIL (RA-04, RA-05); AI-07 sẽ thay weight và shift, và giá trị mới đi thẳng qua json → `.vh` mà không phải sửa tay RTL.

Đường lùi: sửa một số trong `quant_params.json`, xuất lại `golden_vectors.npz`, chạy `gen_cnn_params.py` rồi testbench.

Lưu ý cho chỉ tiêu "FP32 → INT8 giảm ≤ 2 điểm %": với shift 8, recall FALL trên test của SisFall giảm 2,05 điểm so với FP32 (98,76 % → 96,71 %), vượt mức 2 điểm 0,05. Chỉ tiêu áp cho mô hình cuối (AI-09), không cho mô hình SisFall này.

## 2. Một nguồn tham số

- `tools/gen_cnn_params.py`: đọc json + `weights.mem` + `bias.mem` + `golden_vectors.npz` của thư mục export; tính lại 20 vector bằng `ml/src/golden_model.py` với shift của json; **dừng (mã thoát 1) nếu không khớp 20/20** hoặc json mâu thuẫn với E1 (GAP >> 5, 3.168 weight, 52 bias).
- Phép âm (`gen_negative.log`): bản sao json với `conv1_shift = 7` → `FAIL ... chỉ khớp 0/20`, không ghi file nào.
- `src/fpga_top.v`: `` `include "cnn_params.vh" ``, cổng shift nối `` `CNN_CONV1_SHIFT ``, `` `CNN_CONV2_SHIFT `` thay cho hằng `5'd7`, `5'd8`.
- `verify_spec_v3.py` đọc shift từ json: vẫn "TẤT CẢ PASS" (`verify_spec_v3.log`).

## 3. Testbench 20 vector (`tb20_shift8_pass.log`, `tb20_am_shift7.log`)

`tb_cnn_core_golden.v` viết lại: 20 vector thay cho 1, Verilog-2001, include `cnn_params.vh`, tự so 4 logit + lớp, in `FAIL tai vector v phan tu i: mong doi X, nhan Y`. Chạy trên bản sao project bằng Icarus 0.9.7 (`run_tb20.sh`): `iverilog -g2001 -I src`.

- shift 8: **20/20 khớp**, 699.800 chu kỳ mỗi lần suy luận (= 13,96 ms ở 50,143 MHz).
- Phép âm, ép `.vh` về shift 7: 0/20, 83 phần tử sai. Testbench bắt được lỗi R1.

`run_golden_sim.bat` sửa R8 (`-g2012` → `-g2001`), thêm bước sinh tham số, bỏ giá trị mong đợi cũ (logit 1431 253 316 −15 của shift 7).

## 4. P&R trên bản sao (`pnr_build.tcl`, `fpga_project.rpt.txt`, `fpga_project_timing.html`, `fpga_project.pin.html`, `fpga_project.power.html`)

Gowin EDA V1.9.11.03, cùng chân J1. GowinSynthesis tìm thấy `src/cnn_params.vh` mà không cần khai đường dẫn include.

| | 13/10 (shift 7) | 14/10 (shift 8) |
|---|---|---|
| Logic | 923/20.736 (5 %) | 913/20.736 (5 %) |
| Register | 590 | 589 |
| BSRAM | 6/46 | 6/46 |
| DSP | 1,25/24 | 1,25/24 |
| Fmax (clock 50,143 MHz) | 101,86 MHz | 108,49 MHz, 3 tầng logic |
| Công suất (ước lượng công cụ) | 156,5 mW | 156,5 mW (tĩnh 122,8 + động 33,7) |

Sáu cổng vẫn đúng ball (H11, K14, K12, J12, J13, H12), LVCMOS33. Fmax đổi chủ yếu do kết quả đặt và đi dây thay đổi giữa hai lần chạy; logic chỉ khác hằng số dịch.
