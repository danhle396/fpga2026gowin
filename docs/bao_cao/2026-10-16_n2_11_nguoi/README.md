# 2026-10-16 — N2 chỉ kênh đầu trên D1 11 người; bitstream 3 dựng lại với mô hình 11 người

**Mục đích.** Nhóm đã chốt mô hình phần cứng là N2 chỉ kênh đầu trên E2 (bitstream 3). Nhưng bitstream 3 vẫn mang N2 huấn luyện trên 6 người (13/10), trong khi D1 đã có 11 người (101–110, 203; 1.180 cú ngã). Thư mục này ghi lại ba việc:
- LOSO trên 11 người, 3 seed;
- phát lại qua Safety FSM;
- huấn luyện mô hình cuối, dựng lại bitstream 3 và kiểm.

**Quy tắc chọn mô hình, đặt trước khi có kết quả:** mô hình cuối đưa vào bitstream là **seed 20261014**, seed chuẩn của dự án (bitstream cũ cũng dùng seed này). Hai seed còn lại chỉ dùng để báo trung bình và độ dao động.

## 1. LOSO 11 người (`n2_11_s*_report.txt`)

`ml/train_cnn.py --arch n2 --seed <s>`, chỉ kênh đầu, 109.970 cửa sổ, mỗi seed khoảng 35 phút.

| | seed 20261014 | seed 7 | seed 99 | TB | (8 người, 16/10) |
|---|---|---|---|---|---|
| Macro-F1 INT8 | 0,9823 | 0,9813 | 0,9847 | **0,9828** | 0,9772 |
| Recall sự kiện, T_SCORE 0 | 1172/1179 | 1174/1179 | 1175/1179 | **99,6 %** | 99,6 % |
| Recall sự kiện, T_SCORE 8 | 97,7 % | 97,5 % | 97,9 % | 97,7 % | 97,7 % |
| Cặp phiếu 2/3 nhầm trước FSM, T_SCORE 8 | 2,60/giờ | 3,53/giờ | 3,16/giờ | 3,10/giờ | 4,15/giờ |
| FP32 → INT8 trùng nhãn | 0,9999 | 0,9999 | 0,9999 | | |
| Mô hình cuối INT8 khớp `golden_model.forward` | 1000/1000 | 1000/1000 | 1000/1000 | | |

Theo từng người, Macro-F1 qua 3 seed:
- **Người 105 yếu nhất: 0,924–0,964**, do khập khiễng, trẹo chân và vấp (xem phân tích ngày 16/10).
- Người 109: 0,964–0,971, lọt 1–5 cú ngã trên 119.
- Những người còn lại: ≥ 0,973.

## 2. Phát lại qua Safety FSM, SPEC v3.1 (`n2_11_s*_playback_v31.txt`, `n2_11_ens3_playback.txt`)

1.180 cú ngã, 961 bản ghi sinh hoạt = 5,43 giờ.

| T_SCORE 8 | seed 20261014 | seed 7 | seed 99 | TB | Gộp 3 seed |
|---|---|---|---|---|---|
| Ngã nằm → PRE_ALARM (769 cú) | 96,4 % | 95,8 % | 96,4 % | **96,2 %** | 95,6 % |
| PRE_ALARM giả/giờ | 0,92 | 0,74 | 1,66 | **1,11** | 0,74 |
| Ngã có đứng dậy → PRE_ALARM | 0/234 | 0/234 | 0/234 | 0 | 0/234 |
| Trễ va chạm → SUSPECT, trung vị | 0,86 s | 0,88 s | 0,84 s | | |

- **Mọi PRE_ALARM giả ở T_SCORE 8 đều từ hoạt động 815**, chủ động nằm xuống giường: người nằm hẳn xuống, đầu ngang, rồi bất động. Trung bình 1,11 lần/giờ, **vượt nhẹ chỉ tiêu ≤ 1**; trên 8 người là 0,68. Chỉ có 4–9 lần mỗi seed, nên khoảng tin cậy rộng.
- Nâng lên **T_SCORE 16**: báo giả còn 0 / 0,37 / 0,92 lần/giờ, nhưng ngã nằm tụt xuống 93,8 / 91,9 / 93,1 %, **dưới chỉ tiêu 95 %**. Chưa có ngưỡng nào đạt cả hai chỉ tiêu ở mọi seed. Gộp 3 seed ở T_SCORE 8 thì đạt cả hai (95,6 %, 0,74/giờ), nhưng cần chạy 3 lần suy luận, tức 15,5 ms ở 1 làn, vượt chỉ tiêu ≤ 6 ms.
- Đội mũ bảo hộ mà nằm xuống giường là tình huống hiếm ngoài đời. Buổi thử trên mũ (đề cương v2.1: ≥ 2 giờ đội mũ) mới là phép đo báo giả thật. Đề nghị **giữ T_SCORE 8** và chốt sau buổi thử.

**Độ trễ theo đúng điều kiện đề cương** (`tre_nam_yen_2s_s*.txt`, script của máy thứ hai):
- Điều kiện: "≤ 5 s khi người nằm yên trong 2 s sau va chạm". Có 514 cú ngã nằm thỏa điều kiện.
- Kết quả: trễ trung vị 3,80 s, **p90 4,32 s, lớn nhất 4,56 s, 0 cú > 5 s**, ở cả 3 seed.

## 3. Bitstream 3 dựng lại với mô hình 11 người (`run_bitstream3.sh`)

| Bước | Kết quả | Log |
|---|---|---|
| Lưu mô hình | `ml/out/n2_11_d1/` (seed 20261014, huấn luyện trên cả 11 người) | |
| Xuất E2, P = 1 | `ml/out/e2_matrix/n2_11_p1/`; biên tích lũy < 2³¹; mô hình địa chỉ ROM == golden | `export_n2_11_p1.log` |
| `tb_e2`, so từng tầng | **50/50**, 258.080 chu kỳ = 5,15 ms | `tb_e2_n2_11_p1.log` |
| `tb_proto` RTL, 10 khung + 7 kịch bản | PASS | `tb_proto_n2_11_p1.log` |
| P&R | Logic 1.473 (8 %), BSRAM 8/46, DSP 2,25/24, **Fmax 98,12 MHz** (bản cũ 107,25), 157,6 mW ước lượng | `pnr_b3.log` |
| Netlist sau P&R, 3 khung + 7 kịch bản | **PASS**. FF INIT = 1 chỉ gồm các khởi tạo cố ý. Bản phát hành trùng bản đã mô phỏng (khác 0 dòng trừ dấu thời gian) | `gl_b3.log` |
| Đáp án tự kiểm A.10 cho firmware | `firmware/src/selftest_expect_v3_e2_n2.h`: lớp 3, SCORE 0, logit {63183, −158442, −2³⁰, 63644} | |
| Keil `fw.uvprojx` | 0 lỗi, 0 cảnh báo | `keil_fw.log` |

- `bitstreams/3_v3_e2_n2/` đã thay `.fs`, báo cáo và `cnn_params.vh`; SHA256 mới.
- **Fmax giảm** từ 107,25 xuống 98,12 MHz. Weight khác thì nội dung ROM và cách đặt, đi dây khác. Mức này vẫn gần gấp đôi clock 50,143 MHz và trên mức cam kết ≥ 55 MHz; mục tiêu mở rộng ≥ 100 MHz thuộc tầng 3.
- Khung tự kiểm cho ra lớp FALL với SCORE 0: logit của FALL chỉ hơn NORMAL 461 đơn vị. Không ảnh hưởng gì, vì tự kiểm so **từng bit** cả 4 logit. Ngoài ra, vì hai logit sát nhau, một sai lệch nhỏ trong phép tính cũng dễ làm đổi cả lớp trả về.
- **Chưa chạy trên chip.**

## 4. Báo giả còn lại (815): một cổng "có va chạm" có giúp được không? (`phan_tich_815.py`, `phan_tich_815_s*.txt`)

Với mỗi lần vào PRE_ALARM ở T_SCORE 8, script đo đỉnh |a| trong 3 s trước lúc vào SUSPECT.

| | seed 20261014 | seed 7 | seed 99 |
|---|---|---|---|
| Đỉnh \|a\| của các báo giả 815 (g) | 1,96 – 2,50 (5 lần) | 1,96 – 2,50 (4 lần) | 1,69 – 2,50 (9 lần) |
| Ngã nằm tới PRE_ALARM: p1 / p5 / trung vị (g) | 2,03 / 2,56 / 4,71 | 2,14 / 2,59 / 4,72 | 2,03 / 2,57 / 4,71 |
| Ngưỡng 2,0 g: giữ ngã nằm / loại báo giả | 99,1 % / 1 trên 5 | 99,5 % / 1 trên 4 | 99,1 % / 2 trên 9 |
| Ngưỡng 2,5 g: giữ ngã nằm / loại báo giả | 95,4 % / 4 trên 5 | 96,3 % / 3 trên 4 | 95,4 % / 8 trên 9 |

**Kết luận: chưa thêm vào SPEC.**
- Báo giả 815 đều là va chạm nhẹ, đỉnh ≤ 2,5 g, và phần lớn đến từ người 109.
- Nhưng 5 % ngã nằm thật cũng có đỉnh dưới khoảng 2,56 g. Ngưỡng 2,5 g kéo tỉ lệ ngã nằm → PRE_ALARM từ 96,2 % xuống khoảng 92 %, dưới chỉ tiêu 95 %. Ngưỡng 2,0 g thì gần như không loại được báo giả.
- D1 lấy mẫu 25 Hz rồi nội suy, nên đỉnh va chạm bị san phẳng. Trên mũ thật (100 Hz, lọc rồi giảm còn 50 Hz), đỉnh của cú ngã sẽ cao hơn.
- Ghi lại thành **ứng viên**: "cổng va chạm: đỉnh |a| ≥ X g trong 3 s trước SUSPECT". Sẽ đo X trên các cú ngã ở buổi thử đội mũ, rồi mới quyết.

## 5. Bảng FP32 / INT8 / RTL của mô hình lên chip (mẫu AI-11)

| Mắt xích | Kết quả | Nguồn |
|---|---|---|
| FP32 → INT8 (LOSO, 3 seed) | Macro-F1 0,9824 → 0,9823 · 0,9813 → 0,9813 · 0,9848 → 0,9847; trùng nhãn 0,9999 | `n2_11_s*_report.txt` |
| Ma trận nhầm lẫn INT8, cộng 3 seed (mức cửa sổ) | NORMAL → FALL 658 / 318.641 (0,21 %); FALL lọt 92 / 10.611; recall cửa sổ FALL 99,13 %, precision 94,11 % | như trên |
| INT8 → RTL E2 (mô phỏng RTL) | `tb_e2` 50/50 từng tầng; `tb_proto` 10 khung + 7 kịch bản | `tb_e2_n2_11_p1.log`, `tb_proto_n2_11_p1.log` |
| INT8 → netlist sau P&R | 3 khung + 7 kịch bản PASS | `gl_b3.log` |
| Firmware → RTL → firmware (6 bản ghi D1 của người 104, 137,7 s) | **423/423 khung** khớp golden, CYCLES 258.080; firmware đọc đúng 423/423; 4 lần đổi trạng thái trùng golden (MONITOR → SUSPECT → PRE_ALARM → ALARM) | `cosim_n2_11_p1_6_ban_ghi.log` |

Lượng tử mất ≤ 0,0001 Macro-F1; RTL và netlist không mất gì. Toàn bộ sai số còn lại nằm ở mô hình và dữ liệu. Chưa đo trên chip: TH-09 cần ≥ 2.000 cửa sổ qua HIL với `--params ml/out/n2_11_d1/params_int8.npz`.
