/*
 * preprocess.h — tiền xử lý trên MCU theo SPEC v3, A.2 và A.3 (việc FW-07). C thuần, không gọi phần cứng.
 *
 *   100 Hz INT16 ──► y[n] = (r[2n−2] + 3·r[2n−1] + 3·r[2n] + r[2n+1] + 4) >> 3, r[−2] = r[−1] = r[0]
 *              ──► q = clamp((y + 2^(s−1)) >> s, −128, 127), s = 7 (gia tốc), 6 (gyro)
 *              ──► ring 128 × 6 INT8, i = t × 6 + c; một cửa sổ mới sau mỗi 16 mẫu 50 Hz
 *
 * Đối chiếu: decimate() và q8() trong ml/src/golden_model.py; vector ở firmware/tv/.
 */
#ifndef PREPROCESS_H
#define PREPROCESS_H

#include <stdint.h>
#include "fw_config.h"

typedef struct {
    int16_t  h2[PRE_CH];        /* r[2n−2] */
    int16_t  h1[PRE_CH];        /* r[2n−1] */
    int16_t  ev[PRE_CH];        /* r[2n], chờ mẫu lẻ r[2n+1] */
    uint8_t  odd;               /* 1: mẫu kế tiếp là mẫu lẻ */
    uint8_t  primed;            /* đã có r[0] */
    uint16_t wr;                /* ô ring sẽ ghi tiếp; khi ring đầy thì cũng là ô cũ nhất */
    uint32_t n_out;             /* số mẫu 50 Hz đã tạo */
    int8_t   ring[PRE_BYTES];
} pre_state_t;

#define PRE_NEW_SAMPLE  1u      /* bit trả về của pre_push_raw */
#define PRE_NEW_WINDOW  2u

void    pre_init(pre_state_t *s);
int8_t  pre_q8(int32_t y, unsigned shift);

/* Đưa một mẫu thô 100 Hz (gyro đã trừ offset). Trả về tổ hợp PRE_NEW_SAMPLE | PRE_NEW_WINDOW.
 * Nếu out != 0 và có mẫu mới thì chép 6 byte INT8 của mẫu đó ra out. */
unsigned pre_push_raw(pre_state_t *s, const int16_t r[PRE_CH], int8_t out[PRE_CH]);

/* Cửa sổ hiện tại = seg1 rồi seg2 (ring vòng, mẫu cũ nhất trước). n1 + n2 = 768. */
void    pre_window(const pre_state_t *s, const int8_t **seg1, uint16_t *n1, const int8_t **seg2, uint16_t *n2);

#endif
