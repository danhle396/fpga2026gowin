/*
 * mpu6050.c — driver MPU6050 theo SPEC mục 2.1.
 */
#include "mpu6050.h"
#include "i2c_soft.h"
#include "board_port.h"
#include <math.h>
#include <string.h>

/* Thứ tự ghi: đánh thức trước, rồi mới cấu hình. */
const mpu_reg_val_t mpu_cfg[] = {
    { MPU_REG_PWR_MGMT_1,   0x01 },   /* thoát sleep, clock = PLL gyro X */
    { MPU_REG_SMPLRT_DIV,   0x09 },   /* 1 kHz / (1+9) = 100 Hz */
    { MPU_REG_CONFIG,       0x03 },   /* DLPF accel 44 Hz, gyro 42 Hz */
    { MPU_REG_GYRO_CONFIG,  0x18 },   /* ±2000 °/s */
    { MPU_REG_ACCEL_CONFIG, 0x18 },   /* ±16 g */
    /* CHỈ CÓ Ở BẢN TEST (không có trong SPEC 2.1): chốt mức INT (LATCH_INT_EN)
       đến khi có lệnh đọc bất kỳ (INT_RD_CLEAR) — để MCU poll được chân INT
       mà không cần cấu hình ngắt ngoài. Firmware chính dùng mặc định 0x00
       (xung 50 us) + ngắt cạnh lên. */
    { MPU_REG_INT_PIN_CFG,  0x30 },
    { MPU_REG_INT_ENABLE,   0x01 },   /* ngắt data-ready */
};
const uint32_t mpu_cfg_len = sizeof(mpu_cfg) / sizeof(mpu_cfg[0]);

int mpu_write(uint8_t reg, uint8_t val)
{
    return i2c_write_reg(MPU_ADDR, reg, val);
}

int mpu_read_regs(uint8_t reg, uint8_t *buf, uint32_t n)
{
    return i2c_read_regs(MPU_ADDR, reg, buf, n);
}

int mpu_who_am_i(uint8_t *id)
{
    return mpu_read_regs(MPU_REG_WHO_AM_I, id, 1);
}

int mpu_reset(void)
{
    int r = mpu_write(MPU_REG_PWR_MGMT_1, 0x80);          /* DEVICE_RESET */
    if (r) return r;
    board_delay_ms(100);
    r = mpu_write(MPU_REG_SIGNAL_PATH_RST, 0x07);         /* reset gyro/accel/temp */
    board_delay_ms(100);
    return r;                                             /* sau reset chip ở sleep (0x6B = 0x40) */
}

int mpu_init(void)
{
    uint32_t i;
    int r;
    for (i = 0; i < mpu_cfg_len; i++) {
        r = mpu_write(mpu_cfg[i].reg, mpu_cfg[i].val);
        if (r) return r;
        if (i == 0) board_delay_ms(10);                   /* chờ chip thức dậy */
    }
    board_delay_ms(50);                                   /* PLL gyro + DLPF ổn định */
    return I2C_OK;
}

int mpu_verify(uint8_t *bad_reg, uint8_t *got)
{
    uint32_t i;
    uint8_t v;
    int r;
    for (i = 0; i < mpu_cfg_len; i++) {
        r = mpu_read_regs(mpu_cfg[i].reg, &v, 1);
        if (r) return r;
        if (v != mpu_cfg[i].val) {
            *bad_reg = mpu_cfg[i].reg;
            *got = v;
            return MPU_ERR_VERIFY;
        }
    }
    return I2C_OK;
}

int mpu_data_ready(void)
{
    uint8_t s;
    int r = mpu_read_regs(MPU_REG_INT_STATUS, &s, 1);
    if (r) return r;
    return (s & 0x01) ? 1 : 0;                            /* DATA_RDY_INT */
}

int mpu_wait_ready(uint32_t timeout_ms)
{
    uint32_t t0 = board_millis();
    int r;
    do {
        r = mpu_data_ready();
        if (r != 0) return (r > 0) ? I2C_OK : r;
    } while (board_millis() - t0 < timeout_ms);
    return MPU_ERR_TIMEOUT;
}

int mpu_read7(int16_t v[7])
{
    uint8_t b[14];
    int i, r = mpu_read_regs(MPU_REG_ACCEL_XOUT_H, b, 14);
    if (r) return r;
    for (i = 0; i < 7; i++)
        v[i] = (int16_t)(((uint16_t)b[2 * i] << 8) | b[2 * i + 1]);   /* byte cao trước */
    return I2C_OK;
}

int mpu_read(int16_t out[6])
{
    int16_t v[7];
    int r = mpu_read7(v);
    if (r) return r;
    out[0] = v[0]; out[1] = v[1]; out[2] = v[2];
    out[3] = v[4]; out[4] = v[5]; out[5] = v[6];
    return I2C_OK;
}

/* Trung bình n mẫu 6 trục (chờ data-ready giữa các mẫu) */
static int average(int32_t avg[6], int n)
{
    int16_t v[6];
    int32_t sum[6] = { 0 };
    int i, k, r;
    for (i = 0; i < n; i++) {
        r = mpu_wait_ready(50);
        if (!r) r = mpu_read(v);
        if (r) return r;
        for (k = 0; k < 6; k++) sum[k] += v[k];
    }
    for (k = 0; k < 6; k++) avg[k] = sum[k] / n;
    return I2C_OK;
}

/*
 * Self-test theo "MPU-6000/6050 Register Map" rev 4.2, mục 4.1:
 * accel đo ở ±8 g, gyro đo ở ±250 °/s. Đáp ứng self-test = (bật ST) − (tắt ST),
 * so với giá trị nhà máy (Factory Trim). Đạt nếu sai lệch trong ±14 %.
 */
int mpu_self_test(mpu_selftest_t *st)
{
    int32_t base[6], test[6];
    uint8_t t[4];
    int     code[6];
    float   ft[6];
    int     i, r;

    memset(st, 0, sizeof(*st));

    r = mpu_write(MPU_REG_GYRO_CONFIG, 0x00);             /* ±250 °/s, tắt ST */
    if (!r) r = mpu_write(MPU_REG_ACCEL_CONFIG, 0x10);    /* ±8 g,     tắt ST */
    if (r) return r;
    board_delay_ms(100);
    r = average(base, 50);
    if (r) return r;

    r = mpu_write(MPU_REG_GYRO_CONFIG, 0xE0);             /* bật ST cả 3 trục gyro */
    if (!r) r = mpu_write(MPU_REG_ACCEL_CONFIG, 0xF0);    /* bật ST cả 3 trục accel */
    if (r) return r;
    board_delay_ms(100);
    r = average(test, 50);

    /* Luôn trả cấu hình về SPEC kể cả khi đo lỗi */
    (void)mpu_write(MPU_REG_GYRO_CONFIG, 0x18);
    (void)mpu_write(MPU_REG_ACCEL_CONFIG, 0x18);
    board_delay_ms(100);
    if (r) return r;

    r = mpu_read_regs(MPU_REG_SELF_TEST_X, t, 4);
    if (r) return r;

    code[0] = ((t[0] >> 3) & 0x1C) | ((t[3] >> 4) & 0x03);   /* XA_TEST (5 bit) */
    code[1] = ((t[1] >> 3) & 0x1C) | ((t[3] >> 2) & 0x03);   /* YA_TEST */
    code[2] = ((t[2] >> 3) & 0x1C) | ( t[3]       & 0x03);   /* ZA_TEST */
    code[3] = t[0] & 0x1F;                                   /* XG_TEST */
    code[4] = t[1] & 0x1F;                                   /* YG_TEST */
    code[5] = t[2] & 0x1F;                                   /* ZG_TEST */

    for (i = 0; i < 3; i++)
        ft[i] = code[i] ? 4096.0f * 0.34f * powf(0.92f / 0.34f, (code[i] - 1) / 30.0f) : 0.0f;
    for (i = 3; i < 6; i++)
        ft[i] = code[i] ? 25.0f * 131.0f * powf(1.046f, (float)(code[i] - 1)) : 0.0f;
    ft[4] = -ft[4];                                          /* gyro Y: FT mang dấu âm */

    st->pass = 1;
    for (i = 0; i < 6; i++) {
        float pct = 0.0f;
        if (ft[i] != 0.0f)
            pct = 100.0f * ((float)(test[i] - base[i]) - ft[i]) / ft[i];
        if (pct > 999.0f)  pct = 999.0f;
        if (pct < -999.0f) pct = -999.0f;
        st->change_x10[i] = (int16_t)(pct * 10.0f);
        st->ok[i] = (ft[i] != 0.0f) && (pct >= -14.0f) && (pct <= 14.0f);
        if (!st->ok[i]) st->pass = 0;
    }
    return I2C_OK;
}
