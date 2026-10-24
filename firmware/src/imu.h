/*
 * imu.h — MPU6050 theo SPEC v3, A.1 (việc FW-04): 100 Hz, DLPF 44 Hz, ±16 g, ±2000 °/s, data-ready báo qua INT_STATUS (không có dây INT).
 */
#ifndef IMU_H
#define IMU_H

#include <stdint.h>

#define IMU_ADDR  0x68

/* Ghi cấu hình A.1 rồi đọc lại 7 thanh ghi; trả về số thanh ghi sai (0 = PASS), −1 nếu WHO_AM_I sai/không trả lời. */
int  imu_init(uint8_t *who_am_i);
/* Đọc burst 14 byte từ 0x3B, trả về AX AY AZ GX GY GZ (bỏ nhiệt độ). 0 = OK. */
int  imu_read(int16_t out[6]);
/* Hỏi INT_STATUS (0x3A): 1 = có mẫu mới (đọc xong thì cờ tự xóa), 0 = chưa, < 0 = lỗi I2C. Dùng khi không có dây INT. */
int  imu_data_ready(void);

#endif
