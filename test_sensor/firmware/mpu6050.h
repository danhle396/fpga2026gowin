/*
 * mpu6050.h — driver MPU6050 theo SPEC mục 2.1.
 */
#ifndef MPU6050_H
#define MPU6050_H

#include <stdint.h>

#define MPU_ADDR                0x68    /* AD0 nối GND */

#define MPU_REG_SELF_TEST_X     0x0D    /* 0x0D..0x10: giá trị self-test từ nhà máy */
#define MPU_REG_SMPLRT_DIV      0x19
#define MPU_REG_CONFIG          0x1A
#define MPU_REG_GYRO_CONFIG     0x1B
#define MPU_REG_ACCEL_CONFIG    0x1C
#define MPU_REG_INT_PIN_CFG     0x37
#define MPU_REG_INT_ENABLE      0x38
#define MPU_REG_INT_STATUS      0x3A
#define MPU_REG_ACCEL_XOUT_H    0x3B
#define MPU_REG_SIGNAL_PATH_RST 0x68
#define MPU_REG_PWR_MGMT_1      0x6B
#define MPU_REG_WHO_AM_I        0x75

#define MPU_WHO_AM_I_VALUE      0x68

#define MPU_ACC_LSB_PER_G       2048    /* ±16 g   */
#define MPU_GYR_LSB_PER_DPS_X10 164     /* ±2000 °/s: 16,4 LSB/(°/s) */

#define MPU_ERR_TIMEOUT        (-10)
#define MPU_ERR_VERIFY         (-11)

/* Một cặp thanh ghi/giá trị trong bảng cấu hình */
typedef struct { uint8_t reg, val; } mpu_reg_val_t;

/* Bảng cấu hình SPEC 2.1 (+ INT_PIN_CFG cho bản test, xem mpu6050.c) */
extern const mpu_reg_val_t mpu_cfg[];
extern const uint32_t      mpu_cfg_len;

typedef struct {
    int16_t change_x10[6];  /* sai lệch so với giá trị nhà máy, đơn vị 0,1 %: AX AY AZ GX GY GZ */
    uint8_t ok[6];          /* 1 nếu |sai lệch| <= 14 % */
    int     pass;           /* 1 nếu cả 6 trục đạt */
} mpu_selftest_t;

int mpu_write(uint8_t reg, uint8_t val);
int mpu_read_regs(uint8_t reg, uint8_t *buf, uint32_t n);

int mpu_who_am_i(uint8_t *id);
int mpu_reset(void);                                 /* reset mềm toàn chip */
int mpu_init(void);                                  /* ghi bảng mpu_cfg */
int mpu_verify(uint8_t *bad_reg, uint8_t *got);      /* đọc lại và so bảng mpu_cfg */
int mpu_data_ready(void);                            /* 1 = có mẫu mới, 0 = chưa, < 0 lỗi */
int mpu_wait_ready(uint32_t timeout_ms);             /* chờ bằng cách poll INT_STATUS */
int mpu_read7(int16_t v[7]);                         /* AX AY AZ TEMP GX GY GZ */
int mpu_read(int16_t out[6]);                        /* AX AY AZ GX GY GZ (bỏ nhiệt độ) */
int mpu_self_test(mpu_selftest_t *st);               /* để yên cảm biến khi chạy (~1,5 s) */

#endif
