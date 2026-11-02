/*
 * blocks.h — "khối" của A.8 (việc FW-11). C thuần.
 * Khối = 32 mẫu thô 100 Hz (0,32 s), tính ngay khi đọc mẫu. Khối "bất động" khi max − min của cả 3 trục gia tốc
 * < T_STILL_A và của cả 3 trục gyro < T_STILL_G. still_run = số khối bất động liên tiếp gần nhất; az_tb = (Σ AZ) >> 5.
 */
#ifndef BLOCKS_H
#define BLOCKS_H

#include <stdint.h>
#include "fw_config.h"

typedef struct {
    int16_t  t_still_a, t_still_g;
} blocks_cfg_t;

typedef struct {
    blocks_cfg_t cfg;
    int16_t  mn[PRE_CH], mx[PRE_CH];
    int32_t  az_sum;
    uint8_t  n;             /* số mẫu trong khối đang mở */
    uint8_t  still;         /* khối vừa đóng có bất động không */
    uint8_t  still_run;     /* bão hòa ở 255 */
    int16_t  az_tb;
} blocks_t;

void blocks_init(blocks_t *b, const blocks_cfg_t *cfg);
/* Trả về 1 khi vừa đóng một khối (still, still_run, az_tb cập nhật). */
int  blocks_push(blocks_t *b, const int16_t r[PRE_CH]);

#endif
