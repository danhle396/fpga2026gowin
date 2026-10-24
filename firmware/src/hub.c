/* hub.c — xem hub.h. */
#include <string.h>
#include "hub.h"
#include "spi_frame.h"
#include "crc.h"

typedef struct { uint8_t *p; uint16_t n; } sink_t;

static void sink_byte(uint8_t b, void *ctx)
{
    sink_t *s = (sink_t *)ctx;
    s->p[s->n++] = b;
}

void hub_init(hub_t *h, uint32_t now)
{
    safety_cfg_t sc;
    blocks_cfg_t bc = { T_STILL_A, T_STILL_G };
    memset(h, 0, sizeof *h);
    safety_default_cfg(&sc);
    app_init(&h->app, &sc, &bc, now);
    h->last_rc = SPI_PENDING;
}

static void send_frame(hub_t *h, const hub_io_t *io, uint8_t seq,
                       const int8_t *s1, uint16_t n1, const int8_t *s2, uint16_t n2, uint32_t now)
{
    sink_t s = { h->frame, 0 };
    if (h->last_rc == SPI_E_TIMEOUT) {          /* kết quả trễ của khung trước có thể còn chờ: đọc xả */
        uint8_t junk[SPI_READ_RUN];
        io->spi_read(junk, SPI_READ_RUN, io->ctx);
    }
    (void)spi_frame_emit(3, seq, s1, n1, s2, n2, &crc16_sw, sink_byte, &s);
    h->nframe = s.n;
    io->spi_write(h->frame, s.n, io->ctx);
    h->seq = seq;
    h->wait = 1;
    h->t_sent = now;
    h->t_poll = now + HUB_FIRST_POLL_MS;
    h->n_sent++;
}

unsigned hub_sample(hub_t *h, const hub_io_t *io, const int16_t r[6], uint8_t keys, uint32_t now)
{
    h->keys = keys;
    h->n_samples++;
    unsigned f = app_on_raw(&h->app, r);
    if (f & APP_FRAME) {                        /* SEQ tăng theo cửa sổ, kể cả khi bỏ qua (như app_main.c) */
        const int8_t *s1, *s2;
        uint16_t n1, n2;
        uint8_t seq = app_take_frame(&h->app, &s1, &n1, &s2, &n2);
        if (!h->wait) send_frame(h, io, seq, s1, n1, s2, n2, now);
        else          h->n_skip++;
    }
    return f;
}

static int all_zero(const uint8_t *b, uint8_t n)
{
    for (uint8_t i = 0; i < n; i++)
        if (b[i]) return 0;
    return 1;
}

int hub_poll(hub_t *h, const hub_io_t *io, uint32_t now)
{
    uint8_t raw[SPI_READ_RUN];
    if (!h->wait || (int32_t)(now - h->t_poll) < 0)
        return SPI_PENDING;
    io->spi_read(raw, SPI_READ_RUN, io->ctx);
    int rc;
    memset(&h->last, 0, sizeof h->last);
    if (all_zero(raw, SPI_READ_RUN)) {
        if (now - h->t_sent <= SPI_TIMEOUT_MS) {
            h->t_poll = now + HUB_POLL_EVERY_MS;
            return SPI_PENDING;
        }
        rc = SPI_E_TIMEOUT;
        h->n_timeout++;
    } else {
        rc = spi_parse_v3(raw, SPI_READ_RUN, h->seq, &h->last);
        if (rc == SPI_OK) h->n_ok++;
        else              h->n_err++;
    }
    h->wait = 0;
    h->last_rc = rc;
    app_on_result(&h->app, rc, &h->last);
    return rc;
}

void hub_tick(hub_t *h, uint32_t now, uint8_t cancel_extra)
{
    app_tick(&h->app, now, 1, (uint8_t)((h->keys & 1u) | (cancel_extra ? 1u : 0u)));
}

int hub_selftest(hub_t *h, const hub_io_t *io, uint32_t (*millis)(void), const uint8_t expect7[7],
                 uint8_t got7[7])
{
    static int8_t pl[PRE_BYTES];
    spi_selftest_payload(pl);
    uint32_t t0 = millis();
    send_frame(h, io, SEQ_SELFTEST, pl, PRE_BYTES, pl, 0, t0);
    h->n_sent--;                                /* không tính vào thống kê chạy */
    memset(got7, 0, 7);
    for (;;) {
        uint32_t now = millis();
        if ((int32_t)(now - h->t_poll) < 0) continue;
        io->spi_read(got7, SPI_READ_RUN, io->ctx);
        if (!all_zero(got7, SPI_READ_RUN) || now - t0 > SPI_TIMEOUT_MS) break;
        h->t_poll = now + HUB_POLL_EVERY_MS;
    }
    h->wait = 0;
    return memcmp(got7, expect7, 7) == 0;
}
