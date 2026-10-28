# 2026-10-28 — Chốt kết quả đề tài (bản cuối)

Nhóm kết thúc đề tài ngày 28/10 với bản đang chạy trên board. Trang này ghi bản cuối gồm những gì, kết quả kiểm cuối và những điểm còn mở.

## Hệ thống bản cuối

- **Đeo ở ngực**, chạy pin.
- **Luồng:** MPU6050 → SN32F407 (`FW_NODE 1`, chỉ đọc cảm biến) → UART 115200 → ESP32 → SPI → Kiwi Primer 20K (bitstream 3, CNN N2 INT8 trên engine E2) → Safety FSM trên ESP32 → còi PZ1 2 kHz qua MCU, trang web `http://<IP ESP32>/`, log TCP 3333.
- **ESP32** (`esp32/mu_nga_hub`, lõi C trùng `firmware/src`):
  - đổi trục cảm biến → trục người cho vị trí ngực (`FW_VI_TRI_DEO 1`, trừ `ACC_OFF`);
  - nhận dạng tư thế (A.11);
  - **xác nhận ngã thật** (`nga.c` bản 3): đủ 4 dấu hiệu — trước đó thẳng, va chạm ≥ 2,5 g, ngực quay ≥ 220 °/s quanh va chạm, ngực nghiêng ≥ 45° trong 3,84 s sau ([nga_that](../2026-10-28_nga_that/README.md));
  - MẤT CẢM BIẾN: quá 3 s không có mẫu thì web đỏ, còi 2 bíp mỗi 3 s;
  - bộ tách UART chịu nhiễu, chèn bù mẫu mất.
- **Còi** chỉ kêu khi ngã đã được xác nhận, hoặc ALARM do SOS.
- **Nguồn MPU6050** lấy từ 3,3 V của ESP32 (`MPU_NGUON_GPIO 0`). MPU treo thì rút pin ≈ 5 s.

## Kiểm cuối (28/10)

| Phép kiểm | Kết quả | Bằng chứng |
|---|---|---|
| `bash fpga/scripts/test.sh` (RTL: tb_e2, tb_proto, bản sao ESP32 trùng `firmware/src`; Icarus 0.9.7) | TẤT CẢ PASS | [test_rtl.txt](test_rtl.txt) |
| `firmware/build.sh test` + `tools/m0_test.py` (mã máy Cortex-M0 trong Unicorn) | 70/70 PASS, TẤT CẢ PASS | [m0_test.txt](m0_test.txt) |
| `tools/sync_spec.py --check` | PASS | — |
| ESP32 sau khi nạp bản cuối, web `/data` | MONITOR, 20.863 mẫu, mất 0, hỏng 0, FPGA 644/644 OK, timeout 0 | [web_data_sau_khi_nap.json](web_data_sau_khi_nap.json) |

## Kết quả chính

- **Ngã thật / động tác khác, log đeo ngực của nhóm** (chạy lại nguyên lõi ESP32, [nga_that](../2026-10-28_nga_that/README.md)):
  - ngồi phịch xuống ghế: báo nhầm 0/10 (bản 2: 9/10);
  - cả log động tác (cúi, đi, nằm xuống, ngồi dậy, lăn người): báo nhầm 0;
  - ngã lên nệm: 14/15. Cú bị sót là ngã nhẹ 1,74 g, CNN cũng không nghi.
- **D1 người 102** (kênh đầu): ngã 70/101, sinh hoạt báo nhầm 0/81. Không báo 15 cú ngã kết thúc quỳ / ngồi; nhóm chấp nhận điều này.
- **Tư thế khi đeo ngực:** 9/9 tư thế đúng ([tu_the_nguc](../2026-10-28_tu_the_nguc/README.md)).
- **CNN N2 trên FPGA** (D1 11 người, kênh đầu, LOSO): Macro-F1 0,983 ([d1_11_nguoi](../2026-10-16_d1_11_nguoi/README.md)).

## Còn mở

- Ngưỡng `NGA_*` được chọn trên chính log dùng để chấm: một người, một buổi.
- CNN học từ kênh đầu, chưa train lại cho ngực (B4).
- Quy tắc ngã thật chưa vào SPEC A.8 và chưa có golden Python (B3).
- Đề cương vẫn ghi "mũ" (C2).
- Chưa có buổi thử có số đo: đeo ≥ 2 giờ, ≥ 20 cú ngã (D1/D2).
- Nguyên nhân MPU6050 treo nghi do 3,3 V sụt khi WiFi phát; chưa đo bằng dao động ký, chưa có tần suất theo giờ.
- Theo giấy tờ, các cổng G0 trở đi chưa đánh [x], vì thiếu bằng chứng theo *Pass criterion*.
