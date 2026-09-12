# 开发环境记录

记录日期：2026-09-03（Asia/Shanghai）

## 已自动探测

| 项目 | 当前值 | 探测方式 |
|---|---|---|
| 操作系统 | Microsoft Windows 11 家庭版 中文版，64 位 | `Get-CimInstance Win32_OperatingSystem` |
| OS 版本 | 10.0.26200（Build 26200） | 同上 |
| PowerShell | 7.6.4 Core | `$PSVersionTable` |
| Python | 3.12.10 | `python --version` |
| Python 可执行文件 | `D:\IDE\python\python.exe` | `Get-Command python` |
| Python Launcher | 3.12.10，`C:\Windows\py.exe` | `py --version` |
| Git | 2.55.0.windows.5 | `git --version` |
| Git 可执行文件 | `C:\Program Files\Git\cmd\git.exe` | `Get-Command git` |
| Codex 运行目录 | `C:\Users\developer\Desktop\huiyan-shizhu` | `Get-Location` |

## M1 已验证运行环境

| 项目 | 已验证值 | 证据 |
|---|---|---|
| Python | 3.12.10 | TEST-001 |
| OpenCV | 包 `opencv-python` 5.0.0.93；运行时 `cv2.__version__` 为 5.0.0 | `requirements.txt`、TEST-001 |
| NumPy | 2.5.2 | `requirements.txt` |
| pytest | 9.1.1 | 13 项自动化测试通过 |
| 摄像头枚举 | `cv2-enumerate-cameras` 1.3.3 | `requirements.txt` |
| 摄像头（当前） | 笔记本内置 `HD Webcam`，VID `2B7E`，PID `B663`；2026-09-10 起使用。**方法学限制：固定在屏幕上方，无法三脚架垂直俯拍，采集须手持 A3 白纸对准镜头** | TEST-010、TEST-017、TEST-018 |
| 摄像头（历史） | Insta360 Ace Pro 2，VID `2E1A`，PID `1003`；已不再接入本机 | TEST-001 |
| 当前枚举索引 | 0（MSMF） | 仅为本次枚举结果；运行时仍按名称选择 |
| 采集模式（当前） | MSMF / 1280×720 / 请求 30 fps；实测 29.99 fps、1800/1800 帧、最大帧间隔 0.084 s | TEST-010 |
| 采集模式（历史） | DirectShow / MJPG / 1920×1080 / 请求 30 fps | TEST-001 |

- 2026-09-10 枚举结果只剩内置 `HD Webcam`；Insta360 与旧的 `OBS Virtual Camera` 均不在列表中。
- 内置摄像头对 1920×1080 的请求会被降到 1280×720，且不接受 MJPG（实际为 YUY2）；
  同一机位下 DSHOW 只能跑到约 10 fps，MSMF 才能跑满 30 fps，因此后端选 MSMF。
- FFmpeg 未安装；M1 使用 OpenCV/DirectShow（2026-09-10 起内置摄像头用 MSMF），不依赖 FFmpeg。
- Ubuntu 环境具体版本与本项目用途仍为 TODO。

## 待确认或待安装评估

| 项目 | 状态 | 说明 |
|---|---|---|
| PySide6 | 已安装 | M5 实测锁定 6.11.2；绑定 Qt 6.11.2 |
| PLC 型号与固件 | 型号与在线固件已确认 | 2026-09-05 负责人确认 CPU 1214C DC/DC/DC；**在线固件 `V4.5.1`**（TIA 下载预览 + 原生 python-snap7 双来源一致，ISSUE-002 已结案）；Online & diagnostics 截图待归档 |
| PLC 编程软件及版本 | 计划环境 | 同学使用虚拟机 + TIA Portal V20；来宾 OS、Update、许可及运行验证待补 |
| PLC IP、端口、协议 | 部分资料已登记 | 本机 .1、虚拟机 .2 为口述；PLC IP 不能据此推定，详见 `PLC_HARDWARE.md` |
| 固定相机与白色工作区 | PARTIAL | 两台相机各完成一轮实时识别（Insta360 为历史，现用内置 HD Webcam）；背景板是否严格为 A3 及其材质未单独测量，受控照明未能复现 |

M1 的最小依赖已锁定在 `requirements.txt`。虚拟环境 `.venv/` 不进入 Git。

## M2 第一阶段已执行环境

记录日期：2026-09-04（Asia/Shanghai）

| 项目 | 实际值 | 说明 |
|---|---|---|
| Python | 3.12.10，`.venv/Scripts/python.exe` | M2 pytest 和离线批处理实际使用 |
| OpenCV | 5.0.0 | 灰度、Otsu、形态学、Canny、轮廓和 `approxPolyDP` |
| NumPy | 2.5.2 | 图像数组及合成轮廓测试 |
| pytest | 9.1.1 | 完整测试执行环境 |
| 原始图片 | 10 张 JPEG，均为 1920×1080 | 位于被 Git 忽略的 `test_data/raw/m2/` |

- 系统级 `python` 当前指向 `D:\IDE\python\python.exe`，未安装 pytest；直接运行 `python -m pytest -q` 得到 `No module named pytest`，所以不作为测试结果。
- 仓库 `.venv` 的锁定依赖完整；加入 M2 实时集成 mock/合成测试后，当前完整测试为 57 项通过。
- M2 第一阶段不打开摄像头；拍摄装置条件来自项目负责人说明和图片内容，实时运行条件仍待后续阶段验证。

## M2 第二阶段真实验证环境

- 仍使用 Python 3.12.10、OpenCV 5.0.0、NumPy 2.5.2 和 pytest 9.1.1，未新增第三方依赖。
- 自动化测试通过 mock 验证复用 M1 摄像头打开函数；M2 的真实验收**历史轮次**使用 Insta360 Ace Pro 2 USB Webcam（VID `2E1A`、PID `1003`、DirectShow、MJPG、1920×1080@30）；**现用相机为内置 `HD Webcam`**，M2 已用 MSMF / 1280×720 / YUY2 重跑（TEST-017）。
- 第一轮 session 处理 13087 帧，处理 FPS 27.547318；第二轮处理 8989 帧，处理 FPS 29.473403。两轮均 `failed_reads=0`、`error=null`。
- 第一轮使用 manual / selected ROI；第二轮改变相机机位后未复用旧 ROI，使用 auto / detected ROI，score 0.677265。实际数据见 TEST-003 和 `evidence/data/m2-live-acceptance-summary.json`。

## M3 软件准备环境

- 继续复用 M2 的 Python、OpenCV、NumPy、摄像头配置和 ROI 校准；未新增第三方依赖。
- 新增多目标合成测试和 Otsu / CLAHE+Otsu 同帧证据测试；2026-09-07 已用真实 Insta360 Ace Pro 2 完成 normal、bright/side、dark、partial occlusion、touching/merged 五项验收（历史，详见 TEST-004）。**2026-09-11 在内置 HD Webcam 上完成 normal 与 bright/side 两组复测，详见 TEST-018。**

## M5 GUI 软件环境

记录日期：2026-09-04（Asia/Shanghai）

| 项目 | 实际值 | 说明 |
|---|---|---|
| Python | 3.12.10，`.venv/Scripts/python.exe` | GUI、pytest 和 soak 实际使用 |
| PySide6 | 6.11.2 | 通过 pip 可用版本检查后安装并锁定 |
| Qt runtime | 6.11.2 | `PySide6.QtCore.qVersion()` 实测 |
| Qt headless | `QT_QPA_PLATFORM=offscreen` | 只在测试进程/CLI 参数内设置，不修改系统环境变量 |
| OpenCV / NumPy | 5.0.0 / 2.5.2 | 继续复用 M2/M3 管线，未升级 |
| pytest | 9.1.1 | M5 UI/UX 阶段曾为 110 项；2026-09-07 加入 M6 后仓库全量回归 172 项通过 |

- `pip check` 最终回归结果：`No broken requirements found.`。
- 60 秒 synthetic soak 达到 processing 21.395960 FPS、GUI update 21.395960 FPS；这不是 Insta360 camera FPS。
- PySide6 是 M5 的正式 GUI 选型，不混用 PyQt、QML、Web 或 Electron。

## M3/M4/M5 真实联合验收环境

记录日期：2026-09-07（Asia/Shanghai）。

| 项目 | 实际值 | 证据 |
|---|---|---|
| 运行代码 | `78597f58e63f8f262fd0df25757218994345dc39` | M3 evidence 与 M5 session |
| 摄像头 | Insta360 Ace Pro 2，VID 2E1A、PID 1003 | session `source_metadata.device` |
| 采集 | DirectShow / MJPG / 1920×1080 / 请求 30 FPS | session camera config |
| actual properties | 1920×1080、reported 30.000030 FPS | session source metadata |
| Python / PySide6 | 3.12.10 / 6.11.2 | session environment |
| OpenCV / NumPy | 5.0.0 / 2.5.2 | 每组 M3 evidence environment |
| ROI | auto 请求失败后 manual/selected `[548,126,1346,698]` | session calibration 与五组 evidence |
| session | 1577.142974 s、46235 read/processed/GUI updates | M5 session summary |
| throughput | processing/GUI update 均 29.315668 FPS | M5 session summary |
| health | 0 failed read、0 display drop、0 buffer overwrite、`error=null`、clean shutdown | M5 session summary |

原始 session 报告 `git.dirty=true`；审计开始时没有 tracked diff，只有操作者保存的 M4/M5 live 截图为未跟踪文件。M3 五组 evidence 在保存时均记录 `dirty=false`。Qt 控制台的 `QFont::setPointSize Point size <=0 (-1)` 仅为现场观察且未写入 session；GUI 正常、Last error 为 No errors、session `error=null`，因此记为非阻断 UI warning。

## 2026-09-10 离线全量回归环境（通信桥改动后）

记录日期：2026-09-10（Asia/Shanghai）。本次在**当前开发机**重建 `.venv` 并跑全量回归，用于确认 `pc/communication/` 改动未破坏 M1–M6。

| 项目 | 实际值 | 说明 |
|---|---|---|
| 电脑 / OS | Windows 11 10.0.26200 | 当前开发机；与 2026-09-03 记录的 `C:\Users\developer` 机器不是同一台 |
| Python | 3.12.10，`.venv/Scripts/python.exe` | 系统 Python 为 `C:\Users\developer\AppData\Local\Programs\Python\Python312\python.exe`，未安装 pytest |
| OpenCV / NumPy | 5.0.0 / 2.5.2 | 按 `requirements.txt` 锁定 |
| pytest | 9.1.1 | 全量执行环境 |
| PySide6 | 6.11.2 | GUI 测试依赖；`QT_QPA_PLATFORM=offscreen` |
| python-snap7 | 3.1.2 | 来自 `plc/tools/requirements.txt`；`plc/tests` 导入验收工具需要它 |
| `pip check` | `No broken requirements found.` | 两套锁定依赖同时安装后仍一致 |
| 全量回归 | **190 passed, 1 skipped in 3.15s** | `pc/tests` 180 passed + 1 skipped；`plc/tests` 10 passed |
| 跳过原因 | `test_offline_m2_dataset.py:18` | 被 Git 忽略的真实 M2 原始图片集不在本机，属预期跳过 |
| 离线通信桥验收 | 5/5 `OFFLINE PASS` | `python -m pc.communication acceptance` |

- 本次修复了两处测试基础设施缺陷：`plc/tests/test_m8_real_plc_acceptance.py` 的 `sys.modules` 登记，以及 `plc/tools/m8_real_plc_acceptance.py --dry-run` 不再强制 `--db-number`。详见 `notes/tests/TEST-008-PC-PLC通信桥离线验收.md`。
- 本机**没有**真实摄像头与真实 PLC；本次不含真实硬件结论。
