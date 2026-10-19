#!/bin/sh
# WorkBuddy hook —— 空闲 / 收尾 → idle。
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/../signal.sh" idle
exit 0