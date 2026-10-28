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
    posture_init(&h->pos, FW_VI_TRI_DEO == 1);
    nga_init(&h->nga);
    h->nga_en = 1;
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

static int16_t truc(const int16_t *v, int c, int32_t off)
{
    int32_t x = (c > 0 ? v[c - 1] : -(int32_t)v[-c - 1]) - off;
    return (int16_t)(x > 32767 ? 32767 : x < -32768 ? -32768 : x);   /* −(−32768), trừ offset */
}

void hub_doi_truc(const int16_t in[6], int16_t out[6])
{
    static const int8_t  k[3]   = { TRUC_X, TRUC_Y, TRUC_Z };
    static const int16_t off[3] = { ACC_OFF_X, ACC_OFF_Y, ACC_OFF_Z };
    for (int i = 0; i < 3; i++) {
        out[i]     = truc(in, k[i], off[i]);
        out[3 + i] = truc(in + 3, k[i], 0);               /* gyro quay cùng phép xoay; offset gyro MCU đã trừ */
    }
}

unsigned hub_sample(hub_t *h, const hub_io_t *io, const int16_t raw[6], uint8_t keys, uint32_t now)
{
    const int16_t *r = h->r;
    hub_doi_truc(raw, h->r);
    h->keys = keys;
    h->n_samples++;
    unsigned f = app_on_raw(&h->app, r);
    if (posture_push(&h->pos, r)) f |= HUB_POSTURE;
    nga_mau(&h->nga, (uint32_t)(r[0] * r[0]) + (uint32_t)(r[1] * r[1]) + (uint32_t)(r[2] * r[2]));
    if (h->pos.nb == 0) nga_khoi(&h->nga, h->pos.huong);           /* posture.c vừa đóng khối 32 mẫu */
    if (h->pos_moving && !h->pos.moving) nga_dot(&h->nga, h->pos.dh_cuoi);
    h->pos_moving = h->pos.moving;
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
    safety_t *f = &h->app.fsm;
    app_tick(&h->app, now, 1, (uint8_t)((h->keys & 1u) | (cancel_extra ? 1u : 0u)));
    h->nga_hd = NGA_HD_KHONG;
    if (!h->nga_en) return;
    if (f->st == ST_MONITOR || f->st == ST_STANDBY) nga_het(&h->nga);
    else if ((f->events & SAFETY_EV_STATE) && f->st == ST_SUSPECT) nga_bat_dau(&h->nga, now);
    h->nga_hd = (uint8_t)nga_buoc(&h->nga, now, h->pos.huong, f->st == ST_PRE_ALARM);
    if (h->nga_hd == NGA_HD_BO) safety_bo_nghi(f, now);      /* không phải ngã: FSM về MONITOR, không ai thấy */
}

static int an_nga(const hub_t *h)                           /* trạng thái ngã chưa được xác nhận: giấu */
{
    const safety_t *f = &h->app.fsm;
    if (!h->nga_en || h->nga.trang_thai == NGA_XAC_NHAN) return 0;
    if (f->st == ST_ALARM) return f->why != WHY_SOS;
    return f->st == ST_SUSPECT || f->st == ST_PRE_ALARM;
}

uint8_t hub_coi(const hub_t *h, uint32_t now)
{
    return an_nga(h) ? 0u : app_buzzer(&h->app, now);
}

const char *hub_ten_trang_thai(const hub_t *h)
{
    return an_nga(h) ? safety_state_name(ST_MONITOR) : safety_state_name(h->app.fsm.st);
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
