# 2026-10-15 — X15: có nên báo động khi ngã rồi ngồi/quỳ bất động?

**Câu hỏi (Phụ lục C, X15):**
- Ngã kết thúc quỳ hoặc ngồi (D1: 903, 909, 920) chỉ có 3/90 lần tới PRE_ALARM, vì A.8 v3.1 đòi đầu nghiêng 45°–135°.
- X15 đề xuất: nếu cần báo cả trường hợp này thì thêm nhánh "bất động ≥ N khối dù đầu thẳng" và đo lại báo giả.

Đây là bản đo đó, để nhóm có số liệu khi quyết. **SPEC, `safety.c` và `safety_model.py` không đổi.**

## Cách đo

- `tools/playback_d1.py --still-upright N`: lớp con `SafetyX15` thêm một nhánh. Khi đang SUSPECT và `still_run ≥ N` khối (khối 0,32 s) thì chuyển sang PRE_ALARM, không xét độ nghiêng.
- Với `N = 0` thì giống hệt SPEC v3.1. Đã kiểm: `n2_s0_u0.log` trùng từng dòng `../2026-10-14_ai10_playback/v31/n2_s0_k2.log`.
- SUSPECT hết hạn sau 8 s, nên N ≤ 24.
- Mô hình N2: 3 mô hình LOSO (seed 20261014 / 7 / 99) và gộp 3 seed. 2/3 phiếu, T_SCORE 8. D1 có 604 cú ngã và 2,65 giờ sinh hoạt.

## Kết quả (T_SCORE 8)

| Nhánh đầu thẳng | Ngã nằm → PRE_ALARM (TB 3 seed) | Ngã quỳ/ngồi → PRE_ALARM | **Ngã đã đứng dậy → PRE_ALARM** | PRE_ALARM giả/giờ: 3 seed (TB) | Gộp 3 seed: nằm / quỳ-ngồi / đứng dậy / giả/giờ |
|---|---|---|---|---|---|
| tắt (SPEC v3.1) | 95,5 % | 9/270 = 3,3 % | 0/360 | 2,64 / 0,75 / 0,38 (1,26) | 95,7 % / 3/90 / 0/120 / 0,75 |
| N = 12 (3,84 s) | 97,8 % | 229/270 = 84,8 % | **250/360 = 69,4 %** | 6,04 / 3,40 / 1,89 (3,78) | 98,0 % / 75/90 / 84/120 / 3,02 |
| N = 16 (5,12 s) | 97,5 % | 205/270 = 75,9 % | **129/360 = 35,8 %** | 4,15 / 1,89 / 0,38 (2,14) | 97,7 % / 67/90 / 43/120 / 1,51 |
| N = 20 (6,40 s) | 97,5 % | 143/270 = 53,0 % | 10/360 = 2,8 % | 3,40 / 1,51 / 0,38 (1,76) | 97,7 % / 46/90 / 2/120 / 1,13 |

Báo giả mới đến từ:
- cúi nhặt đồ (806);
- vấp rồi đứng yên (808, 809).

## Nhận xét

1. **Nhánh đầu thẳng không phân biệt được "ngồi bất động sau ngã" với "đã đứng dậy rồi đứng yên".**
   - Trong D1, người làm các kiểu 905, 906, 914, 916 đứng dậy rồi đứng yên tới hết bản ghi.
   - Với N = 12 hoặc 16, 36–69 % các cú ngã đó bị báo động.
   - Như vậy vi phạm tiêu chí đề xuất "0 cú ngã có đứng dậy tới ALARM" (AI-10, X15).
2. **N = 20 bớt được lỗi trên nhưng chỉ bắt được khoảng một nửa số ngã quỳ/ngồi (53 %),** và báo giả tăng từ 1,26 lên 1,76 lần/giờ (gộp: 0,75 → 1,13), vượt chỉ tiêu ≤ 1.
3. Ngã nằm tăng nhẹ (95,5 → 97,5–97,8 %): một số ngã nằm có đầu nghiêng chưa tới 45° nay được bắt nhờ nhánh mới. Phần lợi này không đủ bù cho hai điểm trên.
4. **Đề xuất cho nhóm** (nhóm vẫn là người quyết X15):
   - Giữ SPEC v3.1: chỉ tự báo động khi "ngã và nằm bất động", đúng mục tiêu ở mục 1.
   - Người ngã rồi ngồi mà vẫn tỉnh thì tự gọi SOS (giữ CANCEL 3 s, đã có trong A.8).
   - Sửa Pass của AI-10 thành: "≥ 95 % ngã kết thúc nằm tới PRE_ALARM; 0 ngã có đứng dậy tới ALARM".
   - Nếu nhóm vẫn muốn báo ngã ngồi thì cần thêm tín hiệu khác. Phân biệt "ngồi" với "đứng" bằng độ cao (barometer) hoặc bằng đặc trưng của cú ngã. Đó là việc của tầng 3.
5. **Giới hạn:**
   - D1 ghi ngắn: người đứng yên sau khi đứng dậy là do giao thức thu, ngoài đời có thể đi tiếp.
   - Chỉ 6 người, 90 lần ngã quỳ/ngồi. Cần đo lại trên D3.
