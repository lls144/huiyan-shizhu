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
| PySide6 | TODO | M5 前评估并锁定版本 |
| PLC 型号与固件 | TODO | 需在实验室读取铭牌/工程信息 |
| PLC 编程软件及版本 | TODO | 不依据经验猜测 |
| PLC IP、端口、协议 | TODO | 需结合实验室网络与 PLC 能力确认 |
| 三脚架垂直俯拍与 A3 背景 | TODO | 本次只验证 USB 采集稳定性；M2 前布置并记录 |

M1 的最小依赖已锁定在 `requirements.txt`。虚拟环境 `.venv/` 不进入 Git。
