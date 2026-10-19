"""渲染层 —— 把点阵帧渲染成像素 PNG / ASCII / 终端颜色块。

用于：无键盘时的预览、README 配图、自检（render --check）。
真实推屏走 transport，不经过这里。"""

from __future__ import annotations

import sys

from . import protocol


def frame_to_rgb_matrix(frame: dict, cols: int = 6) -> list[list[tuple[int, int, int]]]:
    """返回 cols×cols 的 RGB 二维数组。"""
    grid = [[(0, 0, 0) for _ in range(cols)] for _ in range(cols)]
    for (r, c), rgb in frame.items():
        if 0 <= r < cols and 0 <= c < cols:
            grid[r][c] = rgb
    return grid


def frame_to_flat(frame: dict, cols: int = 6) -> bytes:
    """渲染成 108 字节 RGB，可直接推屏。"""
    grid = frame_to_rgb_matrix(frame, cols)
    dots = [(r, c, grid[r][c]) for r in range(cols) for c in range(cols)]
    return protocol.dots_to_flat(dots, cols)


def frame_to_ascii(frame: dict, cols: int = 6) -> str:
    """把一帧渲染成 ASCII 图，'X' 为亮点。"""
    grid = frame_to_rgb_matrix(frame, cols)
    lines = []
    for r in range(cols):
        line = "".join("#" if sum(grid[r][c]) > 0 else "·" for c in range(cols))
        lines.append(line)
    return "\n".join(lines)


def frame_to_terminal(frame: dict, cols: int = 6) -> str:
    """带颜色的终端输出（TrueColor）。"""
    grid = frame_to_rgb_matrix(frame, cols)
    lines = []
    for r in range(cols):
        cells = []
        for c in range(cols):
            R, G, B = grid[r][c]
            if R or G or B:
                cells.append(f"\x1b[48;2;{R};{G};{B}m  \x1b[0m")
            else:
                cells.append("  ")
        lines.append("".join(cells))
    return "\n".join(lines)


def render_png(frame: dict, path: str, scale: int = 24, cols: int = 6):
    """渲染一帧为 PNG。scale 为每格的像素尺寸。"""
    from PIL import Image

    grid = frame_to_rgb_matrix(frame, cols)
    img = Image.new("RGB", (cols * scale, cols * scale), (0, 0, 0))
    px = img.load()
    for r in range(cols):
        for c in range(cols):
            for dy in range(scale):
                for dx in range(scale):
                    px[c * scale + dx, r * scale + dy] = grid[r][c]
    img.save(path)


def render_animation(frames: list[dict], prefix: str, scale: int = 24, cols: int = 6):
    """把多帧存成 PNG 序列 file00.png, file01.png ..."""
    from PIL import Image

    paths = []
    for i, frame in enumerate(frames):
        p = f"{prefix}{i:02d}.png"
        render_png(frame, p, scale=scale, cols=cols)
        paths.append(p)
    return paths


def render_gif(frames: list[dict], path: str, scale: int = 24, cols: int = 6,
               duration_ms: int = 120):
    """把多帧合成一张 GIF 动图。"""
    from PIL import Image

    grid_frames = [frame_to_rgb_matrix(f, cols) for f in frames]
    imgs = []
    for grid in grid_frames:
        img = Image.new("RGB", (cols * scale, cols * scale), (0, 0, 0))
        px = img.load()
        for r in range(cols):
            for c in range(cols):
                for dy in range(scale):
                    for dx in range(scale):
                        px[c * scale + dx, r * scale + dy] = grid[r][c]
        imgs.append(img)
    imgs[0].save(path, save_all=True, append_images=imgs[1:],
                 duration=duration_ms, loop=0)


if __name__ == "__main__":
    # 自检：把五态的中间帧打到终端
    from . import patterns  # 相对导入在此上下文中可能失败，见 cli.py
    print("patterns import needs package context; use `yas check` instead.")
    sys.exit(1)