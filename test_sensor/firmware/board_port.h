/*
 * board_port.h — lớp "port" phần cứng cho firmware test MPU6050.
 *
 * Toàn bộ code test (i2c_soft.c, mpu6050.c, test_main.c) CHỈ gọi các hàm
 * dưới đây. Muốn chạy trên board khác (SN32F407, STM32, ...) thì chỉ cần
 * viết lại một file board_xxx.c, không đụng vào phần còn lại.
 */
#ifndef BOARD_PORT_H
#define BOARD_PORT_H

#include <stdint.h>

/* Khởi tạo clock, SysTick 1 ms, GPIO (SCL, SDA, INT, LED, nút), UART 460800 8N1. */
void     board_init(void);

/* Thời gian */
uint32_t board_millis(void);              /* ms kể từ khi khởi động (SysTick) */
void     board_delay_us(uint32_t us);
void     board_delay_ms(uint32_t ms);

/* I2C bit-bang kiểu open-drain:
 *   *_low()     : kéo chân xuống 0 (chân là output, mức 0)
 *   *_release() : thả chân (chân là input, điện trở kéo lên đưa về 1)
 *   *_read()    : đọc mức thực tế trên dây (0/1)                       */
void     board_scl_low(void);
void     board_scl_release(void);
int      board_scl_read(void);
void     board_sda_low(void);
void     board_sda_release(void);
int      board_sda_read(void);

/* Chân INT của MPU6050 (input) — trả về 0/1 */
int      board_int_read(void);

/* Nút đánh dấu (btn trong CSV) — trả về 1 khi đang nhấn; không có nút thì trả 0 */
int      board_button_read(void);

/* LED báo trạng thái */
void     board_led(int on);

/* UART gửi 1 byte (chờ đến khi gửi xong là được — đây chỉ là firmware test) */
void     board_uart_putc(char c);

#endif
