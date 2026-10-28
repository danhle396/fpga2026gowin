/* safety.c — xem safety.h. Thời gian là ms 32 bit, so bằng hiệu không dấu nên qua được lúc tràn (49,7 ngày). */
#include <string.h>
#include "safety.h"
#include "fw_config.h"

void safety_default_cfg(safety_cfg_t *c)
{
    c->vote_k = VOTE_K;
    c->vote_n = VOTE_N;
    c->t_score = T_SCORE;
    c->still_blocks = STILL_BLOCKS;
    c->tilt_en = TILT_EN;
    c->t_tilt = T_TILT;
    c->wear_off_ms = WEAR_OFF_MS;
    c->wear_recent_ms = WEAR_RECENT_MS;
    c->suspect_timeout_ms = SUSPECT_TIMEOUT_MS;
    c->pre_alarm_ms = PRE_ALARM_MS;
    c->cooldown_ms = COOLDOWN_MS;
    c->sos_hold_ms = SOS_HOLD_MS;
    c->alarm_hold_ms = ALARM_HOLD_MS;
}

void safety_init(safety_t *s, const safety_cfg_t *cfg, uint32_t now)
{
    memset(s, 0, sizeof(*s));
    s->cfg = *cfg;
    s->st = ST_STANDBY;
    s->t_enter = now;
}

uint8_t safety_fall_votes(const safety_t *s)
{
    uint8_t n = 0, bits = s->vote_bits & (uint8_t)((1u << s->cfg.vote_n) - 1u);
    while (bits) {
        n += bits & 1u;
        bits >>= 1;
    }
    return n;
}

void safety_on_result(safety_t *s, uint8_t cls, uint8_t score)
{
    uint8_t vote = (cls == CLS_FALL && score >= s->cfg.t_score);
    s->vote_bits = (uint8_t)((s->vote_bits << 1) | vote);
    if (cls == CLS_IMPACT && score >= s->cfg.t_score)
        s->impact_pending = 1;
}

void safety_on_block(safety_t *s, uint8_t still_run, int16_t az_tb)
{
    s->still_run = still_run;
    s->az_tb = az_tb;
}

static void go(safety_t *s, safety_state_t st, uint8_t why, uint32_t now)
{
    s->st = st;
    s->why = why;
    s->t_enter = now;
    s->events |= SAFETY_EV_STATE;
    if (st == ST_SUSPECT || st == ST_MONITOR)
        s->vote_bits = 0;
}

void safety_tick(safety_t *s, uint32_t now, uint8_t wear, uint8_t cancel_down)
{
    const safety_cfg_t *c = &s->cfg;
    uint32_t in_state = now - s->t_enter;
    uint8_t press = cancel_down && !s->btn_prev;
    uint8_t impact = s->impact_pending;

    s->events = 0;
    s->impact_pending = 0;
    if (wear) {
        s->t_wear_on = now;
        s->wear_seen = 1;
    }
    if (press) {
        s->t_btn_down = now;
        s->btn_used = 0;
    }
    s->btn_prev = cancel_down;
    uint32_t held = cancel_down ? now - s->t_btn_down : 0;
    uint8_t  hold_ok = cancel_down && !s->btn_used;

    /* 1. CANCEL */
    switch (s->st) {
    case ST_PRE_ALARM:
        if (press) { s->btn_used = 1; go(s, ST_MONITOR, WHY_CANCEL, now); return; }
        break;
    case ST_MONITOR:
    case ST_SUSPECT:
        if (hold_ok && held >= c->sos_hold_ms) { s->btn_used = 1; go(s, ST_ALARM, WHY_SOS, now); return; }
        break;
    case ST_ALARM:
        if (hold_ok && held >= c->alarm_hold_ms) { s->btn_used = 1; go(s, ST_COOLDOWN, WHY_ALARM_ACK, now); return; }
        break;
    default:
        break;
    }

    /* 2. timeout (gồm cả WEAR: STANDBY ↔ MONITOR) */
    switch (s->st) {
    case ST_STANDBY:
        if (wear) { go(s, ST_MONITOR, WHY_WEAR_ON, now); return; }
        break;
    case ST_MONITOR:
        if (!wear && s->wear_seen && now - s->t_wear_on >= c->wear_off_ms) { go(s, ST_STANDBY, WHY_WEAR_OFF, now); return; }
        if (!s->wear_seen && in_state >= c->wear_off_ms) { go(s, ST_STANDBY, WHY_WEAR_OFF, now); return; }
        break;
    case ST_SUSPECT:
        if (in_state >= c->suspect_timeout_ms) { go(s, ST_MONITOR, WHY_TIMEOUT, now); return; }
        break;
    case ST_PRE_ALARM:
        if (in_state >= c->pre_alarm_ms) { go(s, ST_ALARM, WHY_TIMEOUT, now); return; }
        break;
    case ST_COOLDOWN:
        if (in_state >= c->cooldown_ms) { go(s, ST_MONITOR, WHY_TIMEOUT, now); return; }
        break;
    default:
        break;
    }

    /* 3. phiếu CNN */
    if (s->st == ST_MONITOR) {
        if (impact && wear)
            s->events |= SAFETY_EV_BEEP;
        if (safety_fall_votes(s) >= c->vote_k && s->wear_seen && now - s->t_wear_on <= c->wear_recent_ms) {
            go(s, ST_SUSPECT, WHY_VOTES, now);
            return;
        }
    }

    /* 4. khối */
    /* A.8 (v3.1): đầu nằm ngang, |az_tb| < T_TILT; đầu thẳng hay lộn ngược (cúi gập) đều không tính là nằm */
    if (s->st == ST_SUSPECT && s->still_run >= c->still_blocks &&
        (!c->tilt_en || (s->az_tb < c->t_tilt && s->az_tb > -c->t_tilt)))
        go(s, ST_PRE_ALARM, WHY_STILL, now);
}

void safety_bo_nghi(safety_t *s, uint32_t now)
{
    if (s->st == ST_SUSPECT || s->st == ST_PRE_ALARM) go(s, ST_MONITOR, WHY_KHONG_NGA, now);
}

const char *safety_state_name(safety_state_t st)
{
    static const char *const k[] = { "STANDBY", "MONITOR", "SUSPECT", "PRE_ALARM", "ALARM", "COOLDOWN" };
    return (unsigned)st < 6u ? k[st] : "?";
}
