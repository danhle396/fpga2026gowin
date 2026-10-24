#ifndef FALL_BOARD_CONFIG_H
#define FALL_BOARD_CONFIG_H

/* SN32F407F U3, EVK V1.0 schematic sheet 1. Not STM32F407.
 * TODO_HW_VERIFY: match physical revision, Y2 population and 3.3 V jumpers.
 * Datasheet v2.2 pp.50-57: select EHS directly, no PLL, HCLK=/1.
 * 12 MHz IHRC fallback is diagnostic only; acquisition stays disabled. */
#define BOARD_EHS_HZ             16000000UL
#define BOARD_FALLBACK_HZ        12000000UL
#define BOARD_CLOCK_WAIT_LIMIT   1000000UL
#define BOARD_SYSTICK_HZ         1000UL

/* PFPA PA2, datasheet pp.76,79 and schematic J11/J10. Peripheral enable
 * takes ownership of these GPIO pins. Do not remap SWD/BOOT pins. */
#define BOARD_I2C_SCL_PORT        0U
#define BOARD_I2C_SCL_PIN         10U
#define BOARD_I2C_SDA_PORT        0U
#define BOARD_I2C_SDA_PIN         11U
#define BOARD_UART_TX_PORT       3U
#define BOARD_UART_TX_PIN        1U
#define BOARD_UART_RX_PORT       3U
#define BOARD_UART_RX_PIN        2U
#define BOARD_I2C_PFPA           0x0AU
#define BOARD_UART_PFPA          0x0AU

/* I2C0 PCLK=HCLK/4. Datasheet p.193 disagrees about +1 in the total.
 * Counts=20/20 at 4 MHz yield <=100 kHz under either interpretation.
 * TODO_HW_VERIFY: scope SCL, external 3.3 V pullups and shared U5 EEPROM.
 * Do not enable the MCU's weak pulls as a substitute for I2C pullups. */
#define BOARD_I2C_PRESCALE       2U
#define BOARD_I2C_DIVISOR        4UL
#define BOARD_I2C_TARGET_HZ      100000UL
#define BOARD_UART_BAUD          115200UL

/* User-authorized default. TODO_HW_VERIFY: tie AD0 low for 0x68;
 * override to 0x69 for AD0 high. WHO_AM_I remains 0x68. */
#ifndef BOARD_MPU6050_ADDRESS
#define BOARD_MPU6050_ADDRESS    0x68U
#endif
#if BOARD_MPU6050_ADDRESS != 0x68U && BOARD_MPU6050_ADDRESS != 0x69U
#error MPU6050 address must be 0x68 or 0x69
#endif
/* Selected internal timer CT16B0: HCLK -> PRE -> 1 MHz -> MR0=10000.
 * No external timer pin needed. TODO_HW_VERIFY: measure 10 ms IRQ period. */
#define BOARD_TIMER_TICK_HZ      1000000UL

/* SN32F400 v2.2 pp.76/80,174: SPI0 PA2 on P1.0 SCK, P1.1 MISO,
 * P1.2 MOSI. Do not map SEL0 P1.8: it also selects EVK flash.
 * HCLK=16 MHz, DIV=7 gives nominal 1 MHz SPI; bring-up changes this at
 * runtime for the 12 MHz IHRC fallback. This keeps a 774-byte
 * upload below one 10 ms sample interval; TODO_HW_VERIFY on
 * board: clock waveform and FPGA oversampling/timing. Independent FPGA
 * CS GPIO is intentionally not assigned until physical wiring is known. */
#define BOARD_SPI0_PFPA          0x2AU
#define BOARD_SPI_DIV_EHS       7U
#define BOARD_SPI_DIV_IHRC      5U
#define BOARD_SPI_BYTE_TIMEOUT_MS 2UL

/* EVK V1.0 schematic: D6/D7 LED0/LED1, active low; PZ1 active high. */
#define BOARD_LED0_PIN          8U  /* P3.8 */
#define BOARD_LED1_PIN          9U  /* P3.9 */
#define BOARD_BUZZER_PIN        0U  /* P3.0, PZ1 + to BUZ_P30 */
/* EVK keypad SW3 is ROW0 P1.4 / COL0 P2.4. */
#define BOARD_CANCEL_ROW_PIN    4U
#define BOARD_CANCEL_COL_PIN    4U
/* J7 exposes P2.2. Dedicated FPGA CS; TODO_HW_VERIFY external wire/FPGA pin. */
#define BOARD_FPGA_CS_PIN       2U
#define BOARD_SPI_FLASH_CS_PIN  8U  /* P1.8 SEL_P18, active-low onboard flash */
/* SSD1306 module is external to EVK; TODO_HW_VERIFY address/geometry. */
#define BOARD_OLED_ADDRESS      0x3CU

#endif
