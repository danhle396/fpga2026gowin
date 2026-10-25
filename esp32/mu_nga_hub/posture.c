/* posture.c — xem posture.h. Dịch từng dòng của ml/src/posture_model.py; phép / của C làm tròn về 0 như tdiv(). */
#include <string.h>
#include "posture.h"

#define G_LSB          2048
#define MOVE_DEV       120
#define STILL_N        30u
#define LONG_N         400u
#define BLK            32
#define HOLD           3
#define UP_PCT         82
#define LIE_PCT        50
#define LIE_LONG       300u
#define NGOI_H         522094LL       /* 0,25 m */
#define NGOI_H_NGA     313256LL       /* 0,15 m */
#define DUNG_TU_NAM_H  3132568LL      /* 1,5 m */
#define CAP            1000000u
enum { O_THANG = 0, O_NAM, O_CUI };

static const char *const k_ten[] = { "DUNG", "NGOI", "NAM_NGUA", "NAM_SAP", "NGHIENG_TRAI", "NGHIENG_PHAI", "CUI",
                                     "DI_LAI" };

const char *posture_name(uint8_t tt) { return tt < 8u ? k_ten[tt] : "?"; }

static uint32_t isqrt32(uint32_t x)
{
    uint32_t r = 0, b = 1UL << 30;
    while (b > x) b >>= 2;
    while (b) {
        if (x >= r + b) { x -= r + b; r = (r >> 1) + b; }
        else            { r >>= 1; }
        b >>= 2;
    }
    return r;
}

static int32_t iabs(int32_t a) { return a < 0 ? -a : a; }

void posture_init(posture_t *p)
{
    memset(p, 0, sizeof *p);
    p->tt = TT_DUNG;
    p->huong = O_THANG;
    p->cand = O_THANG;
    p->since_move = STILL_N;
    p->g_ref = G_LSB;
}

static void quyet(posture_t *p, int64_t dh, uint8_t ngh)
{
    p->cho = 0;
    if (dh <= -(ngh ? NGOI_H_NGA : NGOI_H)) p->ngoi = 1;
    else if (dh >= NGOI_H)                  p->ngoi = 0;
}

static void quyet_day(posture_t *p, int64_t dh)
{
    p->ngoi = dh < DUNG_TU_NAM_H ? 1u : 0u;
    p->cho_day = 0;
}

static void upd_tt(posture_t *p)
{
    if (p->huong == O_THANG)    p->tt = p->di_lai ? TT_DI_LAI : (p->ngoi ? TT_NGOI : TT_DUNG);
    else if (p->huong == O_CUI) p->tt = TT_CUI;
    else if (iabs(p->my) > iabs(p->mx)) p->tt = p->my > 0 ? TT_NGHIENG_PHAI : TT_NGHIENG_TRAI;
    else                        p->tt = p->mx > 0 ? TT_NAM_NGUA : TT_NAM_SAP;
}

int posture_push(posture_t *p, const int16_t r[6])
{
    int32_t ax = r[0], ay = r[1], az = r[2];
    int32_t mag = (int32_t)isqrt32((uint32_t)(ax * ax) + (uint32_t)(ay * ay) + (uint32_t)(az * az));
    uint8_t old = p->tt;
    if (p->huong == O_NAM && p->nam_n < CAP) {
        p->nam_n++;
        if (p->nam_n >= LIE_LONG) p->nam_lau = 1;
    }
    /* --- đợt cử động, độ cao đầu --- */
    if (iabs(mag - G_LSB) > MOVE_DEV) p->since_move = 0;
    else if (p->since_move < CAP)     p->since_move++;
    if (p->since_move < STILL_N) {
        if (!p->moving) {
            p->moving = 1; p->n_ep = 0; p->v = 0; p->h = 0;
            p->ep_nghieng = (p->huong == O_NAM);
            p->cho = 0;
        }
        p->n_ep++;
        p->v += mag - p->g_ref;
        p->h += p->v;
        if (p->n_ep > LONG_N && p->huong == O_THANG && !p->ep_nghieng) { p->di_lai = 1; p->ngoi = 0; }
    } else if (p->moving) {
        p->moving = 0;
        int64_t dh = p->h - (p->v * (int64_t)(p->n_ep + 1u)) / 2;
        p->dh_cuoi = dh;
        if (p->di_lai)                        p->di_lai = 0;
        else if (p->huong == O_THANG && p->cho_day) quyet_day(p, dh);
        else if (p->huong == O_THANG)         quyet(p, dh, p->ep_nghieng);
        else                                  { p->cho = 1; p->ngh_cuoi = p->ep_nghieng; }
    } else {
        p->g_acc += mag;
        if (++p->g_n == BLK) { p->g_ref = p->g_acc / BLK; p->g_acc = 0; p->g_n = 0; }
    }
    /* --- hướng đầu theo khối 32 mẫu --- */
    p->sx += ax; p->sy += ay; p->sz += az;
    if (++p->nb == BLK) {
        p->mx = p->sx / BLK; p->my = p->sy / BLK;
        int32_t mz = p->sz / BLK;
        p->sx = p->sy = p->sz = 0; p->nb = 0;
        int32_t gm = (int32_t)isqrt32((uint32_t)(p->mx * p->mx) + (uint32_t)(p->my * p->my) + (uint32_t)(mz * mz));
        uint8_t o = (mz * 100 > UP_PCT * gm) ? O_THANG : (mz * 100 < LIE_PCT * gm) ? O_NAM : O_CUI;
        if (o == p->cand) { if (p->cand_n < 255u) p->cand_n++; }
        else              { p->cand = o; p->cand_n = 1; }
        if (p->cand_n >= HOLD && o != p->huong) {
            if (o == O_THANG && p->nam_lau) {
                p->nam_lau = 0;
                p->cho_day = 1;
                if (!p->moving) { quyet_day(p, p->dh_cuoi); p->cho = 0; }
            } else if (o == O_THANG && p->cho && !p->moving) {
                quyet(p, p->dh_cuoi, p->ngh_cuoi);
            }
            if (o != O_NAM) p->nam_n = 0;
            p->huong = o;
        }
        if (p->moving && p->huong == O_NAM) p->ep_nghieng = 1;
        upd_tt(p);
    }
    return p->tt != old;
}
