/*
 * nga.h — xác nhận ngã thật (28/10, chạy trên ESP32 trong hub.c). Nhóm: chỉ báo ngã thật, không có "nghi ngã":
 * ngồi xuống mạnh hay lăn người khi đang nằm làm CNN báo 2/3 FALL (SUSPECT) nhưng không phải ngã.
 *
 * SUSPECT của Safety FSM chỉ là bước nghi (CNN). Ngã thật khi có ĐỦ bốn dấu hiệu vật lý:
 *   1. trước đó đang thẳng (đứng / ngồi / đi): trong khoảng NGA_TRUOC_TU..NGA_TRUOC_DEN khối trước SUSPECT có ít
 *      nhất một khối hướng ngực đã chốt THẲNG (posture.c) → lăn người khi đang nằm bị loại, kể cả khi lúc lăn ngực
 *      đi qua vùng CÚI (log đeo ngực 28/10, giây 100,8–101,8: N → C → N, đỉnh 2,7 g);
 *   2. va chạm: đỉnh |a| trong NGA_VA_CHAM_KHOI khối gần nhất ≥ NGA_VA_CHAM_LSB (2,5 g); khối có đỉnh là "khối va chạm";
 *   3. quay nhanh: đỉnh |ω| trong ±NGA_QUAY_KHOI khối quanh khối va chạm ≥ NGA_QUAY_LSB (220 °/s);
 *   4. ngực nghiêng: một khối từ khối va chạm tới NGA_NGHIENG_KHOI khối sau có hướng trung bình của gia tốc lệch
 *      ≥ 45° khỏi phương thẳng đứng.
 * Thiếu dấu hiệu 3 hoặc 4 khi đã hết cửa sổ (hoặc NGA_CHO_MS sau SUSPECT) thì loại.
 * Bản 3 (28/10): bản 2 xác nhận ngay mọi va chạm ≥ 3 g, nên ngồi phịch xuống ghế khi đeo ngực (4,3–6,2 g) bị báo
 * ngã 9/10 lần. Log đeo ngực của nhóm (dong_tac, nga 28/10): ngồi mạnh nghiêng ≤ 31°, quay ≤ 149 °/s; 14 cú ngã lên
 * nệm nghiêng 58–80°, quay 258–467 °/s. Đổi lại, ngã ngồi / ngã quỳ mà thân vẫn thẳng sẽ bị bỏ sót.
 * Loại → hub gọi safety_bo_nghi() (FSM về MONITOR, WHY_KHONG_NGA): còi, web, bộ đếm không hề thấy.
 * Mỗi lần xét ghi dòng log để chỉnh ngưỡng. Chưa vào SPEC / golden Python: việc B3.
 */
#ifndef NGA_H
#define NGA_H

#include <stdint.h>

#define NGA_KHOI_VONG   36u     /* lịch sử khối 32 mẫu: 11,5 s */

enum { NGA_KHONG = 0, NGA_DANG_XET, NGA_XAC_NHAN, NGA_BO };
enum { NGA_HD_KHONG = 0, NGA_HD_XAC_NHAN, NGA_HD_BO };        /* nga_buoc(): việc hub phải làm */
enum { NGA_LD_KHONG = 0, NGA_LD_DANG_NAM /* trước đó không thẳng */, NGA_LD_KHONG_VA_CHAM,      /* lý do loại */
       NGA_LD_KHONG_NGHIENG, NGA_LD_KHONG_QUAY,
       NGA_LD_NGA };                                                                 /* xác nhận: đủ 4 dấu hiệu */

typedef struct {
    uint32_t peak2[NGA_KHOI_VONG];  /* đỉnh |a|² của từng khối (LSB²) */
    uint32_t wpeak2[NGA_KHOI_VONG]; /* đỉnh |ω|² của từng khối (LSB²) */
    uint8_t  huong[NGA_KHOI_VONG];  /* hướng ngực đã chốt ở cuối khối (posture.c: 0 thẳng, 1 nằm, 2 cúi) */
    uint8_t  nghieng[NGA_KHOI_VONG];/* gia tốc trung bình của khối lệch ≥ 45° khỏi phương thẳng đứng */
    uint8_t  i, n;
    uint32_t blk_peak2, blk_wpeak2;
    int32_t  blk_s[3];              /* tổng ax, ay, az của khối đang gom */
    uint8_t  trang_thai, ly_do, truoc_thang, co_va_cham, co_quay, co_nghieng, co_dot;
    uint8_t  d_moi;                 /* đang xét: khối sắp đóng là khối thứ d_moi sau khối va chạm (0 = chính nó) */
    uint32_t t0, peak2_sk, wpeak2_sk; /* lúc vào SUSPECT; đỉnh |a|² khối va chạm; đỉnh |ω|² quanh va chạm */
    int64_t  dh_dot;                /* Δh của đợt cử động kết thúc sau t0 (đơn vị posture.c), chỉ để ghi log */
    uint32_t n_xac_nhan, n_bo;
} nga_t;

void nga_init(nga_t *n);
void nga_mau(nga_t *n, const int16_t r[6]);         /* mỗi mẫu: ax ay az gx gy gz theo trục người (LSB) */
void nga_khoi(nga_t *n, uint8_t huong);             /* mỗi khi posture.c đóng khối 32 mẫu */
void nga_dot(nga_t *n, int64_t dh);                 /* mỗi khi posture.c kết thúc một đợt cử động */
void nga_bat_dau(nga_t *n, uint32_t now);           /* FSM vừa vào SUSPECT */
void nga_het(nga_t *n);                             /* FSM đã về MONITOR / STANDBY */
/* Mỗi khe 10 ms. Trả về NGA_HD_*. */
int  nga_buoc(nga_t *n, uint32_t now);

#endif
