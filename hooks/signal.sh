#!/bin/sh
# 通用信号发送封装 —— 供各类 agent hook 调用。
# 用法：signal.sh running | waiting | done | idle | error
#
# 设计原则：状态灯是「增强」，绝不阻断 agent。本脚本永远 exit 0，
# daemon 没起 / 网络不通时静默失败，不影响主流程。

PORT="${YAS_PORT:-8787}"
HOST="${YAS_HOST:-127.0.0.1}"
STATE="$1"

if [ -z "$STATE" ]; then
  echo "用法：signal.sh <state>" >&2
  exit 0
fi

# 优先用 python（跨平台），没有则用 curl，再没有则放弃
if command -v python3 >/dev/null 2>&1; then
  python3 - "$STATE" "$HOST" "$PORT" <<'PY'
import json, sys, urllib.request
state, host, port = sys.argv[1], sys.argv[2], sys.argv[3]
url = f"http://{host}:{port}/state"
try:
    req = urllib.request.Request(url, data=json.dumps({"state": state}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=1)
except Exception:
    pass  # 静默：状态灯不属于关键路径
PY
elif command -v curl >/dev/null 2>&1; then
  curl -s -X POST "http://${HOST}:${PORT}/state" \
    -H "Content-Type: application/json" \
    -d "{\"state\":\"${STATE}\"}" >/dev/null 2>&1
fi

exit 0