/* host_startup.c — bảng vector tối giản cho ảnh test chạy trong trình giả lập (không dùng startup của SONiX). */
#include <stdint.h>

extern void __main(void);           /* MicroLIB: khởi tạo vùng RW/ZI rồi gọi main() */

void Reset_Handler(void) { __main(); }
static void Fault_Handler(void)
{
    *(volatile uint32_t *)0x40000008u = 0xFA017u;   /* báo lỗi cứng cho trình giả lập */
    for (;;) { }
}

__attribute__((section("RESET"), used))
const uintptr_t __Vectors[4] = {
    0x20040000u,                    /* SP đầu, đỉnh RAM 256 KB của trình giả lập */
    (uintptr_t)Reset_Handler,
    (uintptr_t)Fault_Handler,       /* NMI */
    (uintptr_t)Fault_Handler,       /* HardFault */
};
