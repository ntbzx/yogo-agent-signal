#!/bin/sh
# WorkBuddy hook —— 等待人工确认 → waiting。
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/../signal.sh" waiting
exit 0