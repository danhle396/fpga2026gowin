#!/usr/bin/env bash
# SessionStart: kéo bản mới nhất từ GitHub (chỉ khi cây làm việc sạch) rồi báo cho Claude trạng thái repo,
# để phiên trên máy / tài khoản khác bắt đầu từ đúng chỗ phiên trước dừng (CLAUDE.md mục 1, 3).
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

echo "== Hook SessionStart (CLAUDE.md mục 3: thay phiên) =="
if [ -n "$(git status --porcelain)" ]; then
    echo "CẢNH BÁO: repo có thay đổi chưa commit từ trước. KHÔNG git pull; hỏi người dùng trước khi làm tiếp:"
    git status --short | head -20
else
    out=$(GIT_TERMINAL_PROMPT=0 timeout 60 git pull --ff-only 2>&1)
    rc=$?
    if [ $rc -eq 0 ]; then
        echo "git pull: $(echo "$out" | tail -1)"
    else
        echo "CẢNH BÁO: git pull thất bại (mạng / đăng nhập / lịch sử rẽ nhánh). Báo người dùng. Chi tiết:"
        echo "$out" | tail -5
    fi
fi
echo "Commit gần nhất:"
git log --oneline -5
f=PROJECT_MASTER.md
if [ -f "$f" ]; then
    n=$(grep -c "ĐANG DỞ" "$f")
    [ "$n" -gt 0 ] && { echo "Có mục ĐANG DỞ trong $f (đọc trước khi làm việc khác):"; grep -n "ĐANG DỞ" "$f" | tail -3 | cut -c1-300; }
fi
echo "Nhắc: đọc CLAUDE.md, PROMPT_KHOI_CONG.md, khung TRẠNG THÁI và 10 dòng cuối Phụ lục D trước khi làm."
exit 0
