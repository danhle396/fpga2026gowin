// do_thoi_gian_fpga.ino — sketch TẠM để đo thời gian suy luận FPGA trên board (không phải firmware sản phẩm).
// Nối dây giống esp32/nguc_nga_hub: CS 27, SCK 18, MOSI 23, MISO 19, SPI mode 0, 1 MHz. Không dùng WiFi, không ghi NVS.
//
// Mỗi khung: ghi 772 byte [A5][SEQ][768][CRC-16], rồi đọc thăm 1 byte đến khi thấy 0x5A, rồi đọc 20 byte.
// Đọc thăm 1 byte không làm mất kết quả: RTL chỉ xóa valid khi đọc xong byte thứ 7 (spi_result_tx_v3.v, read_done).
// Đọc thăm lúc FPGA đang tính cũng an toàn: byte đầu 0x00 đưa parser về S_IGNORE (packet_parser_v3.v).
//
// Số đo:
//   cyc    bộ đếm CYCLES trong RTL, byte 15..17 của khung đọc, đếm từ payload_done tới inference_done.
//   t_lo   µs từ lúc ghi xong tới lần CS xuống cuối cùng còn đọc được 0x00 (kết quả chưa sẵn sàng).
//   t_hi   µs từ lúc ghi xong tới lần CS xuống đầu tiên đọc được 0x5A (kết quả đã sẵn sàng).
// Thời điểm xong thật nằm giữa t_lo và t_hi, đo bằng đồng hồ của ESP32, độc lập với clock FPGA.
//
// Ba chế độ, mỗi chế độ N khung:
//   A  khung tự kiểm A.10 (LFSR mầm 0xACE1, SEQ 0xEE), kiểm thêm 7 byte đầu đúng đáp án của bitstream.
//   B  dữ liệu giả ngẫu nhiên, mỗi khung một mầm, SEQ tăng dần: xem CYCLES có đổi theo dữ liệu không.
//   C  như A nhưng không đọc thăm khi FPGA đang tính (chờ 6 ms rồi mới đọc, giống hub.c): xem đọc thăm có ảnh hưởng không.
// Gõ R + Enter để chạy, in từng khung rồi END.
#include <SPI.h>

#define FPGA_CS_PIN   27
#define FPGA_SCK_PIN  18
#define FPGA_MOSI_PIN 23
#define FPGA_MISO_PIN 19
#define MCU_TX_PIN    17            // giữ mức cao (UART rảnh) để MCU không nhận rác trên dây lệnh còi
#define SPI_HZ        1000000UL
#define USB_BAUD      460800
#define N_KHUNG       2000
#define TIMEOUT_US    50000UL
#define CHO_C_US      6000UL

static const uint8_t DAP_AN_7[7] = { 0x5A, 0xEE, 0x01, 0x03, 0x00, 0x06, 0x43 };   // selftest_expect_v3_e2_n2.h

enum { RC_OK = 0, RC_TIMEOUT, RC_HDR, RC_CRC, RC_STATUS, RC_SEQ, RC_CLASS, RC_TAIL, RC_DAP_AN };

typedef struct {
    uint32_t cyc, t_w, t_lo, t_hi;
    uint16_t npoll;
    uint8_t  rc, cls, score;
} ket_t;

static uint8_t s_khung[772];
static ket_t   s_kq[N_KHUNG];
static uint8_t s_f0[20];

static uint16_t crc16(const uint8_t *p, size_t n)
{
    uint16_t c = 0xFFFF;
    while (n--) {
        c ^= (uint16_t)(*p++) << 8;
        for (int i = 0; i < 8; i++) c = (c & 0x8000) ? (uint16_t)((c << 1) ^ 0x1021) : (uint16_t)(c << 1);
    }
    return c;
}

static void dung_khung(uint8_t seq, uint16_t mam)
{
    uint16_t s = mam;
    s_khung[0] = 0xA5;
    s_khung[1] = seq;
    for (int i = 0; i < 768; i++) {
        uint16_t lsb = s & 1u;
        s >>= 1;
        if (lsb) s ^= 0xB400u;
        s_khung[2 + i] = (uint8_t)s;
    }
    uint16_t c = crc16(s_khung, 770);
    s_khung[770] = (uint8_t)(c >> 8);
    s_khung[771] = (uint8_t)c;
}

static inline void cs_len(void)  { digitalWrite(FPGA_CS_PIN, HIGH); SPI.endTransaction(); }
static inline void cs_xuong(void) { SPI.beginTransaction(SPISettings(SPI_HZ, MSBFIRST, SPI_MODE0)); digitalWrite(FPGA_CS_PIN, LOW); }

static void mot_khung(ket_t *k, uint8_t seq, bool doc_tham, bool kiem_dap_an, uint8_t *raw)
{
    uint32_t t_bat_dau = micros();
    cs_xuong();
    SPI.writeBytes(s_khung, sizeof s_khung);
    uint32_t t0 = micros();
    cs_len();
    k->t_w = t0 - t_bat_dau;
    k->t_lo = 0;
    k->t_hi = 0;
    k->npoll = 0;
    k->rc = RC_TIMEOUT;
    k->cyc = 0;
    k->cls = 0xFF;
    k->score = 0;

    if (!doc_tham) while (micros() - t0 < CHO_C_US) { }

    for (;;) {
        uint32_t t_cs = micros();
        cs_xuong();
        uint8_t b = SPI.transfer(0x00);
        cs_len();
        k->npoll++;
        if (b == 0x5A) { k->t_hi = t_cs - t0; break; }
        k->t_lo = t_cs - t0;
        if (t_cs - t0 > TIMEOUT_US) return;
    }

    memset(raw, 0, 20);
    cs_xuong();
    for (int i = 0; i < 20; i++) raw[i] = SPI.transfer(0x00);
    cs_len();

    k->cls = raw[3];
    k->score = raw[4];
    k->cyc = ((uint32_t)raw[15] << 16) | ((uint32_t)raw[16] << 8) | raw[17];
    if (raw[0] != 0x5A)                                                    k->rc = RC_HDR;
    else if (crc16(raw, 5) != (uint16_t)((raw[5] << 8) | raw[6]))          k->rc = RC_CRC;
    else if (raw[2] != 0x01)                                               k->rc = RC_STATUS;
    else if (raw[1] != seq)                                                k->rc = RC_SEQ;
    else if (raw[3] > 3)                                                   k->rc = RC_CLASS;
    else if (crc16(&raw[7], 11) != (uint16_t)((raw[18] << 8) | raw[19]))   k->rc = RC_TAIL;
    else if (kiem_dap_an && memcmp(raw, DAP_AN_7, 7))                      k->rc = RC_DAP_AN;
    else                                                                   k->rc = RC_OK;
}

static void in_hex(const char *ten, const uint8_t *b, int n)
{
    Serial.print(ten);
    for (int i = 0; i < n; i++) {
        Serial.print(b[i] < 16 ? " 0" : " ");
        Serial.print(b[i], HEX);
    }
    Serial.println();
}

static void chay_che_do(char m)
{
    uint8_t raw[20];
    if (m != 'B') dung_khung(0xEE, 0xACE1u);
    for (int i = 0; i < N_KHUNG; i++) {
        uint8_t seq = 0xEE;
        if (m == 'B') {
            seq = (uint8_t)i;
            uint16_t mam = (uint16_t)(0xACE1u ^ ((uint32_t)(i + 1) * 0x9E37u));
            dung_khung(seq, mam ? mam : 1u);
        }
        mot_khung(&s_kq[i], seq, m != 'C', m != 'B', raw);
        if (i == 0) memcpy(s_f0, raw, 20);
        delayMicroseconds(200);
    }
    Serial.print("MODE,"); Serial.println(m);
    in_hex("F0", s_f0, 20);
    for (int i = 0; i < N_KHUNG; i++) {
        const ket_t *k = &s_kq[i];
        char s[80];
        snprintf(s, sizeof s, "F,%d,%u,%lu,%lu,%lu,%lu,%u,%u,%u", i, k->rc, (unsigned long)k->cyc, (unsigned long)k->t_w,
                 (unsigned long)k->t_lo, (unsigned long)k->t_hi, k->npoll, k->cls, k->score);
        Serial.println(s);
    }
    Serial.flush();
}

void setup()
{
    pinMode(MCU_TX_PIN, OUTPUT);
    digitalWrite(MCU_TX_PIN, HIGH);
    pinMode(FPGA_CS_PIN, OUTPUT);
    digitalWrite(FPGA_CS_PIN, HIGH);
    SPI.begin(FPGA_SCK_PIN, FPGA_MISO_PIN, FPGA_MOSI_PIN, FPGA_CS_PIN);
    Serial.begin(USB_BAUD);
    delay(200);
    Serial.println("# do_thoi_gian_fpga san sang, go R de chay");
}

void loop()
{
    if (!Serial.available()) { delay(5); return; }
    int c = Serial.read();
    if (c != 'R' && c != 'r') return;
    Serial.print("# bat dau, N="); Serial.print(N_KHUNG);
    Serial.print(", SPI Hz="); Serial.print(SPI_HZ);
    Serial.print(", CPU MHz="); Serial.println(getCpuFrequencyMhz());
    chay_che_do('A');
    chay_che_do('B');
    chay_che_do('C');
    Serial.println("END");
}
