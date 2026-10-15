# ml/src/safety_model.py — bản Python của firmware/src/safety.c và blocks.c (A.8), bám từng dòng để phát lại dữ liệu
# trên PC (AI-10). tools/m0_test.py kiểm bản này trùng bản C (mã máy Cortex-M0) trên chuỗi sự kiện ngẫu nhiên.
import numpy as np

STANDBY, MONITOR, SUSPECT, PRE_ALARM, ALARM, COOLDOWN = range(6)
NAMES = ["STANDBY", "MONITOR", "SUSPECT", "PRE_ALARM", "ALARM", "COOLDOWN"]
WHY_NONE, WHY_WEAR_ON, WHY_WEAR_OFF, WHY_VOTES, WHY_STILL, WHY_TIMEOUT, WHY_CANCEL, WHY_SOS, WHY_ALARM_ACK = range(9)
EV_STATE, EV_BEEP = 1, 2
CLS_IMPACT, CLS_FALL = 1, 3
M32 = 0xFFFFFFFF

DEFAULT = dict(vote_k=2, vote_n=3, t_score=0, still_blocks=8, tilt_en=1, t_tilt=1450, wear_off_ms=3000,
               wear_recent_ms=3000, suspect_timeout_ms=8000, pre_alarm_ms=10000, cooldown_ms=30000,
               sos_hold_ms=3000, alarm_hold_ms=1000)


class Safety:
    def __init__(self, cfg=None, now=0):
        self.c = dict(DEFAULT, **(cfg or {}))
        self.st, self.why, self.events = STANDBY, WHY_NONE, 0
        self.t_enter, self.t_wear_on, self.wear_seen = now & M32, 0, 0
        self.vote_bits, self.impact_pending = 0, 0
        self.still_run, self.az_tb = 0, 0
        self.btn_prev, self.btn_used, self.t_btn_down = 0, 0, 0

    def fall_votes(self):
        bits = self.vote_bits & ((1 << self.c["vote_n"]) - 1)
        return bin(bits).count("1")

    def on_result(self, cls, score):
        vote = int(cls == CLS_FALL and score >= self.c["t_score"])
        self.vote_bits = ((self.vote_bits << 1) | vote) & 0xFF
        if cls == CLS_IMPACT and score >= self.c["t_score"]:
            self.impact_pending = 1

    def on_block(self, still_run, az_tb):
        self.still_run, self.az_tb = still_run, az_tb

    def _go(self, st, why, now):
        self.st, self.why, self.t_enter = st, why, now
        self.events |= EV_STATE
        if st in (SUSPECT, MONITOR):
            self.vote_bits = 0

    def tick(self, now, wear, cancel):
        c = self.c
        now &= M32
        in_state = (now - self.t_enter) & M32
        press = int(cancel and not self.btn_prev)
        impact = self.impact_pending
        self.events, self.impact_pending = 0, 0
        if wear:
            self.t_wear_on, self.wear_seen = now, 1
        if press:
            self.t_btn_down, self.btn_used = now, 0
        self.btn_prev = int(bool(cancel))
        held = ((now - self.t_btn_down) & M32) if cancel else 0
        hold_ok = cancel and not self.btn_used
        st = self.st
        if st == PRE_ALARM and press:
            self.btn_used = 1; self._go(MONITOR, WHY_CANCEL, now); return
        if st in (MONITOR, SUSPECT) and hold_ok and held >= c["sos_hold_ms"]:
            self.btn_used = 1; self._go(ALARM, WHY_SOS, now); return
        if st == ALARM and hold_ok and held >= c["alarm_hold_ms"]:
            self.btn_used = 1; self._go(COOLDOWN, WHY_ALARM_ACK, now); return
        if st == STANDBY and wear:
            self._go(MONITOR, WHY_WEAR_ON, now); return
        if st == MONITOR:
            if not wear and self.wear_seen and ((now - self.t_wear_on) & M32) >= c["wear_off_ms"]:
                self._go(STANDBY, WHY_WEAR_OFF, now); return
            if not self.wear_seen and in_state >= c["wear_off_ms"]:
                self._go(STANDBY, WHY_WEAR_OFF, now); return
        if st == SUSPECT and in_state >= c["suspect_timeout_ms"]:
            self._go(MONITOR, WHY_TIMEOUT, now); return
        if st == PRE_ALARM and in_state >= c["pre_alarm_ms"]:
            self._go(ALARM, WHY_TIMEOUT, now); return
        if st == COOLDOWN and in_state >= c["cooldown_ms"]:
            self._go(MONITOR, WHY_TIMEOUT, now); return
        if self.st == MONITOR:
            if impact and wear:
                self.events |= EV_BEEP
            if self.fall_votes() >= c["vote_k"] and self.wear_seen and ((now - self.t_wear_on) & M32) <= c["wear_recent_ms"]:
                self._go(SUSPECT, WHY_VOTES, now); return
        if self.st == SUSPECT and self.still_run >= c["still_blocks"] and (
                not c["tilt_en"] or -c["t_tilt"] < self.az_tb < c["t_tilt"]):     # A.8 v3.1: |az_tb| < T_TILT
            self._go(PRE_ALARM, WHY_STILL, now)


class Blocks:
    """blocks.c: khối n mẫu; bất động khi max − min của 3 trục gia tốc < t_a và 3 trục gyro < t_g."""
    def __init__(self, t_a=300, t_g=250, n=32):
        self.t_a, self.t_g, self.n_blk = t_a, t_g, n
        self.n, self.still, self.still_run, self.az_tb = 0, 0, 0, 0
        self.mn = self.mx = None
        self.az_sum = 0

    def push(self, r):
        r = [int(v) for v in r]
        if self.n == 0:
            self.mn, self.mx, self.az_sum = list(r), list(r), 0
        else:
            self.mn = [min(a, b) for a, b in zip(self.mn, r)]
            self.mx = [max(a, b) for a, b in zip(self.mx, r)]
        self.az_sum += r[2]
        self.n += 1
        if self.n < self.n_blk:
            return False
        still = all((self.mx[c] - self.mn[c]) < (self.t_a if c < 3 else self.t_g) for c in range(6))
        self.still = int(still)
        self.still_run = min(self.still_run + 1, 255) if still else 0
        sh = self.n_blk.bit_length() - 1                  # 32 → >> 5 (C); 16 mẫu 50 Hz → >> 4
        self.az_tb = self.az_sum >> sh
        self.n = 0
        return True
