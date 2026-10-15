# 2026-10-15 — Máy thứ hai (DESKTOP-A00FJKC): RB-01 trên Icarus 12, dựng lại bitstream 1

Repo clone từ GitHub `danhle396/fpga2026gowin` sang một máy khác máy gốc. Máy này ban đầu có Gowin EDA V1.9.11.03 Education và Keil MDK 5.43 (pack SONiX.SN32F4_DFP 1.1.1, CMSIS 6.3.0), **không có Python và Icarus**. Đã cài bằng `winget`:

- `Python.Python.3.12` 3.12.10 (cài cho user), venv `C:\Users\nhath\venvs\fpga2026` với numpy 2.5.4, matplotlib, pyserial, pymupdf, pypdf, unicorn 2.1.4. Trong venv có thêm bản chép `python3.exe`, vì `command -v python3` của Git Bash bắt trúng alias Microsoft Store trước.
- `Icarus.Verilog` **12.0** (s20150603-1539-g2693dd32b), cài vào `C:\iverilog\bin`, đúng đường dẫn script tự thêm vào PATH.

## Kết quả

| Việc kiểm | Lệnh | Kết quả | Log |
|---|---|---|---|
| **RB-01, nửa "bản mới"** | `bash rtl/tb/run_all.sh` (Icarus 12.0) | **7/7 PASS**, ≈ 9,7 phút | `run_all_icarus12.log`, `tb_*_icarus12.log` |
| SPEC v3 | `tools/verify_spec_v3.py` | TẤT CẢ PASS | `verify_spec_v3.log` |
| Firmware C thuần trong Unicorn | `firmware/build.sh test` + `tools/m0_test.py` | TẤT CẢ PASS (53/53 ca FSM, FW-15 50/50 × 4 mô hình, app_core 402 kết quả) | `m0_test.log` |
| Firmware chính | `UV4.exe -r firmware/keil/fw.uvprojx` | 0 lỗi, 0 cảnh báo; Code 15.360, RO 1.680, RW 4, ZI 5.416 (trùng máy gốc) | `keil_fw_uv4.log` |
| Dựng lại bitstream 1 | `SIM_NETLIST=1 rtl/v3/pnr_v3.sh … p1` (trong `rtl/gl/run_gl.sh`) | `.fs` **trùng từng dòng** với `bitstreams/1_e1_proto1_sisfall/fpga_project.fs`, chỉ khác dòng `Created Time`; Logic 907, Register 589, BSRAM 6/46, DSP 1,25/24, Fmax 105,196 MHz; FF INIT = 1 chỉ có `cs_sync` (cố ý) | `bitstream1_diff.txt`, `bitstream1_dung_lai.rpt.txt` |
| SHA-256 3 bitstream | `sha256sum -c SHA256.txt` | OK × 3 | — |

Thời gian từng testbench trên Icarus 12 (máy này): tb_pin_probe 1 s, tb_top_spi 70 s, tb_cnn_core_golden 222 s, tb_e1_layers 109 s, tb_proto_v3_e1 128 s, tb_e2 P = 1 33 s, P = 4 20 s.

## Khác biệt so với Icarus 0.9.7

Icarus 12 in 7 cảnh báo `$readmemh(...): Too many words in the file for the requested range` ở `tb_e1_layers.v` và `rtl/e2/tb_e2.v`. Nguyên nhân: `export_mem.py` xuất 50 vector, còn `run_all.sh` chạy hai testbench này với `TB_NV=10` nên mảng chỉ chứa 10 vector. Hành vi đúng như ý (đọc 10 vector đầu); 0.9.7 không báo. Không sửa.

## Kết luận

- **RB-01 đạt Pass**: `run_all` chạy được và PASS trên cả Icarus 0.9.7 (máy gốc, 14–15/10, [2026-10-14_rb01_run_all](../2026-10-14_rb01_run_all/)) lẫn Icarus 12.0 (máy này).
- Bitstream 1 dùng cho đợt B dựng lại được trên máy thứ hai, nội dung không đổi, nên không phụ thuộc vào máy gốc.
- TH-01 (repo Git, cả nhóm clone được): đã có thêm một máy clone và chạy được cả chuỗi kiểm. Vẫn **chưa đánh [x]**, vì Pass yêu cầu cả nhóm clone được, và còn thiếu `docs/spec.md`.
