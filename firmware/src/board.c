/*
 * board.c — xem board.h. Clock, SysTick và UART0 lấy từ test_sensor/firmware/board_sn32f407.c (đã build, chưa chạy
 * trên board); tên thanh ghi theo SN32F400.h của pack SONiX.SN32F4_DFP 1.1.1, giá trị theo datasheet V2.2.
 */
#include "SN32F400.h"
#include "board.h"

/* ---------------- SysTick 1 ms ---------------- */
static volatile uint32_t s_ms;

static volatile uint8_t s_buzz;

static volatile uint8_t s_seg[4];
static uint8_t s_seg_d;

void board_seg7(const uint8_t pat[4])
{
    for (int i = 0; i < 4; i++) s_seg[i] = pat[i];
}

static void seg7_scan(void)
{
    SN_GPIO1->BCLR = (0xFUL << 9);                  /* tắt cả 4 COM trước khi đổi đoạn */
    SN_GPIO0->BCLR = 0xFFUL;
    SN_GPIO0->BSET = s_seg[s_seg_d];
    SN_GPIO1->BSET = (1UL << (9 + s_seg_d));
    s_seg_d = (uint8_t)((s_seg_d + 1u) & 3u);
}

void SysTick_Handler(void)
{
    s_ms++;
    seg7_scan();
    if (s_buzz) {                                   /* 1 kHz đảo → 500 Hz */
        if (s_ms & 1u) PIN_SET(SN_GPIO3, 0);
        else           PIN_CLR(SN_GPIO3, 0);
    }
}

void board_buzzer(int on)
{
    s_buzz = (uint8_t)(on != 0);
    if (!on) {
        if (BUZZER_ACTIVE_HIGH) PIN_CLR(SN_GPIO3, 0);
        else                    PIN_SET(SN_GPIO3, 0);
    }
}

int board_wear(void)
{
    return WEAR_PRESENT ? (PIN_READ(SN_GPIO2, 3) == 0) : 1;
}

void board_wdt_init(void)
{
    SN_WDT->TC  = 0x5AFA0000UL | 0xFFu;
    SN_WDT->FEED = 0x5AFA55AAUL;
    SN_WDT->CFG = 0x5AFA0001UL;                     /* WDTEN, chế độ reset */
}

void board_wdt_feed(void)
{
    SN_WDT->FEED = 0x5AFA55AAUL;
}
uint32_t board_millis(void) { return s_ms; }

void board_delay_us(uint32_t us)
{
    uint32_t load = SysTick->LOAD + 1u;
    uint32_t target = us * (SystemCoreClock / 1000000u);
    uint32_t prev = SysTick->VAL, now, elapsed = 0;
    while (elapsed < target) {
        now = SysTick->VAL;
        elapsed += (prev >= now) ? (prev - now) : (prev + load - now);
        prev = now;
    }
}

void board_delay_ms(uint32_t ms)
{
    uint32_t t0 = s_ms;
    while (s_ms - t0 < ms) { }
}

/* ---------------- LED D6: P3.8, thấp = sáng ---------------- */
void board_led(int on)
{
    if (on) PIN_CLR(SN_GPIO3, 8);
    else    PIN_SET(SN_GPIO3, 8);
}

/* ---------------- UART0 460800 8N1, buffer vòng + ngắt (FW-06) ----------------
 * Baud = PCLK / (OVER × DL); 48 MHz, OVER8 = 1, DL = 13 → 461.538 baud (lệch +0,16 %). */
#define TXN 512u
#define RXN 1024u
static volatile uint8_t  s_tx[TXN], s_rx[RXN];
static volatile uint16_t s_tx_h, s_tx_t, s_rx_h, s_rx_t;
volatile uint32_t g_uart_rx_overflow;

static void uart_init(void)
{
    SN_SYS1->AHBCLKEN |= (1UL << 16);           /* UART0CLKEN */
    SN_PFPA->UART0 = (2UL << 2) | 2UL;          /* URXD0 = P3.2, UTXD0 = P3.1 */
    SN_UART0->LC  = 0x83;                       /* DLAB = 1, 8N1 */
    SN_UART0->DLL = 13;
    SN_UART0->DLM = 0;
    SN_UART0->LC  = 0x03;
    SN_UART0->FD  = (1UL << 8);                 /* OVER8 = 1 */
    SN_UART0->FIFOCTRL = 0x01;
    SN_UART0->CTRL = (1UL << 0) | (1UL << 6) | (1UL << 7);     /* UARTEN, RXEN, TXEN */
    SN_UART0->IE = (1UL << 0);                  /* RDAIE; THREIE bật khi có byte cần gửi */
    NVIC_EnableIRQ(UART0_IRQn);
}

void UART0_IRQHandler(void)
{
    while (SN_UART0->LS & 1UL) {                /* RDR */
        uint8_t b = (uint8_t)SN_UART0->RB;
        uint16_t n = (uint16_t)((s_rx_h + 1u) % RXN);
        if (n == s_rx_t) g_uart_rx_overflow++;
        else { s_rx[s_rx_h] = b; s_rx_h = n; }
    }
    if (SN_UART0->LS & (1UL << 5)) {            /* THRE */
        if (s_tx_t != s_tx_h) {
            SN_UART0->TH = s_tx[s_tx_t];
            s_tx_t = (uint16_t)((s_tx_t + 1u) % TXN);
        } else {
            SN_UART0->IE &= ~(1UL << 1);        /* hết byte: tắt THREIE */
        }
    }
}

uint16_t uart_tx_free(void)
{
    return (uint16_t)((s_tx_t + TXN - s_tx_h - 1u) % TXN);
}

void uart_putc(char c)
{
    uint16_t n = (uint16_t)((s_tx_h + 1u) % TXN);
    while (n == s_tx_t) { }                     /* đầy: chờ ngắt xả bớt */
    s_tx[s_tx_h] = (uint8_t)c;
    s_tx_h = n;
    SN_UART0->IE |= (1UL << 1);                 /* THREIE */
}

void uart_flush(void)
{
    while (s_tx_t != s_tx_h) { }
}

void uart_puts(const char *s)
{
    while (*s) {
        if (*s == '\n') uart_putc('\r');
        uart_putc(*s++);
    }
}

void uart_put_dec(int32_t v)
{
    char buf[12];
    int i = 0;
    uint32_t u = (v < 0) ? (uint32_t)(-(v + 1)) + 1u : (uint32_t)v;
    if (v < 0) uart_putc('-');
    do { buf[i++] = (char)('0' + u % 10u); u /= 10u; } while (u);
    while (i) uart_putc(buf[--i]);
}

void uart_put_hex(uint32_t v, int digits)
{
    while (digits--)
        uart_putc("0123456789ABCDEF"[(v >> (4 * digits)) & 0xFu]);
}

int uart_getc(void)
{
    if (s_rx_t == s_rx_h)
        return -1;
    uint8_t b = s_rx[s_rx_t];
    s_rx_t = (uint16_t)((s_rx_t + 1u) % RXN);
    return b;
}

/* ---------------- phím SW3 / SW6 ---------------- */
uint8_t keys_raw(void)
{
    uint8_t m = 0;
    if (PIN_READ(SN_GPIO2, 4) == 0) m |= KEY_SW3;
    if (PIN_READ(SN_GPIO2, 7) == 0) m |= KEY_SW6;
    return m;
}

uint8_t keys_scan(uint32_t now)
{
    static uint8_t stable, cand;
    static uint32_t t_cand;
    uint8_t raw = keys_raw();
    if (raw != cand) {
        cand = raw;
        t_cand = now;
    } else if (now - t_cand >= 20u) {
        stable = cand;
    }
    return stable;
}

/* ---------------- ngắt cổng P2 (IRQ của FPGA, INT của MPU6050) ---------------- */
volatile uint8_t g_fpga_irq;
volatile uint8_t g_imu_int;

void P2_IRQHandler(void)
{
    uint32_t ris = SN_GPIO2->RIS;
    if (ris & (1UL << 9)) g_fpga_irq = 1;
    if (ris & (1UL << 2)) g_imu_int = 1;
    SN_GPIO2->IC = ris;
}

void board_p2_irq_enable(uint32_t mask)
{
    SN_GPIO2->IS  &= ~mask;                     /* cạnh */
    SN_GPIO2->IBS &= ~mask;                     /* một cạnh */
    SN_GPIO2->IEV &= ~mask;                     /* cạnh lên */
    SN_GPIO2->IC   = mask;
    SN_GPIO2->IE  |= mask;
    NVIC_ClearPendingIRQ(P2_IRQn);
    NVIC_EnableIRQ(P2_IRQn);
}

/* ---------------- khởi tạo ---------------- */
static void clock_48mhz(void)
{
    SN_FLASH->LPCTRL = 0x5AFA0029;              /* nhiều wait-state nhất trước khi tăng clock; */
    SN_SYS0->ANBCTRL_b.IHRCFREQ = 1;            /* SystemCoreClockUpdate() hạ về 0x5AFA0019 cho 48 MHz */
    SN_SYS0->CLKCFG = 0x0;                      /* SYSCLK = IHRC 48 MHz */
    while ((SN_SYS0->CLKCFG & 0x70) != 0x0) { }
    SystemCoreClockUpdate();
}

void board_init(void)
{
    clock_48mhz();
    SysTick_Config(SystemCoreClock / 1000u);

    PIN_SET(SN_GPIO3, 8);                       /* LED tắt */
    PIN_OUTPUT(SN_GPIO3, 8);

    PIN_CLR(SN_GPIO1, 4);                       /* ROW0 = 0: SW3, SW6 thành nút kéo xuống GND */
    PIN_OUTPUT(SN_GPIO1, 4);
    PIN_INPUT(SN_GPIO2, 4);
    PIN_CFG(SN_GPIO2, 4, PIN_CFG_PULLUP);
    PIN_INPUT(SN_GPIO2, 7);
    PIN_CFG(SN_GPIO2, 7, PIN_CFG_PULLUP);

    SN_GPIO0->BCLR = 0xFFUL;                    /* LED 7 đoạn: đoạn P0.0..P0.7, COM P1.9..P1.12, tắt hết */
    SN_GPIO0->MODE |= 0xFFUL;
    SN_GPIO1->BCLR = (0xFUL << 9);
    SN_GPIO1->MODE |= (0xFUL << 9);
    PIN_CLR(SN_GPIO3, 0);                       /* còi tắt */
    PIN_OUTPUT(SN_GPIO3, 0);
    PIN_INPUT(SN_GPIO2, 3);                     /* WEAR, kéo lên */
    PIN_CFG(SN_GPIO2, 3, PIN_CFG_PULLUP);
    PIN_INPUT(SN_GPIO2, 2);                     /* INT của MPU6050, kéo xuống, ngắt cạnh lên */
    PIN_CFG(SN_GPIO2, 2, PIN_CFG_PULLDOWN);

    uart_init();
}
