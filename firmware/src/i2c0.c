/* i2c0.c — xem i2c0.h. Bit thanh ghi theo datasheet V2.2 mục 15.10 (I2Cn_CTRL, I2Cn_STAT). */
#include "SN32F400.h"
#include "i2c0.h"

#define CTRL_NACK   (1UL << 1)
#define CTRL_ACK    (1UL << 2)
#define CTRL_STO    (1UL << 4)
#define CTRL_STA    (1UL << 5)
#define CTRL_EN     (1UL << 8)
#define CTRL_ARB    (1UL << 21)
#define ST_RX_DN    (1UL << 0)
#define ST_ACK      (1UL << 1)
#define ST_NACK     (1UL << 2)
#define ST_STOP_DN  (1UL << 3)
#define ST_START_DN (1UL << 4)
#define ST_LOST_ARB (1UL << 8)
#define ST_TIMEOUT  (1UL << 9)
#define LOOPS       20000UL          /* ≈ 1,5 ms ở 48 MHz, dư cho 1 byte ở 100 kHz (90 µs) */

static int s_err;

static int wait(uint32_t want)
{
    for (uint32_t n = LOOPS; n; n--) {
        uint32_t st = SN_I2C0->STAT;
        if (st & ST_LOST_ARB) return s_err = I2C_E_ARB;
        if (st & ST_TIMEOUT)  return s_err = I2C_E_TIMEOUT;
        if (st & want)        return s_err = I2C_OK;
        if (st & ST_NACK)     return s_err = I2C_E_NACK;
    }
    return s_err = I2C_E_TIMEOUT;
}

static int start(void)  { SN_I2C0->CTRL = CTRL_EN | CTRL_ARB | CTRL_STA; return wait(ST_START_DN); }
static void stop(void)  { SN_I2C0->CTRL = CTRL_EN | CTRL_ARB | CTRL_STO; (void)wait(ST_STOP_DN); }
static int tx(uint8_t b) { SN_I2C0->TXDATA = b; return wait(ST_ACK); }

void i2c0_init(uint32_t bus_hz)
{
    uint32_t half = SystemCoreClock / (2u * bus_hz);            /* SCL cao + thấp = PCLK / bus_hz */
    SN_SYS1->AHBCLKEN |= (1UL << 21);                          /* I2C0CLKEN */
    SN_PFPA->I2C0 = 0x0A;                                      /* SDA0 = P0.11, SCL0 = P0.10 */
    SN_I2C0->CTRL = 0;
    /* Datasheet 15.10.7 ghi hai công thức: f = PCLK / (SCLHT + SCLLT) và "thời gian cao = (SCLH + 1) chu kỳ". Ghi half
     * thì theo công thức nào SCL cũng ≤ bus_hz (400 kHz → 400 hoặc 393 kHz); half − 1 có thể ra 406,8 kHz > chuẩn. */
    SN_I2C0->SCLHT = half;
    SN_I2C0->SCLLT = half;
    SN_I2C0->TOCTRL = 0xFFFF;                                  /* SCL bị giữ thấp quá ≈ 43 ms → timeout */
    SN_I2C0->CTRL = CTRL_EN | CTRL_ARB;                        /* I2CEN đặt sau cùng (ghi chú 1, mục 15.10.1) */
}

int i2c0_write_reg(uint8_t addr7, uint8_t reg, uint8_t val)
{
    int rc;
    if ((rc = start()) == I2C_OK && (rc = tx((uint8_t)(addr7 << 1))) == I2C_OK && (rc = tx(reg)) == I2C_OK)
        rc = tx(val);
    stop();
    return rc;
}

int i2c0_read(uint8_t addr7, uint8_t reg, uint8_t *buf, uint8_t n)
{
    int rc;
    if ((rc = start()) != I2C_OK || (rc = tx((uint8_t)(addr7 << 1))) != I2C_OK || (rc = tx(reg)) != I2C_OK)
        goto out;
    if ((rc = start()) != I2C_OK || (rc = tx((uint8_t)((addr7 << 1) | 1u))) != I2C_OK)  /* START lặp */
        goto out;
    for (uint8_t i = 0; i < n; i++) {
        SN_I2C0->CTRL = CTRL_EN | CTRL_ARB | (i + 1u < n ? CTRL_ACK : CTRL_NACK);   /* byte cuối: NACK */
        if ((rc = wait(ST_RX_DN)) != I2C_OK)
            goto out;
        buf[i] = (uint8_t)SN_I2C0->RXDATA;
    }
out:
    stop();
    return rc;
}

int i2c0_last_error(void) { return s_err; }
