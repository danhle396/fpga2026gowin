/*
 * board_sn32f407.c — port phần cứng cho SONiX SN32F407 (Cortex-M0, Keil MDK).
 *
 * Viết theo SN32F400.h / SN32F400.svd trong pack SONiX.SN32F4_DFP 1.1.2
 * (sdk/SN32F4_DFP). Clock: IHRC 48 MHz (không cần thạch anh ngoài).
 *
 * Chân theo board "32F407 EVK V1.0" (PROJECT_MASTER.md, Phụ lục E). Trên board này
 * P0.0..P0.7 là LED 7 đoạn, P1.4..P1.7 / P2.4..P2.7 là phím ma trận, nên không dùng làm I2C/UART.
 *   P0.10 = SCL   (I2C0 trên EVK: đã có pull-up 10 kOhm và EEPROM 24C05 ở địa chỉ 0x50;
 *   P0.11 = SDA    firmware chính dùng lại đúng hai chân này với I2C0 phần cứng, PFPA = 2)
 *   P2.2  = INT của MPU6050
 *   P3.1  = UART0 TX, P3.2 = UART0 RX (PFPA = 2)
 *   P3.8  = LED D6, sáng ở mức thấp
 *   Nút đánh dấu = phím SW3 của ma trận: ROW0 (P1.4) kéo xuống 0, đọc COL0 (P2.4)
 */
#include "SN32F400.h"
#include "board_port.h"

/* ===================== (1) CHỌN CHÂN ===================== */
#define SCL_PORT    SN_GPIO0
#define SCL_BIT     10
#define SDA_PORT    SN_GPIO0
#define SDA_BIT     11
#define INT_PORT    SN_GPIO2
#define INT_BIT     2

#define HAS_LED     1           /* 1 nếu board có LED ở chân dưới đây */
#define LED_PORT    SN_GPIO3
#define LED_BIT     8
#define LED_ON_LVL  0

#define HAS_BUTTON  1           /* 1 nếu đã nối nút đánh dấu (nhấn = kéo xuống GND) */
#define BTN_PORT    SN_GPIO2    /* COL0 của phím ma trận */
#define BTN_BIT     4
#define BTN_ROW_PORT SN_GPIO1   /* ROW0: giữ ở mức 0 để SW3 thành nút kéo xuống GND */
#define BTN_ROW_BIT 4

/* GPIOn_CFG: 2 bit/chân. 00 = pull-up, 01 = pull-down, 10 = không kéo */
#define CFG_PULLUP      0u
#define CFG_PULLDOWN    1u
#define PIN_CFG(p, b, v)    ((p)->CFG = ((p)->CFG & ~(3UL << (2 * (b)))) | ((uint32_t)(v) << (2 * (b))))

/* GPIOn_MODE: 1 = output, 0 = input. BSET/BCLR: ghi 1 để set/clear bit DATA. */
#define PIN_OUTPUT(p, b)    ((p)->MODE |=  (1UL << (b)))
#define PIN_INPUT(p, b)     ((p)->MODE &= ~(1UL << (b)))
#define PIN_SET(p, b)       ((p)->BSET  =  (1UL << (b)))
#define PIN_CLR(p, b)       ((p)->BCLR  =  (1UL << (b)))
#define PIN_READ(p, b)      ((int)(((p)->DATA >> (b)) & 1UL))

/* ===================== SysTick 1 ms ===================== */
static volatile uint32_t s_ms;

void SysTick_Handler(void)
{
    s_ms++;
}

uint32_t board_millis(void)
{
    return s_ms;
}

void board_delay_us(uint32_t us)
{
    /* Đếm bằng SysTick->VAL (đếm lùi, nạp lại mỗi 1 ms) */
    uint32_t load   = SysTick->LOAD + 1u;
    uint32_t target = us * (SystemCoreClock / 1000000u);
    uint32_t prev   = SysTick->VAL, now, elapsed = 0;
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

/* ===================== I2C open-drain giả lập ===================== */
/* Bit DATA luôn để 0; "kéo xuống" = bật output, "thả" = chuyển về input. */
void board_scl_low(void)     { PIN_CLR(SCL_PORT, SCL_BIT); PIN_OUTPUT(SCL_PORT, SCL_BIT); }
void board_scl_release(void) { PIN_INPUT(SCL_PORT, SCL_BIT); }
int  board_scl_read(void)    { return PIN_READ(SCL_PORT, SCL_BIT); }
void board_sda_low(void)     { PIN_CLR(SDA_PORT, SDA_BIT); PIN_OUTPUT(SDA_PORT, SDA_BIT); }
void board_sda_release(void) { PIN_INPUT(SDA_PORT, SDA_BIT); }
int  board_sda_read(void)    { return PIN_READ(SDA_PORT, SDA_BIT); }

int board_int_read(void)
{
    return PIN_READ(INT_PORT, INT_BIT);
}

int board_button_read(void)
{
#if HAS_BUTTON
    return PIN_READ(BTN_PORT, BTN_BIT) == 0;
#else
    return 0;
#endif
}

void board_led(int on)
{
#if HAS_LED
    if ((on != 0) == (LED_ON_LVL != 0)) PIN_SET(LED_PORT, LED_BIT);
    else                                PIN_CLR(LED_PORT, LED_BIT);
#else
    (void)on;
#endif
}

/* ===================== UART0 460800 8N1 ===================== */
/*
 * Baud = PCLK / (OVER x DL x (1 + DIVADDVAL/MULVAL)).
 * 48 MHz, OVER8 = 1 (lấy mẫu x8), DL = 13, không dùng phân số:
 * 48e6 / (8 x 13) = 461538 baud (lệch +0,16 %, USB-UART chấp nhận tốt).
 */
static void board_uart_init(void)
{
    SN_SYS1->AHBCLKEN |= (1UL << 16);   /* UART0CLKEN */
    SN_PFPA->UART0 = (2UL << 2) | 2UL;  /* URXD0 = P3.2, UTXD0 = P3.1 */

    SN_UART0->LC  = 0x83;               /* DLAB = 1, 8 bit, 1 stop, không parity */
    SN_UART0->DLL = 13;
    SN_UART0->DLM = 0;
    SN_UART0->LC  = 0x03;               /* DLAB = 0 */
    SN_UART0->FD  = (1UL << 8);         /* OVER8 = 1, DIVADDVAL = 0 */
    SN_UART0->FIFOCTRL = 0x01;          /* bật FIFO */
    SN_UART0->CTRL = (1UL << 0)         /* UARTEN */
                   | (1UL << 6)         /* RXEN */
                   | (1UL << 7);        /* TXEN, MODE = 0 (UART) */
}

void board_uart_putc(char c)
{
    while (!(SN_UART0->LS & (1UL << 5))) { }    /* THRE: thanh ghi phát rỗng */
    SN_UART0->TH = (uint8_t)c;
}

/* ===================== khởi tạo ===================== */
static void clock_48mhz(void)
{
    /* Theo nhánh IHRC_48M trong system_SN32F400.c của pack */
    SN_FLASH->LPCTRL = 0x5AFA0029;      /* wait-state Flash cho 48 MHz — phải đặt TRƯỚC khi tăng clock */
    SN_SYS0->ANBCTRL_b.IHRCFREQ = 1;    /* IHRC 48 MHz */
    SN_SYS0->CLKCFG = 0x0;              /* SYSCLK = IHRC */
    while ((SN_SYS0->CLKCFG & 0x70) != 0x0) { }
    SystemCoreClockUpdate();
}

void board_init(void)
{
    clock_48mhz();                                  /* SystemInit() đã được startup gọi (12 MHz) */
    SysTick_Config(SystemCoreClock / 1000u);        /* ngắt 1 ms */

    /* GPIO có clock sẵn sau reset (example Blinky của SONiX cũng không bật) */
    PIN_CFG(SCL_PORT, SCL_BIT, CFG_PULLUP);         /* module GY-521 đã có pull-up, thêm pull-up trong không sao */
    PIN_CFG(SDA_PORT, SDA_BIT, CFG_PULLUP);
    board_scl_release();
    board_sda_release();

    PIN_INPUT(INT_PORT, INT_BIT);
    PIN_CFG(INT_PORT, INT_BIT, CFG_PULLDOWN);       /* chưa nối dây INT -> đọc 0, T6 báo rõ */
#if HAS_BUTTON
    PIN_CLR(BTN_ROW_PORT, BTN_ROW_BIT);
    PIN_OUTPUT(BTN_ROW_PORT, BTN_ROW_BIT);
    PIN_INPUT(BTN_PORT, BTN_BIT);
    PIN_CFG(BTN_PORT, BTN_BIT, CFG_PULLUP);
#endif
#if HAS_LED
    PIN_OUTPUT(LED_PORT, LED_BIT);
#endif
    board_led(0);

    board_uart_init();
}
