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

## 已知但尚未验证

- 主开发机为 Windows 11；另有 Ubuntu 环境，具体版本与本项目用途为 TODO。
- 计划优先使用 Insta360 Ace Pro 2 的 USB Webcam 模式；本机枚举、画面稳定性、分辨率与帧率均待 M1 实测。

## 待确认或待安装评估

| 项目 | 状态 | 说明 |
|---|---|---|
| OpenCV (`opencv-python`) | TODO | 未在 Phase 0 安装或验证；M1 决定版本 |
| PySide6 | TODO | M5 前评估并锁定版本 |
| 测试框架（如 pytest） | TODO | 随第一个可测试模块确定 |
| PLC 型号与固件 | TODO | 需在实验室读取铭牌/工程信息 |
| PLC 编程软件及版本 | TODO | 不依据经验猜测 |
| PLC IP、端口、协议 | TODO | 需结合实验室网络与 PLC 能力确认 |
| USB 摄像头设备 ID | TODO | M1 枚举后写入配置，不硬编码 |

Phase 0 不创建复杂 `requirements.txt`。依赖文件应在 M1 根据可运行的摄像头/OpenCV 环境生成，并记录精确版本。
