/*
 * app_main.c — SN32F407 là nút cảm biến của mũ (phần cứng nối cố định, đề cương v2.2): MCU không nối SPI/IRQ/RST_N với
 * FPGA, chỉ có UART TX P3.1 → ESP32 GPIO16 (115200 8N1). Không RTOS; ngắt chỉ đặt cờ.
 *
 * Khởi động: clock 48 MHz, UART, watchdog → I2C0 + MPU6050 (A.1, đọc lại 7 thanh ghi) → hiệu chuẩn gyro 2 s
 * (đứng yên) → vòng lặp: mỗi mẫu 100 Hz (MPU6050 báo bằng INT_STATUS, không có dây INT) trừ offset gyro rồi gửi một
 * khung node_link 21 byte (F1 7E ..., kèm trạng thái nút SW3/SW6). Tiền xử lý A.2, cửa sổ, khung v3 gửi FPGA, bỏ phiếu
 * + Safety FSM chạy trên ESP32 bằng cùng mã C (hub.c, esp32/mu_nga_hub).
 * Chữ in ra (dòng "# ...", STAT mỗi 5 s) đi cùng đường UART; ESP32 chuyển lên log với tiền tố "MCU ".
 * LED D6 nháy 1 Hz khi đang gửi mẫu; nháy nhanh 2 Hz khi MPU6050 lỗi.
 */
#include "SN32F400.h"
#include "board.h"
#include "fw_config.h"
#include "i2c0.h"
#include "imu.h"
#include "gyro_cal.h"
#include "node_link.h"

#define I2C_HZ  400000u     /* hạ 100000 nếu sườn lên chậm với cáp dài tới mũ (E.1) */

static void put_kv(const char *k, int32_t v) { uart_puts(k); uart_put_dec(v); }

/* Có mẫu mới: hỏi thanh ghi INT_STATUS của MPU6050 tối đa một lần mỗi mili giây (đọc xong thì cờ tự xóa). */
static int sample_ready(void)
{
    static uint32_t t_last;
    uint32_t now = board_millis();
    if (now == t_last) return 0;
    t_last = now;
    return imu_data_ready() == 1;
}

int main(void)
{
    int16_t r[6];
    uint8_t who = 0;

    board_init();
    board_wdt_init();
    uart_puts("\n# mu bao ho - MCU nut cam bien (" __DATE__ " " __TIME__ ")\n");
    put_kv("# HCLK=", (int32_t)SystemCoreClock); uart_puts("\n");

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

    /* ---- hiệu chuẩn gyro (FW-05): giữ mũ đứng yên ---- */
    gyro_cal_t gc;
    gyro_cal_init(&gc);
    uint32_t t_hint = board_millis();
    while (!gc.done) {
        board_wdt_feed();
        if (sample_ready()) {
            t_hint = board_millis();
            if (imu_read(r) == 0) gyro_cal_push(&gc, r);
        } else if (board_millis() - t_hint >= 2000u) {
            t_hint = board_millis();
            uart_puts("# MPU6050: 2 s khong co mau moi (INT_STATUS) - kiem I2C\n");
        }
    }
    put_kv("# gyro_off,", gc.off[0]); put_kv(",", gc.off[1]); put_kv(",", gc.off[2]);
    put_kv(" lam_lai=", gc.restarts); uart_puts("\n");
    uart_puts("# NODE: mau 100 Hz -> ESP32 (node_link F1 7E, 115200)\n");

    /* ---- gửi mẫu cho ESP32 ---- */
    uint8_t f[NODE_SAMPLE_FRAME], seq = 0, keys = 0;
    uint32_t t_tick = board_millis(), t_stat = t_tick, t_last = t_tick, n = 0, n_err = 0, n_lost = 0;
    for (;;) {
        uint32_t now = board_millis();
        board_wdt_feed();
        if (sample_ready()) {
            if (n && now - t_last >= 15u) n_lost++;                 /* A.9: hở ≥ 15 ms là mất mẫu */
            t_last = now;
            if (imu_read(r) == 0) {
                for (int c = 3; c < 6; c++) {                       /* trừ offset, bão hòa như app_core.c */
                    int32_t v = r[c] - gc.off[c - 3];
                    r[c] = (int16_t)(v > 32767 ? 32767 : v < -32768 ? -32768 : v);
                }
                uint16_t len = node_pack_sample(f, seq++, r, keys);
                for (uint16_t i = 0; i < len; i++) uart_putc((char)f[i]);
                n++;
            } else {
                n_err++;
            }
        }
        if (now - t_tick >= 10u) {                                  /* khe 10 ms: phím, LED */
            t_tick += 10u;
            uint8_t k = keys_scan(now);
            keys = (uint8_t)(((k & KEY_SW3) ? 1u : 0u) | ((k & KEY_SW6) ? 2u : 0u));
            board_led(((now / 500u) & 1u) != 0);
        }
        if (now - t_stat >= 5000u) {
            t_stat = now;
            put_kv("STAT,mau=", (int32_t)n); put_kv(",i2c_loi=", (int32_t)n_err); put_kv(",mat=", (int32_t)n_lost);
            uart_puts("\n");
        }
    }
}
