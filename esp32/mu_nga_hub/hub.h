/*
 * hub.h — lõi chạy trên ESP32 khi phần cứng nối cố định theo codecanthiet (24/10): MCU → UART → ESP32 → SPI → FPGA.
 * C thuần, dùng lại nguyên app_core (tiền xử lý A.2, khối A.8, bỏ phiếu + Safety FSM, nút bấm) đã kiểm khớp golden.
 *
 * Không có dây IRQ và RST_N giữa ESP32 và FPGA, nên kết quả lấy bằng hỏi vòng: sau khi ghi khung v3 (772 byte),
 * chờ HUB_FIRST_POLL_MS rồi đọc 7 byte mỗi HUB_POLL_EVERY_MS. FPGA chốt "có kết quả" ngay lúc CS xuống
 * (spi_result_tx_v3.v); chưa có kết quả thì trả toàn 0 và không mất gì, nên hỏi vòng an toàn. Quá SPI_TIMEOUT_MS
 * mà vẫn toàn 0 → SPI_E_TIMEOUT.
 *
 * Đọc/ghi SPI qua hàm do bên gọi cấp (SPI thật trên ESP32, FPGA giả lập trong bộ test).
 */
#ifndef HUB_H
#define HUB_H

#include <stdint.h>
#include "app_core.h"
#include "fw_config.h"

#define HUB_FIRST_POLL_MS   6u      /* engine E2: 258.080 chu kỳ = 5,15 ms */
#define HUB_POLL_EVERY_MS   1u

typedef struct {
    void (*spi_write)(const uint8_t *buf, uint16_t n, void *ctx);
    void (*spi_read)(uint8_t *buf, uint8_t n, void *ctx);
    void *ctx;
} hub_io_t;

typedef struct {
    app_t    app;
    uint8_t  frame[SPI_FRAME_V3];
    uint16_t nframe;
    uint8_t  wait, seq, keys;
    uint32_t t_sent, t_poll;
    uint32_t n_samples, n_sent, n_ok, n_timeout, n_err, n_skip;
    spi_result_t last;
    int      last_rc;
} hub_t;

void hub_init(hub_t *h, uint32_t now);
/* Một mẫu 100 Hz từ MCU (gyro đã trừ offset). Có cửa sổ mới và FPGA rảnh thì ghi khung ngay. Trả về cờ APP_*. */
unsigned hub_sample(hub_t *h, const hub_io_t *io, const int16_t r[6], uint8_t keys, uint32_t now);
/* Gọi thường xuyên (≥ 1 lần/ms). Trả về SPI_PENDING nếu chưa có gì mới, ngược lại mã SPI_* của kết quả vừa đọc
 * (kết quả nằm ở h->last và đã đưa vào app_on_result). */
int  hub_poll(hub_t *h, const hub_io_t *io, uint32_t now);
/* Khe 10 ms: Safety FSM, nút. cancel_extra: nút CANCEL phụ trên ESP32 (OR với SW3 của MCU). */
void hub_tick(hub_t *h, uint32_t now, uint8_t cancel_extra);
/* Tự kiểm A.10 qua SPI: ghi khung SEQ 0xEE (payload LFSR), hỏi vòng, so 7 byte với expect7. 1 = PASS. */
int  hub_selftest(hub_t *h, const hub_io_t *io, uint32_t (*millis)(void), const uint8_t expect7[7],
                  uint8_t got7[7]);

#ifndef SPI_PENDING
#define SPI_PENDING (-1)
#endif

#endif
