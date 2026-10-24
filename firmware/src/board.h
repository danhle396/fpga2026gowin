/*
 * board.h — phần cứng của board "32F407 EVK V1.0" cho firmware chính (việc FW-03). Chân theo PROJECT_MASTER.md, E.1.
 *   Clock IHRC 48 MHz · SysTick 1 ms · UART0 460800 8N1 trên P3.1 (TX) / P3.2 (RX) · LED D6 trên P3.8 (thấp = sáng)
 *   Phím SW3 (CANCEL) và SW6 (đánh dấu / chọn LOG): ROW0 = P1.4 giữ mức 0, đọc COL0 = P2.4 và COL3 = P2.7 (kéo lên)
 *   Ngắt cổng P2: IRQ của FPGA ở P2.9, INT của MPU6050 ở P2.2, cùng một trình phục vụ.
 */
#ifndef BOARD_H
#define BOARD_H

#include <stdint.h>

void     board_init(void);
uint32_t board_millis(void);
void     board_delay_us(uint32_t us);
void     board_delay_ms(uint32_t ms);

void     board_led(int on);

/* UART0 460800 8N1, buffer vòng + ngắt cho cả TX (512 B) và RX (1024 B) — việc FW-06.
 * uart_putc chờ THRE rồi ghi (phát kiểu hỏi vòng, không bỏ byte). */
void     uart_putc(char c);
void     uart_puts(const char *s);
void     uart_put_dec(int32_t v);
void     uart_put_hex(uint32_t v, int digits);
int      uart_getc(void);              /* −1 nếu chưa có byte */
uint16_t uart_tx_free(void);
void     uart_flush(void);             /* chờ gửi hết */
extern volatile uint32_t g_uart_rx_overflow;

/* LED 7 đoạn của EVK: đoạn A..G, DP = P0.0..P0.7 (cao = sáng), COM0..COM3 = P1.9..P1.12 (cao = bật, qua NPN).
 * Quét trong SysTick, mỗi ms một chữ số (250 Hz). pat[i] = mã gfedcba của chữ số i (trái → phải). */
void     board_seg7(const uint8_t pat[4]);

/* Còi P3.0: đảo trong SysTick → âm 500 Hz (kêu được với còi thụ động lẫn chủ động). Cực tính chưa thử (E.1). */
#define BUZZER_ACTIVE_HIGH  1
void     board_buzzer(int on);

/* WEAR P2.3 (kéo lên, công tắc đội mũ nối xuống GND). Chưa có cảm biến đội mũ thì WEAR_PRESENT = 0: luôn coi là đội. */
#define WEAR_PRESENT  0
int      board_wear(void);

/* Watchdog: reset chip nếu không nuôi trong ≈ 1 s (TC = 0xFF, chưa rõ hệ số chia mặc định — CẦN XÁC MINH trên board) */
void     board_wdt_init(void);
void     board_wdt_feed(void);

/* Phím: mức tức thời (1 = đang nhấn) và trạng thái đã chống dội 20 ms (gọi keys_scan mỗi 1–10 ms) */
#define KEY_SW3   0x01u
#define KEY_SW6   0x02u
uint8_t  keys_raw(void);
uint8_t  keys_scan(uint32_t now);      /* trả về mặt nạ phím đã chống dội */

/* GPIO dùng chung */
#define PIN_CFG_PULLUP    0u
#define PIN_CFG_PULLDOWN  1u
#define PIN_CFG_NONE      2u
#define PIN_CFG(p, b, v)  ((p)->CFG = ((p)->CFG & ~(3UL << (2 * (b)))) | ((uint32_t)(v) << (2 * (b))))
#define PIN_OUTPUT(p, b)  ((p)->MODE |=  (1UL << (b)))
#define PIN_INPUT(p, b)   ((p)->MODE &= ~(1UL << (b)))
#define PIN_SET(p, b)     ((p)->BSET  =  (1UL << (b)))
#define PIN_CLR(p, b)     ((p)->BCLR  =  (1UL << (b)))
#define PIN_READ(p, b)    ((int)(((p)->DATA >> (b)) & 1UL))

#endif
