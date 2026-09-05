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
| 首选摄像头 | Insta360 Ace Pro 2，VID `2E1A`，PID `1003` | TEST-001 |
| 当前 DirectShow 索引 | 1 | 仅为本次枚举结果；运行时仍按名称选择 |
| 采集模式 | DirectShow / MJPG / 1920×1080 / 请求 30 fps | TEST-001 |

- 另检测到 `USB2.0 HD UVC WebCam`（索引 0）和 `OBS Virtual Camera`（DirectShow 索引 2）。
- FFmpeg 未安装；M1 使用 OpenCV/DirectShow，不依赖 FFmpeg。
- Ubuntu 环境具体版本与本项目用途仍为 TODO。

## 待确认或待安装评估

| 项目 | 状态 | 说明 |
|---|---|---|
| PySide6 | 已安装 | M5 实测锁定 6.11.2；绑定 Qt 6.11.2 |
| PLC 型号与固件 | 型号已确认 / 固件待实测 | 2026-09-05 负责人确认 CPU 1214C DC/DC/DC；同学报 V4.1，在线证据待补 |
| PLC 编程软件及版本 | 计划环境 | 同学使用虚拟机 + TIA Portal V20；来宾 OS、Update、许可及运行验证待补 |
| PLC IP、端口、协议 | 部分资料已登记 | 本机 .1、虚拟机 .2 为口述；PLC IP 不能据此推定，详见 `PLC_HARDWARE.md` |
| 固定相机与白色工作区 | PARTIAL | M2 已在两种相机机位下完成实时识别；背景板是否严格为 A3 及其材质未单独测量 |

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
- 自动化测试通过 mock 验证复用 M1 摄像头打开函数；真实验收另行使用 Insta360 Ace Pro 2 USB Webcam，VID `2E1A`、PID `1003`、DirectShow、MJPG、1920×1080@30。
- 第一轮 session 处理 13087 帧，处理 FPS 27.547318；第二轮处理 8989 帧，处理 FPS 29.473403。两轮均 `failed_reads=0`、`error=null`。
- 第一轮使用 manual / selected ROI；第二轮改变相机机位后未复用旧 ROI，使用 auto / detected ROI，score 0.677265。实际数据见 TEST-003 和 `evidence/data/m2-live-acceptance-summary.json`。

## M3 软件准备环境

- 继续复用 M2 的 Python、OpenCV、NumPy、摄像头配置和 ROI 校准；未新增第三方依赖。
- 新增多目标合成测试和 Otsu / CLAHE+Otsu 同帧证据测试；真实摄像头的光照条件、FPS 和输出尚待 TEST-004 记录。

## M5 GUI 软件环境

记录日期：2026-09-04（Asia/Shanghai）

| 项目 | 实际值 | 说明 |
|---|---|---|
| Python | 3.12.10，`.venv/Scripts/python.exe` | GUI、pytest 和 soak 实际使用 |
| PySide6 | 6.11.2 | 通过 pip 可用版本检查后安装并锁定 |
| Qt runtime | 6.11.2 | `PySide6.QtCore.qVersion()` 实测 |
| Qt headless | `QT_QPA_PLATFORM=offscreen` | 只在测试进程/CLI 参数内设置，不修改系统环境变量 |
| OpenCV / NumPy | 5.0.0 / 2.5.2 | 继续复用 M2/M3 管线，未升级 |
| pytest | 9.1.1 | M5 UI/UX 重构及 overlay 对比度优化后全量 110 项通过 |

- `pip check` 最终回归结果：`No broken requirements found.`。
- 60 秒 synthetic soak 达到 processing 21.395960 FPS、GUI update 21.395960 FPS；这不是 Insta360 camera FPS。
- PySide6 是 M5 的正式 GUI 选型，不混用 PyQt、QML、Web 或 Electron。
