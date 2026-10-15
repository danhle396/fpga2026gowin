#!/usr/bin/env bash
# Stop: nếu repo còn thay đổi chưa commit hoặc commit chưa push thì chặn việc dừng và yêu cầu Claude "Chốt phiên"
# (CLAUDE.md mục 3). Chống lặp: lần dừng thứ hai (stop_hook_active = true) luôn được cho qua, chỉ cảnh báo.
input=$(cat)
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

dirty=$(git -c core.quotepath=off status --porcelain | head -20)
ahead=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
[ -z "$dirty" ] && [ "$ahead" = "0" ] && exit 0

if echo "$input" | grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
    msg="Chốt phiên chưa xong: còn thay đổi chưa commit hoặc chưa push. Gõ: Chốt phiên, trước khi đóng."
    printf '{"systemMessage": "%s"}\n' "$msg"
    exit 0
fi

files=""
[ -n "$dirty" ] && files=$(echo "$dirty" | cut -c4- | tr -d '"' | head -8 | tr '\n' ';')
reason="Hook chốt phiên: repo còn thay đổi chưa lưu lên GitHub (file: ${files:-không có}; commit chưa push: $ahead). Làm Chốt phiên theo CLAUDE.md mục 3: (1) nếu phiên này sửa ba file chính, kết quả kiểm hoặc mã thì thêm một dòng Phụ lục D, cập nhật khung TRẠNG THÁI nếu đổi mốc, lưu bằng chứng vào docs/bao_cao/; việc dở thì ghi ĐANG DỞ kèm bước tiếp theo; (2) git add -A, git commit với thông điệp '<ngày> <việc> — <kết quả>', rồi git push. Không commit file build hay file tạm (xem .gitignore). Nếu push lỗi thì báo người dùng, đừng thử lại liên tục."
reason=${reason//\\/\\\\}                 # thoát \ rồi " cho JSON
reason=${reason//\"/\\\"}
printf '{"decision": "block", "reason": "%s"}\n' "$reason"
exit 0
