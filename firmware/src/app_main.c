/*
 * app_main.c — vòng lặp chính của mũ (PROJECT_MASTER.md mục 4.3, A.9, A.10). Không RTOS; ngắt chỉ đặt cờ.
 *
 * Khởi động: clock 48 MHz, UART, watchdog → giữ SW3: menu chẩn đoán (diag.c) → I2C0 + MPU6050 (A.1, đọc lại 7 thanh
 * ghi) → hiệu chuẩn gyro 2 s (đứng yên) → SPI tới FPGA → tự kiểm khung LFSR (A.10, SEQ 0xEE) → chế độ:
 *   RUN (mặc định): mỗi kết quả in  t_ms,seq,class,score,state,err   ; mỗi lần đổi trạng thái in  S,t_ms,state,why
 *   LOG (giữ SW6 lúc khởi động, hoặc lệnh "LOG"): mỗi mẫu  t_ms,ax,ay,az,gx,gy,gz,btn,wear  (gyro đã trừ offset)
 *   TRC (lệnh "TRC"): như LOG, thêm  F,seq,crc  cho mỗi khung đã gửi (tools/check_frames.py dựng lại và so CRC)
 *   HIL (lệnh "HIL"): PC gửi khung ghi 772 byte, MCU chuyển sang FPGA, trả nguyên 20 byte khung đọc (tools/hil_test.py)
 *   lệnh "RUN", "DIAG" (menu chẩn đoán), "STAT" (đếm lỗi)
 * Mất mẫu: khoảng cách hai ngắt cảm biến ≥ 15 ms (A.9). PROTO 1 / 3 chọn bằng FW_PROTO bên dưới.
 */
#include <string.h>
#include "SN32F400.h"
#include "board.h"
#include "fw_config.h"
#include "i2c0.h"
#include "imu.h"
#include "gyro_cal.h"
#include "app_core.h"
#include "spi_fpga.h"
#include "spi_frame.h"
#include "crc.h"
/* FW_BITSTREAM, FW_PROTO: fw_config.h (mặc định 3 = project chính fpga/). */
#if FW_BITSTREAM == 3
#include "selftest_expect_v3_e2_n2.h"
#else
#include "selftest_expect.h"
#endif
#define I2C_HZ       400000u    /* hạ 100000 nếu sườn lên chậm với cáp dài (E.1) */

void diag_run(void);

enum { M_RUN, M_LOG, M_TRC, M_HIL };
static app_t   s_app;
static uint8_t s_mode = M_RUN;
static uint32_t s_lost, s_t_last;
static char    s_cmd[8];
static uint8_t s_cmd_n;

static void put_kv(const char *k, int32_t v) { uart_puts(k); uart_put_dec(v); }

static void log_sample(uint32_t t, const int16_t r[6], uint8_t btn, uint8_t wear)
{
    uart_put_dec((int32_t)t);
    for (int c = 0; c < 6; c++) { uart_putc(','); uart_put_dec(r[c]); }
    uart_putc(','); uart_put_dec(btn);
    uart_putc(','); uart_put_dec(wear);
    uart_puts("\n");
}

/* ---------- A.10: tự kiểm khi bật nguồn ---------- */
static int selftest(void)
{
    static int8_t pl[PRE_BYTES];
    spi_result_t r;
    uint8_t raw[SPI_READ_HIL];
    spi_selftest_payload(pl);
    int rc = spi_fpga_transact(SEQ_SELFTEST, pl, PRE_BYTES, pl, 0, FW_PROTO == 1 ? SPI_READ_V1 : SPI_READ_RUN, &r, raw);
    int ok;
    if (FW_PROTO == 1)
        ok = (rc == SPI_OK && r.cls == SELFTEST_CLASS && r.score32 == selftest_logits[SELFTEST_CLASS]);
    else
        ok = (rc == SPI_OK && memcmp(raw, selftest_frame7, 7) == 0);
    put_kv("tu kiem FPGA (A.10): rc=", rc); put_kv(" class=", r.cls);
    uart_puts(ok ? "  PASS\n" : "  FAIL\n");
    return ok;
}

/* ---------- HIL (FW-13): PC → MCU → FPGA → PC ---------- */
static void hil_loop(void)
{
    static uint8_t f[SPI_FRAME_V3];
    uart_puts("HIL: gui khung 772 byte; 'Q' de thoat\n");
    for (;;) {
        board_wdt_feed();
        int b = uart_getc();
        if (b < 0) continue;
        if (b == 'Q') { uart_puts("thoat HIL\n"); return; }
        if (b != SPI_HDR_WRITE) continue;
        f[0] = (uint8_t)b;
        uint32_t t0 = board_millis();
        uint16_t n = 1;
        while (n < SPI_FRAME_V3 && board_millis() - t0 < 200u) {
            int c = uart_getc();
            if (c >= 0) f[n++] = (uint8_t)c;
        }
        uint8_t out[SPI_READ_HIL];
        memset(out, 0, sizeof out);
        if (n == SPI_FRAME_V3 && crc16_ccitt(f, SPI_FRAME_V3) == 0) {    /* khung PC gửi phải nguyên vẹn */
            spi_result_t r;
            (void)spi_fpga_transact(f[1], (const int8_t *)&f[2], PRE_BYTES, (const int8_t *)f, 0, SPI_READ_HIL, &r, out);
        } else {
            out[0] = 0xEE;                                                 /* báo PC: khung UART hỏng */
            out[1] = (uint8_t)n;
        }
        for (int i = 0; i < SPI_READ_HIL; i++) uart_putc((char)out[i]);
    }
}

static void command(const char *c, uint32_t now)
{
    if (!strcmp(c, "RUN"))       { s_mode = M_RUN; uart_puts("# RUN\n"); }
    else if (!strcmp(c, "LOG"))  { s_mode = M_LOG; uart_puts("# LOG\n"); }
    else if (!strcmp(c, "TRC"))  { s_mode = M_TRC; uart_puts("# TRC\n"); }
    else if (!strcmp(c, "HIL"))  { hil_loop(); }
    else if (!strcmp(c, "DIAG")) { diag_run(); }
    else if (!strcmp(c, "STAT")) {
        put_kv("# t_ms=", (int32_t)now); put_kv(" raw=", (int32_t)s_app.n_raw); put_kv(" frames=", (int32_t)s_app.n_frames);
        put_kv(" ok=", (int32_t)s_app.n_ok); put_kv(" err=", (int32_t)s_app.n_err); put_kv(" lost=", (int32_t)s_lost);
        put_kv(" timeout=", (int32_t)g_spi_stats.timeouts); put_kv(" crc=", (int32_t)g_spi_stats.crc_err);
        put_kv(" rst=", (int32_t)g_spi_stats.resets); put_kv(" uart_rx_ovf=", (int32_t)g_uart_rx_overflow);
        uart_puts("\n");
    }
}

static void poll_uart(uint32_t now)
{
    int b;
    while ((b = uart_getc()) >= 0) {
        if (b == '\n' || b == '\r') {
            if (s_cmd_n) { s_cmd[s_cmd_n] = 0; command(s_cmd, now); s_cmd_n = 0; }
        } else if (s_cmd_n < sizeof s_cmd - 1) {
            s_cmd[s_cmd_n++] = (char)b;
        }
    }
}

int main(void)
{
    int16_t r[6];
    uint8_t who = 0;

    board_init();
    board_wdt_init();
    uart_puts("\n# mu bao ho - firmware chinh (" __DATE__ " " __TIME__ ")\n");
    board_delay_ms(30);
    if (keys_raw() & KEY_SW3)
        diag_run();
    if (keys_raw() & KEY_SW6)
        s_mode = M_LOG;

    /* ---- cảm biến (FW-04) ---- */
    i2c0_init(I2C_HZ);
    int bad;
    while ((bad = imu_init(&who)) != 0) {
        put_kv("# MPU6050 loi: WHO_AM_I=0x", 0); uart_put_hex(who, 2); put_kv(" thanh ghi sai=", bad);
        put_kv(" i2c=", i2c0_last_error()); uart_puts("\n");
        board_led(1); board_delay_ms(250); board_wdt_feed();      /* feed mỗi 250 ms; WDT ≈ 1 s nếu ILRC 32 kHz */
        board_led(0); board_delay_ms(250); board_wdt_feed();
    }
    uart_puts("# MPU6050 OK: WHO_AM_I=0x68, 7 thanh ghi doc lai dung\n");
    board_p2_irq_enable(1UL << 2);

    /* ---- hiệu chuẩn gyro (FW-05) ---- */
    gyro_cal_t gc;
    gyro_cal_init(&gc);
    uint32_t t_hint = board_millis();
    while (!gc.done) {
        board_wdt_feed();
        if (g_imu_int) {
            g_imu_int = 0;
            t_hint = board_millis();
            if (imu_read(r) == 0) gyro_cal_push(&gc, r);
        } else if (board_millis() - t_hint >= 2000u) {     /* không có ngắt: dây INT chưa nối thì báo thay vì đứng im */
            t_hint = board_millis();
            uart_puts("# cho ngat INT cua MPU6050 (P2.2, J7): 2 s khong co mau - kiem day INT\n");
        }
    }
    put_kv("# gyro_off,", gc.off[0]); put_kv(",", gc.off[1]); put_kv(",", gc.off[2]);
    put_kv(" lam_lai=", gc.restarts); uart_puts("\n");

    /* ---- FPGA (FW-08, A.10) ---- */
    spi_fpga_init(SPI_DIV_RUN, FW_PROTO);
    int st_ok = selftest();

    safety_cfg_t sc;
    blocks_cfg_t bc = { T_STILL_A, T_STILL_G };
    safety_default_cfg(&sc);
    app_init(&s_app, &sc, &bc, board_millis());
    app_set_gyro_offset(&s_app, gc.off);
    if (!st_ok) s_app.err_flag = 1;
    uart_puts("# start\n");

    uint32_t t_tick = board_millis();
    s_t_last = t_tick;
    uint8_t keys = 0;
    for (;;) {
        uint32_t now = board_millis();
        board_wdt_feed();

        /* 1. mẫu cảm biến */
        if (g_imu_int) {
            g_imu_int = 0;
            if (now - s_t_last >= 15u) s_lost++;
            s_t_last = now;
            if (imu_read(r) == 0) {
                unsigned f = app_on_raw(&s_app, r);
                if (s_mode == M_LOG || s_mode == M_TRC) {
                    int16_t rc[6];
                    for (int c = 0; c < 6; c++) rc[c] = (int16_t)(r[c] - (c >= 3 ? gc.off[c - 3] : 0));
                    log_sample(now, rc, (keys & KEY_SW6) != 0, (uint8_t)board_wear());
                }
                /* 2. đủ 16 mẫu 50 Hz → gửi khung thẳng từ ring */
                if ((f & APP_FRAME) && s_mode != M_LOG) {          /* SEQ tăng theo cửa sổ, kể cả khi bỏ qua */
                    const int8_t *s1, *s2;
                    uint16_t n1, n2;
                    uint8_t seq = app_take_frame(&s_app, &s1, &n1, &s2, &n2);
                    if (!spi_fpga_busy()) {
                        uint16_t crc = spi_fpga_start(seq, s1, n1, s2, n2);
                        if (s_mode == M_TRC) {
                            uart_puts("F,"); uart_put_dec(seq); uart_putc(','); uart_put_hex(crc, 4); uart_puts("\n");
                        }
                    } else if (s_mode == M_TRC) {
                        uart_puts("X,"); uart_put_dec(seq); uart_puts("\n");        /* FPGA còn bận: bỏ cửa sổ */
                    }
                }
            }
        }

        /* 3. kết quả FPGA */
        spi_result_t res = { 0 };
        int rc = spi_fpga_poll(now, SPI_READ_RUN, &res, 0);
        if (rc != SPI_PENDING) {
            app_on_result(&s_app, rc, &res);
            if (s_mode == M_RUN) {
                uart_put_dec((int32_t)now); uart_putc(','); uart_put_dec(res.seq); uart_putc(',');
                uart_put_dec(rc == SPI_OK ? res.cls : -1); uart_putc(','); uart_put_dec(res.score); uart_putc(',');
                uart_puts(safety_state_name(s_app.fsm.st)); uart_putc(','); uart_put_dec(rc); uart_puts("\n");
            }
        }

        /* 4–5. khe 10 ms: phím, WEAR, Safety FSM, còi, LED */
        if (now - t_tick >= 10u) {
            t_tick += 10u;
            keys = keys_scan(now);
            app_tick(&s_app, now, (uint8_t)board_wear(), (keys & KEY_SW3) != 0);
            if ((s_app.fsm.events & SAFETY_EV_STATE) && s_mode == M_RUN) {
                put_kv("S,", (int32_t)now); uart_putc(','); uart_puts(safety_state_name(s_app.fsm.st));
                put_kv(",", s_app.fsm.why); uart_puts("\n");
            }
            board_buzzer(app_buzzer(&s_app, now));
            board_led(app_led(&s_app, now));
            uint8_t seg[4];
            app_display(&s_app, now, seg);
            board_seg7(seg);
        }

        /* 7. lệnh UART */
        poll_uart(now);
    }
}
