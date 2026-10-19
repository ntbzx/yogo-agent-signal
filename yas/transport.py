"""传输层 —— 点阵帧如何到达键盘。

两个后端：
  - HIDTransport  ：经 hidapi 走真实 HID 厂商通道（Mac/Linux/Windows 通用，
                    替代 Windows-only 的 ctypes 实现）
  - DummyTransport：无键盘时打印到终端 / 写 PNG，方便演示与 CI
"""

from __future__ import annotations

import time

from . import protocol


class TransportError(Exception):
    pass


class HIDTransport:
    """用 hidapi 找到键盘的厂商通道并推流。

    hidapi 屏蔽了平台差异：macOS 用 IOHIDManager、Windows 用 HidD_*、
    Linux 用 hidraw，我们只需按 VID + usage_page 过滤。
    """

    def __init__(self, vid: int = protocol.VID):
        self.vid = vid
        self.dev = None
        self.path = None
        self._seq = 0
        self._matrix_last: bytes | None = None
        self._matrix_t = 0.0

    # ── 设备枚举与打开 ────────────────────────────────────────────
    def _enum_vendor(self):
        import hid
        devices = []
        for info in hid.enumerate(self.vid, 0):
            # usage_page 由 hidapi 暴露在 info 里（不同版本字段名略有差异）
            up = getattr(info, "usage_page", None)
            if up is None:
                up = getattr(info, "interface_number", None)
            devices.append(info)
        return devices

    def open(self) -> bool:
        import hid
        try:
            candidates = [i for i in hid.enumerate(self.vid, 0)
                          if getattr(i, "usage_page", 0) == protocol.VENDOR_USAGE_PAGE
                          or getattr(i, "usage", 0) == protocol.VENDOR_USAGE_PAGE]
            # 若按 usage_page 过滤不到（依赖 hidapi 版本），退化为拿第一个 VID 匹配设备
            if not candidates:
                candidates = list(hid.enumerate(self.vid, 0))
            if not candidates:
                raise TransportError(
                    "没找到 VID 0x373B 的设备。请确认键盘已开机且处于 2.4G 或有线档。")
            info = candidates[0]
            self.dev = hid.device()
            self.dev.open_path(info["path"])
            self.path = info["path"]
            self._seq = 0
            return True
        except TransportError:
            raise
        except Exception as e:  # noqa: BLE001
            raise TransportError(f"打开键盘失败：{e}") from e

    def close(self):
        if self.dev:
            try:
                self.dev.close()
            except Exception:  # noqa: BLE001
                pass
            self.dev = None
            self.path = None

    @property
    def connected(self) -> bool:
        return self.dev is not None

    # ── 收发 ──────────────────────────────────────────────────────
    def _send(self, cmd, offset=0, payload=b"", length=None, wait=True, timeout=0.9):
        self._seq = self._seq % 250 + 1
        pkt = protocol.make_packet(cmd, offset, payload, length, self._seq)
        self.dev.write(bytes(pkt))
        if not wait:
            return None
        # hidapi 会阻塞读，我们用 read 的 timeout 参数
        t0 = time.time()
        while time.time() - t0 < timeout:
            reply = self.dev.read(protocol.PKT, timeout_ms=int(timeout * 1000))
            if reply and len(reply) > 0:
                if protocol.seq_of_reply(bytes(reply)) == self._seq:
                    return bytes(reply)
        return None

    def handshake(self) -> None:
        self._send(protocol.C_HAND, 0, b"", 0, wait=False)

    def push_matrix(self, flat: bytes) -> bool:
        """108 字节点阵帧 → 5 包推流。返回是否已写设备。"""
        flat = bytes(flat)[:protocol.MATRIX_BYTES].ljust(protocol.MATRIX_BYTES, b"\x00")
        if flat == self._matrix_last:
            return False  # 与上一帧相同，跳过
        self.handshake()
        for offset, chunk in protocol.matrix_packets(flat):
            self._send(protocol.C_MATRIX, offset, chunk, wait=False)
        self._matrix_last = flat
        self._matrix_t = time.time()
        return True

    def read_battery(self) -> int | None:
        """读电量百分比，读不到返回 None。"""
        try:
            self.handshake()
            r = self._send(protocol.C_POWER, 0, b"", 0)
        except Exception:  # noqa: BLE001
            return None
        if not r or len(r) < 11:
            return None
        return min(100, r[9])


class DummyTransport:
    """无硬件后端：推流打印 ASCII / 终端色块，可选写 PNG。"""

    def __init__(self, sink: str = "terminal", out_dir: str | None = None):
        self.sink = sink
        self.out_dir = out_dir
        self._last = None
        self._count = 0

    def open(self) -> bool:
        return True

    def close(self):
        pass

    @property
    def connected(self) -> bool:
        return True

    def push_matrix(self, flat: bytes) -> bool:
        grid = [tuple(flat[i:i + 3]) for i in range(0, protocol.MATRIX_BYTES, 3)]
        self._count += 1
        if self.sink == "none":
            return True
        # 只打印变化帧
        if flat == self._last:
            return False
        self._last = flat
        if self.sink == "ascii":
            from .render import frame_to_ascii
            frame = {(i // 6, i % 6): grid[i] for i in range(36) if any(grid[i])}
            print(f"[frame {self._count}]")
            print(frame_to_ascii(frame))
            print()
        elif self.sink == "terminal":
            from .render import frame_to_terminal
            frame = {(i // 6, i % 6): grid[i] for i in range(36) if any(grid[i])}
            print(f"[frame {self._count}]")
            print(frame_to_terminal(frame))
            print()
        return True