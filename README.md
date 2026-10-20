# yogo-agent-signal

把 **ATK YOGO 75 PRO** 键盘右上角的 6×6 点阵屏，变成你 AI Agent 的**状态灯**。

Agent 在执行任务时屏幕转圈、需要你确认时闪琥珀色、干完活亮一个绿勾——不用切窗口看终端，瞄一眼键盘就知道现在能不能走开。

![五态图案](assets/running.gif)

## 状态对照

| 状态 | 图案 | 含义 |
|---|---|---|
| `running` | 绿色循环点 | Agent 正在干活 |
| `waiting` | 琥珀色感叹号/圆点闪烁 | **等你人工确认**（权限弹窗等）|
| `done` | 绿色勾 | 任务完成 |
| `error` | 红色叉 | 出错 |
| `idle` | 蓝色呼吸点 | 空闲 |

## 工作原理

```
Agent (Claude Code / WorkBuddy)
   │  hook 事件触发
   ▼
signal.sh / yas signal ──POST──► 127.0.0.1:8787/state
                                    │
                              StateMachine (6 FPS)
                                    │
                              transport.push_matrix()
                                    │
                         108 字节 → 5 个 HID 包 (cmd 59)
                                    ▼
                         键盘 6×6 点阵屏
```

点阵屏是**实时推送**的，不写键盘固件、不改按键、不联网。协议走 HID 厂商通道（VID `0x373B`，usage page `0xFF60`），逆向自社区项目 [YogoDot](https://github.com/Wednesque/yogodot)（MIT）。

## 安装

```bash
git clone https://github.com/<你的账号>/yogo-agent-signal.git
cd yogo-agent-signal
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

macOS 装 hidapi 时如需编译，可先 `brew install hidapi`。

## 快速开始

**1. 先看效果（不需要键盘）**

```bash
python -m yas check --color --gif   # 把五态图案打到终端 + 生成 GIF
```

**2. 启守护进程**

```bash
python -m yas run --dummy --sink terminal   # 模拟模式，终端看色块
python -m yas run                          # 真键盘模式
```

同一时间只能跑一个 `yas run`。退出请按 **Ctrl+C**；别用 Ctrl+Z，被挂起的进程会继续占着键盘和 8787 端口，屏幕停在最后一帧、信号也没反应。不小心挂起了可以用 `pkill -f 'yas run'; pkill -CONT -f 'yas run'` 清掉。

**3. 手动切状态**

```bash
./hooks/signal.sh running
python -m yas signal waiting
curl -X POST http://127.0.0.1:8787/state -d '{"state":"done"}'
```

## 接入 Claude Code

把 `hooks/claude-code/settings.example.json` 里的 `hooks` 段合并进 `~/.claude/settings.json`（把里面的绝对路径改成你的实际路径）。

对应事件：

| Claude Code 事件 | 点亮阵状态 |
|---|---|
| `PreToolUse` | `running` |
| `PermissionRequest` | `waiting` |
| `Stop` | `done` |
| `SessionEnd` | `idle` |

**核心价值**：`PermissionRequest` 正好就是「等你确认」的时刻——人在真正被卡住之前就会看到键盘闪琥珀色。

## 接入 WorkBuddy

`hooks/workbuddy/` 下四个脚本对应同样四个状态。在你的 hook 配置里指向它们即可；没有 hook 也能手动跑：

```bash
./hooks/workbuddy/on-waiting.sh
```

## 已知限制

- **会把点阵屏切到「自定义」模式**。点阵屏处在内置效果模式时不显示推送的画面，所以 `probe` / `run` 连上键盘后会把配置里的点阵模式（第 30 字节）改成 6，其它设置不动。想换回内置效果，用官方 ATK HUB 切回即可。
- **蓝牙模式下无法控制**。点阵屏控制只走 2.4G 接收器或 USB 有线——蓝牙模式下键盘不暴露厂商通道，这是固件限制，所有方案（含官方驱动）都绕不开。多设备场景建议：2.4G 常驻你的 Mac 跑状态灯，蓝牙留给手机/iPad。
- 仅验证过 YOGO 75 PRO（同厂带点阵屏的型号应该也能用）。
- 目前做了点阵屏；**键盘背光还没接**（协议已就位：cmd 46/47，见 `protocol.py`）。

## 二次开发

`yas/` 下四个模块各司其职：

- `protocol.py` — 报文编解码、命令号
- `patterns.py` — 五态 6×6 图案（配色按键盘 LED 红:绿:蓝≈1:4:14 的发光效率校过）
- `transport.py` — HID 真实后端 / 模拟后端
- `agent.py` — 状态机 + HTTP 接口

想加自己的状态？在 `patterns.py` 里加一个图案函数，往 `STATE_EFFECTS` 注册即可。

## 致谢

协议与 LED 校色经验来自 [YogoDot](https://github.com/Wednesque/yogodot)。本项目与 ATK、Anthropic 均无隶属关系，风险自负。

## License

MIT
