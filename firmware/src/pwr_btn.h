/*
 * pwr_btn.h — một nút cho cả bật/tắt hệ thống, CANCEL và SOS (đề cương v2.1; nhóm chọn ngày 16/10).
 * Nằm ngoài Safety FSM: giữ cờ "hệ thống bật" thay cho WEAR, và lọc nút trước khi đưa vào FSM.
 *   FSM ở STANDBY (hệ thống TẮT): giữ PB_ON_HOLD_MS → BẬT. Lần nhấn này không chuyển cho FSM, nên giữ lâu
 *       hơn cũng không thành SOS.
 *   Hệ thống BẬT, FSM ở MONITOR: nhấn nhanh 2 lần (mỗi lần < PB_TAP_MS, lần 2 bắt đầu < PB_GAP_MS sau khi nhả
 *       lần 1) → TẮT; FSM về STANDBY sau WEAR_OFF_MS.
 *   Mọi cử chỉ khác chuyển nguyên cho FSM (A.8): giữ 3 s = SOS, nhấn ở PRE_ALARM = CANCEL, giữ 1 s ở ALARM = tắt còi.
 * Lúc cấp nguồn hệ thống BẬT. Nút đã chống dội ở keys_scan (20 ms).
 */
#ifndef PWR_BTN_H
#define PWR_BTN_H

#include <stdint.h>

#define PB_ON_HOLD_MS  2000u
#define PB_TAP_MS       400u
#define PB_GAP_MS       600u

#define PB_EV_ON   1u
#define PB_EV_OFF  2u

typedef struct {
    uint8_t  on;            /* 1 = hệ thống bật */
    uint8_t  prev;          /* trạng thái nút ở tick trước */
    uint8_t  mask;          /* lần nhấn đang diễn ra là cử chỉ BẬT: không đưa cho FSM */
    uint8_t  tap_ok;        /* lần nhấn đang diễn ra bắt đầu khi hệ thống bật và FSM ở MONITOR */
    uint8_t  taps;          /* 1 = vừa có một lần nhấn ngắn hợp lệ */
    uint8_t  ev;            /* PB_EV_ON / PB_EV_OFF trong tick này */
    uint32_t t_down, t_up;
} pwr_btn_t;

void    pwr_btn_init(pwr_btn_t *p, uint8_t on);
/* Gọi mỗi tick trước safety_tick. down = nút đang nhấn; fsm_st = trạng thái FSM hiện tại (safety_state_t).
 * Trả về trạng thái nút để đưa cho FSM. */
uint8_t pwr_btn_tick(pwr_btn_t *p, uint32_t now, uint8_t down, uint8_t fsm_st);

#endif
