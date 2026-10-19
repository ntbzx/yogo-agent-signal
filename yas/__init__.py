"""yogo-agent-signal (yas) —— 把 ATK YOGO 75 PRO 点阵屏变成 Agent 状态灯。

用键盘右上角的 6x6 点阵屏显示 AI Agent（WorkBuddy / Claude Code 等）的运行状态：
执行中 / 等待人工确认 / 已完成 / 出错 / 空闲。

协议逆向自社区项目 YogoDot（https://github.com/Wednesque/yogodot，MIT 许可），
点阵屏通过 HID 厂商通道（VID 0x373B, usage page 0xFF60）实时推送，非固件写入。
"""

__version__ = "0.1.0"