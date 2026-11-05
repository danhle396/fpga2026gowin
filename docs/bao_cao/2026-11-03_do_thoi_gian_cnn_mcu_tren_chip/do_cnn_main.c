/*
 * do_cnn_main.c — chương trình TẠM đo thời gian suy luận CNN N2 trên chip SN32F407 (không phải firmware sản phẩm).
 * Cùng clock với firmware chính (board_init: IHRC 48 MHz, wait-state của SystemCoreClockUpdate), cnn_mcu.c của FW-15.
 * Weight nằm trong Flash, cửa sổ vào chép sang RAM như khi chạy thật. Tắt ngắt lúc đo, SysTick đếm HCLK.
 * Kết quả in qua UART, ESP32 chuyển tiếp thành dòng "MCU ...":
 *   MUL,<chu kỳ MULS>                  đo bộ nhân
 *   CNN,<cửa sổ>,<lần>,<chu kỳ>,<đúng> mỗi lần suy luận, đúng = khớp golden cả lớp, SCORE, 4 logit
 *   CAL,0 / CAL,1                      cách nhau đúng 20.000 ms theo clock MCU, để đối chiếu với đồng hồ máy tính
 */
#include <string.h>
#include "SN32F400.h"
#include "board.h"
#include "so_lieu.h"

#define SO_LAN 20u

static int8_t s_x[768];

static void systick_dem_bat(void)
{
    __disable_irq();
    SysTick->CTRL = 0u;
    SysTick->LOAD = 0xFFFFFFu;
    SysTick->VAL = 0u;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk;
}

static void systick_dem_tat(void)
{
    SysTick_Config(SystemCoreClock / 1000u);
    __enable_irq();
}

/* Chu kỳ MULS: hiệu giữa hai vòng lặp chỉ khác một lệnh, cộng 1 chu kỳ của MOVS bị thay. */
static uint32_t do_vong(int nhan)
{
    uint32_t a = 3u, b = 0x12345u, n = 1000u, t0, t1;
    systick_dem_bat();
    t0 = SysTick->VAL;
    if (nhan)
        __asm volatile("1: muls %0, %1, %0\n subs %2, %2, #1\n bne 1b\n" : "+l"(a), "+l"(b), "+l"(n) : : "cc");
    else
        __asm volatile("1: movs %0, %1\n subs %2, %2, #1\n bne 1b\n" : "+l"(a), "+l"(b), "+l"(n) : : "cc");
    t1 = SysTick->VAL;
    systick_dem_tat();
    return t0 - t1;
}

static uint32_t mot_lan(const cnn_model_t *m, const int8_t *x, int32_t lg[4], uint8_t *diem, int *lop, uint32_t *tran)
{
    uint32_t t0, t1;
    systick_dem_bat();
    t0 = SysTick->VAL;
    *lop = cnn_mcu_run(m, x, lg, diem);
    t1 = SysTick->VAL;
    *tran = (SysTick->CTRL >> 16) & 1u;     /* COUNTFLAG: quá 2^24 chu kỳ thì số đo không dùng được */
    systick_dem_tat();
    return t0 - t1;
}

int main(void)
{
    board_init();
    board_delay_ms(1500);
    for (;;) {
        uart_puts("\n# BAT DAU do CNN N2 tren SN32F407\n");
        uart_puts("# HCLK="); uart_put_dec((int32_t)SystemCoreClock);
        uart_puts(" LPCTRL="); uart_put_hex(SN_FLASH->LPCTRL, 8); uart_puts("\n");
        uint32_t v0 = do_vong(0), v1 = do_vong(1);
        uart_puts("MUL,"); uart_put_dec((int32_t)v0); uart_puts(","); uart_put_dec((int32_t)v1); uart_puts("\n");
        for (uint32_t i = 0; i < SO_CUA_SO; i++) {
            memcpy(s_x, VAO[i], sizeof s_x);
            for (uint32_t k = 0; k < SO_LAN; k++) {
                int32_t lg[4];
                uint8_t diem;
                int lop;
                uint32_t tran;
                uint32_t c = mot_lan(&MO_HINH, s_x, lg, &diem, &lop, &tran);
                const dap_an_t *d = &DAP_AN[i];
                int dung = lop == d->lop && diem == d->diem && !memcmp(lg, d->lg, sizeof lg) && !tran;
                uart_puts("CNN,"); uart_puts(d->ten); uart_puts(","); uart_put_dec((int32_t)k); uart_puts(",");
                uart_put_dec((int32_t)c); uart_puts(","); uart_put_dec(dung); uart_puts("\n");
                uart_flush();
            }
        }
        uart_puts("CAL,0\n"); uart_flush();
        board_delay_ms(20000);
        uart_puts("CAL,1\n"); uart_flush();
        uart_puts("# KET THUC\n"); uart_flush();
        board_delay_ms(2000);
    }
}
