# Mũ bảo hộ phát hiện té ngã — VKU-NewBie

MPU6050 trên mũ → SONiX SN32F407 → UART → ESP32 → SPI → Kiwi Primer 20K (Gowin GW2A-18C) chạy 1D-CNN INT8 bằng RTL tự viết → Safety FSM → báo động. Phần cứng của nhóm đã nối cố định (đề cương v2.2).

## Nạp và chạy

| Board | Project | Vai trò |
|---|---|---|
| **FPGA** Kiwi Primer 20K | `fpga/fpga_project.gprj` (Gowin IDE: Run All). Bản dựng sẵn: `fpga/bitstream/fpga_project.fs` | Nhận cửa sổ 128 × 6 mẫu INT8, chạy CNN (engine E2, 5,15 ms), trả lớp + điểm |
| **ESP32** | `esp32/mu_nga_hub/mu_nga_hub.ino` (Arduino IDE, ESP32 Dev Module) | Tiền xử lý, cửa sổ, khung SPI v3, hỏi vòng FPGA, bỏ phiếu + Safety FSM, nút, log USB + WiFi |
| **MCU** SN32F407 EVK | `firmware/keil/fw.uvprojx` (Keil: F7, F8) | Đọc MPU6050 100 Hz, hiệu chuẩn gyro, gửi từng mẫu + nút sang ESP32 |

Xem dữ liệu: mở `http://<IP ESP32>` trên điện thoại hoặc laptop cùng WiFi (trang web do ESP32 phục vụ: trạng thái, biểu đồ gia tốc, sự kiện, nút hủy). Từng bước, cách ghi log và lỗi hay gặp: **[docs/huong_dan_nap_chay.md](docs/huong_dan_nap_chay.md)**.

## Cấu trúc

```
fpga/            project Gowin của sản phẩm
  src/             RTL (nguồn duy nhất): top v3, SPI, parser, CRC-16, engine E2, rPLL, chân .cst, .sdc, mô hình N2
  sim/             testbench Icarus: tb_proto, tb_e2, tb_stream
  scripts/         build.sh (Gowin), test.sh (Icarus), gl.sh (mô phỏng netlist sau P&R)
  bitstream/       fpga_project.fs + SHA256 + báo cáo P&R
firmware/        mã C: MCU (nút cảm biến) + lõi C dùng chung với ESP32; Keil project, bộ test Cortex-M0
esp32/           sketch ESP32 (lõi C chép từ firmware/src bằng dong_bo_core.sh)
ml/              golden model (đáp án từng bit), huấn luyện, dữ liệu D1, mô hình đang nạp (out/n2_11_d1)
tools/           kiểm thử (m0_test, cosim), xuất weight, phát lại, ghi log (ghi_uart, logger), chấm buổi thử
docs/            hướng dẫn, SPEC, quy trình thu dữ liệu, datasheet, bằng chứng theo ngày (bao_cao/), báo cáo cuối
```

| Tài liệu | Nội dung |
|---|---|
| [CLAUDE.md](CLAUDE.md), [PROMPT_KHOI_CONG.md](PROMPT_KHOI_CONG.md) | Luật làm việc cho mỗi phiên AI, thay phiên giữa nhiều máy |
| [PROJECT_MASTER.md](PROJECT_MASTER.md) | Kế hoạch, cổng G0–G7, danh sách việc, **Phụ lục A = SPEC v3**, nối dây (Phụ lục E), nhật ký (Phụ lục D) |
| [DE_CUONG_v2.md](DE_CUONG_v2.md), [THAY_DOI_SO_VOI_v1.md](THAY_DOI_SO_VOI_v1.md) | Đề cương nộp BTC và các lần điều chỉnh (v2.1, v2.2) |

## Kiểm không cần board

```bash
bash fpga/scripts/test.sh                                 # RTL: mô hình trong fpga/src, tb_e2 P=1/4, tb_proto 10 khung + 7 kịch bản, lõi ESP32
bash firmware/build.sh test && python -I tools/m0_test.py # C trên Cortex-M0 giả lập (pip install unicorn numpy): 22 phép kiểm
python -I tools/cosim.py --e2 ml/out/e2_matrix/n2_11_p1   # firmware ↔ RTL trên dữ liệu ngã thật
python -I tools/sync_spec.py --check                      # docs/spec.md trùng Phụ lục A
bash fpga/scripts/build.sh                                # Gowin: dựng bitstream, so với fpga/bitstream/
bash fpga/scripts/gl.sh                                   # netlist sau P&R (≈ 10 phút)
```

## Mô hình → phần cứng

Mô hình đang nạp: `ml/out/n2_11_d1/` (N2 chỉ kênh đầu, D1 11 người); bản xuất cho engine E2: `ml/out/e2_matrix/n2_11_p1/`, chép vào `fpga/src/` (`cnn_params.vh`, `weights.mem` → `weights_e2.mem`, `bias.mem` → `bias_e2.mem`). Huấn luyện lại chỉ tái lập về thống kê, không tái lập từng bit; nguồn cố định cho RTL và firmware là `params_int8.npz` và các file `.mem` đã lưu.

```bash
python ml/train_cnn.py --arch n2 --out <thư mục>         # LOSO + mô hình cuối (đặt --out ra ngoài repo khi thử)
python -I tools/export_mem.py --params <thư mục>/params_int8.npz --engine e2 --lanes 1 --out <thư mục xuất>
python -I tools/playback_d1.py --model <thư mục>          # phát lại qua Safety FSM
python -I tools/playback_log.py ml/data/raw               # chấm buổi thử trên mũ (file của logger.py)
```
