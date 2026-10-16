/* pwr_btn.c — xem pwr_btn.h. */
#include "pwr_btn.h"
#include "safety.h"

void pwr_btn_init(pwr_btn_t *p, uint8_t on)
{
    p->on = on;
    p->prev = p->mask = p->tap_ok = p->taps = p->ev = 0;
    p->t_down = p->t_up = 0;
}

uint8_t pwr_btn_tick(pwr_btn_t *p, uint32_t now, uint8_t down, uint8_t fsm_st)
{
    uint8_t press = down && !p->prev;
    uint8_t release = !down && p->prev;

    p->ev = 0;
    p->prev = down;
    if (press) {
        p->t_down = now;
        /* Lần nhấn chỉ dùng để BẬT khi: FSM ở STANDBY, hoặc vừa TẮT mà FSM còn ở MONITOR / SUSPECT (3 s chờ
         * WEAR_OFF_MS). Nếu không che ở đây, giữ nút để bật lại trong 3 s đó sẽ thành SOS → ALARM khi đang tắt.
         * PRE_ALARM / ALARM vẫn nhận nút (CANCEL, tắt còi). */
        p->mask = (fsm_st == ST_STANDBY) || (!p->on && (fsm_st == ST_MONITOR || fsm_st == ST_SUSPECT));
        p->tap_ok = p->on && fsm_st == ST_MONITOR;
        if (p->taps && (!p->tap_ok || now - p->t_up > PB_GAP_MS))
            p->taps = 0;
    }
    if (p->mask && down && !p->on && now - p->t_down >= PB_ON_HOLD_MS) {
        p->on = 1;
        p->ev = PB_EV_ON;
    }
    if (release) {
        if (!p->mask && p->tap_ok && fsm_st == ST_MONITOR && now - p->t_down < PB_TAP_MS) {
            if (p->taps) {
                p->taps = 0;
                p->on = 0;
                p->ev = PB_EV_OFF;
            } else {
                p->taps = 1;
            }
        } else {
            p->taps = 0;
        }
        p->t_up = now;
        p->mask = 0;
        return 0;
    }
    return p->mask ? 0 : down;
}
