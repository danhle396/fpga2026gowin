# Mũ bảo hộ phát hiện té ngã — VKU-NewBie

MPU6050 trên mũ → SONiX SN32F407 (EVK V1.0) → SPI → Kiwi Primer 20K (Gowin GW2A-18C) chạy 1D-CNN INT8 bằng RTL tự viết → Safety FSM trên MCU → còi tại chỗ.

| Tài liệu | Nội dung |
|---|---|
| [CLAUDE.md](CLAUDE.md) | **Đọc đầu tiên mỗi phiên AI**: cách bắt đầu phiên, luật, cách thay phiên giữa nhiều máy và nhiều tài khoản Claude, công cụ cần cài |
| [PROJECT_MASTER.md](PROJECT_MASTER.md) | Kế hoạch, cổng G0–G7, danh sách việc, **Phụ lục A = SPEC v3 (luật)**, chân và nối dây (Phụ lục E) |
| [DE_CUONG_v2.md](DE_CUONG_v2.md), [THAY_DOI_SO_VOI_v1.md](THAY_DOI_SO_VOI_v1.md) | Đề cương nộp BTC và các thay đổi |
| [docs/huong_dan_dot_B.md](docs/huong_dan_dot_B.md) | **Làm gì khi cầm board**: 8 bước có Pass |
| [docs/data_protocol.md](docs/data_protocol.md) | Quy trình thu dữ liệu trên mũ (D2, D3) |
| [docs/bao_cao/](docs/bao_cao/) | Bằng chứng theo ngày cho mọi việc đã đánh [x] |

## Thư mục

| Thư mục | Nội dung |
|---|---|
| `firmware/` | Firmware chính SN32F407: Keil `keil/fw.uvprojx` hoặc `bash firmware/build.sh` ([README](firmware/README.md)) |
| `Document Board Kiwi Primer 20K/Kiwi20K_FallDetection_FPGA/` | Project Gowin của nhóm: engine E1, `fpga_top` (giao thức PROTO 1) |
| `rtl/v3/` | Top giao thức v3 (CRC-16, SEQ, STATUS, RST_N), `tb_proto`, script P&R |
| `rtl/e2/` | Engine E2 (1 chu kỳ/MAC, P làn), `tb_e2` |
| `rtl/tb/` | `run_all.sh`, `tb_top_spi`, `tb_e1_layers` |
| `rtl/gl/` | Mô phỏng netlist sau P&R (`run_gl.sh`, stub rPLL cho Icarus) |
| `rtl/pin_probe/` | Bitstream dò chân J1 |
| `bitstreams/` | **3 bitstream dựng sẵn** để nạp thẳng: PROTO 1 + E1 (đợt B), v3 + E1, v3 + E2 + N2 ([README](bitstreams/README.md)) |
| `ml/src/` | `golden_model.py` (đáp án số nguyên), `cnn_numpy.py`, `rom_layout.py`, `safety_model.py` |
| `ml/train_cnn.py` | Huấn luyện N1 / N2 / N2-S / N2-L bằng numpy, LOSO, xuất INT8 |
| `ml/data/public/` | Bộ D1 (Özdemir & Barshan) đã chuyển về SPEC; thêm kênh ngực, thắt lưng chỉ để huấn luyện (`--train-only`) |
| `tools/` | Công cụ: kiểm SPEC, xuất ROM, sinh vector, phát lại, HIL, ghi log, mô phỏng ghép |
| `test_sensor/` | Bộ test MPU6050 (FW-02) |

## Chạy các bộ kiểm (không cần board)

```bash
python tools/verify_spec_v3.py ml/src "FPGA_Fall_Detection_AI-20261012T141515Z-1-001/FPGA_Fall_Detection_AI/fpga_export"  # golden: TẤT CẢ PASS
bash rtl/tb/run_all.sh                                   # 7 testbench RTL (Icarus -g2001), ≈ 4,5 phút
bash firmware/build.sh test && python tools/m0_test.py   # firmware C trên Cortex-M0 giả lập (pip install unicorn)
python tools/cosim.py --e2 ml/out/e2_matrix/n2_11_p1     # ghép firmware ↔ RTL trên dữ liệu ngã thật (mô hình của bitstream 3)
bash rtl/v3/run_tb_proto.sh --ng 50                       # giao thức v3 qua chân SPI, 50 khung + 7 kịch bản lỗi
bash rtl/gl/run_gl.sh <thư mục> ml/out/e2_matrix/n2_11_p1 3  # NETLIST sau P&R của Gowin (gate-level), 10–30 phút
```

Trước khi chạy `cosim.py`, tạo thư mục xuất:

```
python tools/export_mem.py --params ml/out/n2s_d1/params_int8.npz --engine e2 --lanes 1 --out ml/out/e2_matrix/n2s_p1
```

## Chuỗi mô hình → phần cứng

**Mô hình của bitstream 3 là `ml/out/n2_11_d1/`** (N2 chỉ kênh đầu, D1 11 người, seed 20261014; xuất E2 ở `ml/out/e2_matrix/n2_11_p1/`). Các mô hình khác trong `ml/out/*_d1/` (`n1_d1`, `n2_d1`, `n2s_d1`, `n2t_d1`) được huấn luyện ngày 13–15/10 trên **6 người 101–106**, chỉ giữ để đối chiếu. Lưu ý:
- Không có `--out`, lệnh dưới **ghi đè** `ml/out/<arch>_d1/`. Thử nghiệm thì đặt `--out` ra ngoài repo.
- `--subjects 101 102 103 104 105 106` chọn lại đúng 6 người cũ.
- Huấn luyện lại chỉ tái lập về mặt thống kê, không tái lập từng bit, vì số thực float khác nhau giữa các máy. Nguồn cố định cho RTL và firmware là `params_int8.npz` và các file `.mem` đã lưu.

```bash
python ml/train_cnn.py --arch n2s                        # LOSO + mô hình cuối → ml/out/n2s_d1/
python tools/export_mem.py --params ml/out/n2s_d1/params_int8.npz --engine e2 --lanes 1 --out <thư mục>
bash rtl/e2/run_tb_e2.sh <thư mục> 50                    # RTL E2 so từng tầng với golden
python tools/playback_d1.py --model ml/out/n2s_d1         # phát lại qua Safety FSM
```

Weight E1 (N1) cho project Gowin:

```
python -I tools/gen_cnn_params.py --export <fpga_export>   # ghi src/cnn_params.vh, tb/vec_*.mem
```

## Công cụ máy

Gowin EDA V1.9.11.03 Education · Keil MDK-ARM 5.43 (Arm Compiler 6.24) · Icarus Verilog 0.9.7 hoặc 12.0 · Python 3 với numpy (thêm pyserial cho board; unicorn cho kiểm firmware trên PC; matplotlib cho hình).
