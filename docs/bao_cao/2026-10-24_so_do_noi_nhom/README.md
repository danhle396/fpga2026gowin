# 2026-10-24 — Chuyển chân FPGA sang sơ đồ nối thực tế của nhóm (header J2)

## Nguồn

Nhóm gom mã và ghi chú nối dây của project riêng vào `codecanthiet/` (thư mục tạm, không đưa lên git). Hai file quyết định chân được chép vào `nguon_nhom/`:
- `kiwi_primer_20k.cst`: chân FPGA nhóm đang dùng;
- `board_config.h`: chân MCU của firmware nhóm.

Ngoài ra đã đọc `esp32/README_wiring.md` và các dòng khai báo chân của `cnn_live_mpu6050_bridge.ino`. Hai file này không chép vào đây vì có tên và mật khẩu WiFi thử nghiệm.

## Nhóm đang nối thế nào

| Đoạn | Thực tế của nhóm |
|---|---|
| ESP32 → Kiwi (SPI, ESP32 làm master, 100 kHz) | GPIO27 → **R11 / J2-16 (CS_N)** · GPIO18 → **T14 / J2-10 (SCK)** · GPIO23 → **R13 / J2-11 (MOSI)** · GPIO19 ← **R12 / J2-13 (MISO)** · GND chung. README của nhóm ghi bộ dây này đã chạy thông ("passing baseline") |
| MCU → ESP32 | UART0 TX P3.1 → ESP32 GPIO16, 115200 baud |
| MCU → Kiwi | **Chưa nối.** README nhóm: "Do not connect the MCU SPI0 to the FPGA for this mode". `board_config.h` dự định CS của FPGA ở P2.2, ghi `TODO_HW_VERIFY` |
| MCU ↔ MPU6050 | I²C0 P0.10 / P0.11, 100 kHz, 0x68. Lấy mẫu bằng timer CT16B0 10 ms, **không dùng chân INT** |
| Kiwi khác | `reset` T8 / J2-23 (mức cao = reset, kéo xuống); 5 chân debug R8, R7, R6, T7, T6 trên J2 |

Giao thức FPGA của nhóm khác A.7: yêu cầu 774 byte bắt đầu bằng 0xA5, trả lời 23 byte, MCU hỏi vòng BUSY/READY, không có IRQ, weight `DEVELOPMENT_TEST`. Vì vậy bitstream của nhóm (`FPGA_CNN_Hardware_Test_CRC_Fixed.fs`) không chạy được với firmware của repo, và ngược lại.

## Quyết định

Giữ kiến trúc của đề tài: MCU làm master nối thẳng FPGA, giao thức A.7, có IRQ và RST_N. Chỉ đổi chân phía FPGA sang header J2:

1. **Bốn chân SPI** dùng đúng R11 / T14 / R13 / R12. Đây là bốn chân nhóm đã cắm dây và chạy thông ở 3,3 V. Header J1 cũ thì vị trí chân mới chỉ đọc từ hình.
2. **IRQ = R8 (J2-24), RST_N = T8 (J2-23).** Cả hai chân nằm bank 3 (3,3 V theo sơ đồ Kiwi rev v1.0, Phụ lục E.3) và không thuộc danh sách chân cấu hình phải tránh (R9, T10, T9, P9, N9, M8). Nhóm cũng đã khai báo hai chân này là GPIO của J2. Pin report ghi R8 = IOR29[B] và T8 = IOR42[B], khớp tên `B3_R29_N` và `B3_R42_N` trong file của nhóm.
3. **Phía MCU giữ nguyên firmware**:
   - SPI: P1.0 / P1.1 / P1.2, trùng với nhóm.
   - CS: **P2.8**, không dùng P2.2 như nhóm dự định. P2.2 là INT của MPU6050 trong firmware này, và vòng hiệu chuẩn gyro chờ INT. P2.2 cũng chưa có dây nào nối, nên giữ P2.8 không tốn công đi lại dây.
   - IRQ P2.9 và RST_N P2.1 trên J7.
4. **ESP32 phải tháo khỏi J2** khi chạy hệ thống này: hai master trên một bus SPI sẽ tranh nhau. ESP32 không nằm trong luồng chính. Muốn dùng làm đồ gá TH-13 hoặc gửi log qua WiFi thì phải viết lại sketch theo A.7 và theo log 460800 baud.

`rst_n` của repo là **mức thấp = reset, kéo lên**, ngược với `reset` của nhóm (mức cao = reset, kéo xuống), dù cùng chân T8. Firmware giữ P2.1 ở mức cao và chỉ kéo xuống ≥ 1 ms sau 3 lỗi liên tiếp.

## Sơ đồ nối dây mới (Phụ lục E.1)

| Tín hiệu | MCU (header EVK) | Kiwi (header · ball) | Dùng cho bitstream |
|---|---|---|---|
| GND | GND của J12 | J1-1 / J1-2 hoặc GND bất kỳ của Kiwi | tất cả, **nối trước** |
| SCK | P1.0 `SCK_P10` (J12) | J2-10 · T14 | 1, 2, 3 |
| MOSI | P1.2 `MOSI_P12` (J12) | J2-11 · R13 | 1, 2, 3 |
| MISO | P1.1 `MISO_P11` (J12) | J2-13 · R12 | 1, 2, 3 |
| CS | P2.8 `P28` (J7) | J2-16 · R11 | 1, 2, 3 |
| IRQ | P2.9 `P29` (J7) | J2-24 · R8 | 1, 2, 3 |
| RST_N | P2.1 `P21` (J7) | J2-23 · T8 | 2, 3 |
| MPU6050 INT | P2.2 `P22` (J7) | — | **dây mới**: firmware nhóm không dùng INT |
| MPU6050 SCL / SDA | P0.10 / P0.11 (J13) | — | như nhóm |
| UART log | P3.1 / P3.2 (J10) → USB-UART 3,3 V → PC, 460800 baud | — | không qua ESP32 |

## File đã sửa

| File | Thay đổi |
|---|---|
| `rtl/v3/fpga_top_v3.cst` | Sáu chân sang J2 (bitstream 2, 3) |
| `rtl/v3/fpga_top_p1.cst` (mới) | Như trên, không có `rst_n` (bitstream 1). `pnr_v3.sh p1` chép file này đè lên `src/fpga_top.cst` của bản sao; không sửa project của nhóm |
| `rtl/pin_probe/pin_probe_top.cst`, `pin_probe.fs` | Dò 6 chân J2. Thứ tự k = 1..6: J2-16, J2-10, J2-11, J2-13, J2-24, J2-23 |
| `bitstreams/*/fpga_project.fs`, `.rpt.txt`, `SHA256.txt` | Dựng lại cả 3 bitstream. `cnn_params.vh` trùng từng byte bản cũ |
| `PROJECT_MASTER.md` (TRẠNG THÁI, H3, E.1, E.3, E.4, mục timing), `DE_CUONG_v2.md`, `THAY_DOI_SO_VOI_v1.md`, `docs/huong_dan_dot_B.md` (B6, B7, B10), `bitstreams/README.md`, báo cáo cuối nháp | Chân J2 và Fmax mới |

Firmware không sửa.

## Kết quả P&R (Gowin V1.9.11.03, `pnr_chan_j2.log`)

| Bitstream | Logic | BSRAM | DSP | Fmax (cần 50,143 MHz) | Trước, chân J1 |
|---|---|---|---|---|---|
| 1 `fpga_top` + E1 | 907 (5 %) | 6/46 | 1,25 | **103,33 MHz** | 105,20 |
| 2 `fpga_top_v3` + E1 | 1.521 (8 %) | 6/46 | 1,25 | **104,92 MHz** | 103,01 |
| 3 `fpga_top_v3` + E2 + N2 11 người | 1.473 (8 %) | 8/46 | 2,25 | **111,01 MHz** | 98,12 |
| `pin_probe` | — | — | — | — | — |

- Mọi cổng nằm đúng ball, `IO Type` = LVCMOS33, `BankVccio` = 3,3 V ở cả bank 2 (SPI) và bank 3 (IRQ, RST_N).
- TNS = 0, không có lỗi.
- Tài nguyên không đổi so với bản cũ. Fmax lệch vài MHz là do đặt chỗ và đi dây khác nhau.

## Mô phỏng netlist sau P&R

Chạy `rtl/gl/run_gl.sh`. Lệnh này dựng lại bằng P&R kèm netlist mô phỏng, rồi chạy chính netlist đó.

| Bitstream | Testbench | Kết quả | `.fs` của bản mô phỏng so với file trong `bitstreams/` |
|---|---|---|---|
| 1 | `tb_top_spi`, 5 khung, có 1 khung sai CRC | **PASS 5/5** (`gl_bitstream1.log`) | trùng từng bit, chỉ khác dòng giờ tạo |
| 3 | `tb_proto`, 3 khung + 7 kịch bản lỗi, NG = 1 | **PASS**, CYCLES = 258.080 (`gl_bitstream3.log`) | trùng từng bit, chỉ khác dòng giờ tạo |

- Danh sách FF lên nguồn ở mức 1 giống bản 16/10: chỉ có các khởi tạo cố ý (`cs_sync`, `crc`, …).
- Bitstream 2 dùng cùng `fpga_top_v3` và cùng `.cst` với bitstream 3, cùng E1 với bitstream 1, nên lần này không chạy lại netlist.

## Còn phải đo trên board

- **B6:** dò 6 chân J2 bằng `rtl/pin_probe/pin_probe.fs`. Bốn chân SPI nhóm đã dùng; R8 / J2-24 và T8 / J2-23 thì số thứ tự trên header mới lấy theo ghi chú của nhóm, chưa ai đo.
- Chân GND nào trên J2 thì chưa rõ. Dùng J1-1 / J1-2 như cũ.
- **Phải tháo ESP32 khỏi J2 trước khi cấp nguồn cho MCU với bitstream này.**

## Project Gowin mở được bằng IDE (thêm cùng ngày)

Trước đây repo chỉ có `fpga_project.gprj` của nhóm. File chân trong đó là J1 cũ và không có top v3 / engine E2, nên mở nó rồi Run All sẽ ra bitstream **sai chân**.

- **Mới:** `bash rtl/gowin/tao_project.sh` tạo 4 project ở `gowin_proj/` (không lên git): `1_e1_proto1_sisfall`, `2_v3_e1_sisfall`, `3_v3_e2_n2`, `pin_probe`.
  - Mỗi project có `.gprj` và `impl/*_process_config.json` (đặt top module và include path), sinh bằng `rtl/gowin/tao_gprj.py` từ chính `build.tcl` của `pnr_v3.sh`.
- **Kiểm:** mở từng `.gprj` bằng `gw_sh open_project` rồi `run all`. Cả 4 file `.fs` **trùng từng dòng bit** với `bitstreams/*` và `rtl/pin_probe/pin_probe.fs`; chỉ khác các dòng chú thích `//`.
  - `pnr_v3.sh` sau khi sửa vẫn dựng ra bitstream 3 trùng bit.
