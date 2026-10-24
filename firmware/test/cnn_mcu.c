/* cnn_mcu.c — xem cnn_mcu.h. Không float, không chia; requant sau max-pool (A.5: kết quả như nhau vì requant đơn điệu). */
#include "cnn_mcu.h"

static int8_t s_buf[2][CNN_BUF_BYTES];

static int8_t requant(int32_t acc, uint8_t n)
{
    if (acc <= 0)
        return 0;
    acc >>= n;
    return (int8_t)(acc > 127 ? 127 : acc);
}

/* Một lớp: in (L × IC) → out (L/2 × OC). */
static void conv_pool(const cnn_layer_t *ly, const int8_t *in, int L, int8_t *out)
{
    const int IC = ly->ic, OC = ly->oc;
    for (int j = 0; j < L / 2; j++) {
        for (int oc = 0; oc < OC; oc++) {
            const int8_t *wo = ly->w + oc * IC * 5;
            int32_t best = INT32_MIN;
            for (int q = 0; q < 2; q++) {
                int t = 2 * j + q;
                int32_t acc = ly->b[oc];
                for (int k = 0; k < 5; k++) {
                    int pos = t + k - 2;
                    if (pos < 0 || pos >= L)
                        continue;
                    const int8_t *xp = in + pos * IC;
                    const int8_t *wp = wo + k;
                    for (int ic = 0; ic < IC; ic++)
                        acc += (int32_t)wp[ic * 5] * xp[ic];
                }
                if (acc > best)
                    best = acc;
            }
            out[j * OC + oc] = requant(best, ly->shift);
        }
    }
}

int cnn_mcu_run(const cnn_model_t *m, const int8_t *x, int32_t logits[4], uint8_t *score)
{
    const int8_t *in = x;
    int L = 128, C = 6, b = 0;
    int32_t lg[4];

    for (int i = 0; i < m->n_layers; i++) {
        conv_pool(&m->L[i], in, L, s_buf[b]);
        in = s_buf[b];
        b ^= 1;
        L /= 2;
        C = m->L[i].oc;
    }
    for (int c = 0; c < 4; c++) {
        int32_t acc = m->bd[c];
        const int8_t *w = m->wd + c * m->F;
        if (m->head_gap) {
            int sh = 0;
            while ((1 << sh) < L) sh++;
            for (int ch = 0; ch < C; ch++) {
                int32_t s = 0;
                for (int t = 0; t < L; t++)
                    s += in[t * C + ch];
                acc += (int32_t)w[ch] * (s >> sh);
            }
        } else {
            for (int i = 0; i < m->F; i++)
                acc += (int32_t)w[i] * in[i];
        }
        lg[c] = acc;
    }
    int cls = 0;
    for (int c = 1; c < 4; c++)
        if (lg[c] > lg[cls]) cls = c;
    int32_t top2 = INT32_MIN;
    for (int c = 0; c < 4; c++)
        if (c != cls && lg[c] > top2) top2 = lg[c];
    if (logits)
        for (int c = 0; c < 4; c++) logits[c] = lg[c];
    if (score) {
        uint32_t d = (uint32_t)(lg[cls] - top2) >> m->score_shift;     /* lg[cls] ≥ top2 */
        *score = (uint8_t)(d > 127u ? 127u : d);
    }
    return cls;
}
