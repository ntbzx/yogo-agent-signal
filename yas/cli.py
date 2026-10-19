"""yas 命令行入口。

用法：
  python -m yas check             # 渲染五态图案到终端 + 生成 PNG/GIF 到 assets/
  python -m yas probe             # 探测真实键盘并推一帧测试图案
  python -m yas run               # 启动状态守护进程（HTTP 127.0.0.1:8787）
  python -m yas run --dummy       # 无键盘模拟运行（终端色块演示）
"""

from __future__ import annotations

import argparse
import os
import sys

from . import patterns, protocol, render


def cmd_check(args):
    print("=" * 40)
    print("五态图案自检（6×6 点阵）")
    print("=" * 40)
    os.makedirs(args.out, exist_ok=True)

    for state in ("idle", "running", "waiting", "done", "error"):
        frames = patterns.STATE_EFFECTS[state]()
        mid = frames[len(frames) // 2]
        print(f"\n【{state}】 ({len(frames)} 帧)")
        if args.color and sys.stdout.isatty():
            print(render.frame_to_terminal(mid))
        else:
            print(render.frame_to_ascii(mid))
        if args.gif:
            render.render_gif(frames, os.path.join(args.out, f"{state}.gif"))
        else:
            render.render_png(mid, os.path.join(args.out, f"{state}.png"))

    print(f"\n图案已写出到 {args.out}/")
    print("提示：真实推屏前请先用 `yas probe` 确认键盘这条通路。")
    return 0


def cmd_probe(args):
    from .transport import HIDTransport

    print("探测 ATK YOGO 75 PRO …")
    t = HIDTransport()
    try:
        ok = t.open()
    except Exception as e:  # noqa: BLE001
        print(f"✗ {e}")
        return 1
    if not ok:
        print("✗ 未连接")
        return 1
    print(f"✓ 已打开：{t.path}")
    batt = t.read_battery()
    if batt is not None:
        print(f"  电量：{batt}%")
    # 推一帧绿色勾作为连通性测试
    flat = render.frame_to_flat(patterns.done_frame())
    pushed = t.push_matrix(flat)
    print("  已推测试帧（绿色勾）" if pushed else "  帧与上帧相同，跳过")
    t.close()
    return 0


def cmd_run(args):
    import threading

    from .agent import StateMachine, run_server
    from .transport import DummyTransport, HIDTransport

    # 选择后端
    if args.dummy:
        transport = DummyTransport(sink=args.sink, out_dir=args.out)
        print("[yas] 使用模拟后端（无键盘）")
    else:
        transport = HIDTransport()
        if not transport.open():
            print("[yas] ⚠️ 未检测到键盘，回落到模拟后端")
            transport = DummyTransport(sink="terminal")

    machine = StateMachine(
        transport=transport,
        state_file=args.state_file,
        fps=args.fps,
        idle_timeout=args.idle_timeout,
    )

    # HTTP 服务器线程
    server_thread = threading.Thread(
        target=run_server, args=(machine, args.host, args.port), daemon=True)
    server_thread.start()

    # 主循环
    try:
        machine.run()
    except KeyboardInterrupt:
        print("\n[yas] 退出")
    finally:
        machine.stop()
        transport.close()
    return 0


def cmd_signal(args):
    """向运行中的 daemon 发一个状态（供 hooks 调用）。"""
    import json
    import urllib.request

    url = f"http://{args.host}:{args.port}/state"
    body = json.dumps({"state": args.state}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return 0 if resp.status == 200 else 1
    except Exception as e:  # noqa: BLE001
        # daemon 没起时不报错，静默失败（状态灯是增强，不该阻断 agent）
        print(f"[yas] 发状态失败（daemon 未运行？）：{e}", file=sys.stderr)
        return 1


def build_parser():
    p = argparse.ArgumentParser(
        prog="yas", description="ATK YOGO 75 PRO 点阵屏 Agent 状态灯")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="渲染五态图案到终端/PNG")
    c.add_argument("--out", default="assets", help="输出目录")
    c.add_argument("--gif", action="store_true", help="生成 GIF 动图")
    c.add_argument("--color", action="store_true", help="终端彩色输出")
    c.set_defaults(func=cmd_check)

    pr = sub.add_parser("probe", help="探测真实键盘并推测试帧")
    pr.set_defaults(func=cmd_probe)

    r = sub.add_parser("run", help="启动状态守护进程")
    r.add_argument("--dummy", action="store_true", help="强制使用模拟后端")
    r.add_argument("--sink", choices=["terminal", "ascii", "none"],
                   default="terminal", help="模拟后端输出方式")
    r.add_argument("--out", default="assets", help="模拟后端 PNG 输出目录")
    r.add_argument("--state-file", default="state.json",
                   help="状态文件路径（hooks 写入）")
    r.add_argument("--host", default="127.0.0.1")
    r.add_argument("--port", type=int, default=8787)
    r.add_argument("--fps", type=float, default=6.0)
    r.add_argument("--idle-timeout", type=float, default=30.0,
                   help="短暂状态超过此秒数回落 idle")
    r.set_defaults(func=cmd_run)

    s = sub.add_parser("signal", help="向 daemon 发送一个状态（hooks 用）")
    s.add_argument("state", choices=sorted(patterns.VALID_STATES),
                   help="目标状态")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8787)
    s.set_defaults(func=cmd_signal)

    return p


def main(argv=None):
    # 重定向到文件时也实时刷新，保证 --dummy 演示帧可见
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())