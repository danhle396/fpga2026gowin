/*
 * fw_config.h — hằng số của SPEC v3 (PROJECT_MASTER.md, Phụ lục A) dùng chung cho firmware và bộ test trên PC.
 * Đổi một số ở đây thì đổi cùng lúc ở Phụ lục A và chạy lại `bash firmware/build.sh test`.
 */
#ifndef FW_CONFIG_H
#define FW_CONFIG_H

/* ---- A.2 tiền xử lý ---- */
#define PRE_CH          6       /* AX AY AZ GX GY GZ */
#define ACC_SHIFT       7       /* 1 mức INT8 = 1/16 g ở ±16 g */
#define GYR_SHIFT       6       /* 1 mức INT8 = 3,90 °/s ở ±2000 °/s */

/* ---- A.3 cửa sổ ---- */
#define PRE_WIN         128     /* mẫu 50 Hz trong một cửa sổ (2,56 s) */
#define PRE_HOP         16      /* cửa sổ mới sau mỗi 16 mẫu (0,32 s) */
#define PRE_BYTES       (PRE_WIN * PRE_CH)      /* 768 */

/* ---- A.4 lớp ---- */
#define CLS_NORMAL      0
#define CLS_IMPACT      1
#define CLS_RESERVED    2
#define CLS_FALL        3

/* ---- A.7 giao tiếp ---- */
#define SPI_HDR_WRITE   0xA5
#define SPI_HDR_READ    0x5A
#define SPI_FRAME_V3    (2 + PRE_BYTES + 2)     /* 772 */
#define SPI_FRAME_V1    (2 + PRE_BYTES + 1)     /* 771, khung CRC-8 của RTL hiện có */
#define SPI_READ_RUN    7
#define SPI_READ_HIL    20
#define SPI_READ_V1     7
#define SPI_TIMEOUT_MS  50
#define SPI_ERR_RESET   3       /* 3 lỗi liên tiếp → RST_N thấp ≥ 1 ms */
#define SPI_DIV_TEST    23      /* SCK = 48 MHz / (2·23 + 2) = 1 MHz */
#define SPI_DIV_RUN     5       /* SCK = 48 MHz / (2·5 + 2)  = 4 MHz */
#define SEQ_SELFTEST    0xEE    /* A.10 */

/* Bitstream đang nạp trong Kiwi: quyết định giao thức và đáp án tự kiểm A.10. Phải khớp file .fs đã nạp.
 *   3 = project chính fpga/ = bitstreams/3_v3_e2_n2 (giao thức v3, engine E2, mô hình N2)  ← mặc định
 *   1 = bitstreams/1_e1_proto1_sisfall (PROTO 1, E1; chỉ để gỡ lỗi)   2 = bitstreams/2_v3_e1_sisfall (v3, E1) */
#ifndef FW_BITSTREAM
#define FW_BITSTREAM    3
#endif
#define FW_PROTO        (FW_BITSTREAM == 1 ? 1 : 3)

/* Phần cứng nối cố định theo codecanthiet của nhóm (24/10): MCU TX P3.1 → ESP32 GPIO16 (một chiều, 115200);
 * ESP32 GPIO27/18/23/19 → Kiwi J2 (CS, SCK, MOSI, MISO); MCU không nối SPI/IRQ/RST_N với FPGA; INT của MPU6050 không nối.
 *   FW_NODE 1: MCU là nút cảm biến: đọc MPU6050 100 Hz, gửi từng mẫu cho ESP32 (node_link.h); tiền xử lý, khung v3,
 *              Safety FSM chạy trên ESP32 (hub.c, esp32/mu_nga_hub/). FW_NODE 0: MCU nối thẳng FPGA như thiết kế gốc.
 *   IMU_INT_WIRED 0: không có dây INT → hỏi thanh ghi INT_STATUS (0x3A) của MPU6050 mỗi mili giây. */
#ifndef FW_NODE
#define FW_NODE         1
#endif
#ifndef IMU_INT_WIRED
#define IMU_INT_WIRED   0
#endif

/* ---- A.8 khối và Safety FSM (giá trị đầu; chốt ở AI-10) ---- */
#define BLK_SAMPLES     32      /* 32 mẫu thô 100 Hz = 0,32 s */
#define T_STILL_A       300     /* LSB ở ±16 g, ≈ 0,15 g */
#define T_STILL_G       250     /* LSB ở ±2000 °/s, ≈ 15 °/s */
#define STILL_BLOCKS    8       /* 8 khối = 2,56 s */
#define T_TILT          1450    /* |az_tb| < 1450 ↔ đầu lệch 45°–135° khỏi phương thẳng đứng (nằm) */
#define TILT_EN         1
#define VOTE_K          2
#define VOTE_N          3
#define T_SCORE         0       /* chưa chốt (AI-10); 0 = mọi cửa sổ FALL đều tính phiếu */
#define WEAR_OFF_MS     3000    /* MONITOR → STANDBY khi WEAR = 0 liên tục 3 s */
#define WEAR_RECENT_MS  3000    /* MONITOR → SUSPECT cần mũ được đội trong 3 s gần nhất */
#define SUSPECT_TIMEOUT_MS  8000
#define PRE_ALARM_MS    10000
#define COOLDOWN_MS     30000
#define SOS_HOLD_MS     3000
#define ALARM_HOLD_MS   1000
/* Một nút cho bật/tắt + CANCEL + SOS (pwr_btn.h, đề cương v2.1). 1 = cờ "hệ thống bật" của nút thay cho WEAR
 * (WEAR thật, nếu có, vẫn AND vào); 0 = nút chỉ là CANCEL/SOS như A.8. */
#ifndef BTN_POWER
#define BTN_POWER       1
#endif

#endif
