#!/bin/sh
# WorkBuddy hook —— 任务完成 → done。
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/../signal.sh" done
exit 0