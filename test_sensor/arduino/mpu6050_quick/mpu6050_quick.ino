/*
 * mpu6050_quick.ino — kiểm tra nhanh module MPU6050 bằng Arduino (Uno/Nano/ESP32).
 * Dùng để KHOANH VÙNG LỖI: nếu chạy được ở đây mà không chạy trên SN32F407
 * thì module tốt, lỗi nằm ở dây/firmware MCU.
 *
 * Nối dây (Uno/Nano): VCC->5V (GY-521 có ổn áp 3,3 V), GND->GND, SCL->A5, SDA->A4,
 *                     AD0->GND, INT không cần.  ESP32: SCL->22, SDA->21, VCC->3V3.
 * Serial Monitor / sensor_check.py: 115200 baud.
 *   python sensor_check.py check --port COM7 --baud 115200
 */
#include <Wire.h>

const uint8_t MPU = 0x68;
int fails = 0;

void wr(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

int rd(uint8_t reg, uint8_t *buf, uint8_t n) {
  Wire.beginTransmission(MPU);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(MPU, n) != n) return -1;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return 0;
}

void report(const char *id, const char *name, bool ok, const String &detail) {
  Serial.print("# "); Serial.print(id); Serial.print(" "); Serial.print(name);
  Serial.print(" : "); Serial.print(detail); Serial.println(ok ? " -> PASS" : " -> FAIL");
  if (!ok) fails++;
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(400000);
  delay(200);
  Serial.println("# ===== MPU6050 QUICK TEST (Arduino) =====");

  Wire.beginTransmission(MPU);
  bool ack = Wire.endTransmission() == 0;
  report("T2", "I2C_SCAN", ack, ack ? "0x68 ACK" : "0x68 khong tra loi (day? AD0?)");

  uint8_t id = 0;
  rd(0x75, &id, 1);
  report("T3", "WHO_AM_I", id == 0x68, "0x" + String(id, HEX));

  /* Cấu hình đúng SPEC 2.1 */
  const uint8_t cfg[][2] = { {0x6B, 0x01}, {0x19, 0x09}, {0x1A, 0x03}, {0x1B, 0x18},
                             {0x1C, 0x18}, {0x38, 0x01} };
  bool ok = true;
  for (auto &c : cfg) { wr(c[0], c[1]); if (c[0] == 0x6B) delay(10); }
  delay(50);
  for (auto &c : cfg) { uint8_t v = 0; rd(c[0], &v, 1); if (v != c[1]) ok = false; }
  report("T4", "CONFIG", ok, ok ? "doc lai dung" : "doc lai sai");

  Serial.print("# SUMMARY fail="); Serial.println(fails);
  Serial.println("# STREAM START (gyro CHUA tru offset)");
  Serial.println("# t_ms,ax,ay,az,gx,gy,gz,btn");
}

void loop() {
  uint8_t st = 0, b[14];
  if (rd(0x3A, &st, 1) || !(st & 0x01)) return;      /* chờ DATA_RDY (100 Hz) */
  uint32_t t = millis();
  if (rd(0x3B, b, 14)) { Serial.println("# ERR doc I2C"); return; }
  int16_t v[7];
  for (int i = 0; i < 7; i++) v[i] = (int16_t)((b[2 * i] << 8) | b[2 * i + 1]);
  char line[64];
  snprintf(line, sizeof(line), "%lu,%d,%d,%d,%d,%d,%d,0", (unsigned long)t,
           v[0], v[1], v[2], v[4], v[5], v[6]);
  Serial.println(line);
}
