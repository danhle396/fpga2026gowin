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
#define SEQ_SELFTEST    0xEE    /* A.10 */

/* Phần cứng nối cố định (đề cương v2.2): SN32F407 → UART → ESP32 → SPI → FPGA (bitstream 3, giao thức v3).
 * Khung v3 dựng và đọc trên ESP32 (hub.c), không có IRQ/RST_N: ESP32 hỏi vòng, SPI_TIMEOUT_MS là hạn chờ kết quả. */

/* Còi PZ1 của EVK theo lệnh ESP32 (node_link.h) qua dây ESP32 GPIO17 → MCU P3.2 (nhóm thêm dây 28/10).
 * 1: MCU nhận lệnh bật/tắt còi ở P3.2. 0: MCU bỏ qua P3.2 (dùng khi chưa có dây: chân thả nổi có thể ra byte rác trùng
 * lệnh bật còi). ESP32 luôn gửi lệnh, không có dây thì vô hại. */
#ifndef COI_TU_ESP32
#define COI_TU_ESP32    1
#endif

/* Vị trí đeo (28/10). Mọi phần sau MCU (CNN, khối A.8, tư thế A.11) dùng trục người: X trước, Y trái, Z lên.
 * hub.c đổi trục cảm biến về trục người trước khi xử lý (hub_doi_truc). Mã ±1/±2/±3 = ± trục X/Y/Z của MPU6050.
 *   0 = mũ: cảm biến đã đúng trục người.
 *   1 = ngực (đo ket_qua_board/truc_nguc_20261028_151551, docs/bao_cao/2026-10-28_deo_nguc): X = +Z, Y = −X, Z = −Y. */
#ifndef FW_VI_TRI_DEO
#define FW_VI_TRI_DEO   1
#endif
/* ACC_OFF_*: offset gia tốc theo trục người (LSB), trừ sau khi đổi trục. Ngực: đo 28/10 khi đeo, 9 tư thế yên
 * (docs/bao_cao/2026-10-28_tu_the_nguc): trước khi trừ |g| = 1.840–2.254, sau khi trừ 2.034–2.054. Offset làm
 * |a| lệch > 120 LSB lúc yên → posture.c tưởng đang cử động suốt, độ cao trôi. Đổi cảm biến thì đo lại. */
#if FW_VI_TRI_DEO == 1
#define TRUC_X  3
#define TRUC_Y  (-1)
#define TRUC_Z  (-2)
#define ACC_OFF_X  204
#define ACC_OFF_Y  (-3)
#define ACC_OFF_Z  (-4)
#else
#define TRUC_X  1
#define TRUC_Y  2
#define TRUC_Z  3
#define ACC_OFF_X  0
#define ACC_OFF_Y  0
#define ACC_OFF_Z  0
#endif

/* ---- A.8 khối và Safety FSM (giá trị đầu; chốt ở AI-10) ---- */
#define BLK_SAMPLES     32      /* 32 mẫu thô 100 Hz = 0,32 s */
#define T_STILL_A       300     /* LSB ở ±16 g, ≈ 0,15 g */
#define T_STILL_G       250     /* LSB ở ±2000 °/s, ≈ 15 °/s */
#define STILL_BLOCKS    8       /* 8 khối = 2,56 s */
#define T_TILT          1450    /* |az_tb| < 1450 ↔ đầu lệch 45°–135° khỏi phương thẳng đứng (nằm) */

/* ---- xác nhận ngã thật (nga.h, 28/10; bản đầu, chốt bằng dữ liệu đeo ngực của nhóm) ---- */
#define NGA_VA_CHAM_LSB     5120        /* đỉnh |a| ≥ 2,5 g: va chạm, cần thêm nằm / hạ ngực / bất động */
#define NGA_VA_CHAM_MANH    6144        /* đỉnh |a| ≥ 3,0 g: va chạm mạnh, đủ để xác nhận (ngã quỳ, ngã ngồi, ngã rồi
                                         * đứng dậy: D1 người 102 đỉnh 2,9–5,0 g, Δh đo không tin được) */
#define NGA_VA_CHAM_KHOI    12u         /* tìm đỉnh trong 12 khối (3,84 s) trước SUSPECT */
#define NGA_TRUOC_DEN       10u         /* "trước đó thẳng": xét khối lùi 10..32 (3,2–10,2 s trước SUSPECT); ngất xỉu
                                         * (D1 917) gục từ từ, CNN nghi muộn, nên phải nhìn lùi xa */
#define NGA_TRUOC_TU        32u
#define NGA_HA_H            1044189     /* ngực hạ ≥ 0,5 m (đơn vị posture.c: 2048·10⁴/9,80665 mỗi mét) */
#define NGA_CHO_MS          4000u       /* chờ nằm / hạ ngực tối đa 4 s sau khi vào SUSPECT */
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
