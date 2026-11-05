// hil_board.ino — sketch TẠM phát dữ liệu thật qua ESP32 + FPGA thật (không phải firmware sản phẩm, không dùng WiFi, không ghi NVS).
// Lõi hub.c, nga.c, posture.c, safety.c, app_core.c... chép nguyên từ esp32/nguc_nga_hub; SPI giống hệt sản phẩm: 1 MHz, mode 0.
// PC gửi qua USB 921600. MCU vẫn chạy nhưng không dùng mẫu của MCU; GPIO17 giữ mức cao nên không có lệnh còi.
//
// T                               tự kiểm A.10 bằng hub_selftest. Trả: TK,<PASS|FAIL>,<7 byte hex>
// W idx(u32) 768 byte crc16       một cửa sổ: dựng khung v3 → FPGA → đọc 20 byte. Trả: r,<idx>,<rc>,<t_us>,<40 hex>
// I nga_en pace in_r              phiên mới: hub_init. pace 1 = theo đúng thời gian thực, 0 = chỉ theo thời gian thực khi đang chờ FPGA
// B n(u8) n×12 byte crc16         n mẫu 100 Hz (trục cảm biến như MCU gửi). Mỗi mẫu một khe 10 ms theo thứ tự của
//                                 firmware/test/host_main.c mode 11: hub_sample, hub_tick, rồi hub_poll ở ms 1..9. Trả: a
// E                               kết thúc phiên. Trả: E,<mẫu>,<gửi>,<ok>,<timeout>,<lỗi>,<bỏ qua>,<xác nhận>,<loại>
// Sự kiện trong phiên: F,t,st,why  N,t,hd,ly_do,truoc,co_vc,peak2,wpeak2,nghieng  P,t,tu_the  R,t,seq,cls,score,rc
// Lỗi đường truyền: X,<mô tả>, phép đo đó phải chạy lại.
#include <SPI.h>

extern "C" {
#include "hub.h"
#include "safety.h"
#include "spi_frame.h"
#include "crc.h"
}
#include "selftest_expect_v3_e2_n2.h"

#define MCU_TX_PIN    17
#define FPGA_CS_PIN   27
#define FPGA_SCK_PIN  18
#define FPGA_MOSI_PIN 23
#define FPGA_MISO_PIN 19
#define SPI_HZ        1000000UL
#define USB_BAUD      921600
#define TIMEOUT_US    50000UL

static hub_t H;
static uint32_t s_k, s_send_us, s_send_v, s_t0_us;
static uint8_t s_pace, s_in_r;

static uint32_t cs_gap_us() { return 3000000UL / SPI_HZ + 2; }

static void spi_write_fn(const uint8_t *b, uint16_t n, void *ctx)
{
    (void)ctx;
    SPI.beginTransaction(SPISettings(SPI_HZ, MSBFIRST, SPI_MODE0));
    digitalWrite(FPGA_CS_PIN, LOW);
    delayMicroseconds(cs_gap_us());
    SPI.writeBytes(b, n);
    delayMicroseconds(cs_gap_us());
    digitalWrite(FPGA_CS_PIN, HIGH);
    SPI.endTransaction();
    delayMicroseconds(cs_gap_us());
}

static void spi_read_fn(uint8_t *b, uint8_t n, void *ctx)
{
    (void)ctx;
    SPI.beginTransaction(SPISettings(SPI_HZ, MSBFIRST, SPI_MODE0));
    digitalWrite(FPGA_CS_PIN, LOW);
    delayMicroseconds(cs_gap_us());
    for (uint8_t i = 0; i < n; i++) b[i] = SPI.transfer(0x00);
    delayMicroseconds(cs_gap_us());
    digitalWrite(FPGA_CS_PIN, HIGH);
    SPI.endTransaction();
    delayMicroseconds(cs_gap_us());
}

static const hub_io_t IO = { spi_write_fn, spi_read_fn, nullptr };
static uint32_t ms_fn(void) { return millis(); }

static bool doc_du(uint8_t *b, size_t n)
{
    return Serial.readBytes(b, n) == n;
}

static void loi(const char *s)
{
    Serial.print("X,");
    Serial.println(s);
    Serial.flush();
    delay(300);
    while (Serial.available()) Serial.read();
}

static void cmd_tu_kiem()
{
    uint8_t got[7];
    hub_init(&H, millis());
    int ok = hub_selftest(&H, &IO, ms_fn, selftest_frame7, got);
    char s[64];
    snprintf(s, sizeof s, "TK,%s,%02X%02X%02X%02X%02X%02X%02X", ok ? "PASS" : "FAIL", got[0], got[1], got[2], got[3], got[4], got[5], got[6]);
    Serial.println(s);
}

static uint8_t s_khung[SPI_FRAME_V3];
static uint16_t s_nkhung;
static void vao_khung(uint8_t b, void *ctx) { (void)ctx; s_khung[s_nkhung++] = b; }

static void cmd_cua_so()
{
    static uint8_t pk[4 + PRE_BYTES + 2];
    if (!doc_du(pk, sizeof pk)) { loi("W thieu byte"); return; }
    if (crc16_ccitt(pk, 4 + PRE_BYTES) != (uint16_t)((pk[4 + PRE_BYTES] << 8) | pk[4 + PRE_BYTES + 1])) { loi("W sai crc"); return; }
    uint32_t idx;
    memcpy(&idx, pk, 4);
    s_nkhung = 0;
    (void)spi_frame_emit(3, (uint8_t)idx, (const int8_t *)&pk[4], PRE_BYTES, (const int8_t *)&pk[4], 0, &crc16_sw, vao_khung, nullptr);
    spi_write_fn(s_khung, s_nkhung, nullptr);
    uint32_t t0 = micros(), t;
    uint8_t rc = 1, b = 0;
    do {
        t = micros() - t0;
        SPI.beginTransaction(SPISettings(SPI_HZ, MSBFIRST, SPI_MODE0));
        digitalWrite(FPGA_CS_PIN, LOW);
        b = SPI.transfer(0x00);                  // đọc thăm 1 byte không làm mất kết quả (read_done chỉ ở byte thứ 7)
        digitalWrite(FPGA_CS_PIN, HIGH);
        SPI.endTransaction();
        if (b == 0x5A) { rc = 0; break; }
    } while (t < TIMEOUT_US);
    uint8_t raw[SPI_READ_HIL];
    memset(raw, 0, sizeof raw);
    if (rc == 0) spi_read_fn(raw, SPI_READ_HIL, nullptr);
    char s[80];
    int n = snprintf(s, sizeof s, "r,%lu,%u,%lu,", (unsigned long)idx, rc, (unsigned long)t);
    for (int i = 0; i < SPI_READ_HIL; i++) n += snprintf(s + n, sizeof s - n, "%02X", raw[i]);
    Serial.println(s);
}

static void pace(uint32_t v)
{
    if (s_pace) { while ((uint32_t)(micros() - s_t0_us) < v * 1000UL) { } }
    else if (H.wait) { while ((uint32_t)(micros() - s_send_us) < (v - s_send_v) * 1000UL) { } }
}

static void poll_mot(uint32_t v)
{
    pace(v);
    int rc = hub_poll(&H, &IO, v);
    if (rc != SPI_PENDING && s_in_r) {
        char s[48];
        snprintf(s, sizeof s, "R,%lu,%u,%d,%u,%d", (unsigned long)v, H.last.seq, rc == SPI_OK ? H.last.cls : -1, H.last.score, rc);
        Serial.println(s);
    }
}

static void mot_mau(const int16_t raw[6])
{
    char s[96];
    uint32_t t = 10u * s_k;
    pace(t);
    uint32_t n0 = H.n_sent, us0 = micros();
    unsigned f = hub_sample(&H, &IO, raw, 0, t);
    if (H.n_sent != n0) { s_send_us = us0; s_send_v = t; }
    if (f & HUB_POSTURE) {
        snprintf(s, sizeof s, "P,%lu,%s", (unsigned long)t, posture_name(H.pos.tt));
        Serial.println(s);
    }
    hub_tick(&H, t, 0);
    if (H.app.fsm.events & SAFETY_EV_STATE) {
        snprintf(s, sizeof s, "F,%lu,%u,%u", (unsigned long)t, (unsigned)H.app.fsm.st, (unsigned)H.app.fsm.why);
        Serial.println(s);
    }
    if (H.nga_hd != NGA_HD_KHONG) {
        snprintf(s, sizeof s, "N,%lu,%u,%u,%u,%u,%lu,%lu,%u", (unsigned long)t, H.nga_hd, H.nga.ly_do, H.nga.truoc_thang, H.nga.co_va_cham,
                 (unsigned long)H.nga.peak2_sk, (unsigned long)H.nga.wpeak2_sk, H.nga.co_nghieng);
        Serial.println(s);
    }
    for (uint32_t ms = 1; ms < 10; ms++) poll_mot(t + ms);
    s_k++;
}

static void cmd_phien()
{
    uint8_t p[3];
    if (!doc_du(p, 3)) { loi("I thieu byte"); return; }
    uint32_t v = 10u * s_k;
    while (H.wait) poll_mot(++v);
    hub_init(&H, 0);
    H.nga_en = p[0];
    s_pace = p[1];
    s_in_r = p[2];
    s_k = 0;
    s_t0_us = micros();
    Serial.println("i");
}

static void cmd_mau()
{
    static uint8_t pk[1 + 255 * 12 + 2];
    int n = Serial.read();
    uint32_t t0 = millis();
    while (n < 0 && millis() - t0 < 1000) n = Serial.read();
    if (n < 0) { loi("B thieu n"); return; }
    pk[0] = (uint8_t)n;
    size_t m = 12u * (size_t)n + 2u;
    if (!doc_du(pk + 1, m)) { loi("B thieu byte"); return; }
    if (crc16_ccitt(pk, 1 + 12u * n) != (uint16_t)((pk[1 + 12 * n] << 8) | pk[2 + 12 * n])) { loi("B sai crc"); return; }
    for (int i = 0; i < n; i++) {
        int16_t raw[6];
        memcpy(raw, pk + 1 + 12 * i, 12);
        mot_mau(raw);
    }
    Serial.println("a");
}

static void cmd_het()
{
    uint32_t v = 10u * s_k;
    while (H.wait) poll_mot(++v);
    char s[96];
    snprintf(s, sizeof s, "E,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu", (unsigned long)H.n_samples, (unsigned long)H.n_sent, (unsigned long)H.n_ok,
             (unsigned long)H.n_timeout, (unsigned long)H.n_err, (unsigned long)H.n_skip, (unsigned long)H.nga.n_xac_nhan, (unsigned long)H.nga.n_bo);
    Serial.println(s);
}

void setup()
{
    pinMode(MCU_TX_PIN, OUTPUT);
    digitalWrite(MCU_TX_PIN, HIGH);
    pinMode(FPGA_CS_PIN, OUTPUT);
    digitalWrite(FPGA_CS_PIN, HIGH);
    SPI.begin(FPGA_SCK_PIN, FPGA_MISO_PIN, FPGA_MOSI_PIN, FPGA_CS_PIN);
    Serial.setRxBufferSize(16384);
    Serial.setTxBufferSize(8192);
    Serial.setTimeout(1000);
    Serial.begin(USB_BAUD);
    delay(200);
    hub_init(&H, 0);
    Serial.println("# hil_board san sang");
}

void loop()
{
    int c = Serial.read();
    if (c < 0) return;
    switch (c) {
    case 'T': cmd_tu_kiem(); break;
    case 'W': cmd_cua_so(); break;
    case 'I': cmd_phien(); break;
    case 'B': cmd_mau(); break;
    case 'E': cmd_het(); break;
    default: break;
    }
}
