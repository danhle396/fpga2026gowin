/*
 * app_core.h — lõi vòng lặp chính của firmware (mục 4.3 của PROJECT_MASTER.md), C thuần: mẫu thô → trừ offset gyro →
 * tiền xử lý (A.2) + khối (A.8) → báo khi có cửa sổ cần gửi → nhận kết quả FPGA → bỏ phiếu + Safety FSM → còi, LED.
 * Phần cứng (I2C, SPI, UART, GPIO) nằm ở app_main.c; tools/m0_test.py chạy lõi này trong trình giả lập với
 * cnn_mcu.c đứng thay FPGA và so với chuỗi golden của Python.
 */
#ifndef APP_CORE_H
#define APP_CORE_H

#include <stdint.h>
#include "preprocess.h"
#include "blocks.h"
#include "safety.h"
#include "spi_frame.h"

#define APP_FRAME   1u              /* app_on_raw: có cửa sổ mới cần gửi */
#define APP_BLOCK   2u              /* app_on_raw: vừa đóng một khối */

typedef struct {
    pre_state_t pre;
    blocks_t    blk;
    safety_t    fsm;
    int16_t     gyro_off[3];
    uint8_t     seq;                /* SEQ của khung kế tiếp */
    uint8_t     consec_err;         /* lỗi SPI liên tiếp */
    uint8_t     err_flag;           /* ≥ 3 lỗi liên tiếp: hiện ERR cho tới khi có kết quả đúng */
    uint8_t     last_cls, last_score;
    uint32_t    n_raw, n_frames, n_ok, n_err;
    uint32_t    t_beep;             /* bíp IMPACT tới thời điểm này */
} app_t;

void     app_init(app_t *a, const safety_cfg_t *sc, const blocks_cfg_t *bc, uint32_t now);
void     app_set_gyro_offset(app_t *a, const int16_t off[3]);
unsigned app_on_raw(app_t *a, const int16_t raw[6]);
/* Cửa sổ hiện tại để gửi; trả về SEQ đã dùng và tăng SEQ. */
uint8_t  app_take_frame(app_t *a, const int8_t **s1, uint16_t *n1, const int8_t **s2, uint16_t *n2);
void     app_on_result(app_t *a, int rc, const spi_result_t *r);
void     app_tick(app_t *a, uint32_t now, uint8_t wear, uint8_t cancel);
uint8_t  app_buzzer(const app_t *a, uint32_t now);      /* 1 = còi kêu */
uint8_t  app_led(const app_t *a, uint32_t now);         /* 1 = LED sáng */
/* LED 7 đoạn 4 số của EVK (FW-12, khi chưa có OLED): mã đoạn gfedcba, bit 7 = DP, chữ số trái → phải.
 * oFF = STANDBY · rUn = MONITOR · SUS = SUSPECT · P 09 = PRE_ALARM còn 9 s · ALr = ALARM · CL = COOLDOWN · Err = lỗi FPGA */
void     app_display(const app_t *a, uint32_t now, uint8_t seg[4]);

#endif
