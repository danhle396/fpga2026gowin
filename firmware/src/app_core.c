/* app_core.c — xem app_core.h. */
#include <string.h>
#include "app_core.h"
#include "fw_config.h"

void app_init(app_t *a, const safety_cfg_t *sc, const blocks_cfg_t *bc, uint32_t now)
{
    memset(a, 0, sizeof(*a));
    pre_init(&a->pre);
    blocks_init(&a->blk, bc);
    safety_init(&a->fsm, sc, now);
}

void app_set_gyro_offset(app_t *a, const int16_t off[3])
{
    for (int c = 0; c < 3; c++) a->gyro_off[c] = off[c];
}

unsigned app_on_raw(app_t *a, const int16_t raw[6])
{
    int16_t r[6];
    unsigned f = 0;
    for (int c = 0; c < 6; c++) {
        int32_t v = raw[c] - (c >= 3 ? a->gyro_off[c - 3] : 0);
        r[c] = (int16_t)(v > 32767 ? 32767 : v < -32768 ? -32768 : v);
    }
    a->n_raw++;
    if (blocks_push(&a->blk, r)) {
        safety_on_block(&a->fsm, a->blk.still_run, a->blk.az_tb);
        f |= APP_BLOCK;
    }
    if (pre_push_raw(&a->pre, r, 0) & PRE_NEW_WINDOW)
        f |= APP_FRAME;
    return f;
}

uint8_t app_take_frame(app_t *a, const int8_t **s1, uint16_t *n1, const int8_t **s2, uint16_t *n2)
{
    pre_window(&a->pre, s1, n1, s2, n2);
    a->n_frames++;
    return a->seq++;
}

void app_on_result(app_t *a, int rc, const spi_result_t *r)
{
    if (rc == SPI_OK || rc == SPI_E_TAIL) {
        a->n_ok++;
        a->consec_err = 0;
        a->err_flag = 0;
        a->last_cls = r->cls;
        a->last_score = r->score;
        safety_on_result(&a->fsm, r->cls, r->score);
    } else {
        a->n_err++;                                 /* A.7: bỏ cửa sổ, đếm lỗi */
        if (++a->consec_err >= SPI_ERR_RESET)
            a->err_flag = 1;
    }
}

void app_tick(app_t *a, uint32_t now, uint8_t wear, uint8_t cancel)
{
    safety_tick(&a->fsm, now, wear, cancel);
    if (a->fsm.events & SAFETY_EV_BEEP)
        a->t_beep = now + 100u;                     /* IMPACT khi đang đội: bíp 100 ms */
}

uint8_t app_buzzer(const app_t *a, uint32_t now)
{
    uint32_t t = now - a->fsm.t_enter;
    switch (a->fsm.st) {
    case ST_PRE_ALARM: return (t % 1000u) < 150u;   /* bíp ngắn mỗi giây trong lúc đếm ngược 10 s */
    case ST_ALARM:     return (t % 500u) < 350u;    /* hú liên tục */
    default:           return (int32_t)(a->t_beep - now) > 0;
    }
}

uint8_t app_led(const app_t *a, uint32_t now)
{
    if (a->err_flag) return (now % 200u) < 100u;   /* lỗi FPGA: nháy nhanh */
    switch (a->fsm.st) {
    case ST_STANDBY:   return (now % 2000u) < 50u;
    case ST_MONITOR:   return (now % 1000u) < 50u;
    case ST_SUSPECT:   return (now % 400u) < 200u;
    case ST_PRE_ALARM:
    case ST_ALARM:     return 1;
    default:           return (now % 1000u) < 500u;
    }
}

/* ---------- LED 7 đoạn (FW-12) ---------- */
#define SG_A 0x77u
#define SG_C 0x39u
#define SG_E 0x79u
#define SG_F 0x71u
#define SG_L 0x38u
#define SG_P 0x73u
#define SG_S 0x6Du
#define SG_U 0x3Eu
#define SG_n 0x54u
#define SG_o 0x5Cu
#define SG_r 0x50u
static const uint8_t k_digit[10] = { 0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F };

void app_display(const app_t *a, uint32_t now, uint8_t seg[4])
{
    seg[0] = seg[1] = seg[2] = seg[3] = 0;
    if (a->err_flag) { seg[0] = SG_E; seg[1] = SG_r; seg[2] = SG_r; return; }
    switch (a->fsm.st) {
    case ST_STANDBY: seg[0] = SG_o; seg[1] = SG_F; seg[2] = SG_F; break;
    case ST_MONITOR: seg[0] = SG_r; seg[1] = SG_U; seg[2] = SG_n; break;
    case ST_SUSPECT: seg[0] = SG_S; seg[1] = SG_U; seg[2] = SG_S; break;
    case ST_PRE_ALARM: {
        uint32_t el = now - a->fsm.t_enter, tot = a->fsm.cfg.pre_alarm_ms;
        uint32_t left = (el >= tot) ? 0u : (tot - el + 999u) / 1000u;     /* làm tròn lên: 10, 9, …, 1 */
        if (left > 99u) left = 99u;
        seg[0] = SG_P;
        seg[2] = k_digit[left / 10u];
        seg[3] = k_digit[left % 10u];
        break;
    }
    case ST_ALARM:    seg[0] = SG_A; seg[1] = SG_L; seg[2] = SG_r; break;
    case ST_COOLDOWN: seg[0] = SG_C; seg[1] = SG_L; break;
    default: break;
    }
}
