#!/bin/sh
# Claude Code hook —— 把执行阶段映射到点阵屏状态。
# 三个脚本同构：running / waiting / done，全部 exit 0（状态灯不干预 agent）。
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/../signal.sh" running
exit 0