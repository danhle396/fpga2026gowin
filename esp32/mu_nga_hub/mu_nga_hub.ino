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
#include <WebServer.h>
#include <math.h>

extern "C" {
#include "hub.h"
#include "node_link.h"
#include "safety.h"
}
#include "selftest_expect_v3_e2_n2.h"
#include "trang_web_html.h"

// ---- chân và tốc độ (theo codecanthiet/esp32/README_wiring.md của nhóm) ----
#define MCU_RX_PIN      16
#define MCU_TX_PIN      17          // → MCU P3.2 (J10 URX_P32), dây thêm 25/10: lệnh còi PZ1 của EVK
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
// WiFi của nhóm (mạng duy nhất đang dùng). Mang đi nơi khác thì sửa 2 dòng này rồi nạp lại ESP32.
#define WIFI_STA_SSID     "Tro Bao Tran T4"
#define WIFI_STA_PASSWORD "thy0905542257"
#define WIFI_TCP_PORT   3333

static hub_t H;
static node_rx_t NR;
static uint32_t s_spi_hz = SPI_HZ_FAST;
static bool s_log = false;
static WiFiServer s_server(WIFI_TCP_PORT);
static WiFiClient s_client;
static uint32_t s_tcp_drop = 0;
static uint32_t s_rx_bytes = 0;                // mọi byte nhận ở GPIO16, kể cả rác (chẩn đoán dây, baud)
static uint8_t  s_raw_left = 0;                 // lệnh RAW: in hex các byte kế tiếp
static bool s_wifi_shown = false;

// ---------------- trang web http://<IP>/ : lịch sử cho biểu đồ và danh sách sự kiện ----------------
static WebServer s_web(80);
#define ACC_N 300                               // |a| mỗi 100 ms, 30 s
#define RES_N 120                               // kết quả FPGA gần nhất (≈ 38 s)
#define EV_N  20
static uint32_t s_acc_t[ACC_N]; static uint16_t s_acc_v[ACC_N]; static uint16_t s_acc_i = 0, s_acc_n = 0;
static uint32_t s_res_t[RES_N]; static uint8_t s_res_c[RES_N]; static uint16_t s_res_i = 0, s_res_n = 0;
static String   s_ev[EV_N]; static uint8_t s_ev_i = 0, s_ev_n = 0;
#define PT_N  24                                // các lần đổi tư thế gần nhất (posture.c, A.11)
static uint32_t s_pt_t[PT_N]; static uint8_t s_pt_v[PT_N]; static uint8_t s_pt_i = 0, s_pt_n = 0;
static bool     s_tk_ok = false;
static int      s_last_rc = -1;
static uint32_t s_web_cancel_until = 0;
static uint32_t s_n_nga = 0, s_t_nga = 0;     // số lần phát hiện ngã (vào SUSPECT) từ lúc bật, lúc lần gần nhất

// ---------------- in ra USB + TCP ----------------
static void out(const char *s)
{
    Serial.println(s);
    // sự kiện cho trang web (tư thế "P,..." có khung lịch sử riêng, không lấn sự kiện báo ngã)
    if (!(s[0] >= '0' && s[0] <= '9') && strncmp(s, "STAT", 4) != 0 && strncmp(s, "P,", 2) != 0) {
        s_ev[s_ev_i] = String((unsigned long)(millis() / 1000)) + " s  " + s;
        s_ev_i = (uint8_t)((s_ev_i + 1) % EV_N);
        if (s_ev_n < EV_N) s_ev_n++;
    }
    if (s_client && s_client.connected()) {
        // availableForWrite() của NetworkClient (core 3.x) luôn trả 0, nên ghi thẳng; lwIP đệm vài KB, đủ cho log
        size_t n = strlen(s);
        if (s_client.write((const uint8_t *)s, n) != n || s_client.write((const uint8_t *)"\r\n", 2) != 2)
            s_tcp_drop++;
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
    s_tk_ok = ok != 0;
    return ok != 0;
}

// 1 MHz trước, không được thì 100 kHz (tốc độ nhóm đã chạy thông trên bộ dây này)
static bool thu_tu_kiem()
{
    s_spi_hz = SPI_HZ_FAST;
    if (selftest()) return true;
    s_spi_hz = SPI_HZ_SLOW;
    if (selftest()) return true;
    s_spi_hz = SPI_HZ_FAST;
    return false;
}

// ---------------- lệnh ----------------
static void command(const char *c)
{
    char s[64];
    if (!strcmp(c, "LOG"))       { s_log = true;  out("# LOG"); }
    else if (!strcmp(c, "RUN"))  { s_log = false; out("# RUN"); }
    else if (!strcmp(c, "ST"))   { if (thu_tu_kiem()) H.app.err_flag = 0; }
    else if (!strcmp(c, "RAW"))  { s_raw_left = 64; out("# RAW: 64 byte ke tiep tu MCU (hex)"); }
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

// ---------------- /data: JSON cho trang web ----------------
static void web_data()
{
    String j;
    j.reserve(6000);
    j += "{\"t\":"; j += millis();
    j += ",\"st\":\""; j += safety_state_name(H.app.fsm.st);
    j += "\",\"rc\":"; j += s_last_rc;
    j += ",\"cls\":"; j += H.last.cls; j += ",\"score\":"; j += H.last.score; j += ",\"seq\":"; j += H.last.seq;
    j += ",\"tk\":"; j += s_tk_ok ? 1 : 0;
    j += ",\"nga\":"; j += s_n_nga; j += ",\"t_nga\":"; j += s_t_nga;
    j += ",\"tt\":\""; j += posture_name(H.pos.tt); j += '"';
    j += ",\"pt\":[";
    for (uint8_t k = 0; k < s_pt_n; k++) {
        uint8_t i = (uint8_t)((s_pt_i + PT_N - s_pt_n + k) % PT_N);
        if (k) j += ','; j += "["; j += s_pt_t[i]; j += ",\""; j += posture_name(s_pt_v[i]); j += "\"]";
    }
    j += ']';
    j += ",\"s\":{\"mau\":"; j += H.n_samples; j += ",\"mat\":"; j += NR.n_lost; j += ",\"hong\":"; j += NR.n_bad;
    j += ",\"gui\":"; j += H.n_sent; j += ",\"ok\":"; j += H.n_ok; j += ",\"to\":"; j += H.n_timeout;
    j += ",\"loi\":"; j += H.n_err; j += ",\"spi_khz\":"; j += s_spi_hz / 1000; j += "}";
    j += ",\"acc\":[";
    for (uint16_t k = 0; k < s_acc_n; k++) {
        uint16_t i = (uint16_t)((s_acc_i + ACC_N - s_acc_n + k) % ACC_N);
        if (k) j += ','; j += '['; j += s_acc_t[i]; j += ','; j += s_acc_v[i]; j += ']';
    }
    j += "],\"res\":[";
    for (uint16_t k = 0; k < s_res_n; k++) {
        uint16_t i = (uint16_t)((s_res_i + RES_N - s_res_n + k) % RES_N);
        if (k) j += ','; j += '['; j += s_res_t[i]; j += ','; j += s_res_c[i]; j += ']';
    }
    j += "],\"ev\":[";
    for (uint8_t k = 0; k < s_ev_n; k++) {
        const String &e = s_ev[(s_ev_i + EV_N - s_ev_n + k) % EV_N];
        if (k) j += ',';
        j += '"';
        for (size_t c = 0; c < e.length(); c++) { char ch = e[c]; if (ch == '"' || ch == '\\') j += '\\'; j += ch; }
        j += '"';
    }
    j += "]}";
    s_web.send(200, "application/json", j);
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
    s_web.on("/", HTTP_GET, []() { s_web.send_P(200, "text/html; charset=utf-8", TRANG_WEB); });
    s_web.on("/data", HTTP_GET, web_data);
    // Nút web giả lập nút trên mũ, nhưng chỉ đúng việc được hỏi: một lần nhấn ở MONITOR không được tính (2 lần = TẮT)
    s_web.on("/huy", HTTP_POST, []() {
        uint8_t st = H.app.fsm.st;
        if (st == ST_PRE_ALARM)  { s_web_cancel_until = millis() + 300;  s_web.send(200, "text/plain", "da huy canh bao"); }
        else if (st == ST_ALARM) { s_web_cancel_until = millis() + 1300; s_web.send(200, "text/plain", "da tat bao dong"); }
        else                     { s_web.send(409, "text/plain", "chi huy duoc khi dang CANH BAO / BAO DONG"); }
    });
    s_web.on("/bat", HTTP_POST, []() {
        if (H.app.fsm.st == ST_STANDBY) { s_web_cancel_until = millis() + 2300; s_web.send(200, "text/plain", "dang bat"); }
        else                            { s_web.send(409, "text/plain", "he thong dang bat"); }
    });
    s_web.begin();
    delay(500);                                 // FPGA nạp cấu hình từ flash sau khi cấp nguồn

    out("# mu bao ho - ESP32 hub (MCU -> UART -> ESP32 -> SPI -> FPGA), firmware/src + hub.c");
    hub_init(&H, millis());
    node_rx_init(&NR);
    // Chạy pin (24/10): cấp nguồn cùng lúc thì FPGA còn đang đọc bitstream từ flash khi ESP32 đã sẵn sàng → tự kiểm
    // FAIL. Thử mỗi 1 s tối đa 20 lần; còn FAIL thì vòng lặp thử lại mỗi 5 s (thu_kiem_lai).
    bool ok = false;
    for (int lan = 0; lan < 20 && !ok; lan++) {
        ok = thu_tu_kiem();
        if (!ok) delay(1000);
    }
    if (!ok) H.app.err_flag = 1;
    out(FW_VI_TRI_DEO == 1 ? "# vi tri deo: NGUC (truc nguoi X=+Z Y=-X Z=-Y cua MPU6050; LOG in truc nguoi)"
                            : "# vi tri deo: MU (truc cam bien = truc nguoi)");
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
        uint8_t b = (uint8_t)Serial2.read();
        s_rx_bytes++;
        if (s_raw_left) {                       // lệnh RAW: 16 byte mỗi dòng
            static char hx[16 * 3 + 1];
            static uint8_t nh = 0;
            snprintf(hx + 3 * nh, 4, "%02X ", b);
            nh++;
            s_raw_left--;
            if (nh == 16 || s_raw_left == 0) { out(hx); nh = 0; }
        }
        int e = node_rx_byte(&NR, b);
        if (e == NODE_SAMPLE) {
            t_last_sample = now;
            if (hub_sample(&H, &IO, NR.r, NR.keys, now) & HUB_POSTURE) {
                s_pt_t[s_pt_i] = now; s_pt_v[s_pt_i] = H.pos.tt;
                s_pt_i = (uint8_t)((s_pt_i + 1) % PT_N); if (s_pt_n < PT_N) s_pt_n++;
                snprintf(s, sizeof s, "P,%lu,%s", (unsigned long)now, posture_name(H.pos.tt));
                out(s);
            }
            if (NR.n_ok % 10u == 0) {           // |a| cho biểu đồ web, 10 điểm/s; ±16 g: 2048 LSB/g
                float a = sqrtf((float)NR.r[0] * NR.r[0] + (float)NR.r[1] * NR.r[1] + (float)NR.r[2] * NR.r[2]) / 2048.0f;
                s_acc_t[s_acc_i] = now; s_acc_v[s_acc_i] = (uint16_t)(a * 100.0f + 0.5f);
                s_acc_i = (uint16_t)((s_acc_i + 1) % ACC_N); if (s_acc_n < ACC_N) s_acc_n++;
            }
            if (s_log) {
                // t theo số mẫu MCU đã gửi (100 Hz, tính cả mẫu mất), không theo lúc ESP32 nhận: UART có thể dồn cục
                unsigned long t_log = 10UL * (unsigned long)(NR.n_ok + NR.n_lost - 1u);
                snprintf(s, sizeof s, "%lu,%d,%d,%d,%d,%d,%d,%u,1", t_log, H.r[0], H.r[1], H.r[2],
                         H.r[3], H.r[4], H.r[5], (unsigned)((NR.keys >> 1) & 1u));
                out(s);
            }
        } else if (e == NODE_TEXT && NR.line[0]) {
            snprintf(s, sizeof s, "MCU %s", NR.line);
            out(s);
        }
    }

    // 2. kết quả FPGA (hỏi vòng)
    int rc = hub_poll(&H, &IO, now);
    if (rc != SPI_PENDING) {
        s_last_rc = rc;
        s_res_t[s_res_i] = now; s_res_c[s_res_i] = rc == SPI_OK ? H.last.cls : 255;
        s_res_i = (uint16_t)((s_res_i + 1) % RES_N); if (s_res_n < RES_N) s_res_n++;
    }
    if (rc != SPI_PENDING && !s_log) {
        snprintf(s, sizeof s, "%lu,%u,%d,%u,%s,%d", (unsigned long)now, H.last.seq, rc == SPI_OK ? H.last.cls : -1,
                 H.last.score, safety_state_name(H.app.fsm.st), rc);
        out(s);
    }

    // 3. khe 10 ms: Safety FSM, nút, LED
    if (now - t_tick >= 10u) {
        t_tick += 10u;
        hub_tick(&H, now, digitalRead(BTN_PIN) == LOW || (int32_t)(s_web_cancel_until - now) > 0);
        if (H.app.fsm.events & SAFETY_EV_STATE) {
            snprintf(s, sizeof s, "S,%lu,%s,%u", (unsigned long)now, safety_state_name(H.app.fsm.st), H.app.fsm.why);
            out(s);
            if (H.app.fsm.st == ST_SUSPECT) { s_n_nga++; s_t_nga = now; }
        }
        uint8_t bz = app_buzzer(&H.app, now);
        digitalWrite(LED_PIN, (bz || app_led(&H.app, now)) ? HIGH : LOW);
        // còi PZ1 trên EVK do MCU kêu theo lệnh 1 byte (node_link.h): gửi khi đổi, nhắc lại mỗi 100 ms
        static uint8_t bz_gui = 0;
        static uint32_t t_bz = 0;
        if (bz != bz_gui || now - t_bz >= NODE_BUZZ_REFRESH_MS) {
            Serial2.write(bz ? NODE_CMD_BUZZ_ON : NODE_CMD_BUZZ_OFF);
            bz_gui = bz;
            t_bz = now;
        }
    }

    // 3b. tự kiểm còn FAIL (FPGA chưa sẵn sàng lúc khởi động): thử lại mỗi 5 s khi không có khung đang chờ
    static uint32_t t_tk = millis();
    if (!s_tk_ok && !H.wait && now - t_tk >= 5000u) {
        t_tk = now;
        if (thu_tu_kiem()) { H.app.err_flag = 0; out("# tu kiem FPGA dat sau khi thu lai"); }
    }

    // 4. thống kê, cảnh báo mất nguồn mẫu
    if (now - t_stat >= 5000u) {
        t_stat = now;
        snprintf(s, sizeof s, "STAT,mau=%lu,mat=%lu,khung_hong=%lu,gui=%lu,ok=%lu,timeout=%lu,loi=%lu,bo_qua=%lu,spi_khz=%lu,"
                 "tcp_bo=%lu,byte_rx=%lu", (unsigned long)H.n_samples, (unsigned long)NR.n_lost, (unsigned long)NR.n_bad,
                 (unsigned long)H.n_sent, (unsigned long)H.n_ok, (unsigned long)H.n_timeout, (unsigned long)H.n_err,
                 (unsigned long)H.n_skip, (unsigned long)(s_spi_hz / 1000), (unsigned long)s_tcp_drop, (unsigned long)s_rx_bytes);
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
        s_client.setNoDelay(true);
        out("# TCP: may xem log da ket noi");
    }

    // 6. trang web, lệnh
    s_web.handleClient();
    read_commands(Serial, cmd_usb, n_usb);
    if (s_client && s_client.connected()) read_commands(s_client, cmd_tcp, n_tcp);
}
