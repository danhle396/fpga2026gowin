/* blocks.c — xem blocks.h. */
#include <string.h>
#include "blocks.h"

void blocks_init(blocks_t *b, const blocks_cfg_t *cfg)
{
    memset(b, 0, sizeof(*b));
    b->cfg = *cfg;
}

int blocks_push(blocks_t *b, const int16_t r[PRE_CH])
{
    int c;

    if (b->n == 0) {
        for (c = 0; c < PRE_CH; c++)
            b->mn[c] = b->mx[c] = r[c];
        b->az_sum = 0;
    } else {
        for (c = 0; c < PRE_CH; c++) {
            if (r[c] < b->mn[c]) b->mn[c] = r[c];
            if (r[c] > b->mx[c]) b->mx[c] = r[c];
        }
    }
    b->az_sum += r[2];
    if (++b->n < BLK_SAMPLES)
        return 0;

    uint8_t still = 1;
    for (c = 0; c < PRE_CH; c++) {
        int32_t span = (int32_t)b->mx[c] - b->mn[c];
        if (span >= (c < 3 ? b->cfg.t_still_a : b->cfg.t_still_g))
            still = 0;
    }
    b->still = still;
    b->still_run = still ? (uint8_t)(b->still_run < 255 ? b->still_run + 1 : 255) : 0;
    b->az_tb = (int16_t)(b->az_sum >> 5);
    b->n = 0;
    return 1;
}
