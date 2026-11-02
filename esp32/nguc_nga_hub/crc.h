/*
 * crc.h — CRC dùng trong khung SPI (A.7). C thuần, không gọi phần cứng.
 *   CRC-16/CCITT-FALSE: đa thức 0x1021, khởi tạo 0xFFFF, không đảo bit, không XOR cuối. "123456789" → 0x29B1.
 *   CRC-8 đa thức 0x07, khởi tạo 0: khung PROTO = 1 của RTL hiện có (packet_parser.v, spi_result_tx.v).
 */
#ifndef CRC_H
#define CRC_H

#include <stdint.h>

#define CRC16_INIT  0xFFFFu

uint16_t crc16_update(uint16_t c, uint8_t b);
uint16_t crc16_ccitt(const uint8_t *p, uint32_t n);
uint8_t  crc8_update(uint8_t c, uint8_t b);

/* Bộ tính CRC-16 đổi được: phần mềm (để test trên PC) hoặc khối CRC phần cứng (crc_hw.c). */
typedef struct {
    void     (*reset)(void);
    void     (*feed)(uint8_t b);
    uint16_t (*result)(void);
} crc16_engine_t;

extern const crc16_engine_t crc16_sw;

#endif
