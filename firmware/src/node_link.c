/* node_link.c — xem node_link.h. */
#include <string.h>
#include "node_link.h"
#include "crc.h"

uint16_t node_pack_sample(uint8_t *out, uint8_t seq, const int16_t r[6], uint8_t keys)
{
    uint8_t *p = out;
    *p++ = NODE_SOF0;
    *p++ = NODE_SOF1;
    *p++ = seq;
    *p++ = (uint8_t)NODE_SAMPLE_LEN;
    *p++ = 0;
    *p++ = NODE_T_SAMPLE;
    for (int c = 0; c < 6; c++) {
        *p++ = (uint8_t)((uint16_t)r[c] & 0xFFu);
        *p++ = (uint8_t)((uint16_t)r[c] >> 8);
    }
    *p++ = keys;
    uint16_t crc = crc16_ccitt(out + 2, 3u + NODE_SAMPLE_LEN);
    *p++ = (uint8_t)(crc & 0xFFu);
    *p++ = (uint8_t)(crc >> 8);
    return (uint16_t)(p - out);
}

enum { S_IDLE, S_SOF1, S_SEQ, S_LEN0, S_LEN1, S_PAY, S_CRC0, S_CRC1 };

void node_rx_init(node_rx_t *s)
{
    memset(s, 0, sizeof *s);
}

static int text_byte(node_rx_t *s, uint8_t b)
{
    if (b == '\n') {
        s->line[s->nline] = 0;
        s->nline = 0;
        return NODE_TEXT;
    }
    if (b == '\r')
        return NODE_NONE;
    if (b >= 0x20 && b < 0x7F && s->nline < NODE_LINE_MAX)
        s->line[s->nline++] = (char)b;
    return NODE_NONE;
}

int node_rx_byte(node_rx_t *s, uint8_t b)
{
    switch (s->st) {
    case S_IDLE:
        if (b == NODE_SOF0) { s->st = S_SOF1; return NODE_NONE; }
        return text_byte(s, b);
    case S_SOF1:
        if (b == NODE_SOF1) { s->st = S_SEQ; return NODE_NONE; }
        s->st = S_IDLE;
        return (b == NODE_SOF0) ? (s->st = S_SOF1, NODE_NONE) : text_byte(s, b);
    case S_SEQ:
        s->seq = b;
        s->crc = crc16_update(CRC16_INIT, b);
        s->st = S_LEN0;
        return NODE_NONE;
    case S_LEN0:
        s->len = b;
        s->crc = crc16_update(s->crc, b);
        s->st = S_LEN1;
        return NODE_NONE;
    case S_LEN1:
        s->len |= (uint16_t)(b << 8);
        s->crc = crc16_update(s->crc, b);
        s->n = 0;
        if (s->len == 0 || s->len > sizeof s->buf) {
            s->st = S_IDLE;
            s->n_bad++;
            return NODE_BAD;
        }
        s->st = S_PAY;
        return NODE_NONE;
    case S_PAY:
        s->buf[s->n++] = b;
        s->crc = crc16_update(s->crc, b);
        if (s->n == s->len) s->st = S_CRC0;
        return NODE_NONE;
    case S_CRC0:
        s->n = b;                       /* tạm giữ byte thấp */
        s->st = S_CRC1;
        return NODE_NONE;
    default: {                          /* S_CRC1 */
        uint16_t got = (uint16_t)(s->n | (b << 8));
        s->st = S_IDLE;
        if (got != s->crc) { s->n_bad++; return NODE_BAD; }
        if (s->len != NODE_SAMPLE_LEN || s->buf[0] != NODE_T_SAMPLE) { s->n_bad++; return NODE_BAD; }
        for (int c = 0; c < 6; c++)
            s->r[c] = (int16_t)(s->buf[1 + 2 * c] | (s->buf[2 + 2 * c] << 8));
        s->keys = s->buf[13];
        if (s->have_seq)
            s->n_lost += (uint8_t)(s->seq - s->last_seq - 1u);
        s->have_seq = 1;
        s->last_seq = s->seq;
        s->rx_seq = s->seq;
        s->n_ok++;
        return NODE_SAMPLE;
    }
    }
}
