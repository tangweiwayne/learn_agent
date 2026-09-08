#!/bin/bash
# 每晚自动提交 learn_agent 的当天改动
# 由 ~/Library/LaunchAgents/com.tangwei.learnagent.dailycommit.plist 定时调用

REPO="${LEARN_AGENT_DIR:-$HOME/Documents/learn_agent}"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"

cd "$REPO" || exit 1
LOG="$REPO/.autocommit.log"
NOW=$(date '+%Y-%m-%d %H:%M:%S')

# 没有任何改动就直接退出，不制造空提交
if [ -z "$(git status --porcelain)" ]; then
    echo "$NOW  无改动，跳过" >> "$LOG"
    exit 0
fi

# 提交信息里带上当天改了哪些文件
FILES=$(git status --porcelain | awk '{print $2}' | head -8 | tr '\n' ' ')
git add -A
git commit -q -m "自动提交 $(date '+%Y-%m-%d')" -m "改动: $FILES"

if git push -q origin main 2>>"$LOG"; then
    echo "$NOW  已提交并推送: $FILES" >> "$LOG"
else
    echo "$NOW  已本地提交，但 push 失败（可能网络或认证问题）: $FILES" >> "$LOG"
fi
