/*
 * nga.h — xác nhận ngã thật (28/10, chạy trên ESP32 trong hub.c). Nhóm: chỉ báo ngã thật, không có "nghi ngã":
 * ngồi xuống mạnh hay lăn người khi đang nằm làm CNN báo 2/3 FALL (SUSPECT) nhưng không phải ngã.
 *
 * SUSPECT của Safety FSM chỉ là bước nghi (CNN). Ngã thật khi có thêm ba dấu hiệu vật lý:
 *   1. trước đó đang thẳng (đứng / ngồi / đi): trong khoảng NGA_TRUOC_TU..NGA_TRUOC_DEN khối trước SUSPECT có ít
 *      nhất một khối hướng ngực đã chốt THẲNG (posture.c) → lăn người khi đang nằm bị loại, kể cả khi lúc lăn ngực
 *      đi qua vùng CÚI (log đeo ngực 28/10, giây 100,8–101,8: N → C → N, đỉnh 2,7 g);
 *   2. va chạm: đỉnh |a| trong NGA_VA_CHAM_KHOI khối gần nhất (D1 kênh ngực: đỉnh khi ngã trung vị 4,11 g, p10
 *      2,68 g; sinh hoạt p90 2,17 g):
 *      ≥ NGA_VA_CHAM_MANH (3,0 g) → xác nhận ngay (ngã quỳ, ngã ngồi, ngã rồi đứng dậy: không nằm, Δh không tin được);
 *      < NGA_VA_CHAM_LSB (2,5 g) → loại (ngồi xuống mạnh; nằm xuống giường khi đeo: 2,4 g);
 *   3. va chạm 2,5–3,0 g thì cần thêm: sau đó nằm (hướng chốt NẰM), hoặc một đợt cử động hạ ngực ≥ NGA_HA_H (0,5 m),
 *      hoặc vào PRE_ALARM; trong NGA_CHO_MS không có thì loại.
 * Bản 2 (28/10): bản 1 bắt buộc mục 3 cho mọi cú ngã, trên D1 người 102 chỉ xác nhận 73/101 cú ngã.
 * Loại → hub gọi safety_bo_nghi() (FSM về MONITOR, WHY_KHONG_NGA): còi, web, bộ đếm không hề thấy.
 * Ngưỡng là bản đầu, chốt bằng dữ liệu nhóm tự thu khi đeo ngực (việc B2); mỗi lần xét ghi dòng log để chỉnh.
 * Chưa vào SPEC / golden Python: việc B3.
 */
#ifndef NGA_H
#define NGA_H

#include <stdint.h>

#define NGA_KHOI_VONG   36u     /* lịch sử khối 32 mẫu: 11,5 s */

enum { NGA_KHONG = 0, NGA_DANG_XET, NGA_XAC_NHAN, NGA_BO };
enum { NGA_HD_KHONG = 0, NGA_HD_XAC_NHAN, NGA_HD_BO };        /* nga_buoc(): việc hub phải làm */
enum { NGA_LD_KHONG = 0, NGA_LD_DANG_NAM /* trước đó không thẳng */, NGA_LD_KHONG_VA_CHAM, NGA_LD_KHONG_HA,     /* lý do loại */
       NGA_LD_NAM, NGA_LD_HA_NGUC, NGA_LD_BAT_DONG, NGA_LD_VA_CHAM_MANH };           /* lý do xác nhận */

typedef struct {
    uint32_t peak2[NGA_KHOI_VONG];  /* đỉnh |a|² của từng khối (LSB²) */
    uint8_t  huong[NGA_KHOI_VONG];  /* hướng ngực đã chốt ở cuối khối (posture.c: 0 thẳng, 1 nằm, 2 cúi) */
    uint8_t  i, n;
    uint32_t blk_peak2;
    uint8_t  trang_thai, ly_do, truoc_thang, co_va_cham, va_cham_manh, co_dot;
    uint32_t t0, peak2_sk;          /* lúc vào SUSPECT, đỉnh |a|² trong cửa sổ va chạm */
    int64_t  dh_dot;                /* Δh của đợt cử động kết thúc sau t0 (đơn vị posture.c) */
    uint32_t n_xac_nhan, n_bo;
} nga_t;

void nga_init(nga_t *n);
void nga_mau(nga_t *n, uint32_t mag2);              /* mỗi mẫu: |a|² (trục người, LSB²) */
void nga_khoi(nga_t *n, uint8_t huong);             /* mỗi khi posture.c đóng khối 32 mẫu */
void nga_dot(nga_t *n, int64_t dh);                 /* mỗi khi posture.c kết thúc một đợt cử động */
void nga_bat_dau(nga_t *n, uint32_t now);           /* FSM vừa vào SUSPECT */
void nga_het(nga_t *n);                             /* FSM đã về MONITOR / STANDBY */
/* Mỗi khe 10 ms. huong = hướng ngực đang chốt, pre_alarm = FSM đang ở PRE_ALARM. Trả về NGA_HD_*. */
int  nga_buoc(nga_t *n, uint32_t now, uint8_t huong, uint8_t pre_alarm);

#endif
