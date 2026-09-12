---
title: "TEST-008 PC-PLC 通信桥离线验收与全量回归"
date: "2026-09-10"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-008 PC-PLC 通信桥离线验收与全量回归

- **Test ID**：TEST-008
- **对应 Requirement ID**：COMM-001 / PLC-001~004 的**软件前置**（不关闭任何要求）；M8 通信桥离线范围
- **日期**：2026-09-10
- **Git commit**：`59bc247`（运行基线）；本轮修复见“本次修复”一节

> [!warning] 证据边界
> 本测试只证明 **PC 侧软件** 与 **内存 Fake PLC** 的行为一致性。没有真实 S7-1200 连接、没有真实按键、没有实体 LED。**不得**用它关闭 `COMM-001/002/003`、`PLC-001~004`、`M8`、`M9` 或 `M10`。

## 测试目标

1. 确认 `pc/communication/` 命令桥在合成事件驱动下产生正确的命令边沿与队列/LED 语义。
2. 恢复仓库锁定依赖后重跑全量 pytest，确认通信桥改动没有破坏 M1–M6。
3. 修复回归过程中发现的测试基础设施缺陷。

## 环境

- 电脑：Windows 11（当前开发机）
- OS：Windows 11 10.0.26200
- Python：3.12.10（新建仓库 `.venv`）
- OpenCV 5.0.0 / NumPy 2.5.2 / pytest 9.1.1 / PySide6 6.11.2
- python-snap7 3.1.2（`plc/tools/requirements.txt`，供 PLC 验收工具与测试导入）
- 摄像头：**未使用**
- PLC：**未连接**；使用内存 `FakeAcceptancePlc`

## 输入条件

- 合成事件：`VisionEvent(OBJECT_ENTER, triangle/rectangle/circle/unknown)`
- `PlcCommunicationConfig(enabled=True, db_number=12, auto_dequeue=False, *_pulse_seconds=0)`
- Fake PLC 容量 3，实现 `DB_M8_Acceptance` 固定字节布局

## 操作步骤

1. `python -m venv .venv`
2. `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. `.\.venv\Scripts\python.exe -m pip install -r plc\tools\requirements.txt`
4. `.\.venv\Scripts\python.exe -m pip check`
5. `$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python.exe -m pytest -q`
6. `.\.venv\Scripts\python.exe -m pc.communication acceptance --output-dir output/m8-bridge`
7. `.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --dry-run`

## 预期结果

- 全量测试通过，无 collection error。
- 离线验收 5/5 场景通过并生成 JSON/CSV。
- `--dry-run` 在不连接 PLC、不提供 DB 号时即可列出用例并返回 0。

## 实际结果

| 项目 | 实际 |
|---|---|
| `pip check` | `No broken requirements found.` |
| 全量 pytest | **190 passed, 1 skipped in 3.15s** |
| 其中 `pc/tests` | 180 passed, 1 skipped |
| 其中 `plc/tests` | 10 passed |
| 跳过项 | `pc\tests\test_offline_m2_dataset.py:18` — 被忽略的真实 M2 原始图片集不在本机 |
| 离线验收 | 5/5 `OFFLINE PASS`（single_shape_led_mapping、three_shape_fifo_order、held_command_valid_single_shot、unknown_event_skipped、reset_clears_state） |
| `--dry-run` | 列出 M8-T01…M8-T11、M8-T15，退出码 0 |

## 本次修复（回归发现）

1. `plc/tests/test_m8_real_plc_acceptance.py` **无法被 pytest 收集**：测试用 `importlib` 加载 `plc/tools/m8_real_plc_acceptance.py` 时未登记 `sys.modules`，而该工具使用 `from __future__ import annotations` 并定义 dataclass，Python 3.12 下抛 `AttributeError: 'NoneType' object has no attribute '__dict__'`。
   - 说明：`plc/records/2026-09-08` 记录当时是“直接调用 6 个 `test_*` 函数”，未经 pytest 收集，因此该缺陷此前未被发现。
   - 修复：执行模块前登记 `sys.modules[SPEC.name] = MODULE`。
2. `plc/tools/m8_real_plc_acceptance.py` 的 `--db-number` 原先为必填，导致 `--dry-run` 无硬件烟测也不可用。
   - 修复：改为可选；仅在非 `--dry-run` 且未提供时以退出码 2 报错。

## 原始数据位置

- `output/m8-bridge/m8-bridge-offline.json`、`.csv`（**被 Git 忽略**；可用步骤 6 重放）

## 截图位置

- 无（纯离线软件测试，不生成截图）

## Pass / Fail

**PASS**（仅限“PC 侧通信桥离线软件”范围）

## 备注

- 本次未修改 `pc/vision/`、`pc/camera/`；未连接真实 PLC；未执行 TIA 编译或下载。
- 发现并登记 [ISSUE-002](../issues/ISSUE-002-固件版本登记不一致.md)（固件版本 `V4.1` vs `V4.5.1` 登记冲突），未擅自覆盖 `docs/PLC_HARDWARE.md`。
- 现场执行清单见 [PLC_FIELD_CHECKLIST.md](../../docs/PLC_FIELD_CHECKLIST.md)。
- 最终交付物骨架见 [docs/deliverables/](../../docs/deliverables/README.md)。
