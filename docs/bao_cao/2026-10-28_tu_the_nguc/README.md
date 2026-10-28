# 2026-10-28 — Tư thế khi đeo ở ngực: offset gia tốc + quy tắc cúi sâu

Lần đo trước (`2026-10-28_deo_nguc`) cầm thiết bị trên tay. Nhóm báo ngồi, đứng thẳng và cúi người chưa phân biệt rõ, nên đo lại khi **đeo trên người**. Lệnh: `ghi_uart --tu-the`, 9 bước, mỗi bước 6 s để đổi + 10 s giữ yên. File log: [truc_nguc_deo_20261028_170503.txt](truc_nguc_deo_20261028_170503.txt), 14.714 mẫu. Lúc ghi, ESP32 đã đổi trục nhưng chưa trừ offset.

## Kết quả đo ([truc_cam_bien_truoc_sua.txt](truc_cam_bien_truoc_sua.txt))

- **Bảng đổi trục đúng**: log đã ở trục người, công cụ suy ra +1 +2 +3; kiểm chéo bằng nghiêng trái cũng đúng.
- Trước khi sửa: đúng **7/9**. Hai bước sai:
  - cúi → NAM_SAP;
  - đứng thẳng lại sau khi cúi → NGOI.

**Nguyên nhân 1, offset gia tốc** ([hieu_chuan_gia_toc.txt](hieu_chuan_gia_toc.txt)):
- |g| đo được: 2254 khi nằm ngửa, 1840–1854 khi cúi hoặc nằm sấp, tức trục X người (trục Z của MPU6050) lệch khoảng 0,1 g.
- Khớp offset từ 9 tư thế yên ra (+204, −3, −4) LSB; sau khi trừ, |g| còn 2034–2054.
- Hậu quả của offset: |a| lệch > 120 LSB ngay cả khi yên, nên `posture.c` tưởng đang cử động suốt. Có đợt "cử động" dài 21 s, độ cao trôi tới −11,9 m.

**Nguyên nhân 2, cúi và nằm sấp trùng hướng:** cúi nhặt đồ ngực ngả 79°, nằm sấp 78°. Sau khi trừ offset, độ cao các đợt cử động ([sau_sua.txt](sau_sua.txt)) là:

| Động tác | Độ cao ngực thay đổi |
|---|---|
| ngồi xuống | −0,36 m |
| đứng dậy | +0,57 m |
| **cúi** | **−0,20 m** |
| **đứng → nằm ngửa** | **−0,89 m** |

## Sửa

1. `fw_config.h`: `ACC_OFF_X/Y/Z` = 204 / −3 / −4 (trục người, khi `FW_VI_TRI_DEO 1`). `hub_doi_truc` trừ offset sau khi đổi trục. CNN, khối A.8 và tư thế đều nhận dữ liệu đã trừ; LOG in dữ liệu đã trừ.
2. `posture_model.py` / `posture.c`, mục 4 của A.11, **chỉ khi đeo ngực** (`Posture(nguc=1)`, `posture_init(p, 1)`): khi hướng chốt NẰM, úp về trước, đi thẳng từ THẲNG/CÚI và đợt cử động vừa xong hạ < 0,5 m thì coi là **CÚI**, không đếm là nằm. Hết cúi sâu khi:
   - đầu/ngực rời hướng NẰM, hoặc quay sang ngửa/nghiêng;
   - một đợt cử động hạ thêm ≥ 0,3 m;
   - úp yên quá 30 s.

## Kết quả sau khi sửa

- Log đeo ngực, đã trừ offset: **9/9 đúng**: đứng, ngồi, đứng dậy, cúi, đứng lại, nằm ngửa, nghiêng phải, nghiêng trái, nằm sấp.
- Chỉ trừ offset mà không có quy tắc cúi sâu: 7/9. Bật quy tắc cúi sâu cho cả D1 (cảm biến ở đầu) thì D1 tụt xuống 82,6 %, nên quy tắc chỉ bật khi đeo ngực. D1 ở chế độ mũ vẫn **85,8 %**, như trước.
- m0_test TẤT CẢ PASS:
  - `posture.c` == Python ở cả hai chế độ, 75 bản ghi, 155.415 mẫu;
  - phép kiểm mới "tư thế đeo ngực 9/9";
  - `hub.c` == golden khi luồng MCU có đổi trục + offset.
- Đã nạp ESP32 (COM4); MCU không đổi. Trên board (nằm ngửa trên bàn): |g| = 2051, tư thế NAM_NGUA.

## Giới hạn

- Offset là của **riêng con MPU6050 này**. Thay cảm biến thì đo lại bằng `ghi_uart --tu-the` + `hc_acc.py`.
- Ngồi và đứng phân biệt bằng độ cao thay đổi lúc ngồi xuống / đứng dậy, nên lúc bật nguồn luôn ra "Đứng thẳng". Ngồi xuống quá chậm (|a| không vượt 0,06 g) thì không nhận ra.
- Cúi rồi nằm hẳn xuống sàn mà ngực hạ < 0,3 m, hoặc nằm sấp ngay từ tư thế ngồi trên giường (ngực hạ < 0,5 m), sẽ hiện CÚI cho tới 30 s.
- Mới thử trên một người, một lần [CẦN XÁC MINH – nguồn: thêm người / thêm lần thử].
