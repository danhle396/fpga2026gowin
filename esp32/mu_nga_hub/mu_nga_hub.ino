// esp32/mu_nga_hub/mu_nga_hub.ino — ESP32 là trung tâm khi phần cứng nối cố định theo codecanthiet của nhóm (24/10):
//
//   MPU6050 → I2C → SN32F407 (FW_NODE: chỉ đọc cảm biến) → UART 115200 → ESP32 GPIO16
//   ESP32 GPIO27 CS / 18 SCK / 23 MOSI / 19 MISO → Kiwi J2-16 / J2-10 / J2-11 / J2-13 (R11 / T14 / R13 / R12)
//   FPGA: fpga/fpga_project.gprj = fpga/bitstream/fpga_project.fs (giao thức v3, engine E2, mô hình N2). Không có dây IRQ, RST_N.
//
// ESP32 chạy nguyên lõi đã kiểm khớp golden (firmware/src: app_core, preprocess, blocks, safety, pwr_btn, spi_frame)
// qua hub.c; FPGA chạy CNN; kết quả lấy bằng hỏi vòng. Các file .c/.h cạnh sketch là BẢN CHÉP từ firmware/src
// (esp32/dong_bo_core.sh); sửa ở firmware/src rồi chạy lại script, đừng sửa ở đây.
//
// Hiển thị: USB Serial 460800 và log TCP cổng 3333 qua WiFi (cùng cách của nhóm; xem bằng
// python tools/monitor/wifi_live_log.py --host <IP> của nhóm, hoặc nc/PuTTY raw). Dòng in ra:
//   t_ms,seq,class,score,state,rc     mỗi cửa sổ (0,32 s) — như chế độ RUN của firmware MCU
//   S,t_ms,STATE,why                  mỗi lần Safety FSM đổi trạng thái
//   MCU <dòng chữ>                    chữ MCU in ra (khởi động, STAT)
//   STAT,...                          mỗi 5 s
//   LOG: t_ms,ax,ay,az,gx,gy,gz,btn,wear mỗi mẫu 100 Hz (lệnh LOG) — tools/logger.py đọc được qua cổng USB của ESP32
// Lệnh (gõ trên USB Serial hoặc TCP, kết thúc bằng Enter): RUN, LOG, STAT, ST (tự kiểm lại), SPI <kHz>.
#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>

extern "C" {
#include "hub.h"
#include "node_link.h"
#include "safety.h"
}
#include "selftest_expect_v3_e2_n2.h"

// ---- chân và tốc độ (theo codecanthiet/esp32/README_wiring.md của nhóm) ----
#define MCU_RX_PIN      16
#define MCU_TX_PIN      17          // không nối; UART2 cần một chân TX
#define MCU_BAUD        115200
#define FPGA_CS_PIN     27
#define FPGA_SCK_PIN    18
#define FPGA_MOSI_PIN   23
#define FPGA_MISO_PIN   19
#define SPI_HZ_FAST     1000000UL   // RTL cho phép ≤ 4 MHz; dây dài thì hạ
#define SPI_HZ_SLOW     100000UL    // tốc độ nhóm đã chạy thông trên bộ dây này
#define LED_PIN         2           // LED trên ESP32 DevKit: sáng/nháy theo còi + LED của Safety FSM
#define BTN_PIN         0           // nút BOOT: CANCEL phụ (OR với nút SW3 của MCU)
#define USB_BAUD        460800
#ifndef WIFI_STA_SSID
#define WIFI_STA_SSID   "test1"     // hotspot thử của nhóm; đổi bằng -DWIFI_STA_SSID=... khi build
#endif
#ifndef WIFI_STA_PASSWORD
#define WIFI_STA_PASSWORD "12345678"
#endif
#define WIFI_TCP_PORT   3333

static hub_t H;
static node_rx_t NR;
static uint32_t s_spi_hz = SPI_HZ_FAST;
static bool s_log = false;
static WiFiServer s_server(WIFI_TCP_PORT);
static WiFiClient s_client;
static uint32_t s_tcp_drop = 0;
static bool s_wifi_shown = false;

// ---------------- in ra USB + TCP ----------------
static void out(const char *s)
{
    Serial.println(s);
    if (s_client && s_client.connected()) {
        size_t n = strlen(s);
        if ((size_t)s_client.availableForWrite() > n + 2) {
            s_client.write((const uint8_t *)s, n);
            s_client.write((const uint8_t *)"\r\n", 2);
        } else {
            s_tcp_drop++;
        }
    }
}

// ---------------- SPI tới FPGA ----------------
static uint32_t cs_gap_us() { return 3000000UL / s_spi_hz + 2; }     // ≥ 2 chu kỳ SCK quanh CS

static void spi_write_fn(const uint8_t *b, uint16_t n, void *ctx)
{
    (void)ctx;
    SPI.beginTransaction(SPISettings(s_spi_hz, MSBFIRST, SPI_MODE0));
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
    SPI.beginTransaction(SPISettings(s_spi_hz, MSBFIRST, SPI_MODE0));
    digitalWrite(FPGA_CS_PIN, LOW);
    delayMicroseconds(cs_gap_us());
    for (uint8_t i = 0; i < n; i++) b[i] = SPI.transfer(0x00);
    delayMicroseconds(cs_gap_us());
    digitalWrite(FPGA_CS_PIN, HIGH);
    SPI.endTransaction();
    delayMicroseconds(cs_gap_us());
}

static const hub_io_t IO = { spi_write_fn, spi_read_fn, nullptr };
static uint32_t ms_fn() { return millis(); }

static bool selftest()
{
    uint8_t got[7];
    int ok = hub_selftest(&H, &IO, ms_fn, selftest_frame7, got);
    char s[160];
    snprintf(s, sizeof s, "tu kiem FPGA (A.10) SPI %lu kHz: doc %02X %02X %02X %02X %02X %02X %02X, mong doi %02X %02X %02X "
             "%02X %02X %02X %02X class=%u  %s", (unsigned long)(s_spi_hz / 1000), got[0], got[1], got[2], got[3], got[4],
             got[5], got[6], selftest_frame7[0], selftest_frame7[1], selftest_frame7[2], selftest_frame7[3],
             selftest_frame7[4], selftest_frame7[5], selftest_frame7[6], got[3], ok ? "PASS" : "FAIL");
    out(s);
    return ok != 0;
}

// ---------------- lệnh ----------------
static void command(const char *c)
{
    char s[64];
    if (!strcmp(c, "LOG"))       { s_log = true;  out("# LOG"); }
    else if (!strcmp(c, "RUN"))  { s_log = false; out("# RUN"); }
    else if (!strcmp(c, "ST"))   { selftest(); }
    else if (!strncmp(c, "SPI ", 4)) {
        long k = atol(c + 4);
        if (k >= 10 && k <= 4000) { s_spi_hz = (uint32_t)k * 1000UL; snprintf(s, sizeof s, "# SPI %ld kHz", k); out(s); }
    } else if (!strcmp(c, "STAT")) {
        snprintf(s, sizeof s, "# STAT xem dong STAT ke tiep"); out(s);
    }
}

static void read_commands(Stream &st, char *buf, uint8_t &n)
{
    while (st.available()) {
        char ch = (char)st.read();
        if (ch == '\r' || ch == '\n') {
            if (n) { buf[n] = 0; command(buf); n = 0; }
        } else if (n < 31) {
            buf[n++] = ch;
        }
    }
}

// ---------------- setup / loop ----------------
void setup()
{
    Serial.begin(USB_BAUD);
    Serial2.setRxBufferSize(4096);
    Serial2.begin(MCU_BAUD, SERIAL_8N1, MCU_RX_PIN, MCU_TX_PIN);
    pinMode(FPGA_CS_PIN, OUTPUT);
    digitalWrite(FPGA_CS_PIN, HIGH);
    SPI.begin(FPGA_SCK_PIN, FPGA_MISO_PIN, FPGA_MOSI_PIN, FPGA_CS_PIN);
    pinMode(LED_PIN, OUTPUT);
    pinMode(BTN_PIN, INPUT_PULLUP);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASSWORD);
    s_server.begin();
    delay(500);                                 // FPGA nạp cấu hình từ flash sau khi cấp nguồn

    out("# mu bao ho - ESP32 hub (MCU -> UART -> ESP32 -> SPI -> FPGA), firmware/src + hub.c");
    hub_init(&H, millis());
    node_rx_init(&NR);
    bool ok = selftest();
    if (!ok && s_spi_hz != SPI_HZ_SLOW) {       // dây dài: thử lại ở tốc độ nhóm đã chạy thông
        s_spi_hz = SPI_HZ_SLOW;
        ok = selftest();
    }
    if (!ok) H.app.err_flag = 1;
    out("# start");
}

void loop()
{
    static uint32_t t_tick = millis(), t_stat = millis(), t_last_sample = millis(), t_warn = 0;
    static char cmd_usb[32], cmd_tcp[32];
    static uint8_t n_usb = 0, n_tcp = 0;
    char s[160];
    uint32_t now = millis();

    // 1. mẫu từ MCU
    while (Serial2.available()) {
        int e = node_rx_byte(&NR, (uint8_t)Serial2.read());
        if (e == NODE_SAMPLE) {
            t_last_sample = now;
            hub_sample(&H, &IO, NR.r, NR.keys, now);
            if (s_log) {
                // t theo số mẫu MCU đã gửi (100 Hz, tính cả mẫu mất), không theo lúc ESP32 nhận: UART có thể dồn cục
                unsigned long t_log = 10UL * (unsigned long)(NR.n_ok + NR.n_lost - 1u);
                snprintf(s, sizeof s, "%lu,%d,%d,%d,%d,%d,%d,%u,1", t_log, NR.r[0], NR.r[1], NR.r[2],
                         NR.r[3], NR.r[4], NR.r[5], (unsigned)((NR.keys >> 1) & 1u));
                out(s);
            }
        } else if (e == NODE_TEXT && NR.line[0]) {
            snprintf(s, sizeof s, "MCU %s", NR.line);
            out(s);
        }
    }

    // 2. kết quả FPGA (hỏi vòng)
    int rc = hub_poll(&H, &IO, now);
    if (rc != SPI_PENDING && !s_log) {
        snprintf(s, sizeof s, "%lu,%u,%d,%u,%s,%d", (unsigned long)now, H.last.seq, rc == SPI_OK ? H.last.cls : -1,
                 H.last.score, safety_state_name(H.app.fsm.st), rc);
        out(s);
    }

    // 3. khe 10 ms: Safety FSM, nút, LED
    if (now - t_tick >= 10u) {
        t_tick += 10u;
        hub_tick(&H, now, digitalRead(BTN_PIN) == LOW);
        if (H.app.fsm.events & SAFETY_EV_STATE) {
            snprintf(s, sizeof s, "S,%lu,%s,%u", (unsigned long)now, safety_state_name(H.app.fsm.st), H.app.fsm.why);
            out(s);
        }
        digitalWrite(LED_PIN, (app_buzzer(&H.app, now) || app_led(&H.app, now)) ? HIGH : LOW);
    }

    // 4. thống kê, cảnh báo mất nguồn mẫu
    if (now - t_stat >= 5000u) {
        t_stat = now;
        snprintf(s, sizeof s, "STAT,mau=%lu,mat=%lu,khung_hong=%lu,gui=%lu,ok=%lu,timeout=%lu,loi=%lu,bo_qua=%lu,spi_khz=%lu,"
                 "tcp_bo=%lu", (unsigned long)H.n_samples, (unsigned long)NR.n_lost, (unsigned long)NR.n_bad,
                 (unsigned long)H.n_sent, (unsigned long)H.n_ok, (unsigned long)H.n_timeout, (unsigned long)H.n_err,
                 (unsigned long)H.n_skip, (unsigned long)(s_spi_hz / 1000), (unsigned long)s_tcp_drop);
        out(s);
    }
    if (now - t_last_sample > 2000u && now - t_warn > 2000u) {
        t_warn = now;
        out("# chua nhan mau tu MCU (GPIO16, 115200): kiem MCU da nap firmware FW_NODE, day TX P3.1 -> GPIO16, GND chung");
    }

    // 5. WiFi: một máy xem log trên TCP 3333
    if (WiFi.status() == WL_CONNECTED && !s_wifi_shown) {
        s_wifi_shown = true;
        snprintf(s, sizeof s, "# WiFi %s IP %s, log TCP cong %d", WIFI_STA_SSID, WiFi.localIP().toString().c_str(),
                 WIFI_TCP_PORT);
        out(s);
    }
    if (s_server.hasClient()) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
        WiFiClient c = s_server.accept();
#else
        WiFiClient c = s_server.available();
#endif
        if (s_client) s_client.stop();
        s_client = c;
        out("# TCP: may xem log da ket noi");
    }

    // 6. lệnh
    read_commands(Serial, cmd_usb, n_usb);
    if (s_client && s_client.connected()) read_commands(s_client, cmd_tcp, n_tcp);
}
