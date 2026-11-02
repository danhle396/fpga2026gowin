/* spi_frame.c — xem spi_frame.h. Đối chiếu: write_frame(), result_frame() trong ml/src/golden_model.py. */
#include "spi_frame.h"
#include "fw_config.h"

static void emit_seg(const int8_t *p, uint16_t n, uint8_t proto, const crc16_engine_t *crc, uint8_t *c8,
                     spi_tx_fn tx, void *ctx)
{
    while (n--) {
        uint8_t b = (uint8_t)*p++;
        if (proto == 1) *c8 = crc8_update(*c8, b);
        else            crc->feed(b);
        tx(b, ctx);
    }
}

uint16_t spi_frame_emit(uint8_t proto, uint8_t seq,
                        const int8_t *seg1, uint16_t n1, const int8_t *seg2, uint16_t n2,
                        const crc16_engine_t *crc, spi_tx_fn tx, void *ctx)
{
    uint8_t c8 = 0;

    if (proto == 1) {
        tx(SPI_HDR_WRITE, ctx);             /* CRC-8 của RTL bắt đầu từ SEQ, không gồm 0xA5 */
        c8 = crc8_update(c8, seq);
        tx(seq, ctx);
        emit_seg(seg1, n1, 1, crc, &c8, tx, ctx);
        emit_seg(seg2, n2, 1, crc, &c8, tx, ctx);
        tx(c8, ctx);
        return c8;
    }

    crc->reset();
    crc->feed(SPI_HDR_WRITE);
    tx(SPI_HDR_WRITE, ctx);
    crc->feed(seq);
    tx(seq, ctx);
    emit_seg(seg1, n1, 3, crc, &c8, tx, ctx);
    emit_seg(seg2, n2, 3, crc, &c8, tx, ctx);
    uint16_t c = crc->result();
    tx((uint8_t)(c >> 8), ctx);
    tx((uint8_t)c, ctx);
    return c;
}

static uint16_t be16(const uint8_t *p) { return (uint16_t)((p[0] << 8) | p[1]); }

int spi_parse_v3(const uint8_t *b, uint8_t n, uint8_t seq_expect, spi_result_t *r)
{
    r->seq = b[1];
    r->status = b[2];
    r->cls = b[3];
    r->score = b[4];
    if (b[0] != SPI_HDR_READ)                       return SPI_E_HDR;
    if (crc16_ccitt(b, 5) != be16(&b[5]))           return SPI_E_CRC;
    if (b[2] != 0x01)                               return SPI_E_STATUS;
    if (b[1] != seq_expect)                         return SPI_E_SEQ;
    if (b[3] > 3)                                   return SPI_E_CLASS;
    if (n >= SPI_READ_HIL) {
        for (int i = 0; i < 4; i++)
            r->logit[i] = (int16_t)be16(&b[7 + 2 * i]);
        r->cycles = ((uint32_t)b[15] << 16) | ((uint32_t)b[16] << 8) | b[17];
        if (crc16_ccitt(&b[7], 11) != be16(&b[18])) return SPI_E_TAIL;
    }
    return SPI_OK;
}

void spi_selftest_payload(int8_t out[768])
{
    uint16_t s = 0xACE1u;
    for (int i = 0; i < 768; i++) {
        uint16_t lsb = s & 1u;
        s >>= 1;
        if (lsb) s ^= 0xB400u;
        out[i] = (int8_t)(uint8_t)s;
    }
}

int spi_parse_v1(const uint8_t *b, spi_result_t *r)
{
    uint8_t c = 0;
    for (int i = 1; i <= 5; i++)
        c = crc8_update(c, b[i]);
    r->cls = b[1];
    r->score32 = (int32_t)(((uint32_t)b[2] << 24) | ((uint32_t)b[3] << 16) | ((uint32_t)b[4] << 8) | b[5]);
    r->score = 0;
    r->status = 0x01;
    if (b[0] != SPI_HDR_READ)                       return SPI_E_HDR;
    if (c != b[6])                                  return SPI_E_CRC;
    if (b[1] > 3)                                   return SPI_E_CLASS;
    return SPI_OK;
}
