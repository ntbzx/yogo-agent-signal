"""状态图案定义 —— 6×6 点阵，五态。

Q：为什么 6×6？
   ATK YOGO 75 PRO 右上角点阵屏是 6×6 像素，且带磨砂灯罩，像素边缘柔和。

Q：配色为什么"怪怪的"？
   键盘 LED 红:绿:蓝 发光效率约 1:4:14。低饱和颜色上灯后会发白，
   所以这里最亮通道拉满、最暗通道压到 50 以下，牺牲一点屏幕上的饱和度
   来换键盘上的准确观感。
"""

from dataclasses import dataclass
from typing import Callable

# (r, g, b) 均为 0-255
COLORS = {
    "run": (8, 200, 80),      # 执行中 —— 绿色循环点
    "wait": (240, 140, 8),    # 等待确认 —— 琥珀色闪烁
    "done": (10, 220, 90),    # 完成 —— 绿色勾
    "err":  (230, 40, 40),    # 出错 —— 红色叉
    "idle": (60, 140, 255),   # 空闲 —— 蓝色呼吸点
}


@dataclass(frozen=True)
class Pattern:
    """一个静态帧。dots 为 { (row,col): (r,g,b) }。"""
    name: str
    dots: dict


def _frame_dict(rows, color) -> dict:
    """把 [(row, col), ...] 角色坐标渲染成 { (r,c): color }。"""
    return {(r, c): color for r, c in rows}


# ── 执行中：转圈（顺时针 6 格外圈循环） ─────────────────────────────
_RUN_FRAMES = [
    [(0, 0)], [(0, 1)], [(0, 2)], [(0, 3)], [(0, 4)],
    [(0, 5)], [(1, 5)], [(2, 5)], [(3, 5)], [(4, 5)],
    [(5, 5)], [(5, 4)], [(5, 3)], [(5, 2)], [(5, 1)],
    [(5, 0)], [(4, 0)], [(3, 0)], [(2, 0)], [(1, 0)],
]


def run_frames(color=None) -> list[dict]:
    c = color or COLORS["run"]
    # 外圈循环 + 尾巴留 2 格余晖，更灵动
    frames = []
    trail = 2
    for i in range(len(_RUN_FRAMES)):
        dots = {}
        for t in range(trail + 1):
            idx = (i - t) % len(_RUN_FRAMES)
            fade = 255 - int(t * (255 / (trail + 1)))  # 越老越暗
            rr, cc = _RUN_FRAMES[idx][0]
            dots[(rr, cc)] = (max(1, c[0] * fade // 255),
                              max(1, c[1] * fade // 255),
                              max(1, c[2] * fade // 255))
        frames.append(dots)
    return frames


# ── 等待确认：感叹号 / 圆点闪烁 ────────────────────────────────────
_WAIT_DOT = [(2, 2), (2, 3), (3, 2), (3, 3)]           # 中心 2×2
_WAIT_BANG = [(0, 2), (0, 3), (1, 2), (1, 3), (2, 2), (2, 3),
              (3, 2), (3, 3), (5, 2), (5, 3)]           # 感叹号


def wait_frames(color=None) -> list[dict]:
    c = color or COLORS["wait"]
    return [_frame_dict(_WAIT_DOT, c), _frame_dict(_WAIT_BANG, c)]


# ── 完成：绿色勾 ──────────────────────────────────────────────────
_DONE_CHECK = [(0, 4), (1, 5), (2, 4), (3, 3), (4, 2), (5, 1)]


def done_frame(color=None) -> dict:
    c = color or COLORS["done"]
    return _frame_dict(_DONE_CHECK, c)


# ── 出错：红色叉 ──────────────────────────────────────────────────
_ERR_X = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5),
          (0, 5), (1, 4), (2, 3), (3, 2), (4, 1), (5, 0)]


def err_frame(color=None) -> dict:
    c = color or COLORS["err"]
    return _frame_dict(_ERR_X, c)


# ── 空闲：单个呼吸点 ──────────────────────────────────────────────
_IDLE_DOT = [(2, 2), (2, 3), (3, 2), (3, 3)]


def idle_frames(color=None) -> list[dict]:
    c = color or COLORS["idle"]
    # 三档亮度呼吸
    levels = [96, 200, 128]
    return [_frame_dict(_IDLE_DOT, tuple(max(1, v * lv // 255) for v in c))
            for lv in levels]


# ── 统一状态机：每种状态产出若干帧，由 daemon 按帧率轮播 ──────────
STATE_EFFECTS: dict[str, Callable[[], list[dict]]] = {
    "idle": idle_frames,
    "running": run_frames,
    "waiting": wait_frames,
    "done": lambda: [done_frame()],
    "error": lambda: [err_frame()],
}

VALID_STATES = set(STATE_EFFECTS.keys())