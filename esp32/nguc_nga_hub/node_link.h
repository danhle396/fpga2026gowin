/*
 * node_link.h — khung truyền MCU → ESP32 qua UART (phần cứng nối cố định theo codecanthiet, 24/10:
 * MCU TX P3.1 → ESP32 GPIO16, 115200 8N1, một chiều). C thuần: MCU dùng để đóng gói, ESP32 dùng để tách khung.
 *
 * Khung cùng định dạng đã chạy trên phần cứng của nhóm (uart_packet_bridge):
 *   F1 7E | SEQ | LEN lo | LEN hi | payload[LEN] | CRC lo | CRC hi
 *   CRC-16/CCITT-FALSE (0x1021, khởi tạo 0xFFFF) trên SEQ, 2 byte LEN và payload; gửi byte thấp trước.
 * Payload mẫu (LEN = 14): 'D' | AX AY AZ GX GY GZ (INT16 LE, gyro đã trừ offset hiệu chuẩn) | KEYS
 *   KEYS bit 0 = SW3 (nút duy nhất: bật/tắt, CANCEL, SOS), bit 1 = SW6 (nút đánh dấu).
 * Ngoài khung, MCU vẫn in chữ ASCII (dòng "# ...", STAT); bên nhận gom thành dòng và chuyển tiếp nguyên văn.
 * Bên nhận chịu nhiễu (28/10, đeo ngực: 137 khung hỏng làm mất 507 mẫu, ≈ 3,7 mẫu mỗi khung hỏng): chỉ nhận LEN = 14
 * (khung duy nhất), và khi một khung hỏng thì dò lại F1 7E ngay trong các byte của khung đó (byte rơi mất làm khung
 * sau bắt đầu giữa khung hỏng), nên một lần nhiễu chỉ mất 1 mẫu (trước: rơi 1 byte hay LEN nhiễu mất 2;
 * tools/m0_test.py test_node_nhieu).
 */
#ifndef NODE_LINK_H
#define NODE_LINK_H

#include <stdint.h>

#define NODE_SOF0        0xF1
#define NODE_SOF1        0x7E
#define NODE_T_SAMPLE    'D'
#define NODE_SAMPLE_LEN  14u
#define NODE_FRAME_MAX   (5u + 32u + 2u)
#define NODE_SAMPLE_FRAME (5u + NODE_SAMPLE_LEN + 2u)      /* 21 byte */
#define NODE_LINE_MAX    96u

/* Chiều ngược ESP32 → MCU (dây thêm 25/10: ESP32 GPIO17 → MCU P3.2, J10 URX_P32), mỗi lệnh 1 byte:
 * còi PZ1 của EVK bật / tắt theo app_buzzer() của Safety FSM chạy trên ESP32. ESP32 gửi khi đổi và nhắc lại mỗi
 * NODE_BUZZ_REFRESH_MS; MCU tắt còi nếu quá NODE_BUZZ_TIMEOUT_MS không nhận lệnh (ESP32 reset hay rút dây). */
#define NODE_CMD_BUZZ_OFF     0xB0
#define NODE_CMD_BUZZ_ON      0xB1
#define NODE_BUZZ_REFRESH_MS  100u
#define NODE_BUZZ_TIMEOUT_MS  500u
/* Kiểu âm còi (28/10): 1 byte NODE_CMD_COI_KIEU + k, ESP32 gửi khi đổi và nhắc lại mỗi NODE_COI_KIEU_REFRESH_MS
 * (MCU khởi động lại vẫn về đúng kiểu). 0 = mức cao liên tục (còi chủ động); 1..5 = sóng vuông 500 / 2000 / 2700 /
 * 3500 / 4000 Hz (còi thụ động to nhất gần tần số cộng hưởng). */
#define NODE_CMD_COI_KIEU     0xC0
#define COI_SO_KIEU           6u
#define COI_KIEU_LIEN_TUC     0u
#define COI_KIEU_500HZ        1u
#define COI_KIEU_2KHZ         2u
#define COI_KIEU_CHOT         COI_KIEU_2KHZ   /* nhóm nghe thử 6 kiểu trên board 28/10, chốt 2 kHz */
#define NODE_COI_KIEU_REFRESH_MS 1000u

/* Đóng gói một mẫu vào out (≥ NODE_SAMPLE_FRAME byte); trả về số byte. */
uint16_t node_pack_sample(uint8_t *out, uint8_t seq, const int16_t r[6], uint8_t keys);

enum { NODE_NONE = 0, NODE_SAMPLE, NODE_TEXT, NODE_BAD };

typedef struct {
    uint8_t  st, seq, buf[32];
    uint8_t  raw[NODE_SAMPLE_FRAME], nraw, quet;   /* byte sau F1 7E của khung đang nhận; quet = đang dò lại */
    uint16_t len, n, crc;
    char     line[NODE_LINE_MAX + 1];
    uint8_t  nline;
    /* kết quả khung vừa tách */
    int16_t  r[6];
    uint8_t  keys, rx_seq;
    /* thống kê */
    uint32_t n_ok, n_bad, n_lost;
    uint8_t  have_seq, last_seq;
} node_rx_t;

void node_rx_init(node_rx_t *s);
/* Đưa từng byte vào; trả về NODE_SAMPLE (mẫu trong s->r, s->keys), NODE_TEXT (dòng chữ trong s->line),
 * NODE_BAD (khung hỏng: CRC sai hoặc LEN lạ), hoặc NODE_NONE. Mẫu mất được đếm theo SEQ nhảy cóc (s->n_lost). */
int  node_rx_byte(node_rx_t *s, uint8_t b);

#endif
