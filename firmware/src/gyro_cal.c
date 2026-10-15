/* gyro_cal.c — xem gyro_cal.h. */
#include <string.h>
#include "gyro_cal.h"

void gyro_cal_init(gyro_cal_t *g)
{
    memset(g, 0, sizeof(*g));
}

static int32_t div_round(int32_t s, int32_t n)      /* làm tròn đối xứng, không dùng float */
{
    return (s >= 0) ? (s + n / 2) / n : -((-s + n / 2) / n);
}

int gyro_cal_push(gyro_cal_t *g, const int16_t raw[6])
{
    if (g->done)
        return 0;
    for (int c = 0; c < 3; c++) {
        int16_t v = raw[3 + c];
        if (g->n == 0) {
            g->mn[c] = g->mx[c] = v;
            g->sum[c] = 0;
        } else {
            if (v < g->mn[c]) g->mn[c] = v;
            if (v > g->mx[c]) g->mx[c] = v;
        }
        g->sum[c] += v;
    }
    g->n++;
    for (int c = 0; c < 3; c++) {
        if (g->mx[c] - g->mn[c] > GYRO_CAL_SPAN) {     /* đang rung: làm lại từ đầu */
            g->n = 0;
            g->restarts++;
            return 0;
        }
    }
    if (g->n < GYRO_CAL_N)
        return 0;
    for (int c = 0; c < 3; c++)
        g->off[c] = (int16_t)div_round(g->sum[c], GYRO_CAL_N);
    g->done = 1;
    return 1;
}
