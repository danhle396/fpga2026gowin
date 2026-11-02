/* nga.c — xem nga.h. */
#include <string.h>
#include "nga.h"
#include "fw_config.h"

#define HUONG_THANG 0u                  /* posture.c O_THANG */

void nga_init(nga_t *n) { memset(n, 0, sizeof *n); }

void nga_mau(nga_t *n, const int16_t r[6])
{
    uint32_t a2 = (uint32_t)(r[0] * r[0]) + (uint32_t)(r[1] * r[1]) + (uint32_t)(r[2] * r[2]);
    uint32_t w2 = (uint32_t)(r[3] * r[3]) + (uint32_t)(r[4] * r[4]) + (uint32_t)(r[5] * r[5]);
    if (a2 > n->blk_peak2) n->blk_peak2 = a2;
    if (w2 > n->blk_wpeak2) n->blk_wpeak2 = w2;
    for (int k = 0; k < 3; k++) n->blk_s[k] += r[k];
}

/* gia tốc trung bình của khối lệch ≥ 45° khỏi trục Z (lên): ax² + ay² ≥ tan²45° · az², hoặc az ≤ 0 */
static uint8_t lech(const int32_t s[3])
{
    int64_t ngang = (int64_t)s[0] * s[0] + (int64_t)s[1] * s[1];
    return s[2] <= 0 || ngang * 100 >= (int64_t)s[2] * s[2] * NGA_NGHIENG_TAN2_X100;
}

void nga_khoi(nga_t *n, uint8_t huong)
{
    uint8_t ng = lech(n->blk_s);
    n->peak2[n->i] = n->blk_peak2;
    n->wpeak2[n->i] = n->blk_wpeak2;
    n->huong[n->i] = huong;
    n->nghieng[n->i] = ng;
    n->i = (uint8_t)((n->i + 1u) % NGA_KHOI_VONG);
    if (n->n < NGA_KHOI_VONG) n->n++;
    if (n->trang_thai == NGA_DANG_XET) {                /* khối vừa đóng là khối thứ d_moi sau khối va chạm */
        if (n->d_moi <= NGA_QUAY_KHOI && n->blk_wpeak2 > n->wpeak2_sk) n->wpeak2_sk = n->blk_wpeak2;
        if (n->d_moi <= NGA_NGHIENG_KHOI && ng) n->co_nghieng = 1;
        if (n->d_moi < 255u) n->d_moi++;
    }
    n->blk_peak2 = 0;
    n->blk_wpeak2 = 0;
    n->blk_s[0] = n->blk_s[1] = n->blk_s[2] = 0;
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
    uint32_t pk = n->blk_peak2;                         /* k = 0: khối đang gom */
    uint8_t k_vc = 0;
    for (uint8_t k = 1; k <= NGA_VA_CHAM_KHOI && k <= n->n; k++)
        if (n->peak2[lui(n, k)] > pk) { pk = n->peak2[lui(n, k)]; k_vc = k; }
    uint32_t wpk = 0;                                   /* quay: khối đã đóng trong ±NGA_QUAY_KHOI quanh khối va chạm */
    uint8_t ng = 0;                                     /* nghiêng: khối đã đóng từ khối va chạm trở về sau */
    for (uint8_t k = 1; k <= n->n && k <= k_vc + NGA_QUAY_KHOI; k++) {
        if (k + NGA_QUAY_KHOI >= k_vc && n->wpeak2[lui(n, k)] > wpk) wpk = n->wpeak2[lui(n, k)];
        if (k <= k_vc && n->nghieng[lui(n, k)]) ng = 1;
    }
    uint8_t thang = n->n < NGA_TRUOC_TU;                /* vừa bật, chưa đủ lịch sử: coi như đang thẳng */
    for (uint8_t k = NGA_TRUOC_DEN; k <= NGA_TRUOC_TU && k <= n->n; k++)
        if (n->huong[lui(n, k)] == HUONG_THANG) thang = 1;
    n->trang_thai = NGA_DANG_XET;
    n->t0 = now;
    n->peak2_sk = pk;
    n->wpeak2_sk = wpk;
    n->d_moi = k_vc;                                    /* khối đang gom là khối thứ k_vc sau khối va chạm */
    n->truoc_thang = thang;
    n->co_va_cham = pk >= (uint32_t)NGA_VA_CHAM_LSB * (uint32_t)NGA_VA_CHAM_LSB;
    n->co_nghieng = ng;
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

int nga_buoc(nga_t *n, uint32_t now)
{
    if (n->trang_thai != NGA_DANG_XET) return NGA_HD_KHONG;
    n->co_quay = n->wpeak2_sk >= (uint32_t)NGA_QUAY_LSB * (uint32_t)NGA_QUAY_LSB;
    if (!n->truoc_thang)                                    return ket(n, NGA_BO, NGA_LD_DANG_NAM);
    if (!n->co_va_cham)                                     return ket(n, NGA_BO, NGA_LD_KHONG_VA_CHAM);
    if (n->co_quay && n->co_nghieng)                        return ket(n, NGA_XAC_NHAN, NGA_LD_NGA);
    if (!n->co_quay && n->d_moi > NGA_QUAY_KHOI)            return ket(n, NGA_BO, NGA_LD_KHONG_QUAY);
    if (n->d_moi > NGA_NGHIENG_KHOI || now - n->t0 >= NGA_CHO_MS)
        return ket(n, NGA_BO, n->co_quay ? NGA_LD_KHONG_NGHIENG : NGA_LD_KHONG_QUAY);
    return NGA_HD_KHONG;
}
