# 2026-10-15 — AI-09: thêm dữ liệu cảm biến ở thân (ngực, thắt lưng của D1) khi huấn luyện N2

**Câu hỏi của AI-09:** có giữ dữ liệu thân người trong tập huấn luyện không? Tiêu chí: "chỉ giữ nếu không làm tăng báo nhầm trên bản ghi thường ngày".

**Cách làm:**
- `ml/train_cnn.py --arch n2 --train-only d1_windows_nguc_340539.npz d1_windows_that_lung_340535.npz`. Tùy chọn `--train-only` là mới.
- Cửa sổ ngực và thắt lưng **chỉ vào tập huấn luyện** của từng lượt LOSO.
- Tập kiểm vẫn chỉ gồm 53.165 cửa sổ **đầu** của người để riêng. Không lần nào dữ liệu thân của người đó được dùng, kể cả để huấn luyện.
- Tập huấn luyện mỗi lượt lớn gấp khoảng 3 lần; mỗi seed mất khoảng 34 phút.
- So với N2 chỉ dùng đầu, cùng 3 seed (20261014, 7, 99), cùng mã nguồn.

Phát lại qua FSM SPEC v3.1 bằng `tools/playback_d1.py`:
- 604 cú ngã và 2,65 giờ sinh hoạt;
- 2/3 phiếu;
- mỗi người dùng mô hình của lượt LOSO để riêng người đó.

## Mức cửa sổ và sự kiện (LOSO, INT8)

| | Chỉ đầu: 3 seed | TB | Đầu + thân: 3 seed | TB |
|---|---|---|---|---|
| Macro-F1 INT8 | 0,9584 / 0,9691 / 0,9774 | 0,9683 | 0,9631 / 0,9712 / 0,9779 | **0,9707** |
| Cửa sổ FALL bị lọt (trên 1.812) | 34 / 35 / 42 | 37 | 18 / 9 / 11 | **12,7** |
| Cửa sổ NORMAL bị gọi FALL (trên 51.353) | 356 / 214 / 128 | 233 | 309 / 227 / 158 | 231 |
| Recall sự kiện, T_SCORE 0 | 98,8 / 99,0 / 98,3 % | 98,7 % | 99,5 / 99,8 / 99,7 % | **99,7 %** |
| Recall sự kiện, T_SCORE 8 | 95,7 / 94,7 / 96,9 % | 95,8 % | 97,8 / 98,8 / 98,3 % | **98,3 %** |
| Cặp phiếu 2/3 nhầm/giờ **trước FSM**, T_SCORE 8 | 11,04 / 7,61 / 5,33 | **8,0** | 10,66 / 10,28 / 8,75 | 9,9 |
| FP32 → INT8 trùng nhãn | ≥ 99,93 % | | ≥ 99,96 % | |

## Mức hệ thống (Safety FSM v3.1)

| T_SCORE | | Ngã nằm → PRE_ALARM: 3 seed | TB | PRE_ALARM giả/giờ: 3 seed | TB | Gộp 3 seed: nằm / giả/giờ |
|---|---|---|---|---|---|---|
| 8 | chỉ đầu | 95,2 / 94,9 / 96,4 % | 95,5 % | 2,64 / 0,75 / 0,38 | 1,26 | 95,7 % / 0,75 |
| 8 | **đầu + thân** | 96,2 / 96,4 / 96,7 % | **96,4 %** | 0,75 / 1,13 / 0,75 | **0,88** | **96,2 % / 0,38** |
| 16 | chỉ đầu | 88,6 / 89,8 / 93,7 % | 90,7 % | 0,38 / 0,38 / 0,00 | 0,25 | 91,9 % / 0,00 |
| 16 | **đầu + thân** | 94,9 / 95,2 / 96,2 % | **95,4 %** | 0,38 / 0,38 / 0,38 | 0,38 | 94,9 % / 0,38 |

Ở cả hai cấu hình:
- ngã có đứng dậy → PRE_ALARM: 0/360;
- ngã quỳ/ngồi: 3/90 (xem X15);
- trễ va chạm → SUSPECT, trung vị 0,84–0,88 s.

Với đầu + thân, PRE_ALARM giả **chỉ còn** đến từ 815 (chủ động nằm xuống giường). Các báo giả do cúi gập 90° (805) của mô hình chỉ đầu không còn.

## Kết luận sơ bộ (chỉ trên D1, 6 người)

1. **Đề nghị giữ dữ liệu thân, chỉ dùng để huấn luyện.**
   - Ở mức hệ thống, báo giả **giảm** (TB 1,26 → 0,88/giờ; gộp 0,75 → 0,38) và recall ngã nằm **tăng** (95,5 → 96,4 %).
   - Phương sai giữa các seed cũng nhỏ hơn: báo giả 0,75–1,13 thay vì 0,38–2,64.
2. Tiêu chí của AI-09 chưa định nghĩa "báo nhầm" ở mức nào:
   - Ở mức cặp phiếu **trước** FSM, báo nhầm tăng (8,0 → 9,9/giờ).
   - Ở mức PRE_ALARM, là cái người dùng nghe thấy, báo nhầm giảm.
   - Đề nghị ghi rõ trong Pass: tính ở mức PRE_ALARM sau FSM.
3. Với dữ liệu thân, **T_SCORE 16** có trung bình 3 seed đạt cả ≥ 95 % ngã nằm (95,4 %) và ≤ 1 báo giả/giờ (0,38). Seed 20261014 đạt 94,9 %, còn thiếu 0,1 điểm. Đây là cấu hình đáng thử đầu tiên khi có D2/D3.
4. **Chưa chốt:**
   - Còn phải kiểm trên D2 (va mũ, sinh hoạt khi đội mũ) và D3 (ngã khi đội mũ) theo Pass của AI-09.
   - Chưa thử SisFall (cảm biến ở thắt lưng, có đủ băng tần 25 Hz).
   - Bitstream 3 và firmware vẫn dùng N2 chỉ đầu.
5. **Mô hình đã lưu, sẵn cho phần cứng:**
   - Seed 20261014, mô hình cuối huấn luyện trên cả 6 người, cả đầu lẫn thân: `ml/out/n2t_d1/`. Gồm `loso_params.npz` cho phát lại và `params_int8.npz`.
   - Xuất E2 P = 1: `ml/out/e2_matrix/n2t_p1/`.
   - `tb_e2` 50/50 ở mọi tầng (`tb_e2_n2t_p1.log`): cùng kiến trúc N2, cùng 258.080 chu kỳ.
   - Muốn có bitstream: `bash rtl/v3/pnr_v3.sh <thư mục> e2 ml/out/e2_matrix/n2t_p1`. Không đổi RTL.

Tái tạo:

```
python ml/train_cnn.py --arch n2 --seed <s> --out <thư mục> --train-only ml/data/public/d1_windows_nguc_340539.npz ml/data/public/d1_windows_that_lung_340535.npz
python tools/playback_d1.py --model <thư mục> --t-score 8 16
```

## Thêm: EMA trọng số không giảm được phương sai theo seed (`ema/`)

- `--ema 0.995` (mới, trong `cn.train`): lấy trung bình trượt mũ của trọng số. EMA không dùng bộ sinh số ngẫu nhiên, nên quỹ đạo huấn luyện **trùng hệt** bản không EMA cùng seed; đây là phép so có cặp.
- **LOSO:** Macro-F1 INT8 0,9632 / 0,9708 / 0,9779 so với 0,9631 / 0,9712 / 0,9779. Ma trận nhầm lẫn chênh 0–3 cửa sổ.
- **FSM v3.1, T_SCORE 8:** ngã nằm 96,2 / 96,4 / 97,0 % so với 96,2 / 96,4 / 96,7 %; PRE_ALARM giả **trùng hoàn toàn** (0,75 / 1,13 / 0,75 lần/giờ).
- **Kết luận:**
  - Lịch lr cosine đã làm phẳng nhiễu cuối huấn luyện. Chênh lệch giữa các seed đến từ quỹ đạo (khởi tạo, thứ tự mẫu), nên EMA không có tác dụng.
  - Cách đã chứng minh có tác dụng là **gộp các mô hình có seed khác nhau** (0,38 giả/giờ).
  - Không dùng EMA. Tùy chọn vẫn giữ, mặc định tắt.
