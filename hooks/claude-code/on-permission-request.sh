#!/bin/sh
# Claude Code hook —— 等待权限确认 → amber 闪烁。
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/../signal.sh" waiting
exit 0