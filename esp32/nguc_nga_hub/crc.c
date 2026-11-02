/* crc.c — xem crc.h. Cùng thuật toán với crc16() trong ml/src/golden_model.py và crc8.v của RTL. */
#include "crc.h"

uint16_t crc16_update(uint16_t c, uint8_t b)
{
    c ^= (uint16_t)b << 8;
    for (int i = 0; i < 8; i++)
        c = (c & 0x8000u) ? (uint16_t)((c << 1) ^ 0x1021u) : (uint16_t)(c << 1);
    return c;
}

uint16_t crc16_ccitt(const uint8_t *p, uint32_t n)
{
    uint16_t c = CRC16_INIT;
    while (n--)
        c = crc16_update(c, *p++);
    return c;
}

uint8_t crc8_update(uint8_t c, uint8_t b)
{
    c ^= b;
    for (int i = 0; i < 8; i++)
        c = (c & 0x80u) ? (uint8_t)((c << 1) ^ 0x07u) : (uint8_t)(c << 1);
    return c;
}

/* ---- bộ tính phần mềm theo giao diện crc16_engine_t ---- */
static uint16_t s_crc;
static void     sw_reset(void)       { s_crc = CRC16_INIT; }
static void     sw_feed(uint8_t b)   { s_crc = crc16_update(s_crc, b); }
static uint16_t sw_result(void)      { return s_crc; }

const crc16_engine_t crc16_sw = { sw_reset, sw_feed, sw_result };
