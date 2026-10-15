/*
 * spi_fpga.h — SPI0 tới FPGA theo A.7 và E.2 (việc FW-08).
 *   SCK P1.0 · MISO P1.1 · MOSI P1.2 (PFPA SPI0 = 0x2A) · CS của FPGA = GPIO P2.8 · IRQ = P2.9 (ngắt cạnh lên)
 *   P1.8 luôn ra mức cao để flash SPI của EVK không bị chọn · RST_N P2.1 (RTL chưa có cổng, xung vẫn phát vô hại)
 *   CRC-16 của khung ghi tính bằng khối CRC phần cứng (crc16_hw); crc16_sw giữ để đối chiếu.
 */
#ifndef SPI_FPGA_H
#define SPI_FPGA_H

#include <stdint.h>
#include "crc.h"
#include "spi_frame.h"

extern const crc16_engine_t crc16_hw;

void    spi_fpga_init(uint8_t clkdiv, uint8_t proto);
void    spi_fpga_set_div(uint8_t clkdiv);
uint8_t spi_fpga_xfer(uint8_t b);                 /* một byte, chờ xong */

/* Không chặn (vòng lặp chính, A.9 / mục 4.3): spi_fpga_start() ghi khung (≈ 1,5 ms ở 4 MHz) rồi trả về;
 * spi_fpga_poll() gọi mỗi khe: trả về SPI_PENDING khi chưa có IRQ và chưa quá 50 ms, ngược lại đọc + kiểm.
 * n_read = 7 (RUN) hoặc 20 (HIL); PROTO 1 luôn 7. raw (có thể là 0) nhận các byte đọc được.
 * Đếm lỗi liên tiếp; tới 3 thì phát RST_N thấp ≥ 1 ms. */
#define SPI_PENDING  (-1)
uint16_t spi_fpga_start(uint8_t seq, const int8_t *seg1, uint16_t n1, const int8_t *seg2, uint16_t n2);  /* trả về CRC đã gửi */
int     spi_fpga_poll(uint32_t now, uint8_t n_read, spi_result_t *res, uint8_t *raw);
int     spi_fpga_busy(void);                      /* đang chờ kết quả của một khung */

/* Một vòng ghi → chờ IRQ ≤ 50 ms → đọc, kiểu chặn (dùng cho lệnh thử 's' và HIL). */
int     spi_fpga_transact(uint8_t seq, const int8_t *seg1, uint16_t n1, const int8_t *seg2, uint16_t n2,
                          uint8_t n_read, spi_result_t *res, uint8_t *raw);

typedef struct {
    uint32_t frames, ok, timeouts, crc_err, status_err, seq_err, other_err, resets;
    uint8_t  consecutive;
} spi_fpga_stats_t;
extern spi_fpga_stats_t g_spi_stats;

#endif
