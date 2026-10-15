/*
 * diag.c — menu chẩn đoán (việc FW-03) kèm các phép thử của đợt B. Vào bằng cách giữ SW3 lúc khởi động, hoặc gửi
 * "DIAG" khi đang chạy (app_main.c). Terminal 460800 8N1 trên UART0.
 *
 *   Vào menu: in "hello", nháy LED D6 1 Hz, in mỗi lần nhấn/nhả SW3, SW6, tự kiểm CRC phần cứng.
 *   Lệnh một ký tự (q: về vòng lặp chính):
 *     h  trợ giúp
 *     f  phép thử flash ở E.4 bước 2: đọc mã JEDEC 0x9F với chân chọn P1.8, rồi P2.8, P2.9.  CHỈ chạy khi CHƯA nối FPGA
 *     c  CRC-16 phần cứng so với phần mềm: "123456789" (phải 0x29B1) và khung tự kiểm 772 byte
 *     1  / 4  SCK 1 MHz / 4 MHz          p  đổi PROTO 1 ↔ 3
 *     s  100 vòng ghi → IRQ → đọc bằng khung tự kiểm (FW-09 (a) khi PROTO = 1), in thống kê
 *     t  thời gian chạy và trạng thái phím
 *     w  đo chu kỳ WDT: ngừng feed, in ms mỗi 20 ms cho tới khi chip tự khởi động lại (mong đợi ≈ 1.024 ms)
 */
#include "SN32F400.h"
#include "board.h"
#include "crc.h"
#include "fw_config.h"
#include "spi_fpga.h"
#include "spi_frame.h"

static uint8_t s_div = SPI_DIV_TEST;
static uint8_t s_proto = 1;                     /* thông mạch lần đầu bằng RTL hiện có (A.7, PROTO = 1) */
static int8_t  s_payload[PRE_BYTES];

static void help(void)
{
    uart_puts("lenh: h f c 1 4 p s t w q   (xem dau diag.c)\n");
}

static void put_kv(const char *k, int32_t v)
{
    uart_puts(k);
    uart_put_dec(v);
}

/* ---------- c: CRC phần cứng ---------- */
static void crc_check(void)
{
    static const uint8_t ref[9] = { '1', '2', '3', '4', '5', '6', '7', '8', '9' };
    crc16_hw.reset();
    for (int i = 0; i < 9; i++) crc16_hw.feed(ref[i]);
    uint16_t hw = crc16_hw.result(), sw = crc16_ccitt(ref, 9);
    uart_puts("CRC \"123456789\": hw=0x"); uart_put_hex(hw, 4);
    uart_puts(" sw=0x"); uart_put_hex(sw, 4);
    uart_puts(hw == 0x29B1 ? " PASS\n" : " FAIL (mong doi 0x29B1)\n");

    crc16_hw.reset();
    crc16_sw.reset();
    crc16_hw.feed(SPI_HDR_WRITE); crc16_sw.feed(SPI_HDR_WRITE);
    crc16_hw.feed(SEQ_SELFTEST);  crc16_sw.feed(SEQ_SELFTEST);
    for (int i = 0; i < PRE_BYTES; i++) {
        crc16_hw.feed((uint8_t)s_payload[i]);
        crc16_sw.feed((uint8_t)s_payload[i]);
    }
    hw = crc16_hw.result();
    sw = crc16_sw.result();
    uart_puts("CRC khung tu kiem SEQ=0xEE: hw=0x"); uart_put_hex(hw, 4);
    uart_puts(" sw=0x"); uart_put_hex(sw, 4);
    uart_puts(hw == sw ? " PASS\n" : " FAIL\n");
}

/* ---------- f: E.4 bước 2 ---------- */
typedef struct { SN_GPIO0_Type *port; uint8_t bit; const char *name; } cs_pin_t;

static void flash_probe(void)
{
    const cs_pin_t pins[3] = {
        { (SN_GPIO0_Type *)SN_GPIO1, 8, "P1.8" },
        { (SN_GPIO0_Type *)SN_GPIO2, 8, "P2.8" },
        { (SN_GPIO0_Type *)SN_GPIO2, 9, "P2.9" },
    };
    uart_puts("E.4 buoc 2: JEDEC 0x9F, SCK 1 MHz. Chi chay khi CHUA noi FPGA.\n");
    spi_fpga_init(SPI_DIV_TEST, 3);
    for (int k = 0; k < 3; k++) {               /* mọi chân chọn ra mức cao trước */
        PIN_SET(pins[k].port, pins[k].bit);
        PIN_OUTPUT(pins[k].port, pins[k].bit);
    }
    for (int k = 0; k < 3; k++) {
        uint8_t id[3];
        PIN_CLR(pins[k].port, pins[k].bit);
        board_delay_us(5);
        (void)spi_fpga_xfer(0x9F);
        for (int i = 0; i < 3; i++) id[i] = spi_fpga_xfer(0x00);
        board_delay_us(5);
        PIN_SET(pins[k].port, pins[k].bit);
        int blank = (id[0] == id[1] && id[1] == id[2] && (id[0] == 0x00 || id[0] == 0xFF));
        uart_puts(pins[k].name);
        uart_puts(": JEDEC = ");
        for (int i = 0; i < 3; i++) { uart_put_hex(id[i], 2); uart_putc(' '); }
        uart_puts(blank ? "-> khong co flash\n" : "-> CO FLASH tren chan nay\n");
    }
    PIN_INPUT(SN_GPIO2, 9);                     /* trả P2.9 về làm IRQ */
    PIN_CFG(SN_GPIO2, 9, PIN_CFG_PULLDOWN);
    uart_puts("Ket luan: flash o P1.8 (hoac khong co) -> giu E.1. Flash o P2.8/P2.9 -> doi CS/IRQ truoc khi noi FPGA.\n");
}

/* ---------- s: vòng thử SPI ---------- */
static void spi_loop(int n)
{
    spi_result_t r;
    uint8_t raw[SPI_READ_HIL];
    spi_fpga_init(s_div, s_proto);
    g_spi_stats = (spi_fpga_stats_t){ 0 };
    put_kv("SPI: PROTO=", s_proto);
    put_kv(" DIV=", s_div);
    put_kv(" vong=", n);
    uart_putc('\n');
    for (int i = 0; i < n; i++) {
        int rc = spi_fpga_transact((uint8_t)i, s_payload, PRE_BYTES, s_payload, 0, SPI_READ_HIL, &r, raw);
        if (i == 0 || rc != SPI_OK) {
            put_kv("  vong ", i); put_kv(" rc=", rc); uart_puts(" doc:");
            for (int k = 0; k < (s_proto == 1 ? SPI_READ_V1 : SPI_READ_HIL); k++) { uart_putc(' '); uart_put_hex(raw[k], 2); }
            uart_putc('\n');
        }
    }
    put_kv("OK ", (int32_t)g_spi_stats.ok);
    put_kv(" / ", (int32_t)g_spi_stats.frames);
    put_kv("  timeout ", (int32_t)g_spi_stats.timeouts);
    put_kv("  crc ", (int32_t)g_spi_stats.crc_err);
    put_kv("  status ", (int32_t)g_spi_stats.status_err);
    put_kv("  seq ", (int32_t)g_spi_stats.seq_err);
    put_kv("  khac ", (int32_t)g_spi_stats.other_err);
    put_kv("  RST_N ", (int32_t)g_spi_stats.resets);
    uart_putc('\n');
}

/* Đo chu kỳ WDT thật. Datasheet ghi ILRC 32 kHz, nhưng sơ đồ clock trang 19 ghi 256 kHz. Ngừng feed, in thời gian mỗi
 * 20 ms; số in cuối cùng trước khi chip khởi động lại là chu kỳ WDT. TC = 0xFF: ≈ 1.024 ms nếu 32 kHz, ≈ 128 ms nếu 256 kHz. */
static void wdt_test(void)
{
    uart_puts("thu WDT: ngung feed, so cuoi truoc khi khoi dong lai = chu ky WDT (mong doi ~1024 ms)\n");
    board_wdt_feed();
    uint32_t t0 = board_millis(), last = t0;
    for (;;) {
        uint32_t now = board_millis();
        if (now - last >= 20u) {
            last = now;
            put_kv("wdt ", (int32_t)(now - t0));
            uart_putc('\n');
        }
        if (now - t0 > 5000u) {
            uart_puts("WDT khong reset sau 5 s -> FAIL\n");
            return;
        }
    }
}

void diag_run(void)
{
    spi_selftest_payload(s_payload);
    SN_SYS1->AHBCLKEN |= (1UL << 27);           /* clock của khối CRC, trước lần kiểm đầu */

    uart_puts("\nhello SN32F407 EVK - firmware FW-03 (" __DATE__ " " __TIME__ ")\n");
    put_kv("HCLK = ", (int32_t)SystemCoreClock);
    uart_puts(" Hz\n");
    crc_check();
    help();

    uint32_t t_led = 0;
    uint8_t keys_prev = 0, led = 0;
    for (;;) {
        uint32_t now = board_millis();
        board_wdt_feed();
        if (now - t_led >= 500u) {
            t_led = now;
            led ^= 1u;
            board_led(led);
        }
        uint8_t k = keys_scan(now);
        if (k != keys_prev) {
            if ((k ^ keys_prev) & KEY_SW3) uart_puts((k & KEY_SW3) ? "SW3 nhan\n" : "SW3 nha\n");
            if ((k ^ keys_prev) & KEY_SW6) uart_puts((k & KEY_SW6) ? "SW6 nhan\n" : "SW6 nha\n");
            keys_prev = k;
        }
        switch (uart_getc()) {
        case 'h': help(); break;
        case 'f': flash_probe(); break;
        case 'c': crc_check(); break;
        case '1': s_div = SPI_DIV_TEST; uart_puts("SCK 1 MHz\n"); break;
        case '4': s_div = SPI_DIV_RUN;  uart_puts("SCK 4 MHz\n"); break;
        case 'p': s_proto = (s_proto == 1) ? 3 : 1; put_kv("PROTO=", s_proto); uart_putc('\n'); break;
        case 's': spi_loop(100); break;
        case 't': put_kv("t_ms=", (int32_t)now); put_kv(" phim=", k); uart_putc('\n'); break;
        case 'w': wdt_test(); break;
        case 'q': uart_puts("thoat DIAG\n"); return;
        default: break;
        }
    }
}
