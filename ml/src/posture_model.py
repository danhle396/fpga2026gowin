"""posture_model.py — nhận dạng tư thế từ cảm biến ở đầu (đáp án số nguyên cho firmware/src/posture.c, A.11).

Không thay Safety FSM: tư thế chỉ để hiển thị và báo cáo (đứng thẳng, ngồi, nằm ngửa, nằm sấp, nằm nghiêng trái/phải,
cúi người, đang di chuyển). Đầu vào: mẫu thô 100 Hz [AX AY AZ ...] INT16 (±16 g: 2048 LSB/g); trục của mũ: X trước,
Y trái, Z lên. Mọi phép tính là số nguyên, chia làm tròn về 0 (tdiv) để posture.c trùng từng bit.

1. Hướng đầu theo trung bình gia tốc khối 32 mẫu (0,32 s): az > 0,82 |g| → THẲNG; az < 0,50 |g| → NẰM
   (|ay| > |ax|: ay > 0 nghiêng phải, ngược lại nghiêng trái; còn lại ax > 0 nằm ngửa, ngược lại nằm sấp); khác → CÚI.
   Giữ 3 khối liên tiếp (≈ 1 s) mới chốt.
2. Đợt cử động: | |a| − 2048 | > 120 LSB (0,06 g) trong 30 mẫu gần nhất. Trong đợt: v += |a| − g_yên, h += v; hết đợt
   chỉnh trôi bằng vận tốc 0 ở hai đầu: Δh = h − v_cuối·(n+1)/2 (đơn vị: Δh[m] = Δh · 9,80665 / 2048 / 100²).
3. Đứng hay ngồi (cùng đầu thẳng):
   - đợt đầu luôn thẳng: Δh ≤ −0,25 m → NGỒI; Δh ≥ +0,25 m → ĐỨNG; đợt dài > 4 s (đi lại) → ĐỨNG;
   - dậy sau khi NẰM ≥ 3 s: Δh < 1,5 m → NGỒI (ngồi dậy), ngược lại ĐỨNG (đứng dậy);
   - đợt có lúc nằm < 3 s (cúi rất sâu, ngã rồi bật dậy ngay): giữ nguyên. Đợt có cúi vẫn dùng Δh (ngồi xuống ghế
     thường cúi người; cúi nhặt đồ trên D1 hầu như không hạ đầu ≥ 0,25 m trong một đợt).
"""

G_LSB = 2048
MOVE_DEV = 120           # 0,06 g
STILL_N = 30             # 0,3 s ở 100 Hz
LONG_N = 400             # đợt cử động > 4 s: đang đi lại
BLK = 32
HOLD = 3                 # khối liên tiếp để chốt hướng đầu
UP_PCT, LIE_PCT = 82, 50
LIE_LONG = 300           # nằm ≥ 3 s mới tính là "dậy từ nằm"
M_TO_H = 2048 * 10000 / 9.80665
NGOI_H = int(0.25 * M_TO_H)          # 522.097
DUNG_TU_NAM_H = int(1.5 * M_TO_H)    # 3.132.580
NGOI_H_NGA = int(0.15 * M_TO_H)      # 313.258: ngồi xuống có ngả / cúi người mạnh (đầu chốt NẰM ngắn)

DUNG, NGOI, NAM_NGUA, NAM_SAP, NGHIENG_TRAI, NGHIENG_PHAI, CUI, DI_LAI = range(8)
TEN = ["DUNG", "NGOI", "NAM_NGUA", "NAM_SAP", "NGHIENG_TRAI", "NGHIENG_PHAI", "CUI", "DI_LAI"]
O_THANG, O_NAM, O_CUI = 0, 1, 2


def tdiv(a, b):
    """Chia nguyên làm tròn về 0, như phép / của C."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def isqrt(x):
    """Căn nguyên của số không âm (cùng thuật toán với posture.c)."""
    r, b = 0, 1 << 30
    while b > x:
        b >>= 2
    while b:
        if x >= r + b:
            x -= r + b
            r = (r >> 1) + b
        else:
            r >>= 1
        b >>= 2
    return r


class Posture:
    def __init__(self):
        self.tt = DUNG
        self.ngoi = 0
        self.huong = O_THANG
        self.cand, self.cand_n = O_THANG, 0
        self.sx = self.sy = self.sz = self.nb = 0
        self.mx = self.my = 0
        self.since_move = STILL_N
        self.moving = 0
        self.n_ep = 0
        self.v = self.h = 0
        self.g_ref = G_LSB
        self.g_acc = self.g_n = 0
        self.di_lai = 0
        self.dh_cuoi = 0
        self.ep_nghieng = 0      # trong đợt có lúc hướng đầu đã chốt là NẰM (cúi thì vẫn tính Δh)
        self.nam_n = 0           # số mẫu đã ở hướng NẰM (đã chốt)
        self.nam_lau = 0         # đã nằm ≥ LIE_LONG, giữ qua giai đoạn CÚI khi ngồi dậy, xóa khi đầu thẳng lại
        self.cho_day = 0         # vừa chốt NẰM → THẲNG sau khi nằm lâu, chờ Δh để biết ngồi dậy hay đứng dậy
        self.cho = 0             # đợt vừa xong khi đầu chưa thẳng: quyết khi đầu chốt THẲNG
        self.ngh_cuoi = 0        # ep_nghieng của đợt vừa xong

    def _quyet(self, dh, ngh):
        self.cho = 0
        if dh <= -(NGOI_H_NGA if ngh else NGOI_H):
            self.ngoi = 1
        elif dh >= NGOI_H:
            self.ngoi = 0

    def _quyet_day(self, dh):
        self.ngoi = 1 if dh < DUNG_TU_NAM_H else 0
        self.cho_day = 0

    def _upd_tt(self):
        if self.huong == O_THANG:
            self.tt = DI_LAI if self.di_lai else (NGOI if self.ngoi else DUNG)
        elif self.huong == O_CUI:
            self.tt = CUI
        elif abs(self.my) > abs(self.mx):
            self.tt = NGHIENG_PHAI if self.my > 0 else NGHIENG_TRAI
        else:
            self.tt = NAM_NGUA if self.mx > 0 else NAM_SAP

    def push(self, r):
        """Một mẫu 100 Hz. Trả về 1 nếu tư thế hiển thị vừa đổi."""
        ax, ay, az = int(r[0]), int(r[1]), int(r[2])
        mag = isqrt(ax * ax + ay * ay + az * az)
        old = self.tt
        if self.huong == O_NAM and self.nam_n < 1000000:
            self.nam_n += 1
            if self.nam_n >= LIE_LONG:
                self.nam_lau = 1
        # --- đợt cử động, độ cao đầu ---
        if abs(mag - G_LSB) > MOVE_DEV:
            self.since_move = 0
        elif self.since_move < 1000000:
            self.since_move += 1
        if self.since_move < STILL_N:
            if not self.moving:
                self.moving, self.n_ep, self.v, self.h = 1, 0, 0, 0
                self.ep_nghieng = int(self.huong == O_NAM)
                self.cho = 0
            self.n_ep += 1
            self.v += mag - self.g_ref
            self.h += self.v
            if self.n_ep > LONG_N and self.huong == O_THANG and not self.ep_nghieng:
                self.di_lai, self.ngoi = 1, 0
        elif self.moving:
            self.moving = 0
            dh = self.h - tdiv(self.v * (self.n_ep + 1), 2)
            self.dh_cuoi = dh
            if self.di_lai:
                self.di_lai = 0
            elif self.huong == O_THANG and self.cho_day:
                self._quyet_day(dh)
            elif self.huong == O_THANG:
                self._quyet(dh, self.ep_nghieng)
            else:                                   # đầu chưa chốt thẳng lại: quyết khi chốt
                self.cho, self.ngh_cuoi = 1, self.ep_nghieng
        else:
            self.g_acc += mag
            self.g_n += 1
            if self.g_n == BLK:
                self.g_ref, self.g_acc, self.g_n = tdiv(self.g_acc, BLK), 0, 0
        # --- hướng đầu theo khối 32 mẫu ---
        self.sx += ax
        self.sy += ay
        self.sz += az
        self.nb += 1
        if self.nb == BLK:
            self.mx, self.my, mz = tdiv(self.sx, BLK), tdiv(self.sy, BLK), tdiv(self.sz, BLK)
            self.sx = self.sy = self.sz = self.nb = 0
            gm = isqrt(self.mx * self.mx + self.my * self.my + mz * mz)
            if mz * 100 > UP_PCT * gm:
                o = O_THANG
            elif mz * 100 < LIE_PCT * gm:
                o = O_NAM
            else:
                o = O_CUI
            if o == self.cand:
                self.cand_n += 1
            else:
                self.cand, self.cand_n = o, 1
            if self.cand_n >= HOLD and o != self.huong:
                if o == O_THANG and self.nam_lau:      # NẰM (→ CÚI) → THẲNG sau khi nằm lâu: ngồi dậy hay đứng dậy
                    self.nam_lau = 0
                    self.cho_day = 1
                    if not self.moving:              # đợt dậy đã xong trước khi chốt: quyết bằng Δh của đợt đó
                        self._quyet_day(self.dh_cuoi)
                        self.cho = 0
                elif o == O_THANG and self.cho and not self.moving:
                    self._quyet(self.dh_cuoi, self.ngh_cuoi)
                if o != O_NAM:
                    self.nam_n = 0
                self.huong = o
            if self.moving and self.huong == O_NAM:
                self.ep_nghieng = 1
            self._upd_tt()
        return int(self.tt != old)
