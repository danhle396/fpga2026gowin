/*
 * i2c0.h — I2C0 phần cứng của SN32F407, master, chờ bằng vòng lặp có giới hạn (việc FW-04).
 * Chân P0.10 = SCL0, P0.11 = SDA0 (PFPA I2C0 = 0x0A, E.2). Dựng từ drivers/i2c0.c của dự án vòng 1
 * (D:\hoctap\fpga\thi_fpga\MCU\firmware), theo datasheet V2.2 chương 15. Chưa chạy trên board.
 */
#ifndef I2C0_H
#define I2C0_H

#include <stdint.h>

enum { I2C_OK = 0, I2C_E_NACK, I2C_E_TIMEOUT, I2C_E_ARB };

void i2c0_init(uint32_t bus_hz);                     /* 400000 hoặc 100000; PCLK = 48 MHz */
int  i2c0_write_reg(uint8_t addr7, uint8_t reg, uint8_t val);
int  i2c0_read(uint8_t addr7, uint8_t reg, uint8_t *buf, uint8_t n);
int  i2c0_last_error(void);

#endif
