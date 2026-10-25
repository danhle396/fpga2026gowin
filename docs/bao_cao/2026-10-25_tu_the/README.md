# 2026-10-25 — Nhận dạng tư thế không phải ngã (SPEC v3.3, A.11)

Nhóm yêu cầu xác định các tư thế sinh hoạt (đứng thẳng, ngồi, nằm thẳng, nằm nghiêng) để phù hợp yêu cầu đề tài, và hiển thị trên trang web. Tư thế **chỉ để theo dõi**: không đưa vào Safety FSM, không đổi quyết định báo ngã.

## Đã làm

| Phần | File | Ghi chú |
|---|---|---|
| Đáp án số nguyên | `ml/src/posture_model.py` | 8 tư thế: `DUNG`, `NGOI`, `NAM_NGUA`, `NAM_SAP`, `NGHIENG_TRAI`, `NGHIENG_PHAI`, `CUI`, `DI_LAI` |
| C cho ESP32 | `firmware/src/posture.c/.h`, gọi trong `hub_sample` (`hub.c`, cờ `HUB_POSTURE`) | đồng bộ sang `esp32/mu_nga_hub/` bằng `dong_bo_core.sh` |
| Kiểm C == Python | `tools/m0_test.py` `test_posture` (mode 13 của `firmware/test/host_main.c`) | mã máy Cortex-M0 trong Unicorn |
| Chấm trên D1 | `tools/posture_eval.py` → [posture_eval.txt](posture_eval.txt) | |
| Trang web | `esp32/mu_nga_hub/trang_web_html.h`, `/data` thêm `tt`, `pt` | thẻ "Tư thế hiện tại", "Lịch sử tư thế", dải màu tư thế dưới biểu đồ |
| Log | dòng `P,<ms>,<tư thế>` (USB + TCP 3333) | không đưa vào danh sách "Sự kiện" để không lấn sự kiện báo ngã |

Cách làm: xem SPEC A.11 ([docs/spec.md](../../spec.md)). Tóm tắt:
- **Hướng đầu** từ trọng lực, trung bình mỗi 0,32 s. Nằm thì phân biệt ngửa / sấp / nghiêng trái / nghiêng phải theo trục lớn nhất.
- **Đứng hay ngồi:** ở cả hai tư thế đầu đều thẳng, nên phân biệt bằng **độ cao đầu thay đổi** qua mỗi đợt cử động. Độ cao lấy bằng tích phân hai lần của |a| − g, hiệu chỉnh trôi bằng điều kiện vận tốc bằng 0 ở hai đầu đợt.

## Kết quả

**C trùng Python từng mẫu.** `m0_test`: 73 bản ghi (2 bản ghi mỗi mã hoạt động của D1, cộng 1 đoạn ngẫu nhiên toàn dải INT16), 137.700 mẫu. So tư thế từng mẫu cùng v, h, Δh cuối: trùng hết, đi qua đủ 8 tư thế. Toàn bộ `m0_test`: TẤT CẢ PASS.

**Độ đúng trên D1.** 1.844 bản ghi; tư thế ở cuối bản ghi so với mô tả hoạt động; mẫu 50 Hz lặp thành 100 Hz:

| Nhóm | Đúng |
|---|---|
| Đứng (801–810, ngã có đứng dậy 905/906/914/916) | 721/774 = **93,2 %** |
| Ngồi (811, 812, 814, 816, ngã ngồi 909) | 246/300 = **82,0 %** |
| Nằm, nhận ra là nằm | 718/770 = **93,2 %** |
| Nằm, đúng cả hướng (ngửa / sấp / nghiêng) | 615/770 = 79,9 % |
| Tổng (nằm tính theo hướng) | 1.582/1.844 = 85,8 % |

Chi tiết theo mã hoạt động ở [posture_eval.txt](posture_eval.txt).

**ESP32:** `arduino-cli` (core 3.0.7) build đạt, 966.801 B flash, 51.432 B RAM, 0 cảnh báo. Trang web đã thử với dữ liệu giả: ảnh [web_tu_the_du_lieu_gia.png](web_tu_the_du_lieu_gia.png); JS đã qua kiểm cú pháp.

## Giới hạn, còn mở

- **Chưa nạp ESP32, chưa thử trên mũ.** Số trên là của D1 (cảm biến ở đầu, 25 Hz gốc). Trên mũ thật: [CẦN XÁC MINH – nguồn: buổi thử tư thế theo `docs/huong_dan_nap_chay.md` mục 3].
- Hướng nằm phụ thuộc trục lắp cảm biến: X trước, Y trái, Z lên. Nếu MPU6050 trên mũ lắp khác hướng thì ngửa/sấp hoặc trái/phải sẽ đổi chỗ, phải đổi dấu trong `posture.c` cùng `posture_model.py`.
- Đứng/ngồi suy từ thay đổi độ cao, nên lúc bật luôn là "Đứng thẳng". Lỗi chính trên D1:
  - ngồi nhưng báo đứng: 811 9/60, 812 10/60, 816 9/61, ngã rồi ngồi 909 11/59 (đầu hạ chưa tới ngưỡng, hoặc Δh của đợt dậy từ giường ≥ 1,5 m);
  - đứng nhưng báo ngồi: 804 7/58;
  - đứng nhưng cuối bản ghi báo nằm: 806–810, 4–5/60 mỗi mã.
- Nằm sau ngã (901–919) đôi khi sai hướng (ngửa ↔ nghiêng) vì người nằm chéo; "nhận ra là nằm" vẫn 93,2 %.
