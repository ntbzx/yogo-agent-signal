#!/bin/sh
# Claude Code hook —— SessionEnd → idle。
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/../signal.sh" idle
exit 0