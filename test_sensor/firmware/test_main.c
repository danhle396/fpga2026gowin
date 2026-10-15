/*
 * test_main.c — firmware kiểm tra MPU6050 trên MCU (SN32F407).
 *
 * Khi khởi động, chạy lần lượt T1..T7 và in báo cáo qua UART (460800 8N1):
 *     # T3 WHO_AM_I       : 0x68 -> PASS
 * Sau đó in luồng CSV 100 Hz đúng định dạng chế độ LOG (SPEC 2.9):
 *     t_ms,ax,ay,az,gx,gy,gz,btn
 * Dòng bắt đầu bằng '#' là báo cáo, tools/sensor_check.py dựa vào đó để chấm.
 * Nhấn RESET trên board để chạy lại toàn bộ.
 *
 * LED: sáng liên tục = mọi test PASS và đang stream; nháy chậm = có WARN/FAIL
 * nhưng vẫn stream được; nháy nhanh = lỗi nặng, tự thử lại sau 2 s.
 */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "board_port.h"
#include "i2c_soft.h"
#include "mpu6050.h"

#define CALIB_SAMPLES   200     /* Bước 4.1: trung bình 200 mẫu gyro khi để yên */

typedef enum { R_PASS, R_WARN, R_FAIL } result_t;

static int     n_pass, n_warn, n_fail;
static int     int_pin_ok;      /* 1: dùng chân INT; 0: poll thanh ghi INT_STATUS */
static int16_t gyro_off[3];

/* ---------- in ra UART ---------- */

static void uart_write(const char *s)
{
    while (*s) board_uart_putc(*s++);
}

static void out(const char *fmt, ...)
{
    char buf[160];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    uart_write(buf);
}

static void report(const char *id, const char *name, result_t r, const char *fmt, ...)
{
    static const char *const txt[] = { "PASS", "WARN", "FAIL" };
    char detail[112];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(detail, sizeof(detail), fmt, ap);
    va_end(ap);
    out("# %s %-14s: %s -> %s\r\n", id, name, detail, txt[r]);
    if (r == R_PASS) n_pass++; else if (r == R_WARN) n_warn++; else n_fail++;
}

static const char *i2c_err_str(int e)
{
    switch (e) {
    case I2C_ERR_NACK_ADDR: return "NACK dia chi";
    case I2C_ERR_NACK_DATA: return "NACK du lieu";
    case I2C_ERR_TIMEOUT:   return "SCL bi giu thap";
    case I2C_ERR_BUS_LOW:   return "bus ket muc thap";
    case MPU_ERR_TIMEOUT:   return "het gio cho data-ready";
    default:                return "loi khac";
    }
}

/* ---------- tiện ích ---------- */

static uint32_t isqrt32(uint32_t x)
{
    uint32_t r = 0, bit = 1uL << 30;
    while (bit > x) bit >>= 2;
    while (bit) {
        if (x >= r + bit) { x -= r + bit; r = (r >> 1) + bit; }
        else              { r >>= 1; }
        bit >>= 2;
    }
    return r;
}

/* Độ lệch chuẩn từ tổng và tổng bình phương */
static uint32_t stddev(int64_t sum, int64_t sumsq, int32_t n)
{
    int64_t var = (sumsq - (sum * sum) / n) / n;
    if (var < 0) var = 0;
    if (var > 0x7FFFFFFF) var = 0x7FFFFFFF;
    return isqrt32((uint32_t)var);
}

static int16_t sat16(int32_t v)
{
    return (int16_t)(v > 32767 ? 32767 : (v < -32768 ? -32768 : v));
}

/* Chờ 1 mẫu mới rồi đọc 7 giá trị (AX AY AZ T GX GY GZ) */
static int wait_sample(int16_t v[7])
{
    if (int_pin_ok) {
        uint32_t t0 = board_millis();
        while (!board_int_read())
            if (board_millis() - t0 > 50u) return MPU_ERR_TIMEOUT;
    } else {
        int r = mpu_wait_ready(50);
        if (r) return r;
    }
    return mpu_read7(v);      /* INT_RD_CLEAR = 1: lệnh đọc này xóa luôn chân INT */
}

/* ---------- các bài test ---------- */

/* T1: bus I2C rảnh (SDA, SCL ở mức 1 sau khi gỡ treo) */
static int t1_bus(void)
{
    int r = i2c_bus_recover();
    if (r == I2C_OK) {
        report("T1", "BUS_IDLE", R_PASS, "SDA=1 SCL=1");
        return 0;
    }
    report("T1", "BUS_IDLE", R_FAIL, "SDA=%d SCL=%d (thieu pull-up / chap GND / sai chan)",
           board_sda_read(), board_scl_read());
    return -1;
}

/* T2: quét địa chỉ 0x08..0x77 */
static int t2_scan(void)
{
    char list[64] = "";
    int found68 = 0, found69 = 0, n = 0;
    uint8_t a;
    for (a = 0x08; a <= 0x77; a++) {
        if (i2c_probe(a) == I2C_OK) {
            if (n < 10) {
                size_t len = strlen(list);
                snprintf(list + len, sizeof(list) - len, "%s0x%02X", n ? " " : "", a);
            }
            n++;
            if (a == 0x68) found68 = 1;
            if (a == 0x69) found69 = 1;
        }
    }
    if (found68) {
        report("T2", "I2C_SCAN", R_PASS, "%d thiet bi: %s", n, list);
        return 0;
    }
    if (found69)
        report("T2", "I2C_SCAN", R_FAIL, "thay 0x69 -> chan AD0 dang o muc 1, noi AD0 xuong GND");
    else
        report("T2", "I2C_SCAN", R_FAIL, "%d thiet bi: %s (khong co 0x68)", n, n ? list : "-");
    return -1;
}

/* T3: WHO_AM_I phải là 0x68 */
static int t3_whoami(void)
{
    uint8_t id = 0;
    int r = mpu_who_am_i(&id);
    if (r) {
        report("T3", "WHO_AM_I", R_FAIL, "loi I2C: %s", i2c_err_str(r));
        return -1;
    }
    if (id == MPU_WHO_AM_I_VALUE) {
        report("T3", "WHO_AM_I", R_PASS, "0x%02X", id);
        return 0;
    }
    if (id == 0x70 || id == 0x71 || id == 0x72 || id == 0x73 || id == 0x98 || id == 0x19) {
        /* MPU6500/9250/clone: thanh ghi dữ liệu gần giống, vẫn chạy tiếp được */
        report("T3", "WHO_AM_I", R_WARN, "0x%02X: khong phai MPU6050 that (MPU6500/clone)", id);
        return 0;
    }
    report("T3", "WHO_AM_I", R_FAIL, "0x%02X (mong doi 0x68)", id);
    return -1;
}

/* T4: reset chip, ghi cấu hình SPEC 2.1, đọc lại từng thanh ghi */
static int t4_config(void)
{
    uint8_t reg = 0, got = 0;
    int r = mpu_reset();
    if (!r) r = mpu_init();
    if (r) {
        report("T4", "CONFIG", R_FAIL, "ghi loi: %s", i2c_err_str(r));
        return -1;
    }
    r = mpu_verify(&reg, &got);
    if (r == MPU_ERR_VERIFY) {
        report("T4", "CONFIG", R_FAIL, "doc lai 0x%02X = 0x%02X (khac gia tri da ghi)", reg, got);
        return -1;
    }
    if (r) {
        report("T4", "CONFIG", R_FAIL, "doc lai loi: %s", i2c_err_str(r));
        return -1;
    }
    report("T4", "CONFIG", R_PASS, "%lu thanh ghi doc lai dung", (unsigned long)mpu_cfg_len);
    return 0;
}

/* T5: self-test của chip (để yên cảm biến) */
static void t5_selftest(void)
{
    static const char *const ax[6] = { "AX", "AY", "AZ", "GX", "GY", "GZ" };
    mpu_selftest_t st;
    char buf[100] = "";
    int i, r = mpu_self_test(&st);
    if (r) {
        report("T5", "SELF_TEST", R_FAIL, "loi: %s", i2c_err_str(r));
        return;
    }
    for (i = 0; i < 6; i++) {
        int v = st.change_x10[i], a = v < 0 ? -v : v;
        size_t len = strlen(buf);
        snprintf(buf + len, sizeof(buf) - len, "%s%s%c%d.%d%%", i ? " " : "", ax[i],
                 v < 0 ? '-' : '+', a / 10, a % 10);
    }
    /* Nhiều module GY-521 dùng chip clone không đạt self-test dù đo vẫn đúng
       -> chỉ WARN; T7 và tools/sensor_check.py mới là kết luận cuối. */
    report("T5", "SELF_TEST", st.pass ? R_PASS : R_WARN, "%s (dat: |x|<=14%%)", buf);
}

/* T6: tần số mẫu qua chân INT (mong đợi 100 Hz = 200 xung / 2 s) */
static void t6_rate(void)
{
    int16_t v[7];
    uint32_t t0, edges = 0, polls = 0;
    int prev, lvl;

    (void)mpu_init();                 /* chắc chắn đúng cấu hình sau self-test */
    (void)mpu_read7(v);               /* xóa chốt INT */
    prev = board_int_read();
    t0 = board_millis();
    while (board_millis() - t0 < 2000u) {
        lvl = board_int_read();
        if (lvl && !prev) {
            edges++;
            (void)mpu_read7(v);
        }
        prev = lvl;
    }
    if (edges >= 194 && edges <= 206) {
        int_pin_ok = 1;
        report("T6", "SAMPLE_RATE", R_PASS, "INT: %lu xung/2s = %lu.%lu Hz",
               (unsigned long)edges, (unsigned long)(edges / 2), (unsigned long)(edges % 2 * 5));
        return;
    }

    /* Chân INT không đúng -> đo lại bằng cách poll INT_STATUS để biết lỗi do dây hay do chip */
    int_pin_ok = 0;
    t0 = board_millis();
    while (board_millis() - t0 < 2000u) {
        if (mpu_data_ready() > 0) {
            polls++;
            (void)mpu_read7(v);
        }
    }
    report("T6", "SAMPLE_RATE", R_FAIL,
           "INT: %lu xung/2s (mong doi 200); poll INT_STATUS: %lu mau/2s",
           (unsigned long)edges, (unsigned long)polls);
    if (polls >= 194 && polls <= 206)
        out("#    -> chip lay mau dung 100 Hz, loi o day/chan INT. Stream se dung che do poll.\r\n");
}

/* T7: hiệu chuẩn gyro + kiểm tra tĩnh (đặt cảm biến nằm yên trên bàn) */
static int t7_static(void)
{
    int16_t v[7];
    int64_t s_a[3] = { 0 }, s_g[3] = { 0 }, ss_g[3] = { 0 }, s_m = 0, ss_m = 0, s_t = 0;
    uint32_t sd_m, sd_g[3], mag;
    int32_t  mean_m, temp_x10, k;
    int i, r;

    for (i = 0; i < CALIB_SAMPLES; i++) {
        r = wait_sample(v);
        if (r) {
            report("T7", "STATIC", R_FAIL, "loi doc mau: %s", i2c_err_str(r));
            return -1;
        }
        for (k = 0; k < 3; k++) {
            s_a[k]  += v[k];
            s_g[k]  += v[4 + k];
            ss_g[k] += (int32_t)v[4 + k] * v[4 + k];
        }
        mag = isqrt32((uint32_t)((int32_t)v[0] * v[0]) + (uint32_t)((int32_t)v[1] * v[1]) +
                      (uint32_t)((int32_t)v[2] * v[2]));
        s_m  += mag;
        ss_m += (int64_t)mag * mag;
        s_t  += v[3];
    }

    for (k = 0; k < 3; k++) {
        gyro_off[k] = (int16_t)(s_g[k] / CALIB_SAMPLES);
        sd_g[k]     = stddev(s_g[k], ss_g[k], CALIB_SAMPLES);
    }
    mean_m   = (int32_t)(s_m / CALIB_SAMPLES);
    sd_m     = stddev(s_m, ss_m, CALIB_SAMPLES);
    temp_x10 = (int32_t)(s_t / CALIB_SAMPLES) * 10 / 340 + 365;     /* T = raw/340 + 36,53 °C */

    out("# T7 accel trung binh: ax=%ld ay=%ld az=%ld (LSB, 2048 = 1 g)\r\n",
        (long)(s_a[0] / CALIB_SAMPLES), (long)(s_a[1] / CALIB_SAMPLES), (long)(s_a[2] / CALIB_SAMPLES));

    /* Sai số zero-rate gyro theo datasheet: ±20 °/s = ±328 LSB ở ±2000 °/s */
    report("T7a", "GYRO_OFFSET",
           (gyro_off[0] > 328 || gyro_off[0] < -328 || gyro_off[1] > 328 || gyro_off[1] < -328 ||
            gyro_off[2] > 328 || gyro_off[2] < -328) ? R_WARN : R_PASS,
           "gx=%d gy=%d gz=%d LSB (se tru o moi mau)", gyro_off[0], gyro_off[1], gyro_off[2]);

    /* |a| khi đứng yên phải ≈ 1 g = 2048; chấp nhận ±10 % (zero-g offset + sai số độ nhạy) */
    report("T7b", "ACCEL_1G", (mean_m >= 1843 && mean_m <= 2253) ? R_PASS : R_FAIL,
           "|a|=%ld LSB = %ld.%02ld g", (long)mean_m, (long)(mean_m / 2048),
           (long)((mean_m % 2048) * 100 / 2048));

    report("T7c", "NOISE", (sd_m < 20 && sd_g[0] < 3 && sd_g[1] < 3 && sd_g[2] < 3) ? R_PASS : R_WARN,
           "std|a|=%lu std g=%lu/%lu/%lu LSB%s", (unsigned long)sd_m, (unsigned long)sd_g[0],
           (unsigned long)sd_g[1], (unsigned long)sd_g[2],
           (sd_m >= 20) ? " (bi rung? de yen roi RESET)" : "");

    report("T7d", "TEMP", (temp_x10 > 0 && temp_x10 < 600) ? R_PASS : R_WARN,
           "%ld.%ld C", (long)(temp_x10 / 10), (long)((temp_x10 < 0 ? -temp_x10 : temp_x10) % 10));
    return 0;
}

/* ---------- chương trình chính ---------- */

static int run_tests(void)
{
    n_pass = n_warn = n_fail = 0;
    int_pin_ok = 0;
    out("\r\n# ===== MPU6050 TEST (VKU-NewBie) =====\r\n");
    out("# De cam bien NAM YEN trong suot qua trinh test (~6 s)\r\n");

    if (t1_bus() || t2_scan() || t3_whoami() || t4_config())
        return -1;
    t5_selftest();
    t6_rate();
    if (t7_static())
        return -1;
    out("# SUMMARY pass=%d warn=%d fail=%d\r\n", n_pass, n_warn, n_fail);
    return 0;
}

static void stream(void)
{
    int16_t v[7];
    uint32_t t_ms, blink = 0;
    int r, errors = 0;

    out("# STREAM START (gyro da tru offset, int=%s)\r\n", int_pin_ok ? "pin" : "poll");
    out("# t_ms,ax,ay,az,gx,gy,gz,btn\r\n");
    for (;;) {
        r = wait_sample(v);
        t_ms = board_millis();
        if (r) {
            out("# ERR doc mau: %s\r\n", i2c_err_str(r));
            if (++errors >= 5) {                       /* lỗi liên tiếp: gỡ bus, cấu hình lại */
                (void)i2c_bus_recover();
                (void)mpu_init();
                errors = 0;
            }
            continue;
        }
        errors = 0;
        out("%lu,%d,%d,%d,%d,%d,%d,%d\r\n", (unsigned long)t_ms, v[0], v[1], v[2],
            sat16((int32_t)v[4] - gyro_off[0]), sat16((int32_t)v[5] - gyro_off[1]),
            sat16((int32_t)v[6] - gyro_off[2]), board_button_read() ? 1 : 0);

        if (n_warn || n_fail) board_led((++blink / 50) & 1);   /* nháy 1 Hz */
        else                  board_led(1);
    }
}

int main(void)
{
    int i;
    board_init();
    board_delay_ms(100);              /* MPU6050 cần ~30-100 ms sau khi cấp nguồn */

    while (run_tests() != 0) {
        out("# SUMMARY pass=%d warn=%d fail=%d\r\n# FATAL: sua loi roi cho, tu thu lai sau 2 s...\r\n",
            n_pass, n_warn, n_fail);
        for (i = 0; i < 20; i++) {    /* nháy nhanh 5 Hz trong 2 s */
            board_led(i & 1);
            board_delay_ms(100);
        }
    }
    stream();
    return 0;
}
