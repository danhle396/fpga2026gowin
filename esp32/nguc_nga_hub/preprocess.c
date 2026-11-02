/* preprocess.c — xem preprocess.h. Không float, không chia. `>>` trên số âm là dịch số học (Arm Compiler 6). */
#include <string.h>
#include "preprocess.h"

static const uint8_t k_shift[PRE_CH] = { ACC_SHIFT, ACC_SHIFT, ACC_SHIFT, GYR_SHIFT, GYR_SHIFT, GYR_SHIFT };

void pre_init(pre_state_t *s)
{
    memset(s, 0, sizeof(*s));
}

int8_t pre_q8(int32_t y, unsigned shift)
{
    int32_t q = (y + (1L << (shift - 1))) >> shift;
    if (q > 127)  q = 127;
    if (q < -128) q = -128;
    return (int8_t)q;
}

unsigned pre_push_raw(pre_state_t *s, const int16_t r[PRE_CH], int8_t out[PRE_CH])
{
    int c;

    if (!s->primed) {                       /* r[−2] = r[−1] = r[0] */
        for (c = 0; c < PRE_CH; c++)
            s->h2[c] = s->h1[c] = r[c];
        s->primed = 1;
    }
    if (!s->odd) {                          /* r[2n]: giữ lại, chờ r[2n+1] */
        for (c = 0; c < PRE_CH; c++)
            s->ev[c] = r[c];
        s->odd = 1;
        return 0;
    }

    int8_t *dst = &s->ring[s->wr * PRE_CH];
    for (c = 0; c < PRE_CH; c++) {
        int32_t y = ((int32_t)s->h2[c] + 3 * (int32_t)s->h1[c] + 3 * (int32_t)s->ev[c] + (int32_t)r[c] + 4) >> 3;
        dst[c] = pre_q8(y, k_shift[c]);
        s->h2[c] = s->ev[c];                /* bước 2 mẫu thô */
        s->h1[c] = r[c];
    }
    s->odd = 0;
    if (out)
        memcpy(out, dst, PRE_CH);

    s->wr = (uint16_t)((s->wr + 1u) % PRE_WIN);
    s->n_out++;
    if (s->n_out >= PRE_WIN && (s->n_out % PRE_HOP) == 0)
        return PRE_NEW_SAMPLE | PRE_NEW_WINDOW;
    return PRE_NEW_SAMPLE;
}

void pre_window(const pre_state_t *s, const int8_t **seg1, uint16_t *n1, const int8_t **seg2, uint16_t *n2)
{
    *seg1 = &s->ring[s->wr * PRE_CH];
    *n1   = (uint16_t)((PRE_WIN - s->wr) * PRE_CH);
    *seg2 = s->ring;
    *n2   = (uint16_t)(s->wr * PRE_CH);
}
