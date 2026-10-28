/*
 * host_main.c — chạy các module C thuần của firmware (preprocess, spi_frame, crc, blocks, safety) dưới dạng mã máy
 * Cortex-M0 thật, biên dịch bằng cùng armclang, trong trình giả lập (tools/m0_test.py, Unicorn). Không dùng ngoại vi.
 *
 * Bản đồ bộ nhớ chỉ có trong trình giả lập:
 *   0x40000000  ghi 1 byte → in ra stdout          0x40000004  ghi → dừng, giá trị = số byte đã ghi ra OUT
 *   0x60000000  IN : [mode u32][n u32][dữ liệu]   0x70000000  OUT: dữ liệu ra, Python so với golden
 */
#include <stdint.h>
#include <string.h>
#include "fw_config.h"
#include "crc.h"
#include "preprocess.h"
#include "spi_frame.h"
#include "blocks.h"
#include "safety.h"
#include "app_core.h"
#include "posture.h"

#define MBOX_PUTC   (*(volatile uint32_t *)0x40000000u)
#define MBOX_EXIT   (*(volatile uint32_t *)0x40000004u)
#define IN_BASE     ((const uint8_t *)0x60000000u)
#define OUT_BASE    ((uint8_t *)0x70000000u)

static uint32_t s_out;
static int s_pass, s_fail;

static void put(const char *s) { while (*s) MBOX_PUTC = (uint8_t)*s++; }
static void put_dec(int32_t v)
{
    char b[12]; int i = 0; uint32_t u = v < 0 ? (uint32_t)(-(v + 1)) + 1u : (uint32_t)v;
    if (v < 0) MBOX_PUTC = '-';
    do { b[i++] = (char)('0' + u % 10u); u /= 10u; } while (u);
    while (i) MBOX_PUTC = (uint8_t)b[--i];
}
static void out_byte(uint8_t b, void *ctx) { (void)ctx; OUT_BASE[s_out++] = b; }
static void out_bytes(const void *p, uint32_t n) { memcpy(OUT_BASE + s_out, p, n); s_out += n; }

static void check(const char *name, int ok)
{
    put(ok ? "PASS  " : "FAIL  ");
    put(name);
    put("\n");
    if (ok) s_pass++; else s_fail++;
}

/* ---------------- mode 1: tiền xử lý + khung (FW-07, FW-08) ----------------
 * IN: n mẫu thô × 6 INT16 LE. OUT: mỗi mẫu 50 Hz 'S' + 6 byte; mỗi cửa sổ 'W' + SEQ + khung v3 772 + khung v1 771. */
static pre_state_t g_pre;

static void mode_pre(uint32_t n, const int16_t *raw)
{
    int8_t q[PRE_CH];
    uint8_t seq = 0;
    pre_init(&g_pre);
    for (uint32_t i = 0; i < n; i++) {
        unsigned f = pre_push_raw(&g_pre, &raw[i * PRE_CH], q);
        if (f & PRE_NEW_SAMPLE) {
            OUT_BASE[s_out++] = 'S';
            out_bytes(q, PRE_CH);
        }
        if (f & PRE_NEW_WINDOW) {
            const int8_t *a, *b; uint16_t na, nb;
            pre_window(&g_pre, &a, &na, &b, &nb);
            OUT_BASE[s_out++] = 'W';
            OUT_BASE[s_out++] = seq;
            spi_frame_emit(3, seq, a, na, b, nb, &crc16_sw, out_byte, 0);
            spi_frame_emit(1, seq, a, na, b, nb, &crc16_sw, out_byte, 0);
            seq++;
        }
    }
}

/* ---------------- mode 2: kiểm khung đọc ----------------
 * IN: n bản ghi [proto][n_read][seq_expect][20 byte]. OUT mỗi bản ghi: rc, seq, status, cls, score, 4 logit (BE),
 * cycles (3 byte BE), score32 (4 byte BE) = 20 byte. */
static void mode_parse(uint32_t n, const uint8_t *p)
{
    for (uint32_t i = 0; i < n; i++, p += 23) {
        spi_result_t r;
        memset(&r, 0, sizeof r);
        int rc = (p[0] == 1) ? spi_parse_v1(&p[3], &r) : spi_parse_v3(&p[3], p[1], p[2], &r);
        uint8_t o[20] = { (uint8_t)rc, r.seq, r.status, r.cls, r.score };
        for (int k = 0; k < 4; k++) { o[5 + 2 * k] = (uint8_t)((uint16_t)r.logit[k] >> 8); o[6 + 2 * k] = (uint8_t)r.logit[k]; }
        o[13] = (uint8_t)(r.cycles >> 16); o[14] = (uint8_t)(r.cycles >> 8); o[15] = (uint8_t)r.cycles;
        o[16] = (uint8_t)((uint32_t)r.score32 >> 24); o[17] = (uint8_t)((uint32_t)r.score32 >> 16);
        o[18] = (uint8_t)((uint32_t)r.score32 >> 8); o[19] = (uint8_t)r.score32;
        out_bytes(o, 20);
    }
}

/* ---------------- mode 3: hằng số A.2, A.7, A.10 ----------------
 * IN: n giá trị INT32 cho q8. OUT: payload tự kiểm 768 byte, CRC16("123456789") 2 byte BE, CRC8("123456789"),
 * rồi q8(v, 7) và q8(v, 6) cho từng giá trị. */
static void mode_consts(uint32_t n, const int32_t *v)
{
    static const uint8_t s9[9] = { '1', '2', '3', '4', '5', '6', '7', '8', '9' };
    int8_t pl[768];
    spi_selftest_payload(pl);
    out_bytes(pl, 768);
    uint16_t c = crc16_ccitt(s9, 9);
    OUT_BASE[s_out++] = (uint8_t)(c >> 8);
    OUT_BASE[s_out++] = (uint8_t)c;
    uint8_t c8 = 0;
    for (int i = 0; i < 9; i++) c8 = crc8_update(c8, s9[i]);
    OUT_BASE[s_out++] = c8;
    for (uint32_t i = 0; i < n; i++) {
        OUT_BASE[s_out++] = (uint8_t)pre_q8(v[i], ACC_SHIFT);
        OUT_BASE[s_out++] = (uint8_t)pre_q8(v[i], GYR_SHIFT);
    }
}

/* ---------------- mode 4: khối và Safety FSM (FW-11), mỗi dòng của bảng A.8 ít nhất một ca ---------------- */
static safety_t S;
static uint32_t T;

static void fsm_reset_at(uint32_t t0, int tilt_en)
{
    safety_cfg_t c;
    safety_default_cfg(&c);
    c.t_score = 64;                             /* giá trị thử; số thật chốt ở AI-10 */
    c.tilt_en = (uint8_t)tilt_en;
    T = t0;
    safety_init(&S, &c, T);
}
static void fsm_reset(void) { fsm_reset_at(0, 1); }
static void step(uint8_t wear, uint8_t btn) { T += 10; safety_tick(&S, T, wear, btn); }
static void run(uint32_t ms, uint8_t wear, uint8_t btn) { for (uint32_t e = 0; e < ms; e += 10) step(wear, btn); }
static void vote(uint8_t cls, uint8_t score) { safety_on_result(&S, cls, score); step(1, 0); }
static void to_suspect(void) { step(1, 0); vote(CLS_FALL, 100); vote(CLS_FALL, 100); }
static void to_prealarm(void) { to_suspect(); safety_on_block(&S, STILL_BLOCKS, 500); step(1, 0); }

static void blk_fill(blocks_t *b, const int16_t r[6], int n) { for (int i = 0; i < n; i++) blocks_push(b, r); }

/* một nút: bật/tắt + CANCEL + SOS (pwr_btn.h), qua app_tick như firmware thật; WEAR phần cứng = 1 */
static app_t PA;
static uint32_t PT;
static void pa_reset(void)
{
    safety_cfg_t c;
    blocks_cfg_t bc = { T_STILL_A, T_STILL_G };
    safety_default_cfg(&c);
    PT = 0;
    app_init(&PA, &c, &bc, 0);
    PT += 10; app_tick(&PA, PT, 1, 0);
}
static void pa_run(uint32_t ms, uint8_t btn) { for (uint32_t e = 0; e < ms; e += 10) { PT += 10; app_tick(&PA, PT, 1, btn); } }
static void pa_fall(void)                   /* 2 phiếu FALL → SUSPECT, rồi bất động + đầu nằm → PRE_ALARM */
{
    safety_on_result(&PA.fsm, CLS_FALL, 100); safety_on_result(&PA.fsm, CLS_FALL, 100); pa_run(10, 0);
    safety_on_block(&PA.fsm, STILL_BLOCKS, 500); pa_run(10, 0);
}
static void pa_tap(void) { pa_run(100, 1); pa_run(10, 0); }

static void mode_pwr_btn(void)
{
    pa_reset();
    check("nut: cap nguon la BAT -> MONITOR", PA.pb.on && PA.fsm.st == ST_MONITOR);

    pa_tap(); pa_run(200, 0); pa_run(100, 1); PT += 10; app_tick(&PA, PT, 1, 0);
    int off_ev = !PA.pb.on && PA.pwr_ev == PB_EV_OFF && app_buzzer(&PA, PT) && app_buzzer(&PA, PT + 590);
    int quiet = !app_buzzer(&PA, PT + 610);
    pa_run(2980, 0);                                /* t_wear_on = tick trước tick TẮT: STANDBY ở +2990 ms */
    int still_mon = PA.fsm.st == ST_MONITOR;
    pa_run(10, 0);
    check("nut: nhan nhanh 2 lan o MONITOR -> TAT, bip dai 0,6 s, STANDBY sau 3 s",
          off_ev && quiet && still_mon && PA.fsm.st == ST_STANDBY);

    pa_run(1000, 1); pa_run(100, 0);
    check("nut: o STANDBY giu 1 s chua du -> van TAT", !PA.pb.on && PA.fsm.st == ST_STANDBY);

    pa_run(2000, 1);                                /* t_down = tick đầu của đoạn giữ: mới giữ 1,99 s */
    int not_yet = !PA.pb.on;
    pa_run(10, 1);
    uint32_t t_on = PT;
    int on_ev = PA.pb.on && PA.pwr_ev == PB_EV_ON;
    int beep2 = app_buzzer(&PA, t_on + 50) && !app_buzzer(&PA, t_on + 150) && app_buzzer(&PA, t_on + 250) &&
                !app_buzzer(&PA, t_on + 310);
    pa_run(4000, 1);                                /* giữ tiếp, tổng 6 s: không được thành SOS */
    int no_sos = PA.fsm.st == ST_MONITOR;
    pa_run(100, 0);
    check("nut: o STANDBY giu 2 s -> BAT, 2 bip ngan; giu tiep toi 6 s khong thanh SOS",
          not_yet && on_ev && beep2 && no_sos && PA.fsm.st == ST_MONITOR && PA.pb.on);

    pa_reset(); pa_run(2990, 1);
    int pre = PA.fsm.st == ST_MONITOR;
    pa_run(20, 1);
    check("nut: dang BAT giu 3 s -> SOS (ALARM), nhu A.8", pre && PA.fsm.st == ST_ALARM && PA.pb.on);

    pa_reset(); pa_tap(); pa_run(800, 0); pa_tap();
    check("nut: 2 lan nhan cach nhau 0,8 s -> van BAT", PA.pb.on && PA.fsm.st == ST_MONITOR);

    pa_reset(); pa_tap(); pa_run(100, 0); pa_run(500, 1); pa_run(10, 0);
    check("nut: nhan ngan roi giu 0,5 s -> van BAT", PA.pb.on);

    pa_reset(); pa_fall();
    int in_pre = PA.fsm.st == ST_PRE_ALARM;
    pa_tap();
    int cancelled = PA.fsm.st == ST_MONITOR && PA.fsm.why == WHY_CANCEL;
    pa_run(100, 0); pa_tap();
    check("nut: o PRE_ALARM nhan = CANCEL; nhan them ngay sau do khong lam TAT",
          in_pre && cancelled && PA.pb.on && PA.fsm.st == ST_MONITOR);

    pa_reset(); pa_tap(); pa_run(200, 0); pa_tap();
    int off2 = !PA.pb.on && PA.fsm.st == ST_MONITOR;
    pa_run(500, 0); pa_fall();
    int fell = PA.fsm.st == ST_PRE_ALARM;
    pa_tap();
    check("nut: vua TAT ma nga trong 3 s -> van PRE_ALARM, nut van CANCEL duoc",
          off2 && fell && PA.fsm.st == ST_MONITOR && PA.fsm.why == WHY_CANCEL);

    /* vừa TẮT (FSM còn MONITOR 3 s) mà giữ nút để bật lại: phải BẬT sau 2 s, giữ tiếp không được thành SOS */
    pa_reset(); pa_tap(); pa_run(200, 0); pa_tap();
    int off3 = !PA.pb.on && PA.fsm.st == ST_MONITOR;
    pa_run(500, 0); pa_run(3500, 1);
    int on3 = PA.pb.on && PA.fsm.st != ST_ALARM;
    pa_run(100, 0);
    check("nut: vua TAT, giu 3,5 s trong luc FSM con MONITOR -> BAT lai, khong SOS",
          off3 && on3 && PA.pb.on && PA.fsm.st == ST_MONITOR);

    /* còi theo trạng thái ngã (28/10, nhóm: "nghi ngã cũng phải được xem là ngã") */
    pa_reset(); pa_run(2000, 0);
    int im = 1;
    for (uint32_t d = 0; d < 2000; d += 10) im &= !app_buzzer(&PA, PT + d);
    safety_on_result(&PA.fsm, CLS_FALL, 100); safety_on_result(&PA.fsm, CLS_FALL, 100); pa_run(10, 0);
    uint32_t ts = PA.fsm.t_enter;
    int sus = PA.fsm.st == ST_SUSPECT, n_on = 0, n_len = 0;
    for (uint32_t d = 0; d < SUSPECT_TIMEOUT_MS; d += 10) {   /* đếm tiếng bíp (sườn lên) suốt SUSPECT */
        uint8_t b = app_buzzer(&PA, ts + d);
        if (b && !n_len) n_on++;
        n_len = b;
    }
    int b_sus = n_on == SUSPECT_TIMEOUT_MS / 1000 && app_buzzer(&PA, ts + 390) && !app_buzzer(&PA, ts + 410);
    pa_run(SUSPECT_TIMEOUT_MS, 0);                       /* ngã nhẹ rồi không nằm yên: hết SUSPECT → MONITOR, còi im */
    int het = PA.fsm.st == ST_MONITOR && !app_buzzer(&PA, PT + 10) && !app_buzzer(&PA, PT + 400);
    safety_on_result(&PA.fsm, CLS_FALL, 100); safety_on_result(&PA.fsm, CLS_FALL, 100); pa_run(10, 0);
    safety_on_block(&PA.fsm, STILL_BLOCKS, 500); pa_run(10, 0);
    uint32_t tp = PA.fsm.t_enter;
    int pre_b = PA.fsm.st == ST_PRE_ALARM && app_buzzer(&PA, tp + 50) && !app_buzzer(&PA, tp + 200) &&
                app_buzzer(&PA, tp + 550);
    check("coi: MONITOR im; SUSPECT (phat hien nga) bip 0,4 s moi giay suot 8 s; het SUSPECT im; PRE_ALARM 2 bip/giay",
          im && sus && b_sus && het && pre_b);
}

static void mode_safety(void)
{
    /* ---- khối ---- */
    blocks_t b;
    blocks_cfg_t bc = { T_STILL_A, T_STILL_G };
    int16_t up[6] = { 0, 0, 2048, 0, 0, 0 }, r[6];

    blocks_init(&b, &bc);
    blk_fill(&b, up, 31);
    int closed = blocks_push(&b, up);
    check("khoi: dong sau dung 32 mau; dung yen; az_tb = 2048", closed && b.still && b.still_run == 1 && b.az_tb == 2048);
    memcpy(r, up, sizeof r); r[0] = 299; blk_fill(&b, up, 31); blocks_push(&b, r);
    check("khoi: AX lech 299 < T_STILL_A van bat dong, still_run = 2", b.still && b.still_run == 2);
    r[0] = 300; blk_fill(&b, up, 31); blocks_push(&b, r);
    check("khoi: AX lech 300 = T_STILL_A -> khong bat dong, still_run ve 0", !b.still && b.still_run == 0);
    memcpy(r, up, sizeof r); r[5] = -249; blk_fill(&b, up, 31); blocks_push(&b, r);
    check("khoi: GZ lech 249 < T_STILL_G van bat dong", b.still && b.still_run == 1);
    r[5] = -250; blk_fill(&b, up, 31); blocks_push(&b, r);
    check("khoi: GZ lech 250 = T_STILL_G -> khong bat dong", !b.still);
    int16_t neg[6] = { 0, 0, -1, 0, 0, 0 };
    blocks_init(&b, &bc); blk_fill(&b, neg, 32);
    int16_t az0 = b.az_tb;
    neg[2] = -2; blk_fill(&b, neg, 1); neg[2] = -1; blk_fill(&b, neg, 31);
    check("khoi: az_tb = (tong AZ) >> 5 lay san: -32 -> -1, -33 -> -2", az0 == -1 && b.az_tb == -2);

    /* ---- bỏ phiếu ---- */
    fsm_reset(); step(1, 0);
    safety_on_result(&S, CLS_FALL, 100); safety_on_result(&S, CLS_NORMAL, 100); safety_on_result(&S, CLS_FALL, 63);
    check("phieu: FALL voi SCORE < T_SCORE khong tinh (1/3)", safety_fall_votes(&S) == 1);
    safety_on_result(&S, CLS_FALL, 64);
    check("phieu: chi dem VOTE_N = 3 cua so gan nhat", safety_fall_votes(&S) == 1);

    /* ---- A.8 dòng 2: STANDBY → MONITOR ---- */
    fsm_reset();
    check("A.8 khoi dau o STANDBY", S.st == ST_STANDBY);
    step(1, 0);
    check("A.8 STANDBY -> MONITOR khi WEAR = 1", S.st == ST_MONITOR && S.why == WHY_WEAR_ON);

    /* ---- dòng 1: MONITOR → STANDBY ---- */
    run(2990, 0, 0);
    check("A.8 MONITOR giu nguyen khi WEAR = 0 moi 2,99 s", S.st == ST_MONITOR);
    step(0, 0);
    check("A.8 MONITOR -> STANDBY khi WEAR = 0 lien tuc 3 s", S.st == ST_STANDBY && S.why == WHY_WEAR_OFF);
    fsm_reset(); step(1, 0); run(2000, 0, 0); step(1, 0); run(2000, 0, 0);
    check("A.8 WEAR chap chon (0 2 s, 1, 0 2 s) khong ve STANDBY", S.st == ST_MONITOR);

    /* ---- dòng 3: MONITOR → SUSPECT ---- */
    fsm_reset(); step(1, 0);
    vote(CLS_FALL, 100); vote(CLS_NORMAL, 100);
    check("A.8 1 phieu FALL chua du VOTE_K = 2", S.st == ST_MONITOR);
    vote(CLS_FALL, 100);
    check("A.8 MONITOR -> SUSPECT khi 2/3 cua so FALL", S.st == ST_SUSPECT && S.why == WHY_VOTES);
    fsm_reset(); step(1, 0);
    vote(CLS_FALL, 10); vote(CLS_FALL, 10); vote(CLS_FALL, 10);
    check("A.8 3 cua so FALL nhung SCORE < T_SCORE: van MONITOR", S.st == ST_MONITOR);
    fsm_reset();
    safety_on_result(&S, CLS_FALL, 100); step(0, 0); safety_on_result(&S, CLS_FALL, 100); step(0, 0);
    check("A.8 phieu khi STANDBY bi bo qua", S.st == ST_STANDBY);
    step(1, 0); step(1, 0);
    check("A.8 phieu cu bi xoa khi vao MONITOR, khong vao SUSPECT", S.st == ST_MONITOR);
    fsm_reset(); step(1, 0); run(2500, 0, 0);
    safety_on_result(&S, CLS_FALL, 100); step(0, 0); safety_on_result(&S, CLS_FALL, 100); step(0, 0);
    check("A.8 MONITOR -> SUSPECT khi mu duoc doi trong 3 s gan nhat (WEAR = 0 moi 2,5 s)", S.st == ST_SUSPECT);

    /* ---- dòng 4: SUSPECT → PRE_ALARM ---- */
    fsm_reset(); to_suspect();
    safety_on_block(&S, STILL_BLOCKS - 1, 500); step(1, 0);
    check("A.8 still_run = 7 < STILL_BLOCKS: van SUSPECT", S.st == ST_SUSPECT);
    safety_on_block(&S, STILL_BLOCKS, 2048); step(1, 0);
    check("A.8 bat dong nhung dau thang (az_tb = 2048 >= T_TILT): van SUSPECT", S.st == ST_SUSPECT);
    safety_on_block(&S, STILL_BLOCKS, -2040); step(1, 0);
    check("A.8 v3.1: bat dong nhung dau lon nguoc (az_tb = -2040, cui gap): van SUSPECT", S.st == ST_SUSPECT);
    safety_on_block(&S, STILL_BLOCKS, -(T_TILT - 1)); step(1, 0);
    check("A.8 v3.1: |az_tb| = T_TILT - 1 phia am -> PRE_ALARM", S.st == ST_PRE_ALARM);
    fsm_reset(); to_suspect();
    safety_on_block(&S, STILL_BLOCKS, T_TILT - 1); step(1, 0);
    check("A.8 SUSPECT -> PRE_ALARM khi still_run >= 8 va |az_tb| < T_TILT", S.st == ST_PRE_ALARM && S.why == WHY_STILL);
    fsm_reset_at(0, 0); to_suspect();
    safety_on_block(&S, STILL_BLOCKS, 2048); step(1, 0);
    check("A.8 TILT_EN = 0: chi can bat dong", S.st == ST_PRE_ALARM);

    /* ---- dòng 5: SUSPECT → MONITOR ---- */
    fsm_reset(); to_suspect();
    run(7990, 1, 0);
    check("A.8 SUSPECT giu nguyen toi 7,99 s", S.st == ST_SUSPECT);
    step(1, 0);
    check("A.8 SUSPECT -> MONITOR khi qua SUSPECT_TIMEOUT 8 s", S.st == ST_MONITOR && S.why == WHY_TIMEOUT);

    /* ---- dòng 6: PRE_ALARM → MONITOR ---- */
    fsm_reset(); to_prealarm(); run(3000, 1, 0);
    step(1, 1);
    check("A.8 PRE_ALARM -> MONITOR khi bam CANCEL", S.st == ST_MONITOR && S.why == WHY_CANCEL);
    run(5000, 1, 1);
    check("lan nhan da huy PRE_ALARM, giu tiep 5 s khong thanh SOS", S.st == ST_MONITOR);
    step(1, 0); step(1, 1); run(2990, 1, 1);
    check("nha roi nhan lai: SOS tinh lai tu dau (2,99 s chua bao)", S.st == ST_MONITOR);
    step(1, 1);
    check("nha roi nhan lai giu 3 s -> ALARM", S.st == ST_ALARM);

    /* ---- dòng 7: PRE_ALARM → ALARM ---- */
    fsm_reset(); to_prealarm();
    run(9990, 1, 0);
    check("A.8 PRE_ALARM giu nguyen toi 9,99 s", S.st == ST_PRE_ALARM);
    step(1, 0);
    check("A.8 PRE_ALARM -> ALARM khi het PRE_ALARM_TIME 10 s", S.st == ST_ALARM && S.why == WHY_TIMEOUT);

    /* ---- dòng 8: MONITOR, SUSPECT → ALARM (SOS) ---- */
    fsm_reset(); step(1, 0);
    step(1, 1); run(2990, 1, 1);
    check("A.8 giu CANCEL 2,99 s o MONITOR: chua SOS", S.st == ST_MONITOR);
    step(1, 1);
    check("A.8 MONITOR -> ALARM khi giu CANCEL 3 s (SOS)", S.st == ST_ALARM && S.why == WHY_SOS);
    fsm_reset(); step(1, 0); step(1, 1); run(2500, 1, 1); run(1000, 1, 0);
    check("A.8 nha CANCEL truoc 3 s: khong SOS", S.st == ST_MONITOR);
    fsm_reset(); to_suspect(); step(1, 1); run(3000, 1, 1);
    check("A.8 SUSPECT -> ALARM khi giu CANCEL 3 s (SOS)", S.st == ST_ALARM && S.why == WHY_SOS);

    /* ---- dòng 9: ALARM → COOLDOWN → MONITOR ---- */
    run(2000, 1, 1);
    check("lan nhan gay SOS, giu tiep 2 s khong huy ALARM", S.st == ST_ALARM);
    step(1, 0); step(1, 1); run(990, 1, 1);
    check("A.8 ALARM: giu CANCEL 0,99 s chua tat", S.st == ST_ALARM);
    step(1, 1);
    check("A.8 ALARM -> COOLDOWN khi giu CANCEL 1 s", S.st == ST_COOLDOWN && S.why == WHY_ALARM_ACK);
    step(1, 0); run(29980, 1, 0);
    check("A.8 COOLDOWN giu nguyen toi 29,99 s", S.st == ST_COOLDOWN);
    step(1, 0);
    check("A.8 COOLDOWN -> MONITOR sau COOLDOWN_TIME 30 s", S.st == ST_MONITOR && S.why == WHY_TIMEOUT);

    /* ---- từ SUSPECT trở đi bỏ qua WEAR ---- */
    fsm_reset(); to_suspect(); run(5000, 0, 0);
    check("A.8 tu SUSPECT bo qua WEAR (WEAR = 0 5 s van SUSPECT)", S.st == ST_SUSPECT);
    safety_on_block(&S, STILL_BLOCKS, 500); step(0, 0);
    check("A.8 WEAR = 0 van vao PRE_ALARM", S.st == ST_PRE_ALARM);
    run(10000, 0, 0);
    check("A.8 WEAR = 0 o PRE_ALARM van toi ALARM", S.st == ST_ALARM);

    /* ---- IMPACT ---- */
    fsm_reset(); step(1, 0);
    safety_on_result(&S, CLS_IMPACT, 100); step(1, 0);
    int beep = (S.events & SAFETY_EV_BEEP) != 0;
    step(1, 0);
    check("A.8 IMPACT khi dang doi: dung mot tieng bip, khong doi trang thai",
          beep && !(S.events & SAFETY_EV_BEEP) && S.st == ST_MONITOR);
    safety_on_result(&S, CLS_IMPACT, 100); step(0, 0);
    check("A.8 IMPACT khi WEAR = 0: khong bip", !(S.events & SAFETY_EV_BEEP));

    /* ---- ưu tiên CANCEL > timeout > phiếu CNN > khối ---- */
    fsm_reset(); to_prealarm(); run(9990, 1, 0); step(1, 1);
    check("uu tien: CANCEL thang timeout o cung tick (PRE_ALARM -> MONITOR)", S.st == ST_MONITOR && S.why == WHY_CANCEL);
    fsm_reset(); step(1, 0); run(2990, 0, 0);
    safety_on_result(&S, CLS_FALL, 100); safety_on_result(&S, CLS_FALL, 100); step(0, 0);
    check("uu tien: timeout WEAR thang phieu CNN o cung tick (-> STANDBY)", S.st == ST_STANDBY);
    fsm_reset(); step(1, 0); step(1, 1); run(2990, 1, 1);
    safety_on_result(&S, CLS_FALL, 100); safety_on_result(&S, CLS_FALL, 100); step(1, 1);
    check("uu tien: SOS thang phieu CNN o cung tick (-> ALARM)", S.st == ST_ALARM && S.why == WHY_SOS);

    /* ---- tràn bộ đếm ms ---- */
    fsm_reset_at(0xFFFFF000u, 1); to_prealarm(); run(9990, 1, 0);
    int before = (S.st == ST_PRE_ALARM);
    step(1, 0);
    check("dem ms tran qua 2^32 khi dang PRE_ALARM: van dung 10 s", before && S.st == ST_ALARM);

    /* ---- LED 7 đoạn (FW-12): đếm ngược PRE_ALARM ---- */
    {
        static app_t ap;
        safety_cfg_t c2;
        blocks_cfg_t b2 = { T_STILL_A, T_STILL_G };
        uint8_t sg[4];
        safety_default_cfg(&c2);
        app_init(&ap, &c2, &b2, 0);
        ap.fsm.st = ST_PRE_ALARM;
        ap.fsm.t_enter = 5000;
        app_display(&ap, 5000, sg);
        int ok10 = sg[0] == 0x73 && sg[2] == 0x06 && sg[3] == 0x3F;
        app_display(&ap, 5001, sg);
        ok10 &= sg[2] == 0x06 && sg[3] == 0x3F;
        app_display(&ap, 6000, sg);
        int ok9 = sg[2] == 0x3F && sg[3] == 0x6F;
        app_display(&ap, 14999, sg);
        int ok1 = sg[3] == 0x06;
        app_display(&ap, 15000, sg);
        int ok0 = sg[3] == 0x3F;
        check("LED 7 doan: PRE_ALARM hien P 10, P 09, ..., P 01, P 00", ok10 && ok9 && ok1 && ok0);
        ap.err_flag = 1;
        app_display(&ap, 15000, sg);
        check("LED 7 doan: loi FPGA hien Err", sg[0] == 0x79 && sg[1] == 0x50 && sg[2] == 0x50);
    }

    mode_pwr_btn();

    put("TONG: "); put_dec(s_pass); put(" PASS, "); put_dec(s_fail); put(" FAIL\n");
}

/* ---------------- mode 5: chuỗi sự kiện bất kỳ qua Safety FSM (đối chiếu ml/src/safety_model.py) ----------------
 * IN: [t_score u8][tilt_en u8][2 byte trống][t0 u32] rồi n bản ghi 12 byte:
 *     [loại u8: 1 kết quả, 2 khối, 3 tick][a u8][b u8][c u8][d i16][2 byte trống][t u32]
 *     kết quả: a = CLASS, b = SCORE · khối: a = still_run, d = az_tb · tick: a = WEAR, b = CANCEL
 * OUT: mỗi tick 3 byte: trạng thái, lý do, events. */
static void mode_fsm(uint32_t n, const uint8_t *p)
{
    safety_cfg_t c;
    uint32_t t0;
    safety_default_cfg(&c);
    c.t_score = p[0];
    c.tilt_en = p[1];
    memcpy(&t0, p + 4, 4);
    safety_init(&S, &c, t0);
    p += 8;
    for (uint32_t i = 0; i < n; i++, p += 12) {
        int16_t d;
        uint32_t t;
        memcpy(&d, p + 4, 2);
        memcpy(&t, p + 8, 4);
        if (p[0] == 1) safety_on_result(&S, p[1], p[2]);
        else if (p[0] == 2) safety_on_block(&S, p[1], d);
        else {
            safety_tick(&S, t, p[1], p[2]);
            OUT_BASE[s_out++] = (uint8_t)S.st;
            OUT_BASE[s_out++] = S.why;
            OUT_BASE[s_out++] = S.events;
        }
    }
}

/* ---------------- mode 6: khối bất động trên chuỗi mẫu thô ----------------
 * IN: n mẫu × 6 INT16. OUT: mỗi khối đóng 4 byte: still, still_run, az_tb (i16 LE). */
static void mode_blocks(uint32_t n, const int16_t *raw)
{
    blocks_t b;
    blocks_cfg_t bc = { T_STILL_A, T_STILL_G };
    blocks_init(&b, &bc);
    for (uint32_t i = 0; i < n; i++) {
        if (blocks_push(&b, &raw[i * PRE_CH])) {
            OUT_BASE[s_out++] = b.still;
            OUT_BASE[s_out++] = b.still_run;
            out_bytes(&b.az_tb, 2);
        }
    }
}

/* ---------------- mode 7: CNN thuần trên MCU (FW-15) ----------------
 * IN: [n_layers][head_gap][score_shift][0] u8×4; mỗi lớp [oc u16][ic u16][shift u32]; [F u32][nvec u32];
 *     rồi weight INT8 (thứ tự E1, đệm tới bội 4), bias INT32 (các lớp rồi Dense), rồi nvec × 768 byte.
 * OUT: mỗi cửa sổ 4 logit INT32 LE, lớp, SCORE, 2 byte trống = 20 byte. */
#include "cnn_mcu.h"
#include "app_core.h"
#include "gyro_cal.h"

/* Đọc mô hình: [n_layers][head_gap][score_shift][0]; mỗi lớp [oc u16][ic u16][shift u32]; [F u32][nvec u32];
 * weight INT8 (thứ tự E1, đệm tới bội 4); bias INT32. Trả về con trỏ ngay sau bias; *nvec = trường nvec. */
static const uint8_t *parse_model(const uint8_t *p, cnn_model_t *m, uint32_t *nvec)
{
    uint32_t F, nw = 0, nb = 0;
    m->n_layers = p[0];
    m->head_gap = p[1];
    m->score_shift = p[2];
    p += 4;
    for (int i = 0; i < m->n_layers; i++, p += 8) {
        memcpy(&m->L[i].oc, p, 2);
        memcpy(&m->L[i].ic, p + 2, 2);
        m->L[i].shift = p[4];
        nw += (uint32_t)m->L[i].oc * m->L[i].ic * 5u;
        nb += m->L[i].oc;
    }
    memcpy(&F, p, 4);
    memcpy(nvec, p + 4, 4);
    p += 8;
    m->F = (uint16_t)F;
    const int8_t *w = (const int8_t *)p;
    for (int i = 0; i < m->n_layers; i++) {
        m->L[i].w = w;
        w += m->L[i].oc * m->L[i].ic * 5;
    }
    m->wd = w;
    nw += 4u * F;
    p += (nw + 3u) & ~3u;
    const int32_t *b = (const int32_t *)p;
    for (int i = 0; i < m->n_layers; i++) {
        m->L[i].b = b;
        b += m->L[i].oc;
    }
    m->bd = b;
    return p + 4u * (nb + 4u);
}

/* ---------------- mode 7: CNN thuần trên MCU (FW-15) ----------------
 * IN: mô hình (parse_model) rồi nvec × 768 byte. OUT: mỗi cửa sổ 4 logit INT32 LE, lớp, SCORE, 2 byte trống. */
static void mode_cnn(const uint8_t *p)
{
    cnn_model_t m;
    uint32_t nvec;
    p = parse_model(p, &m, &nvec);
    for (uint32_t v = 0; v < nvec; v++) {
        int32_t lg[4];
        uint8_t sc;
        int cls = cnn_mcu_run(&m, (const int8_t *)(p + v * 768u), lg, &sc);
        out_bytes(lg, 16);
        OUT_BASE[s_out++] = (uint8_t)cls;
        OUT_BASE[s_out++] = sc;
        s_out += 2;
    }
}

/* ---------------- mode 8: cả lõi firmware (app_core) với cnn_mcu đứng thay FPGA ----------------
 * IN: mô hình (nvec = 0) rồi [n_raw u32][t_score u8][tilt_en u8][lat_ticks u8][0][gyro_off i16 ×3][0 ×2]
 *     rồi n_raw × 6 INT16 (100 Hz, một mẫu mỗi tick 10 ms), rồi n_raw byte CANCEL (1 = đang nhấn). WEAR = 1.
 * OUT: 'R' SEQ CLASS SCORE (kết quả, ghi lúc khung được gửi); 'S' t(u32) trạng thái lý do (mỗi lần đổi trạng thái). */
static app_t A;
static int8_t s_win[768];

static void mode_app(const uint8_t *p)
{
    cnn_model_t m;
    uint32_t nvec, n_raw;
    safety_cfg_t sc;
    blocks_cfg_t bc = { T_STILL_A, T_STILL_G };
    int16_t off[3];
    p = parse_model(p, &m, &nvec);
    memcpy(&n_raw, p, 4);
    safety_default_cfg(&sc);
    sc.t_score = p[4];
    sc.tilt_en = p[5];
    uint32_t lat = p[6];
    memcpy(off, p + 8, 6);
    p += 16;
    const int16_t *raw = (const int16_t *)p;
    const uint8_t *cancel = p + 12u * n_raw;
    app_init(&A, &sc, &bc, 0);
    app_set_gyro_offset(&A, off);
    int pend = 0;
    uint32_t due = 0;
    spi_result_t res;
    for (uint32_t k = 0; k < n_raw; k++) {
        uint32_t t = 10u * k;
        if (pend && due <= k) {
            app_on_result(&A, SPI_OK, &res);
            pend = 0;
        }
        if (app_on_raw(&A, &raw[k * 6]) & APP_FRAME) {
            const int8_t *s1, *s2;
            uint16_t n1, n2;
            uint8_t seq = app_take_frame(&A, &s1, &n1, &s2, &n2);
            memcpy(s_win, s1, n1);
            memcpy(s_win + n1, s2, n2);
            memset(&res, 0, sizeof res);
            res.seq = seq;
            res.status = 0x01;
            res.cls = (uint8_t)cnn_mcu_run(&m, s_win, 0, &res.score);
            pend = 1;
            due = k + lat;
            OUT_BASE[s_out++] = 'R';
            OUT_BASE[s_out++] = seq;
            OUT_BASE[s_out++] = res.cls;
            OUT_BASE[s_out++] = res.score;
        }
        app_tick(&A, t, 1, cancel[k]);
        if (A.fsm.events & SAFETY_EV_STATE) {
            OUT_BASE[s_out++] = 'S';
            out_bytes(&t, 4);
            OUT_BASE[s_out++] = (uint8_t)A.fsm.st;
            OUT_BASE[s_out++] = A.fsm.why;
        }
    }
}

/* ---------------- mode 10: lõi firmware với khung kết quả của RTL (mô phỏng ghép, tools/cosim.py) ----------------
 * IN: [n_raw u32][n_res u32][t_score u8][tilt_en u8][lat_ticks u8][0] rồi n_raw × 6 INT16, rồi n_res × 20 byte
 *     (khung đọc v3 do RTL trả, theo thứ tự cửa sổ). Mỗi cửa sổ lấy một khung, kiểm bằng spi_parse_v3 như trên board.
 * OUT: 'R' SEQ rc CLASS SCORE ; 'S' t(u32) trạng thái lý do. */
static void mode_app_rtl(const uint8_t *p)
{
    uint32_t n_raw, n_res, used = 0;
    safety_cfg_t sc;
    blocks_cfg_t bc = { T_STILL_A, T_STILL_G };
    int16_t zero[3] = { 0, 0, 0 };
    memcpy(&n_raw, p, 4);
    memcpy(&n_res, p + 4, 4);
    safety_default_cfg(&sc);
    sc.t_score = p[8];
    sc.tilt_en = p[9];
    uint32_t lat = p[10];
    const int16_t *raw = (const int16_t *)(p + 12);
    const uint8_t *res_frames = p + 12 + 12u * n_raw;
    app_init(&A, &sc, &bc, 0);
    app_set_gyro_offset(&A, zero);
    int pend = 0, prc = 0;
    uint32_t due = 0;
    spi_result_t res;
    for (uint32_t k = 0; k < n_raw; k++) {
        uint32_t t = 10u * k;
        if (pend && due <= k) {
            app_on_result(&A, prc, &res);
            pend = 0;
        }
        if (app_on_raw(&A, &raw[k * 6]) & APP_FRAME) {
            const int8_t *s1, *s2;
            uint16_t n1, n2;
            uint8_t seq = app_take_frame(&A, &s1, &n1, &s2, &n2);
            memset(&res, 0, sizeof res);
            prc = (used < n_res) ? spi_parse_v3(res_frames + 20u * used, 20, seq, &res) : SPI_E_TIMEOUT;
            used++;
            pend = 1;
            due = k + lat;
            OUT_BASE[s_out++] = 'R';
            OUT_BASE[s_out++] = seq;
            OUT_BASE[s_out++] = (uint8_t)prc;
            OUT_BASE[s_out++] = res.cls;
            OUT_BASE[s_out++] = res.score;
        }
        app_tick(&A, t, 1, 0);
        if (A.fsm.events & SAFETY_EV_STATE) {
            OUT_BASE[s_out++] = 'S';
            out_bytes(&t, 4);
            OUT_BASE[s_out++] = (uint8_t)A.fsm.st;
            OUT_BASE[s_out++] = A.fsm.why;
        }
    }
}

/* ---------------- mode 9: hiệu chuẩn gyro (FW-05) ----------------
 * IN: n mẫu × 6 INT16. OUT: [done u8][0][restarts u16][n_used u16][off i16 ×3] = 12 byte. */
static void mode_gcal(uint32_t n, const int16_t *raw)
{
    gyro_cal_t g;
    uint32_t used = 0;
    gyro_cal_init(&g);
    for (uint32_t i = 0; i < n && !g.done; i++, used++)
        gyro_cal_push(&g, &raw[i * 6]);
    OUT_BASE[s_out++] = g.done;
    OUT_BASE[s_out++] = 0;
    out_bytes(&g.restarts, 2);
    uint16_t u = (uint16_t)used;
    out_bytes(&u, 2);
    out_bytes(g.off, 6);
}

/* ---------------- mode 11: lõi ESP32 (hub.c) với FPGA giả lập, phần cứng nối cố định theo codecanthiet ----------------
 * IN: mô hình (như mode 8) rồi [n_bytes u32][t_score u8][tilt_en u8][engine_ms u8][0] rồi n_bytes byte luồng UART của MCU
 *     (khung node_link + dòng chữ xen giữa). Mỗi mẫu tách được là một khe 10 ms: hub_sample, hub_tick, rồi hỏi vòng
 *     ở các mili giây 1..9. FPGA giả lập: nhận khung ghi v3, kiểm CRC-16, chạy cnn_mcu, có kết quả sau engine_ms,
 *     trả toàn 0 khi chưa có (như spi_result_tx_v3.v).
 * OUT: 'R' SEQ CLASS SCORE (lúc FPGA nhận khung); 'S' t(u32) trạng thái lý do; cuối cùng 'T' 6 × u32:
 *      mẫu, khung gửi, OK, timeout, lỗi, bỏ qua; rồi 'L' u32 số dòng chữ, u32 số khung hỏng. */
#include "hub.h"
#include "node_link.h"
static hub_t H;
static node_rx_t NR;
static struct {
    cnn_model_t *m;
    uint32_t now, ready_at;
    uint8_t  has, rd[7];
    uint8_t  bad_crc;
} FS;

static void fs_write(const uint8_t *b, uint16_t n, void *ctx)
{
    (void)ctx;
    if (n != SPI_FRAME_V3 || b[0] != SPI_HDR_WRITE ||
        crc16_ccitt(b, SPI_FRAME_V3 - 2) != (uint16_t)((b[SPI_FRAME_V3 - 2] << 8) | b[SPI_FRAME_V3 - 1])) {
        FS.bad_crc++;
        return;
    }
    uint8_t score;
    uint8_t cls = (uint8_t)cnn_mcu_run(FS.m, (const int8_t *)&b[2], 0, &score);
    FS.rd[0] = SPI_HDR_READ; FS.rd[1] = b[1]; FS.rd[2] = 0x01; FS.rd[3] = cls; FS.rd[4] = score;
    uint16_t c = crc16_ccitt(FS.rd, 5);
    FS.rd[5] = (uint8_t)(c >> 8); FS.rd[6] = (uint8_t)c;
    FS.has = 1;
    FS.ready_at = FS.now;
    OUT_BASE[s_out++] = 'R';
    OUT_BASE[s_out++] = b[1];
    OUT_BASE[s_out++] = cls;
    OUT_BASE[s_out++] = score;
}

static void fs_read(uint8_t *b, uint8_t n, void *ctx)
{
    (void)ctx;
    memset(b, 0, n);
    if (FS.has && FS.now >= FS.ready_at) {          /* chốt lúc CS xuống: đọc trọn khung */
        memcpy(b, FS.rd, n < 7 ? n : 7);
        FS.has = 0;
    }
}

static void mode_hub(const uint8_t *p)
{
    cnn_model_t m;
    uint32_t nvec, nb;
    p = parse_model(p, &m, &nvec);
    memcpy(&nb, p, 4);
    uint8_t t_score = p[4], tilt = p[5], eng = p[6];
    p += 8;
    FS.m = &m;
    hub_io_t io = { fs_write, fs_read, 0 };
    hub_init(&H, 0);
    H.app.fsm.cfg.t_score = t_score;
    H.app.fsm.cfg.tilt_en = tilt;
    node_rx_init(&NR);
    uint32_t k = 0, n_text = 0;
    for (uint32_t i = 0; i < nb; i++) {
        int e = node_rx_byte(&NR, p[i]);
        if (e == NODE_TEXT) { n_text++; continue; }
        if (e != NODE_SAMPLE) continue;
        uint32_t t = 10u * k;
        FS.now = t;
        hub_sample(&H, &io, NR.r, NR.keys, t);
        if (FS.has) FS.ready_at = t + eng;
        hub_tick(&H, t, 0);
        if (H.app.fsm.events & SAFETY_EV_STATE) {
            OUT_BASE[s_out++] = 'S';
            out_bytes(&t, 4);
            OUT_BASE[s_out++] = (uint8_t)H.app.fsm.st;
            OUT_BASE[s_out++] = H.app.fsm.why;
        }
        for (uint32_t ms = 1; ms < 10; ms++) {
            FS.now = t + ms;
            (void)hub_poll(&H, &io, t + ms);
        }
        k++;
    }
    OUT_BASE[s_out++] = 'T';
    uint32_t st[6] = { H.n_samples, H.n_sent, H.n_ok, H.n_timeout, H.n_err, H.n_skip };
    out_bytes(st, sizeof st);
    OUT_BASE[s_out++] = 'L';
    out_bytes(&n_text, 4);
    out_bytes(&NR.n_bad, 4);
}

/* ---------------- mode 12: node_link: đóng gói (MCU) rồi tách (ESP32) ----------------
 * IN: n mẫu × [seq u8][keys u8][6 × INT16] (14 byte), rồi [m u32] và m byte luồng bất kỳ để tách.
 * OUT: n khung đóng gói nối nhau (n × 21 byte), rồi các sự kiện tách: 'D' seq keys 6 × INT16 | 'T' len chữ | 'B';
 *      cuối cùng 'Z' n_lost u32. */
static void mode_node(uint32_t n, const uint8_t *p)
{
    for (uint32_t i = 0; i < n; i++, p += 14) {
        int16_t r[6];
        memcpy(r, p + 2, 12);
        s_out += node_pack_sample(&OUT_BASE[s_out], p[0], r, p[1]);
    }
    uint32_t m;
    memcpy(&m, p, 4);
    p += 4;
    node_rx_init(&NR);
    for (uint32_t i = 0; i < m; i++) {
        int e = node_rx_byte(&NR, p[i]);
        if (e == NODE_SAMPLE) {
            OUT_BASE[s_out++] = 'D'; OUT_BASE[s_out++] = NR.rx_seq; OUT_BASE[s_out++] = NR.keys;
            out_bytes(NR.r, 12);
        } else if (e == NODE_TEXT) {
            uint8_t len = (uint8_t)strlen(NR.line);
            OUT_BASE[s_out++] = 'T'; OUT_BASE[s_out++] = len;
            out_bytes(NR.line, len);
        } else if (e == NODE_BAD) {
            OUT_BASE[s_out++] = 'B';
        }
    }
    OUT_BASE[s_out++] = 'Z';
    out_bytes(&NR.n_lost, 4);
}

/* ---------------- mode 13: nhận dạng tư thế (A.11, đối chiếu ml/src/posture_model.py) ----------------
 * IN: n bản ghi, mỗi bản ghi [len u32] rồi len mẫu × 6 INT16; posture_init ở đầu mỗi bản ghi.
 * OUT: mỗi mẫu 1 byte tư thế; cuối mỗi bản ghi v, h, dh_cuoi (i64 LE) và ngoi. */
static void mode_posture(uint32_t n, const uint8_t *p)
{
    posture_t ps;
    for (uint32_t k = 0; k < n; k++) {
        uint32_t len;
        memcpy(&len, p, 4);
        p += 4;
        posture_init(&ps);
        for (uint32_t i = 0; i < len; i++, p += 12) {
            int16_t r[6];
            memcpy(r, p, 12);
            (void)posture_push(&ps, r);
            OUT_BASE[s_out++] = ps.tt;
        }
        out_bytes(&ps.v, 8);
        out_bytes(&ps.h, 8);
        out_bytes(&ps.dh_cuoi, 8);
        OUT_BASE[s_out++] = ps.ngoi;
    }
}

int main(void)
{
    uint32_t mode, n;
    memcpy(&mode, IN_BASE, 4);
    memcpy(&n, IN_BASE + 4, 4);
    const void *data = IN_BASE + 8;
    s_out = 0;
    switch (mode) {
    case 1: mode_pre(n, (const int16_t *)data); break;
    case 2: mode_parse(n, (const uint8_t *)data); break;
    case 3: mode_consts(n, (const int32_t *)data); break;
    case 4: mode_safety(); break;
    case 5: mode_fsm(n, (const uint8_t *)data); break;
    case 6: mode_blocks(n, (const int16_t *)data); break;
    case 7: mode_cnn((const uint8_t *)data); break;
    case 8: mode_app((const uint8_t *)data); break;
    case 9: mode_gcal(n, (const int16_t *)data); break;
    case 10: mode_app_rtl((const uint8_t *)data); break;
    case 11: mode_hub((const uint8_t *)data); break;
    case 12: mode_node(n, (const uint8_t *)data); break;
    case 13: mode_posture(n, (const uint8_t *)data); break;
    default: put("mode?\n"); break;
    }
    MBOX_EXIT = s_out;
    for (;;) { }
}
