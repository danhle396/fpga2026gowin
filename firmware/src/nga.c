/* nga.c — xem nga.h. */
#include <string.h>
#include "nga.h"
#include "fw_config.h"

#define HUONG_THANG 0u                  /* posture.c O_THANG */
#define HUONG_NAM   1u                  /* posture.c O_NAM */

void nga_init(nga_t *n) { memset(n, 0, sizeof *n); }

void nga_mau(nga_t *n, uint32_t mag2)
{
    if (mag2 > n->blk_peak2) n->blk_peak2 = mag2;
}

void nga_khoi(nga_t *n, uint8_t huong)
{
    n->peak2[n->i] = n->blk_peak2;
    n->huong[n->i] = huong;
    n->i = (uint8_t)((n->i + 1u) % NGA_KHOI_VONG);
    if (n->n < NGA_KHOI_VONG) n->n++;
    n->blk_peak2 = 0;
}

void nga_dot(nga_t *n, int64_t dh)
{
    if (n->trang_thai != NGA_DANG_XET) return;
    if (!n->co_dot || dh < n->dh_dot) n->dh_dot = dh;  /* đợt hạ sâu nhất kể từ lúc vào SUSPECT */
    n->co_dot = 1;
}

/* khối thứ k tính lùi (k = 1: khối vừa đóng) */
static uint8_t lui(const nga_t *n, uint8_t k) { return (uint8_t)((n->i + NGA_KHOI_VONG - k) % NGA_KHOI_VONG); }

void nga_bat_dau(nga_t *n, uint32_t now)
{
    uint32_t pk = n->blk_peak2;
    for (uint8_t k = 1; k <= NGA_VA_CHAM_KHOI && k <= n->n; k++)
        if (n->peak2[lui(n, k)] > pk) pk = n->peak2[lui(n, k)];
    uint8_t thang = n->n < NGA_TRUOC_TU;                /* vừa bật, chưa đủ lịch sử: coi như đang thẳng */
    for (uint8_t k = NGA_TRUOC_DEN; k <= NGA_TRUOC_TU && k <= n->n; k++)
        if (n->huong[lui(n, k)] == HUONG_THANG) thang = 1;
    n->trang_thai = NGA_DANG_XET;
    n->t0 = now;
    n->peak2_sk = pk;
    n->truoc_thang = thang;
    n->co_va_cham = pk >= (uint32_t)NGA_VA_CHAM_LSB * (uint32_t)NGA_VA_CHAM_LSB;
    n->co_dot = 0;
    n->dh_dot = 0;
    n->ly_do = NGA_LD_KHONG;
}

void nga_het(nga_t *n) { n->trang_thai = NGA_KHONG; }

static int ket(nga_t *n, uint8_t tt, uint8_t ld)
{
    n->trang_thai = tt;
    n->ly_do = ld;
    if (tt == NGA_XAC_NHAN) { n->n_xac_nhan++; return NGA_HD_XAC_NHAN; }
    n->n_bo++;
    return NGA_HD_BO;
}

int nga_buoc(nga_t *n, uint32_t now, uint8_t huong, uint8_t pre_alarm)
{
    if (n->trang_thai != NGA_DANG_XET) return NGA_HD_KHONG;
    if (!n->truoc_thang)                                    return ket(n, NGA_BO, NGA_LD_DANG_NAM);
    if (!n->co_va_cham)                                     return ket(n, NGA_BO, NGA_LD_KHONG_VA_CHAM);
    if (huong == HUONG_NAM)                                 return ket(n, NGA_XAC_NHAN, NGA_LD_NAM);
    if (n->co_dot && n->dh_dot <= -(int64_t)NGA_HA_H)       return ket(n, NGA_XAC_NHAN, NGA_LD_HA_NGUC);
    if (pre_alarm)                                          return ket(n, NGA_XAC_NHAN, NGA_LD_BAT_DONG);
    if (now - n->t0 >= NGA_CHO_MS)                          return ket(n, NGA_BO, NGA_LD_KHONG_HA);
    return NGA_HD_KHONG;
}
