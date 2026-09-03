---
title: ISSUE-001 摄像头枚举CLI缺少duration属性
date: 2026-09-03
tags:
  - 慧眼识珠
  - issue
  - camera
status: closed
---

# ISSUE-001 摄像头枚举 CLI 缺少 duration 属性

- **Issue ID**：ISSUE-001
- **创建日期**：2026-09-03
- **状态**：CLOSED
- **所属模块**：`pc/camera/__main__.py`

## 问题现象

执行 `python -m pc.camera --config pc/config/camera.json enumerate` 时退出并报告 `AttributeError: 'Namespace' object has no attribute 'duration'`。

## 复现步骤

1. 安装 `requirements.txt`。
2. 执行摄像头 `enumerate` 子命令。

## 预期结果

输出配置后端可见的摄像头 JSON 列表。

## 实际结果

程序在读取仅属于 `stability` 子命令的 `duration` 参数时异常退出。

## 环境

- Windows 11 Build 26200
- Python 3.12.10
- OpenCV 5.0.0
- Git 基线：`7082418`

## 初步假设

- `argparse` 只会为选中的子命令创建其专属属性。

## 尝试方案

1. 用 `getattr(args, "duration", None)` 安全读取可选属性。
2. 增加回归测试，模拟不带 `duration` 的 `enumerate` 命令。

## 失败方案

- 首次实现无条件读取 `args.duration`，已确认失败。

## 根因

入口函数把 `stability` 子命令专属参数错误地当作所有子命令共有参数。

## 最终解决方案

仅在属性存在且非 `None` 时应用时长覆盖，并增加 `test_enumerate_command_does_not_require_duration`。

## 修改 commit

`d2b864d852e3910ba10a6572c0bd98bb8249a9f0`

## 验证结果

- 自动化测试：13 项全部通过。
- 枚举命令成功输出 3 个 DirectShow 视频设备。
- 后续 3 秒烟雾测试与 60 秒正式测试均成功。

## 是否可以写入实验报告的问题分析章节

- [x] 是
- [ ] 否
- 理由：可作为“命令行分支参数隔离与自动化回归测试”的轻量软件问题案例；若报告篇幅有限，优先保留对系统功能影响更大的问题。
