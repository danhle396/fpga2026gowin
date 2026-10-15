#!/usr/bin/env python
# tools/svd_decode.py — giải mã mọi lệnh ghi thanh ghi có giá trị hằng trong firmware theo SVD của SONiX: in tên trường và
# giá trị của từng trường, cảnh báo khi ghi bit không thuộc trường nào (bit dự trữ), ghi trường chỉ đọc, hoặc giá trị
# vượt độ rộng trường. Dùng để rà firmware trước khi lên board (phần chạm ngoại vi chưa chạy thật).
#
#   python tools/svd_decode.py firmware/src/*.c test_sensor/firmware/*.c
#
# Chỉ đọc mã nguồn, không sinh file. Lệnh ghi có biến (clkdiv, half, mask…) được liệt kê là "không hằng" để rà bằng mắt.
import argparse
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
SVD = ROOT / "sdk" / "SN32F4_DFP" / "SVD" / "SN32F400.svd"
WRITE = re.compile(r"\b(SN_\w+)->(\w+?)(?:_b\.(\w+))?\s*(\|=|&=|\^=|=)(?!=)\s*([^;]+);")
DEFINE = re.compile(r"^\s*#define\s+(\w+)\s+(.+?)\s*(?:/\*.*)?$")


def load_svd(path):
    root = ET.parse(path).getroot()
    periph = {}
    for p in root.iter("peripheral"):
        periph[p.findtext("name")] = p
    out = {}
    for name, p in periph.items():
        src = periph.get(p.get("derivedFrom"), p) if p.get("derivedFrom") else p
        regs = {}
        for r in src.iter("register"):
            racc = r.findtext("access") or "read-write"
            fields = []
            for f in r.iter("field"):
                if f.findtext("bitOffset") is not None:
                    lo, w = int(f.findtext("bitOffset"), 0), int(f.findtext("bitWidth"), 0)
                else:
                    hi, lo = map(int, f.findtext("bitRange").strip("[]").split(":"))
                    w = hi - lo + 1
                fields.append((f.findtext("name"), lo, w, f.findtext("access") or racc))
            regs[r.findtext("name")] = (racc, sorted(fields, key=lambda x: x[1]))
        out[name] = regs
    return out


def c_eval(expr, defs, depth=0):
    e = expr.strip()
    for _ in range(5):                                  # thay macro (lồng nhau vài tầng)
        e2 = re.sub(r"\b[A-Za-z_]\w*\b", lambda m: "(" + defs[m.group(0)] + ")" if m.group(0) in defs else m.group(0), e)
        if e2 == e:
            break
        e = e2
    e = re.sub(r"\b(0[xX][0-9a-fA-F]+|\d+)[uUlL]+\b", r"\1", e)
    e = re.sub(r"\(\s*uint\d+_t\s*\)", "", e)
    if re.search(r"[A-Za-z_]\w*", re.sub(r"0[xX][0-9a-fA-F]+", "", e)):
        return None
    try:
        return int(eval(e, {"__builtins__": {}}, {})) & 0xFFFFFFFF   # noqa: S307 — chỉ còn số và toán tử
    except Exception:  # noqa: BLE001
        return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+", type=pathlib.Path)
    ap.add_argument("--svd", type=pathlib.Path, default=SVD)
    a = ap.parse_args()
    svd = load_svd(a.svd)
    n_warn = n_const = n_var = 0
    for path in a.files:
        text = path.read_text(encoding="utf-8", errors="replace")
        defs = {}
        for ln in text.splitlines():
            m = DEFINE.match(ln)
            if m and "(" not in m.group(1):
                defs[m.group(1)] = re.sub(r"/\*.*?\*/|//.*", "", m.group(2)).strip()
        # bỏ chú thích nhưng giữ xuống dòng, để câu lệnh trải nhiều dòng vẫn khớp và số dòng vẫn đúng
        code = re.sub(r"/\*.*?\*/|//[^\n]*", lambda c: "\n" * c.group(0).count("\n"), text, flags=re.S)
        for m in WRITE.finditer(code):
            per, reg, bitf, op, rhs = m.groups()
            rhs = " ".join(rhs.split())
            where = f"{path.name}:{code.count(chr(10), 0, m.start()) + 1}"
            if per not in svd:
                print(f"{where}  CẢNH BÁO: {per} không có trong SVD"); n_warn += 1; continue
            if reg not in svd[per]:
                print(f"{where}  CẢNH BÁO: {per}->{reg} không có trong SVD"); n_warn += 1; continue
            racc, fields = svd[per][reg]
            if op == "&=" or op == "^=":
                n_var += 1
                print(f"{where}  {per}->{reg} {op} {rhs.strip()}  (xóa / đảo bit — rà bằng mắt)")
                continue
            v = c_eval(rhs, defs)
            if v is None:
                n_var += 1
                print(f"{where}  {per}->{reg}{'_b.' + bitf if bitf else ''} {op} {rhs.strip()}  (không hằng)")
                continue
            n_const += 1
            warns = []
            if bitf:
                f = [x for x in fields if x[0] == bitf]
                if not f:
                    warns.append(f"trường {bitf} không có trong {reg}")
                    desc = f"{bitf}={v}"
                else:
                    _, lo, w, acc = f[0]
                    desc = f"{bitf}[{lo + w - 1}:{lo}]={v}"
                    if v >> w:
                        warns.append(f"giá trị {v} vượt {w} bit")
                    if acc == "read-only":
                        warns.append("trường chỉ đọc")
            else:
                parts, covered = [], 0
                for name, lo, w, acc in fields:
                    mask = ((1 << w) - 1) << lo
                    covered |= mask
                    fv = (v & mask) >> lo
                    if fv:
                        parts.append(f"{name}={fv:#x}" if w > 1 else name)
                        if acc == "read-only":
                            warns.append(f"ghi 1 vào trường chỉ đọc {name}")
                if fields and v & ~covered & 0xFFFFFFFF:
                    warns.append(f"bit dự trữ {v & ~covered & 0xFFFFFFFF:#010x}")
                if racc == "read-only":
                    warns.append("thanh ghi chỉ đọc")
                desc = ", ".join(parts) if parts else ("0" if fields else f"{v:#x} (SVD không chia trường)")
            n_warn += bool(warns)
            print(f"{where}  {per}->{reg} {op} {v:#x}: {desc}" + ("  ⚠ " + "; ".join(warns) if warns else ""))
    print(f"--- {n_const} lệnh ghi hằng đã giải mã, {n_var} lệnh có biến / xóa bit, {n_warn} dòng có cảnh báo")


if __name__ == "__main__":
    main()
