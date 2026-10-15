/*
 * i2c_soft.c — I2C master bit-bang, open-drain giả lập bằng cách đổi
 * hướng chân (output-0 = kéo xuống, input = thả). Cần điện trở kéo lên
 * trên SDA/SCL (module GY-521 đã có sẵn 4,7 kΩ / 2,2 kΩ).
 */
#include "i2c_soft.h"
#include "board_port.h"

#ifndef I2C_HALF_US
#define I2C_HALF_US         5       /* nửa chu kỳ SCL: 5 us -> ~100 kHz */
#endif
#define I2C_STRETCH_MAX_US  1000    /* chờ tối đa khi slave giữ SCL */

static void dly(void) { board_delay_us(I2C_HALF_US); }

/* Thả SCL và chờ nó thực sự lên 1 (hỗ trợ clock stretching) */
static int scl_high(void)
{
    uint32_t t = 0;
    board_scl_release();
    while (!board_scl_read()) {
        if (++t > I2C_STRETCH_MAX_US) return I2C_ERR_TIMEOUT;
        board_delay_us(1);
    }
    return I2C_OK;
}

/* START (cũng dùng làm REPEATED START). Kết thúc với SCL = 0. */
static int start(void)
{
    board_sda_release();
    dly();
    if (scl_high()) return I2C_ERR_TIMEOUT;
    dly();
    if (!board_sda_read()) return I2C_ERR_BUS_LOW;
    board_sda_low();                /* SDA 1->0 khi SCL = 1 */
    dly();
    board_scl_low();
    dly();
    return I2C_OK;
}

/* STOP. Hạ SCL trước để việc kéo SDA xuống không tạo nhầm START. */
static void stop(void)
{
    board_scl_low();
    dly();
    board_sda_low();
    dly();
    (void)scl_high();
    dly();
    board_sda_release();            /* SDA 0->1 khi SCL = 1 */
    dly();
}

/* Trả về 0 = ACK, 1 = NACK, < 0 = lỗi */
static int write_byte(uint8_t b)
{
    int i, nack;
    for (i = 0; i < 8; i++) {
        if (b & 0x80) board_sda_release(); else board_sda_low();
        b <<= 1;
        dly();
        if (scl_high()) return I2C_ERR_TIMEOUT;
        dly();
        board_scl_low();
    }
    board_sda_release();            /* nhường SDA cho slave trả ACK */
    dly();
    if (scl_high()) return I2C_ERR_TIMEOUT;
    dly();
    nack = board_sda_read();
    board_scl_low();
    return nack;
}

static int read_byte(uint8_t *out, int ack)
{
    int i;
    uint8_t b = 0;
    board_sda_release();
    for (i = 0; i < 8; i++) {
        dly();
        if (scl_high()) return I2C_ERR_TIMEOUT;
        dly();
        b = (uint8_t)((b << 1) | (board_sda_read() ? 1u : 0u));
        board_scl_low();
    }
    if (ack) board_sda_low(); else board_sda_release();
    dly();
    if (scl_high()) return I2C_ERR_TIMEOUT;
    dly();
    board_scl_low();
    board_sda_release();
    *out = b;
    return I2C_OK;
}

/* Đổi kết quả write_byte thành mã lỗi */
static int ack_or(int r, int nack_code)
{
    if (r < 0) return r;
    return r ? nack_code : I2C_OK;
}

int i2c_bus_recover(void)
{
    int i;
    board_sda_release();
    board_scl_release();
    dly();
    /* Slave đang giữa chừng một byte sẽ kéo SDA = 0; phát tối đa 9 xung SCL
       để nó đẩy hết bit còn lại và nhả SDA. */
    for (i = 0; i < 9 && !board_sda_read(); i++) {
        board_scl_low();
        dly();
        board_scl_release();
        dly();
    }
    stop();
    return (board_sda_read() && board_scl_read()) ? I2C_OK : I2C_ERR_BUS_LOW;
}

int i2c_probe(uint8_t addr7)
{
    int r = start();
    if (r == I2C_OK)
        r = ack_or(write_byte((uint8_t)(addr7 << 1)), I2C_ERR_NACK_ADDR);
    stop();
    return r;
}

int i2c_write_reg(uint8_t addr7, uint8_t reg, uint8_t val)
{
    int r = start();
    if (r == I2C_OK) r = ack_or(write_byte((uint8_t)(addr7 << 1)), I2C_ERR_NACK_ADDR);
    if (r == I2C_OK) r = ack_or(write_byte(reg), I2C_ERR_NACK_DATA);
    if (r == I2C_OK) r = ack_or(write_byte(val), I2C_ERR_NACK_DATA);
    stop();
    return r;
}

int i2c_read_regs(uint8_t addr7, uint8_t reg, uint8_t *buf, uint32_t n)
{
    uint32_t i;
    int r = start();
    if (r == I2C_OK) r = ack_or(write_byte((uint8_t)(addr7 << 1)), I2C_ERR_NACK_ADDR);
    if (r == I2C_OK) r = ack_or(write_byte(reg), I2C_ERR_NACK_DATA);
    if (r == I2C_OK) r = start();                                   /* repeated START */
    if (r == I2C_OK) r = ack_or(write_byte((uint8_t)((addr7 << 1) | 1u)), I2C_ERR_NACK_ADDR);
    for (i = 0; r == I2C_OK && i < n; i++)
        r = read_byte(&buf[i], i + 1 < n);                          /* NACK byte cuối */
    stop();
    return r;
}
