# CLAUDE.md — đọc trước mọi phiên (máy nào, tài khoản nào cũng vậy)

Đề tài: mũ bảo hộ phát hiện té ngã, đội VKU-NewBie. Luồng: MPU6050 → SN32F407 → SPI → Kiwi Primer 20K (1D-CNN INT8, RTL tự viết) → Safety FSM → còi. Trả lời bằng **tiếng Việt**.

## 1. Bắt đầu phiên

1. `git pull`. Nếu có thay đổi chưa commit của người khác thì dừng và hỏi.
2. Đọc **`PROMPT_KHOI_CONG.md`**: vai trò, bất biến, luật làm việc, các lệnh ngắn (`Tiếp`, `Sửa`, `Cập nhật`, `Kẹt`, `Phản biện`, `XUẤT FULL`). File đó là luật của phiên.
3. Đọc khung **TRẠNG THÁI** ở đầu `PROJECT_MASTER.md` và **10 dòng cuối của Phụ lục D** (nhật ký), để biết phiên trước đã làm gì.
4. Đọc `docs/huong_dan_dot_B.md` nếu phiên này làm việc trên board.

Khi file và trí nhớ khác nhau, **file thắng**. Mọi con số phải lấy từ file hoặc từ phép đo; không bịa. Chưa chắc thì ghi `[CẦN XÁC MINH – nguồn: …]`.

### Lệnh ngắn dùng khi thay phiên

- **"Chạy tiếp dự án"** (hoặc "Tiếp"):
  1. Làm bước 1–3 ở trên.
  2. Kiểm máy này có công cụ nào (mục 4).
  3. Đọc mục "ĐANG DỞ" cuối Phụ lục D nếu có.
  4. Tự chọn việc có giá trị nhất làm được trên máy này. Việc nào cần board hoặc dữ liệu mới thì viết hướng dẫn cho người cầm board, không tự bịa số đo.
- **"Chốt phiên"**: làm đủ bốn việc ở mục 3 (Phụ lục D, TRẠNG THÁI, bằng chứng, commit + push).

## 2. Luật bắt buộc (tóm tắt; bản đầy đủ ở `PROMPT_KHOI_CONG.md`)

- Ba file `PROJECT_MASTER.md`, `DE_CUONG_v2.md`, `THAY_DOI_SO_VOI_v1.md` phải khớp nhau từng con số. Mỗi lần sửa thì thêm **một dòng Phụ lục D** (ngày, việc, lý do).
- Chỉ đánh `[x]` khi đạt *Pass criterion* và có bằng chứng ở `docs/bao_cao/<YYYY-MM-DD>_<chủ đề>/`.
- Tầng 3 chỉ làm khi đã qua G6. Không ghi đè `Document Board Kiwi Primer 20K/Kiwi20K_FallDetection_FPGA/impl/` của đồng đội.
- Golden model `ml/src/golden_model.py` là đáp án; RTL, firmware và Python phải khớp nó từng bit.
- Thanh ghi nào phát xung (start, done, valid, we, irq) trong RTL **phải có giá trị khởi tạo**. Xem lỗi `conv_start` ở `docs/bao_cao/2026-10-15_loi_init_conv_start/`.
- **Cuối mỗi câu trả lời** có bảng **1 hàng × 5 cột**:
  `| Tầng / cổng hiện tại / % | Thay đổi lần này + lý do | Đồng bộ 3 file | Còn [CẦN XÁC MINH] / rủi ro mở | Việc làm NGAY (≤ 3): việc + nhánh + Pass criterion |`

## 3. Thay phiên giữa nhiều máy và nhiều tài khoản Claude

- **Mỗi lúc chỉ một phiên Claude được sửa repo.** Trước khi bắt đầu, báo trong nhóm chat: "đang giữ repo: <tên>, <việc>". Xong thì báo nhả.
- **Kết thúc phiên**, kể cả khi sắp hết hạn mức, làm đủ bốn việc:
  1. Ghi dòng Phụ lục D.
  2. Cập nhật khung TRẠNG THÁI nếu có thay đổi.
  3. Lưu bằng chứng vào `docs/bao_cao/`.
  4. `git add -A && git commit -m "<ngày> <việc> — <kết quả>"` rồi `git push`.

  Việc dở dang thì ghi vào cuối Phụ lục D với chữ **ĐANG DỞ**: đang làm gì, lệnh nào đang chạy, bước tiếp theo.
- **Hook tự động** (`.claude/settings.json`, script trong `.claude/hooks/`; máy nào clone repo cũng có):
  - *SessionStart*: khi mở phiên, tự `git pull` nếu repo sạch. Nếu repo đang có thay đổi chưa commit thì không pull mà cảnh báo. Sau đó in 5 commit gần nhất và các mục ĐANG DỞ.
  - *Stop*: khi Claude định dừng mà repo còn thay đổi chưa commit hoặc commit chưa push, hook chặn lại và yêu cầu làm Chốt phiên. Lần dừng thứ hai luôn được cho qua (chỉ cảnh báo), để không lặp vô hạn.
  - Tắt tạm bằng `/hooks`, hoặc đặt `"disableAllHooks": true` trong `.claude/settings.local.json` (file này không đưa lên git).
- Phiên mới không có trí nhớ của phiên cũ. Mọi thứ cần biết phải nằm trong repo: file này, `PROMPT_KHOI_CONG.md`, `PROJECT_MASTER.md` và `docs/bao_cao/`.
- File sinh ra khi build hoặc mô phỏng không đưa vào git (xem `.gitignore`). Kết quả tạm thì để ngoài repo, ví dụ thư mục tạm của hệ điều hành.

## 4. Môi trường trên mỗi máy

| Công cụ | Dùng cho | Ghi chú |
|---|---|---|
| Git Bash (Windows) | mọi script `.sh` | |
| Python 3.12 + `numpy`, `matplotlib`, `pyserial`, `pymupdf` | `tools/`, `ml/` | Gọi với `python -I`. Console Windows dùng cp1252, nên script phải gọi `sys.stdout.reconfigure(encoding="utf-8")` |
| `unicorn` (pip, nên cài vào venv riêng) | `tools/m0_test.py`, `tools/cosim.py`: chạy mã máy Cortex-M0 trên PC | |
| Icarus Verilog (máy gốc: 0.9.7; máy thứ hai: 12.0 cài bằng `winget install Icarus.Verilog`; cả hai ở `C:\iverilog\bin`) | mọi testbench | Chỉ dùng cú pháp `-g2001`. Script tự thêm `/c/iverilog/bin` vào PATH nếu không thấy `iverilog` |
| (máy chưa có Python) | | `winget install Python.Python.3.12 --scope user`, tạo venv rồi `pip install numpy matplotlib pyserial pymupdf pypdf unicorn`. Git Bash có thể bắt trúng alias Microsoft Store khi gọi `python3`: chép `python.exe` của venv thành `python3.exe` rồi đưa thư mục `Scripts` của venv lên đầu PATH |
| Gowin EDA V1.9.11.03 Education | `rtl/v3/pnr_v3.sh`, `rtl/gl/run_gl.sh` | Mặc định `/c/Gowin/Gowin_V1.9.11.03_Education_x64/IDE/bin/gw_sh.exe`; đổi bằng biến `GW_SH`, `GW_SIMLIB` |
| Keil MDK-ARM 5.43 (Arm Compiler 6.24) + pack SONiX SN32F4_DFP | `firmware/keil/fw.uvprojx`, `firmware/build.sh` | Máy gốc cài ở `%LOCALAPPDATA%\Keil_v5`. Build không mở giao diện: `UV4.exe -r <project> -j0 -o log.txt` |

Lệnh kiểm nhanh sau khi `git pull` (không cần board):

```bash
python -I tools/verify_spec_v3.py ml/src "FPGA_Fall_Detection_AI-20261012T141515Z-1-001/FPGA_Fall_Detection_AI/fpga_export"
python -I tools/sync_spec.py --check         # docs/spec.md trùng Phụ lục A (sửa Phụ lục A thì chạy lại không có --check)
bash rtl/tb/run_all.sh                       # 7 testbench, khoảng 5 phút
bash firmware/build.sh test && python -I tools/m0_test.py
```

**Chỉ có trên máy gốc, không có trong repo:**
- Dữ liệu thô D1 (8 người, 6 cảm biến): máy thứ hai giữ ở `E:\FPGA2026_GOWIN\d1_raw\`. Bản đã chuyển đổi nằm ở `ml/data/public/`; tải lại bằng `tools/fetch_d1.sh`.
- Dự án vòng 1 `D:\hoctap\fpga\thi_fpga\MCU\`, chỉ để tham khảo.

## 5. Đang ở đâu (cập nhật mỗi khi đổi mốc lớn)

- Tầng 1, **chưa qua G0**. Mọi thứ đã kiểm trong mô phỏng, chưa chạy trên chip.
- Mô hình phần cứng đã chốt (16/10): **N2, chỉ kênh đầu, 2 lớp NORMAL / FALL (SPEC v3.2)** trên **E2, 1 làn, giao thức v3** (bitstream 3). Dữ liệu ngực/thắt lưng đã bỏ. Bitstream 3 hiện vẫn mang N2 huấn luyện trên 6 người; bản 11 người đang làm (xem Phụ lục D).
- Việc tiếp theo: đợt B theo `docs/huong_dan_dot_B.md`, dùng `bitstreams/1_e1_proto1_sisfall` **bản ngày 15/10** (kiểm `SHA256.txt` trước khi nạp).
