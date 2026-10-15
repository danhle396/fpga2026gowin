/*
 * i2c_soft.h — I2C master bit-bang (~100 kHz) dùng cho firmware test.
 *
 * Firmware chính dùng I2C phần cứng 400 kHz (SPEC 2.1). Bản test dùng
 * bit-bang để: (1) không phụ thuộc driver I2C của SDK, (2) tự phát được
 * 9 xung SCL gỡ bus bị treo, (3) chạy chậm nên dễ soi bằng logic analyzer.
 */
#ifndef I2C_SOFT_H
#define I2C_SOFT_H

#include <stdint.h>

#define I2C_OK              0
#define I2C_ERR_NACK_ADDR  (-1)   /* không thiết bị nào trả lời địa chỉ  */
#define I2C_ERR_NACK_DATA  (-2)   /* thiết bị NACK byte thanh ghi / dữ liệu */
#define I2C_ERR_TIMEOUT    (-3)   /* SCL bị giữ ở mức thấp quá lâu        */
#define I2C_ERR_BUS_LOW    (-4)   /* SDA/SCL kẹt mức thấp (thiếu pull-up, chập dây, bus treo) */

int i2c_bus_recover(void);                                   /* 9 xung SCL + STOP */
int i2c_probe(uint8_t addr7);                                /* I2C_OK nếu có ACK */
int i2c_write_reg(uint8_t addr7, uint8_t reg, uint8_t val);
int i2c_read_regs(uint8_t addr7, uint8_t reg, uint8_t *buf, uint32_t n);

#endif
