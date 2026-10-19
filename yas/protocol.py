"""HID 协议层 —— ATK YOGO 75 PRO 点阵屏报文编解码。

协议（对照 YogoDot kbd.py 逆向结果）：
    包 32 字节：[0xAA, cmd, off_lo, off_hi, len, seq, 0, 0, payload@8...]
    HID 收发时前面再加 1 字节 report id（0），合计 33 字节。
    回包 seq 在第 6 字节（含 report id），数据从第 9 字节起。

命令号：
    16 握手 / 20 读配置 / 21 写配置 / 46 逐键推流 / 47 结束推流 /
    48 电量 / 59 点阵屏 / 49 恢复出厂（⚠️ 永不可发送）
"""

VID = 0x373B
VENDOR_USAGE_PAGE = 0xFF60

C_HAND = 16
C_READ = 20
C_WRITE = 21
C_SYNCLED = 46
C_ENDSYNC = 47
C_POWER = 48
C_RESET = 49  # 危险命令，仅作记录，代码中绝不发送
C_MATRIX = 59

HEADER = 0xAA
PKT = 33            # report id + 32
MATRIX_BYTES = 108  # 6 * 6 * 3 (RGB)
MATRIX_PACKETS = 5  # 每包 24 字节，偏移 0/24/48/72/96
CONFIG_BYTES = 64
REPLY_DATA_OFFSET = 9  # 回包有效数据起始字节（含 report id）


def make_packet(cmd: int, offset: int = 0, payload: bytes = b"", length=None, seq: int = 1) -> bytearray:
    """构造一条 33 字节 HID 输出报文。"""
    pkt = bytearray(PKT)
    pkt[0] = 0                     # report id
    pkt[1] = HEADER
    pkt[2] = cmd
    pkt[3] = offset & 0xFF
    pkt[4] = (offset >> 8) & 0xFF
    pkt[5] = length if length is not None else len(payload)
    pkt[6] = seq
    # pkt[7], pkt[8] 保持 0
    pl = bytes(payload)[:24]
    pkt[9:9 + len(pl)] = pl
    return pkt


def seq_of_reply(reply: bytes) -> int:
    """从回包中取出 seq（第 6 字节，含 report id）。"""
    if len(reply) < 7:
        return -1
    return reply[6]


def data_of_reply(reply: bytes) -> bytes:
    """从回包中取出有效数据（从第 9 字节开始）。"""
    if len(reply) <= REPLY_DATA_OFFSET:
        return b""
    return reply[REPLY_DATA_OFFSET:]


def matrix_packets(flat: bytes) -> list[tuple[int, bytes]]:
    """把 108 字节点阵帧切成 5 包 (offset, 24字节)。"""
    flat = bytes(flat)[:MATRIX_BYTES].ljust(MATRIX_BYTES, b"\x00")
    return [(i * 24, flat[i * 24:i * 24 + 24].ljust(24, b"\x00"))
            for i in range(MATRIX_PACKETS)]


def dots_to_flat(rows: list[tuple[int, int, tuple]], cols: int = 6) -> bytes:
    """把 (row, col, (r,g,b)) 列表转成 108 字节 RGB 平铺（row-major）。

    每格 3 字节 RGB。未列出的格为黑（0,0,0）。
    """
    flat = bytearray(MATRIX_BYTES)
    for row, col, rgb in rows:
        if not (0 <= row < cols and 0 <= col < cols):
            continue
        i = (row * cols + col) * 3
        flat[i] = max(0, min(255, rgb[0]))
        flat[i + 1] = max(0, min(255, rgb[1]))
        flat[i + 2] = max(0, min(255, rgb[2]))
    return bytes(flat)