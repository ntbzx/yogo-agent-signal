#!/bin/sh
# Claude Code hook —— 响应完成 → 绿色勾；会话结束 → 回到 idle。
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/../signal.sh" done
exit 0