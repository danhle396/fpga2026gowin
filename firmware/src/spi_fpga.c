/* spi_fpga.c — xem spi_fpga.h. Thanh ghi theo datasheet V2.2 chương 14 (SPI) và 19 (CRC). */
#include "SN32F400.h"
#include "board.h"
#include "fw_config.h"
#include "spi_fpga.h"

spi_fpga_stats_t g_spi_stats;
static uint8_t s_proto = 3;

/* ---------------- CRC-16 phần cứng: CRC[1:0] = 0 là CRC-16-CCITT, mầm 0xFFFF (datasheet 19.2) ---------------- */
static void hw_reset(void)
{
    SN_CRC->CTRL = (1UL << 2);                  /* RESET; phần cứng tự xóa bit này */
    for (int i = 0; i < 100 && (SN_CRC->CTRL & (1UL << 2)); i++) { }
}

static void hw_feed(uint8_t b)
{
    while (SN_CRC->CTRL & (1UL << 4)) { }       /* BUSY */
    *(volatile uint8_t *)&SN_CRC->DATA = b;     /* CRC_DATA chỉ nhận ghi 8 bit (datasheet 19.3.2) */
}

static uint16_t hw_result(void)
{
    while (SN_CRC->CTRL & (1UL << 4)) { }
    return (uint16_t)SN_CRC->DATA;
}

const crc16_engine_t crc16_hw = { hw_reset, hw_feed, hw_result };

/* ---------------- chân ---------------- */
#define CS_LOW()    PIN_CLR(SN_GPIO2, 8)
#define CS_HIGH()   PIN_SET(SN_GPIO2, 8)

static void spi_reset_fifo(void)
{
    SN_SPI0->CTRL0 |= (3UL << 6);               /* FRESET = 3: xóa FSM và FIFO, phần cứng tự xóa */
}

void spi_fpga_set_div(uint8_t clkdiv)
{
    SN_SPI0->CLKDIV = clkdiv;                   /* SCK = PCLK / (2·DIV + 2) */
    spi_reset_fifo();                           /* bắt buộc sau khi đổi cấu hình khi SPIEN = 1 */
}

void spi_fpga_init(uint8_t clkdiv, uint8_t proto)
{
    s_proto = proto;
    SN_SYS1->AHBCLKEN |= (1UL << 12) | (1UL << 27);     /* SPI0, CRC */

    PIN_SET(SN_GPIO1, 8);  PIN_OUTPUT(SN_GPIO1, 8);     /* P1.8 cao: flash của EVK không bị chọn */
    CS_HIGH();             PIN_OUTPUT(SN_GPIO2, 8);     /* CS của FPGA */
    PIN_SET(SN_GPIO2, 1);  PIN_OUTPUT(SN_GPIO2, 1);     /* RST_N */
    PIN_INPUT(SN_GPIO2, 9);
    PIN_CFG(SN_GPIO2, 9, PIN_CFG_PULLDOWN);             /* IRQ: kéo xuống khi chưa nối FPGA */

    SN_PFPA->SPI0 = 0x2A;                       /* MISO0 = P1.1, MOSI0 = P1.2, SCK0 = P1.0; SEL0 không dùng */
    SN_SPI0->CTRL0 = (1UL << 18)                /* SELDIS: phần cứng không đụng chân SEL */
                   | (7UL << 8);                /* DL = 7: khung 8 bit; MS = 0: master; FORMAT = 0: SPI */
    SN_SPI0->CTRL1 = 0;                         /* CPOL = 0, CPHA = 0 (mode 0), MSB trước */
    SN_SPI0->CLKDIV = clkdiv;
    SN_SPI0->CTRL0 |= 1UL;                      /* SPIEN */
    spi_reset_fifo();

    hw_reset();
    g_fpga_irq = 0;
    board_p2_irq_enable(1UL << 9);
}

uint8_t spi_fpga_xfer(uint8_t b)
{
    while (SN_SPI0->STAT & (1UL << 1)) { }      /* TX_FULL */
    SN_SPI0->DATA = b;
    while (SN_SPI0->STAT & (1UL << 2)) { }      /* RX_EMPTY */
    return (uint8_t)SN_SPI0->DATA;
}

/* Ghi khung: đẩy liên tục vào FIFO TX, đọc bỏ FIFO RX để không tràn. */
static void tx_stream(uint8_t b, void *ctx)
{
    (void)ctx;
    while (SN_SPI0->STAT & (1UL << 1)) {        /* TX_FULL: tranh thủ xả RX */
        if (!(SN_SPI0->STAT & (1UL << 2))) (void)SN_SPI0->DATA;
    }
    SN_SPI0->DATA = b;
    if (!(SN_SPI0->STAT & (1UL << 2))) (void)SN_SPI0->DATA;
}

static void tx_drain(void)
{
    while (!(SN_SPI0->STAT & 1UL) || (SN_SPI0->STAT & (1UL << 4))) {   /* chờ TX_EMPTY và hết BUSY */
        if (!(SN_SPI0->STAT & (1UL << 2))) (void)SN_SPI0->DATA;
    }
    while (!(SN_SPI0->STAT & (1UL << 2))) (void)SN_SPI0->DATA;
}

static void rst_pulse(void)
{
    PIN_CLR(SN_GPIO2, 1);
    board_delay_ms(2);                          /* ≥ 1 ms */
    PIN_SET(SN_GPIO2, 1);
    g_spi_stats.resets++;
}

static int count(int rc)
{
    g_spi_stats.frames++;
    switch (rc) {
    case SPI_OK:        g_spi_stats.ok++; break;
    case SPI_E_TIMEOUT: g_spi_stats.timeouts++; break;
    case SPI_E_CRC:     g_spi_stats.crc_err++; break;
    case SPI_E_STATUS:  g_spi_stats.status_err++; break;
    case SPI_E_SEQ:     g_spi_stats.seq_err++; break;
    default:            g_spi_stats.other_err++; break;
    }
    if (rc == SPI_OK || rc == SPI_E_TAIL) {
        g_spi_stats.consecutive = 0;
    } else if (++g_spi_stats.consecutive >= SPI_ERR_RESET) {
        rst_pulse();
        g_spi_stats.consecutive = 0;
    }
    return rc;
}

static uint8_t  s_wait;                          /* 1: đã ghi khung, chờ IRQ */
static uint8_t  s_seq;
static uint32_t s_t_sent;

static void read_bytes(uint8_t *buf, uint8_t n)
{
    CS_LOW();
    board_delay_us(2);
    for (uint8_t i = 0; i < n; i++)
        buf[i] = spi_fpga_xfer(0x00);
    board_delay_us(2);
    CS_HIGH();
}

int spi_fpga_busy(void) { return s_wait; }

uint16_t spi_fpga_start(uint8_t seq, const int8_t *seg1, uint16_t n1, const int8_t *seg2, uint16_t n2)
{
    uint8_t junk[SPI_READ_HIL];
    if (PIN_READ(SN_GPIO2, 9)) {                /* kết quả cũ chưa đọc: IRQ đang cao, sẽ không có cạnh lên mới */
        read_bytes(junk, s_proto == 1 ? SPI_READ_V1 : SPI_READ_RUN);
        g_spi_stats.other_err++;
    }
    g_fpga_irq = 0;
    CS_LOW();
    board_delay_us(2);                          /* ≥ 2 chu kỳ SCK ở 1 MHz trước cạnh đầu */
    uint16_t crc = spi_frame_emit(s_proto, seq, seg1, n1, seg2, n2, &crc16_hw, tx_stream, 0);
    tx_drain();
    board_delay_us(2);                          /* ≥ 1,5 chu kỳ SCK sau cạnh cuối */
    CS_HIGH();
    s_seq = seq;
    s_t_sent = board_millis();
    s_wait = 1;
    return crc;
}

int spi_fpga_poll(uint32_t now, uint8_t n_read, spi_result_t *res, uint8_t *raw)
{
    uint8_t buf[SPI_READ_HIL];
    if (!s_wait)
        return SPI_PENDING;
    if (s_proto == 1 || n_read > SPI_READ_HIL)
        n_read = SPI_READ_V1;
    if (!g_fpga_irq) {
        if (now - s_t_sent <= SPI_TIMEOUT_MS)
            return SPI_PENDING;
        s_wait = 0;
        return count(SPI_E_TIMEOUT);
    }
    g_fpga_irq = 0;
    s_wait = 0;
    read_bytes(buf, n_read);
    if (raw)
        for (uint8_t i = 0; i < n_read; i++) raw[i] = buf[i];
    if (s_proto == 1)
        return count(spi_parse_v1(buf, res));
    return count(spi_parse_v3(buf, n_read, s_seq, res));
}

int spi_fpga_transact(uint8_t seq, const int8_t *seg1, uint16_t n1, const int8_t *seg2, uint16_t n2,
                      uint8_t n_read, spi_result_t *res, uint8_t *raw)
{
    int rc;
    spi_fpga_start(seq, seg1, n1, seg2, n2);
    while ((rc = spi_fpga_poll(board_millis(), n_read, res, raw)) == SPI_PENDING) { }
    return rc;
}
