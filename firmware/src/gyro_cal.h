/*
 * gyro_cal.h — hiệu chuẩn offset con quay lúc khởi động (việc FW-05). C thuần.
 * Lấy trung bình GYRO_CAL_N mẫu; nếu trong lúc đó max − min của trục gyro nào vượt GYRO_CAL_SPAN (mũ đang rung)
 * thì bắt đầu lại. Kết quả làm tròn tới LSB gần nhất.
 */
#ifndef GYRO_CAL_H
#define GYRO_CAL_H

#include <stdint.h>

#define GYRO_CAL_N     200      /* 2 s ở 100 Hz */
#define GYRO_CAL_SPAN  100      /* LSB ở ±2000 °/s ≈ 6 °/s */

typedef struct {
    int32_t  sum[3];
    int16_t  mn[3], mx[3];
    uint16_t n;
    uint16_t restarts;
    uint8_t  done;
    int16_t  off[3];
} gyro_cal_t;

void gyro_cal_init(gyro_cal_t *g);
/* Đưa một mẫu thô (6 kênh; dùng kênh 3..5). Trả về 1 khi vừa xong. */
int  gyro_cal_push(gyro_cal_t *g, const int16_t raw[6]);

#endif
