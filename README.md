# Thiết bị đeo ngực phát hiện té ngã — VKU-NewBie

MPU6050 trên dây đeo ngực → SONiX SN32F407 → UART → ESP32 → SPI → Kiwi Primer 20K (Gowin GW2A-18C) chạy 1D-CNN INT8 bằng RTL tự viết → Safety FSM + xác nhận ngã thật → còi + trang web. Chạy pin; phần cứng của nhóm đã nối cố định (đề cương v2.2). Đề cương nộp BTC ghi mũ bảo hộ; từ 28/10 nhóm chuyển sang đeo ngực và chốt đề tài trên vị trí này.

## Kết quả chốt (28/10)

- Chạy thông trên board bằng pin: tự kiểm FPGA PASS, mẫu đều, mất 0, FPGA trả OK mọi khung.
- **Chỉ báo ngã thật** (`firmware/src/nga.c`, SPEC A.12): CNN 2/3 cửa sổ FALL chỉ là bước nghi; báo ngã khi đủ 4 dấu hiệu: trước đó thẳng, va chạm ≥ 2,5 g, ngực quay ≥ 220 °/s, ngực nghiêng ≥ 45°.
- Log đeo ngực của nhóm: ngồi phịch xuống ghế báo nhầm 0/10, cả log động tác (cúi, đi, nằm xuống, ngồi dậy, lăn) báo nhầm 0, ngã lên nệm 14/15, 9 tư thế nhận đúng 9/9. Ngưỡng chọn trên chính log này (một người, một buổi).
- Không báo theo thiết kế: ngã kết thúc quỳ / ngồi mà thân vẫn thẳng.
- CNN N2 trên FPGA học từ D1 kênh đầu, 11 người: LOSO Macro-F1 0,983; chưa huấn luyện lại cho kênh ngực.
- Kiểm không cần board: `fpga/scripts/test.sh`, `m0_test`, `sync_spec` đều PASS.

Chi tiết: [PROJECT_MASTER.md](PROJECT_MASTER.md) (TRẠNG THÁI), [docs/bao_cao/2026-10-28_chot_ket_qua/](docs/bao_cao/2026-10-28_chot_ket_qua/README.md), [docs/bao_cao/2026-10-28_nga_that/](docs/bao_cao/2026-10-28_nga_that/README.md).

## Nạp và chạy

| Board | Project | Vai trò |
|---|---|---|
| **FPGA** Kiwi Primer 20K | `fpga/fpga_project.gprj` (Gowin IDE: Run All). Bản dựng sẵn: `fpga/bitstream/fpga_project.fs` | Nhận cửa sổ 128 × 6 mẫu INT8, chạy CNN (engine E2, 5,15 ms), trả lớp + điểm |
| **ESP32** | `esp32/mu_nga_hub/mu_nga_hub.ino` (Arduino IDE, ESP32 Dev Module) | Tách khung UART (chịu nhiễu, chèn bù mẫu mất), đổi trục cảm biến → trục người khi đeo ngực, tiền xử lý, cửa sổ, khung SPI v3, hỏi vòng FPGA, bỏ phiếu + Safety FSM, xác nhận ngã thật, tư thế, MẤT CẢM BIẾN, lệnh còi, trang web, log USB + WiFi TCP 3333 |
| **MCU** SN32F407 EVK | `firmware/keil/fw.uvprojx` (Keil: F7, F8) | Đọc MPU6050 100 Hz, hiệu chuẩn gyro, gỡ bus I²C và cấu hình lại khi cảm biến không trả lời, gửi từng mẫu + nút sang ESP32; nhận lệnh còi từ ESP32, kêu PZ1 2 kHz |

Xem dữ liệu: mở `http://<IP ESP32>` trên điện thoại hoặc laptop cùng WiFi (trang web do ESP32 phục vụ: trạng thái, tư thế hiện tại và lịch sử, kết quả CNN, biểu đồ gia tốc, thống kê, sự kiện, nút hủy). Nguồn MPU6050 lấy từ 3,3 V của ESP32; khi web báo MẤT CẢM BIẾN mà cảm biến treo thì rút pin ≈ 5 s rồi cắm lại. Từng bước, cách ghi log và lỗi hay gặp: **[docs/huong_dan_nap_chay.md](docs/huong_dan_nap_chay.md)**.

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
| [PROJECT_MASTER.md](PROJECT_MASTER.md) | Trạng thái chốt, kế hoạch, cổng G0–G7, danh sách việc, **Phụ lục A = SPEC v3.4** (A.12 xác nhận ngã thật), nối dây (Phụ lục E), nhật ký (Phụ lục D) |
| [docs/bao_cao_cuoi/BAO_CAO_KY_THUAT_nhap.md](docs/bao_cao_cuoi/BAO_CAO_KY_THUAT_nhap.md) | Bản nháp báo cáo kỹ thuật (đeo ngực, kết quả 28/10) |

## Kiểm không cần board

```bash
bash fpga/scripts/test.sh                                 # RTL: mô hình trong fpga/src, tb_e2 P=1/4, tb_proto 10 khung + 7 kịch bản, lõi ESP32
bash firmware/build.sh test && python -I tools/m0_test.py # C trên Cortex-M0 giả lập (pip install unicorn numpy): TẤT CẢ PASS
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
python -I tools/playback_log.py ml/data/raw               # chấm buổi thử (file của logger.py)
```

Thu và chấm log khi đeo ngực (laptop cùng WiFi với ESP32):

```bash
python -I tools/ghi_uart.py --tcp <IP ESP32> --lenh LOG --buoc dong_tac --kich-ban dong_tac   # động tác dễ nhầm, có lời nhắc từng bước
python -I tools/ghi_uart.py --tcp <IP ESP32> --lenh LOG --buoc nga --kich-ban nga             # ngã lên nệm dày, có người đỡ
python -I tools/nga_tren_log.py ket_qua_board/<file>.txt                                     # chạy lại lõi ESP32 trên log: CNN nghi / nga.c loại / báo ngã
python -I tools/truc_cam_bien.py ket_qua_board/<file>.txt --da-doi                           # kiểm hướng cảm biến từ log tư thế
```
