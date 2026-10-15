/*
 * spi_frame.h — dựng khung GHI và kiểm khung ĐỌC của A.7 (việc FW-08). C thuần: byte đi ra qua hàm tx do
 * người gọi cấp (SPI0 thật trong spi_fpga.c, bộ đệm trong bộ test), CRC-16 qua crc16_engine_t (phần cứng hoặc mềm).
 *
 *   PROTO 3 (giao thức v3): ghi [A5][SEQ][768][CRC-16 hi][lo] = 772 byte;
 *                           đọc [5A][SEQ][STATUS][CLASS][SCORE][CRC-16 của 0..4] (+ 13 byte đuôi khi HIL).
 *   PROTO 1 (RTL hiện có):  ghi [A5][SEQ][768][CRC-8 của SEQ + 768] = 771 byte;
 *                           đọc [5A][CLASS][SCORE 32 bit][CRC-8 của byte 1..5] = 7 byte.
 */
#ifndef SPI_FRAME_H
#define SPI_FRAME_H

#include <stdint.h>
#include "crc.h"

typedef void (*spi_tx_fn)(uint8_t b, void *ctx);

/* Gửi một khung ghi; payload là seg1 rồi seg2 (n1 + n2 phải bằng 768). Trả về CRC đã gửi (CRC-8 nằm ở byte thấp). */
uint16_t spi_frame_emit(uint8_t proto, uint8_t seq,
                        const int8_t *seg1, uint16_t n1, const int8_t *seg2, uint16_t n2,
                        const crc16_engine_t *crc, spi_tx_fn tx, void *ctx);

enum {
    SPI_OK = 0,
    SPI_E_TIMEOUT,      /* không thấy IRQ trong 50 ms */
    SPI_E_HDR,          /* byte 0 ≠ 0x5A */
    SPI_E_CRC,          /* CRC khung đọc sai */
    SPI_E_STATUS,       /* STATUS ≠ 0x01: FPGA báo CRC khung ghi sai, bận, hoặc khung thiếu byte */
    SPI_E_SEQ,          /* SEQ lệch */
    SPI_E_CLASS,        /* CLASS ngoài 0..3 */
    SPI_E_TAIL          /* CRC phần đuôi HIL sai (phần đầu vẫn dùng được) */
};

typedef struct {
    uint8_t  seq, status, cls, score;
    int16_t  logit[4];      /* chỉ có ở khung 20 byte */
    uint32_t cycles;        /* chỉ có ở khung 20 byte */
    int32_t  score32;       /* PROTO 1: logit lớn nhất */
} spi_result_t;

/* Khung đọc v3, n = 7 (RUN) hoặc 20 (HIL). */
int spi_parse_v3(const uint8_t *b, uint8_t n, uint8_t seq_expect, spi_result_t *r);
/* Khung đọc PROTO 1, 7 byte. RTL hiện có không trả SEQ nên không kiểm được SEQ. */
int spi_parse_v1(const uint8_t *b, spi_result_t *r);

/* A.10: 768 byte từ LFSR Galois 16 bit, đa thức 0xB400, mầm 0xACE1, mỗi byte một bước, lấy 8 bit thấp. */
void spi_selftest_payload(int8_t out[768]);

#endif
