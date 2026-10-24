/* imu.c — xem imu.h. Giá trị thanh ghi đúng bảng A.1 của PROJECT_MASTER.md. */
#include "imu.h"
#include "i2c0.h"

static const uint8_t k_cfg[][2] = {
    { 0x6B, 0x01 },     /* PWR_MGMT_1: đánh thức, clock PLL theo gyro X */
    { 0x1A, 0x03 },     /* CONFIG: DLPF accel 44 Hz, gyro 42 Hz */
    { 0x19, 0x09 },     /* SMPLRT_DIV: 1 kHz / 10 = 100 Hz */
    { 0x1B, 0x18 },     /* GYRO_CONFIG: ±2000 °/s */
    { 0x1C, 0x18 },     /* ACCEL_CONFIG: ±16 g */
    { 0x37, 0x00 },     /* INT_PIN_CFG: xung mức cao, đẩy kéo, xóa khi đọc INT_STATUS */
    { 0x38, 0x01 },     /* INT_ENABLE: data ready */
};

int imu_init(uint8_t *who_am_i)
{
    uint8_t v = 0;
    if (i2c0_read(IMU_ADDR, 0x75, &v, 1) != I2C_OK || v != 0x68) {
        if (who_am_i) *who_am_i = v;
        return -1;
    }
    if (who_am_i) *who_am_i = v;
    int bad = 0;
    for (unsigned i = 0; i < sizeof k_cfg / sizeof k_cfg[0]; i++)
        (void)i2c0_write_reg(IMU_ADDR, k_cfg[i][0], k_cfg[i][1]);
    for (unsigned i = 0; i < sizeof k_cfg / sizeof k_cfg[0]; i++) {     /* đọc lại (Pass của FW-04) */
        if (i2c0_read(IMU_ADDR, k_cfg[i][0], &v, 1) != I2C_OK || v != k_cfg[i][1])
            bad++;
    }
    return bad;
}

int imu_data_ready(void)
{
    uint8_t v = 0;
    int rc = i2c0_read(IMU_ADDR, 0x3A, &v, 1);
    if (rc != I2C_OK)
        return -1;
    return (v & 0x01u) ? 1 : 0;
}

int imu_read(int16_t out[6])
{
    uint8_t b[14];
    int rc = i2c0_read(IMU_ADDR, 0x3B, b, 14);
    if (rc != I2C_OK)
        return rc;
    static const uint8_t pos[6] = { 0, 2, 4, 8, 10, 12 };      /* bỏ TEMP ở byte 6, 7 */
    for (int c = 0; c < 6; c++)
        out[c] = (int16_t)((b[pos[c]] << 8) | b[pos[c] + 1]);
    return 0;
}
