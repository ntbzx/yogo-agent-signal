"""状态协调整体 —— 把「agent 状态」翻译成「点阵帧」并推给传输层。

数据来源（按优先级）：
  1. state.json 文件（hooks 写这里，最稳）
  2. HTTP 接口 POST /state

状态机：
  idle → running → waiting → done/error → idle
  帧动画由 run 循环按 FPS 轮播，push 到 transport。
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone

from . import patterns, protocol, render


class StateMachine:
    def __init__(self, transport, state_file: str, fps: float = 6.0,
                 idle_timeout: float = 30.0):
        self.transport = transport
        self.state_file = state_file
        self.fps = fps
        self.idle_timeout = idle_timeout

        self._state = "idle"
        self._frame_index = 0
        self._frames = patterns.idle_frames()
        self._last_activity = time.time()
        self._lock = threading.Lock()
        self._running = False
        self._state_history: list[dict] = []

    # ── 状态读写 ──────────────────────────────────────────────────
    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def set_state(self, state: str, source: str = "http"):
        if state not in patterns.VALID_STATES:
            raise ValueError(f"未知状态 {state!r}，可选：{sorted(patterns.VALID_STATES)}")
        with self._lock:
            self._state = state
            self._frames = patterns.STATE_EFFECTS[state]()
            self._frame_index = 0
            self._last_activity = time.time()
            self._state_history.append({
                "state": state, "source": source,
                "ts": datetime.now(timezone.utc).isoformat(),
            })

    def _load_state_file(self):
        # 只读最新的 mtime 变化，避免频繁轮询
        try:
            st = os.stat(self.state_file)
            age = time.time() - st.st_mtime
            if age < 2.0:  # 2 秒内写入才采信，防止残留旧状态长期占用
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                state = data.get("state")
                if state in patterns.VALID_STATES:
                    if state != self.state:
                        self.set_state(state, source="file")
                        print(f"[yas] 状态 → {state} (来自 {self.state_file})")
                    return
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError):
            pass

    # ── 动画循环 ──────────────────────────────────────────────────
    def _tick(self):
        self._load_state_file()

        with self._lock:
            # 短暂状态（running/waiting/done/error）超过 idle_timeout 未刷新则回落到 idle
            if self._state != "idle" and time.time() - self._last_activity > self.idle_timeout:
                self._state = "idle"
                self._frames = patterns.idle_frames()
                self._frame_index = 0
                print("[yas] 超时回落 → idle")

            if not self._frames:
                return
            self._frame_index = (self._frame_index + 1) % len(self._frames)
            frame = self._frames[self._frame_index]

        flat = render.frame_to_flat(frame)
        changed = self.transport.push_matrix(flat)
        return changed

    def run(self):
        self._running = True
        interval = 1.0 / self.fps
        print(f"[yas] 状态机启动，FPS={self.fps}，传输后端={type(self.transport).__name__}")
        while self._running:
            try:
                self._tick()
            except Exception as e:  # noqa: BLE001
                print(f"[yas] 循环异常：{e}")
            time.sleep(interval)

    def stop(self):
        self._running = False

    # ── HTTP 接口（供 hooks 调用）────────────────────────────────
    def make_http_app(self):
        """返回一个简单 WSGI/手写 HTTP handler，用 http.server 即可。"""
        from http.server import BaseHTTPRequestHandler

        machine = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # 静默
                pass

            def _send_json(self, obj, code=200):
                body = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path in ("/", "/state", "/status"):
                    self._send_json({"state": machine.state, "ok": True})
                else:
                    self._send_json({"ok": False, "error": "not found"}, 404)

            def do_POST(self):
                if self.path != "/state":
                    self._send_json({"ok": False, "error": "not found"}, 404)
                    return
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length) if length else b"{}"
                    data = json.loads(raw or b"{}")
                    if not isinstance(data, dict):
                        self._send_json(
                            {"ok": False, "error": "body must be a JSON object"}, 400)
                        return
                    state = data.get("state")
                    if state not in patterns.VALID_STATES:
                        self._send_json(
                            {"ok": False, "error": f"invalid state {state!r}"}, 400)
                        return
                    machine.set_state(state, source="http")
                    self._send_json({"ok": True, "state": machine.state})
                except ValueError:
                    # JSONDecodeError / 非 UTF-8 body / 非法 Content-Length 都是 ValueError
                    self._send_json({"ok": False, "error": "bad json"}, 400)

        return Handler


def make_server(machine: StateMachine, host: str = "127.0.0.1", port: int = 8787):
    """绑定端口并返回 HTTPServer。端口被占用时抛 OSError，由调用方提示。

    单独拆出来是为了让 cli 先占端口、再碰键盘：端口被占通常说明已有一个
    yas run 在跑，这时应直接退出，而不是带着一个挂掉的 HTTP 线程继续运行。
    """
    from http.server import HTTPServer
    return HTTPServer((host, port), machine.make_http_app())


def run_server(server) -> None:
    """在当前线程里跑 make_server() 返回的 server，直到进程退出。"""
    try:
        server.serve_forever()
    finally:
        server.server_close()