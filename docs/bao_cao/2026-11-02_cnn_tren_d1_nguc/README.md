# 2026-11-02 — Đo CNN N2 đã có trên D1 kênh ngực

**Câu hỏi:** mô hình đang nạp học từ D1 kênh đầu, vậy nó nhận dữ liệu cảm biến ở ngực tốt tới đâu?

**Cách làm:** không huấn luyện lại, không đổi weight, không nạp board. Chạy `ml/out/n2_11_d1` bằng số học INT8 trùng golden (`cn.int_forward`) trên `ml/data/public/d1_windows_nguc_340539.npz` (cảm biến 340539, 8 người 101–108, 840 cú ngã, 3,85 giờ sinh hoạt). Công thức Macro-F1, recall sự kiện và 2/3 phiếu lấy từ `ml/train_cnn.py`.

```bash
python -I tools/cnn_tren_d1_nguc.py --out docs/bao_cao/2026-11-02_cnn_tren_d1_nguc/ket_qua.txt
```

Số liệu từng người: [ket_qua.txt](ket_qua.txt).

## Kết quả (nguồn: phát lại D1 công khai, T_SCORE 0, chỉ CNN + 2/3 phiếu)

| Mô hình | Kênh | Macro-F1 TB | Recall sự kiện | 2/3 phiếu nhầm trên sinh hoạt |
|---|---|---|---|---|
| Cuối, **đang nạp trên FPGA** | đầu (người đã có trong tập huấn luyện) | 0,9923 | 840/840 = 100 % | 5 lần = 1,30/h |
| Cuối, **đang nạp trên FPGA** | **ngực** | **0,9850** | **816/840 = 97,1 %** | **7 lần = 1,82/h** |
| LOSO, người để riêng | đầu | 0,9814 | 838/840 = 99,8 % | 30 lần = 7,78/h |
| LOSO, người để riêng | **ngực** | **0,9866** | **828/840 = 98,6 %** | **8 lần = 2,08/h** |

Khi sang ngực, recall giảm 1,2–2,9 điểm %. Số báo nhầm rất ít lần nên chỉ là ước lượng thô.

## Kiểm độ tin cậy

- Đối chứng: cùng mã, LOSO kênh đầu trùng `ml/out/n2_11_d1/report.txt` từng người về Macro-F1 và số sự kiện: PASS (8/8).
- File ngực không phải bản sao kênh đầu: trên 2.369 bản ghi chung, 0 cửa sổ đầu tiên của bản ghi nào trùng hết giữa hai kênh.

## Giới hạn: đọc số này như thế nào

1. **Không phải độ chính xác khi đeo thiết bị của nhóm.** D1 dùng cảm biến Xsens 25 Hz (nội suy lên 50 Hz), gắn theo cách của bộ dữ liệu, động tác do người thử mô phỏng.
2. **Hàng "đang nạp" không độc lập về người:** cả 8 người đều có trong tập huấn luyện (kênh đầu), và cùng lần thực hiện được ghi đồng thời ở hai kênh.
3. **Hàng LOSO độc lập về người hơn, nhưng không phải weight đang nạp.**
4. **Chưa qua Safety FSM và `nga.c`:** kênh ngực chưa có bản ghi liền (việc B1).
5. **D1 không có động tác ngồi phịch mạnh như log của nhóm.** Trên log đeo ngực 28/10 (một người, một buổi), CNN nghi đúng 14/14 cú ngã nhưng cũng nghi 19 lần khi ngồi phịch ([PROJECT_MASTER.md](../../../PROJECT_MASTER.md), mục 4.4). Vì vậy tỉ lệ báo nhầm ở trên không đại diện cho thiết bị thật, và `nga.c` vẫn cần thiết.

## Được nói

> CNN học từ D1 kênh đầu. Không huấn luyện lại, đo trên D1 kênh ngực (8 người): Macro-F1 0,985, recall sự kiện 97,1 % với mô hình đang nạp; 98,6 % với mô hình để riêng từng người. Đây là dữ liệu công khai, chỉ đo CNN + 2/3 phiếu.

Không được nói "CNN học từ dữ liệu ngực" hay "độ chính xác khi đeo ngực là 97,1 %".
