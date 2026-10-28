/*
 * safety.h — bỏ phiếu và Safety FSM của A.8 (việc FW-11). C thuần: thời gian và nút do người gọi đưa vào,
 * nên chạy được y nguyên trong bộ test trên PC (firmware/test/) và trên MCU.
 *
 *   STANDBY ◄─ WEAR = 0 liên tục 3 s ─ MONITOR ─► SUSPECT ─► PRE_ALARM (10 s) ─► ALARM ─► COOLDOWN (30 s) ─► MONITOR
 *
 * Cách gọi: safety_on_result() mỗi khung kết quả của FPGA, safety_on_block() mỗi khi blocks_push() đóng khối,
 * safety_tick() mỗi khe 10 ms. Mọi chuyển trạng thái xảy ra trong safety_tick(), theo thứ tự ưu tiên của A.8:
 * CANCEL > timeout > phiếu CNN > khối. Mỗi lần gọi chuyển tối đa một trạng thái.
 *
 * Quy ước thêm (A.8 không nói, ghi ở PROJECT_MASTER.md mục 6, FW-11):
 *   - Một lần nhấn CANCEL đã gây chuyển trạng thái thì "đã dùng" cho tới khi nhả, để giữ nút SOS 3 s rồi giữ tiếp
 *     không tự hủy luôn ALARM, và nhấn hủy PRE_ALARM rồi giữ không thành SOS.
 *   - Lịch sử phiếu bị xóa khi vào SUSPECT và khi về MONITOR, để phiếu cũ không kích lại ngay sau khi hủy.
 *   - IMPACT khi đang đội: chỉ ở MONITOR, cần SCORE ≥ T_SCORE như phiếu FALL.
 */
#ifndef SAFETY_H
#define SAFETY_H

#include <stdint.h>

typedef enum {
    ST_STANDBY = 0, ST_MONITOR, ST_SUSPECT, ST_PRE_ALARM, ST_ALARM, ST_COOLDOWN
} safety_state_t;

typedef struct {
    uint8_t  vote_k, vote_n, t_score, still_blocks, tilt_en;
    int16_t  t_tilt;
    uint32_t wear_off_ms, wear_recent_ms, suspect_timeout_ms, pre_alarm_ms, cooldown_ms, sos_hold_ms, alarm_hold_ms;
} safety_cfg_t;

/* Lý do chuyển trạng thái, để ghi dòng sự kiện RUN (A.9) */
enum {
    WHY_NONE = 0, WHY_WEAR_ON, WHY_WEAR_OFF, WHY_VOTES, WHY_STILL, WHY_TIMEOUT, WHY_CANCEL, WHY_SOS, WHY_ALARM_ACK,
    WHY_KHONG_NGA           /* nga.c loại: phiếu CNN không kèm dấu hiệu ngã thật (safety_bo_nghi) */
};

#define SAFETY_EV_STATE   0x01u     /* vừa đổi trạng thái */
#define SAFETY_EV_BEEP    0x02u     /* IMPACT khi đang đội: một tiếng bíp + ghi log */

typedef struct {
    safety_cfg_t   cfg;
    safety_state_t st;
    uint8_t  why;               /* lý do của lần chuyển gần nhất */
    uint8_t  events;            /* SAFETY_EV_* của lần tick gần nhất */
    uint32_t t_enter;
    uint32_t t_wear_on;         /* lần gần nhất thấy WEAR = 1 */
    uint8_t  wear_seen;
    uint8_t  vote_bits;         /* bit 0 = cửa sổ mới nhất */
    uint8_t  impact_pending;
    uint8_t  still_run;
    int16_t  az_tb;
    uint8_t  btn_prev, btn_used;
    uint32_t t_btn_down;
} safety_t;

void        safety_default_cfg(safety_cfg_t *cfg);       /* giá trị đầu của A.8 (fw_config.h) */
void        safety_init(safety_t *s, const safety_cfg_t *cfg, uint32_t now);
void        safety_on_result(safety_t *s, uint8_t cls, uint8_t score);
void        safety_on_block(safety_t *s, uint8_t still_run, int16_t az_tb);
void        safety_tick(safety_t *s, uint32_t now, uint8_t wear, uint8_t cancel_down);
uint8_t     safety_fall_votes(const safety_t *s);
/* Tầng xác nhận ngã (nga.c, chạy trên ESP32) loại một lần nghi ngã: SUSPECT / PRE_ALARM → MONITOR, lý do
 * WHY_KHONG_NGA. Ngoài bảng A.8; không gọi thì FSM y như safety_model.py. */
void        safety_bo_nghi(safety_t *s, uint32_t now);
const char *safety_state_name(safety_state_t st);

#endif
