/*
 * posture.h — nhận dạng tư thế từ cảm biến ở đầu (A.11). C thuần, số nguyên; trùng từng bit với
 * ml/src/posture_model.py (tools/m0_test.py kiểm). Chạy trên ESP32 trong hub.c, độc lập với Safety FSM:
 * chỉ để hiển thị / báo cáo, không đổi quyết định báo ngã.
 *
 * Tư thế: đứng thẳng, ngồi, nằm ngửa, nằm sấp, nằm nghiêng trái / phải, cúi người, đang di chuyển (đi lại).
 * Đầu vào: mẫu 100 Hz, AX AY AZ INT16 (±16 g: 2048 LSB/g), trục của mũ: X trước, Y trái, Z lên.
 * Cách làm (chi tiết ở posture_model.py):
 *   - hướng đầu theo trung bình khối 32 mẫu: az > 0,82|g| THẲNG, az < 0,50|g| NẰM (hướng nằm theo trục lớn hơn
 *     của ax / ay), còn lại CÚI; giữ 3 khối mới chốt;
 *   - đứng / ngồi theo độ cao đầu qua mỗi đợt cử động (tích phân |a| − g, chỉnh trôi bằng vận tốc 0 hai đầu):
 *     hạ ≥ 0,25 m (0,15 m nếu có lúc ngả / cúi mạnh) → ngồi, lên ≥ 0,25 m → đứng; dậy sau khi nằm ≥ 3 s:
 *     lên < 1,5 m → ngồi dậy, ngược lại đứng dậy; đi lại liên tục > 4 s → đứng.
 * Kết quả trên D1 (tools/posture_eval.py, 1.844 bản ghi, tư thế cuối): đứng 93,2 %, ngồi 82,0 %, nhận ra nằm 93,2 %
 * (đúng cả hướng 79,9 %).
 */
#ifndef POSTURE_H
#define POSTURE_H

#include <stdint.h>

enum { TT_DUNG = 0, TT_NGOI, TT_NAM_NGUA, TT_NAM_SAP, TT_NGHIENG_TRAI, TT_NGHIENG_PHAI, TT_CUI, TT_DI_LAI };

typedef struct {
    uint8_t  tt, ngoi, huong, cand, cand_n, nb;
    uint8_t  moving, di_lai, ep_nghieng, nam_lau, cho_day, cho, ngh_cuoi, g_n;
    int32_t  sx, sy, sz, mx, my;
    uint32_t since_move, n_ep, nam_n;
    int32_t  g_ref, g_acc;
    int64_t  v, h, dh_cuoi;
} posture_t;

void        posture_init(posture_t *p);
/* Một mẫu 100 Hz (r[0..2] = AX AY AZ). Trả về 1 nếu tư thế vừa đổi (p->tt). */
int         posture_push(posture_t *p, const int16_t r[6]);
const char *posture_name(uint8_t tt);     /* "DUNG", "NGOI", "NAM_NGUA", ... */

#endif
