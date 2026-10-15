Board: Kiwi Primer 20K - GW2A-LV18PG256
FPGA clock: 50.143 MHz

SPI:
Mode 0
MSB first
Khuyến nghị SCLK <= 5-10 MHz

MCU -> FPGA:
[A5][SEQ][768 DATA][CRC8]

768 DATA:
128 samples × 6 axes
sample-major:
ax ay az gx gy gz

CRC8:
poly = 0x07
init = 0x00
xorout = 0x00
CRC covers SEQ + 768 data bytes

FPGA -> MCU:
[5A][CLASS][SCORE31:24][SCORE23:16][SCORE15:8][SCORE7:0][CRC8]

CLASS:
0 = NORMAL
1 = SIT_LIE
2 = STUMBLE
3 = FALL

Golden RTL Simulation:
PASS

Golden example:
class  = 0
score  = 1431
logits = 1431 253 316 -15