#!/usr/bin/env bash
# tools/fetch_d1.sh — tải bộ D1 (Özdemir & Barshan, UCI #455, CC BY 4.0) và giải nén các người đã tải trọn (việc AI-13).
#   bash tools/fetch_d1.sh <thư mục ngoài repo>              # tải rồi giải nén
#   bash tools/fetch_d1.sh <thư mục ngoài repo> <file .zip>  # chỉ giải nén từ một file zip có sẵn, kể cả tải dở
# Rồi: python -I tools/convert_d1.py --src <thư mục>/src --out ml/data/public   (thêm --sensor 340539 / 340535 cho ngực / thắt lưng)
#
# Gói zip 1,24 GB chứa đúng một mục Tests.rar lưu nguyên (method 0, dữ liệu bắt đầu ở byte 39). Tests.rar (RAR5) chứa
# Tests/<mã người>.rar, mỗi người 57–73 MB. Máy chủ UCI không nhận Range, nên file tải dở vẫn giải được những người
# nằm trọn trong phần đã tải. Giải RAR bằng bsdtar có sẵn trong Windows 10/11 (C:\Windows\System32\tar.exe); GNU tar
# của Git Bash không đọc được RAR. Dữ liệu tải về là dữ liệu ngoài: đặt ngoài repo, đọc bằng python -I.
set -u
URL="https://archive.ics.uci.edu/static/public/455/simulated+falls+and+daily+living+activities+data+set.zip"
D="${1:?thư mục làm việc ngoài repo}"
ZIP="${2:-$D/dl/d1.zip}"
BSDTAR="${BSDTAR:-/c/Windows/System32/tar.exe}"
mkdir -p "$D/dl" "$D/rar" "$D/src"
if [ $# -lt 2 ]; then
    curl -L -S -o "$ZIP" -w "http=%{http_code} size=%{size_download} speed=%{speed_download} B/s\n" "$URL" \
        || echo "tải bị ngắt; vẫn giải nén phần đã có"
fi
# phần Tests.rar (bỏ 39 byte đầu của local header zip)
tail -c +40 "$ZIP" > "$D/Tests_part.rar"
(cd "$D/rar" && "$BSDTAR" -xf "$(cygpath -w "$D/Tests_part.rar")" 2>&1 | grep -v -i truncated)
rm -f "$D/Tests_part.rar"
# file người cuối cùng có thể bị cắt cụt: giải lỗi thì bỏ cả thư mục người đó
for f in "$D"/rar/Tests/*.rar; do
    [ -f "$f" ] || continue
    sid="$(basename "$f" .rar)"
    if (cd "$D/src" && "$BSDTAR" -xf "$(cygpath -w "$f")") 2>/dev/null; then    # rar có sẵn thư mục <mã người>/
        echo "  $sid: giải nén xong"
    else
        echo "  $sid: file rar cụt hoặc hỏng, bỏ"; rm -rf "$D/src/$sid"
    fi
done
echo "người đã có: $(cd "$D/src" && ls | tr '\n' ' ')"
