#!/bin/sh
# WorkBuddy hook —— 执行中 → running。
# 把本文件放到你的 hooks 目录，并让它在工具执行前/执行中触发。
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/../signal.sh" running
exit 0