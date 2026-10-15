#!/usr/bin/env python
# tools/sync_spec.py — sinh docs/spec.md từ Phụ lục A của PROJECT_MASTER.md (việc TH-01). Bản gốc, tức là luật,
# vẫn là Phụ lục A; docs/spec.md chỉ là bản chép để đọc riêng, không sửa tay. Sửa SPEC thì sửa Phụ lục A rồi chạy lại.
#
#   python -I tools/sync_spec.py            # ghi lại docs/spec.md
#   python -I tools/sync_spec.py --check    # chỉ kiểm: in PASS nếu docs/spec.md trùng Phụ lục A, FAIL (mã 1) nếu lệch
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MASTER = ROOT / "PROJECT_MASTER.md"
OUT = ROOT / "docs" / "spec.md"
BEGIN, END = "## PHỤ LỤC A", "## PHỤ LỤC B"
HEADER = ("<!-- Sinh tự động bằng tools/sync_spec.py từ Phụ lục A của PROJECT_MASTER.md. Đừng sửa tay: sửa Phụ lục A "
          "rồi chạy lại script. Khi hai bản khác nhau, Phụ lục A thắng. -->\n\n")


def build():
    lines = MASTER.read_text(encoding="utf-8").splitlines(keepends=True)
    i = next(k for k, l in enumerate(lines) if l.startswith(BEGIN))
    j = next(k for k, l in enumerate(lines) if k > i and l.startswith(END))
    body = "".join(lines[i:j]).rstrip()
    if body.endswith("---"):                 # đường kẻ ngăn cách phụ lục trong file gốc
        body = body[:-3].rstrip()
    return HEADER + body + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = build()
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print(("PASS" if ok else "FAIL") + f"  {OUT.relative_to(ROOT).as_posix()} "
              + ("trùng Phụ lục A" if ok else "lệch Phụ lục A: chạy python -I tools/sync_spec.py"))
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"ghi   {OUT.relative_to(ROOT).as_posix()} ({text.count(chr(10))} dòng)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
