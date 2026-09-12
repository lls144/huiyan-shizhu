---
title: "TEST-012 PC 侧可靠性层：队列满通知、重复保护与写入确认"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-012 PC 侧可靠性层（Fake PLC）

- **Test ID**：TEST-012
- **对应 Requirement ID**：COMM-003 的 **PC 侧**（超时重发确认、队列满通知与延后）；COMM-001 写入确认
- **日期**：2026-09-11
- **Git commit**：本记录随实现一起提交（见本文件所在 commit）

> [!warning] 证据边界
> 本轮全部证据来自 **内存 Fake PLC（`FakeAcceptancePlc`）+ 合成事件 + 离屏 Qt**，
> **没有连接真实 PLC，没有使用摄像头**。
> 它证明 PC 侧的逻辑正确，**不**证明真机上队列满/重发行为，也**不**代表 COMM-003 或 M9 完成。
> **心跳（1 s）与断连报警（2 s 全闪）本轮未实现**。

## 测试目标

操作者要求“在 python 页面实现超时重发机制和队列满通知”。本轮补上 PC 侧能独立完成的部分，
并如实划出必须由共享协议（PLC 侧）才能完成的部分。

## 环境

- Windows 11；Python 3.12.10；PySide6 6.11.2；pytest 9.1.1
- PLC 模型：`pc/communication/fake_plc.py` 的 `FakeAcceptancePlc`（`DB_M8_Acceptance` 布局，FIFO 容量 3）
- 真实 PLC 与摄像头：**未使用**

## 输入条件

- `pc/communication/reliability.py`：`GuardedPlcSink`（写入前读状态、写入后核对队列长度、语义号去重、超时计数）
- `pc/config/plc.json`：`queue_full_policy=defer`、`duplicate_policy=refuse`、`command_timeout_seconds=3.0`
- `pc/config/sorting.json`：`max_pending_items=6`（可视化缓冲区容量）

## 操作步骤

1. `.\.venv\Scripts\python.exe -m pytest -q`
2. `.\.venv\Scripts\python.exe -m pc.communication --dry-run acceptance`（确认原有 5 个桥场景未被破坏）
3. 模式 A（不按键）离屏运行：`python -m pc.sorting --source synthetic --offscreen --plc-fake --soak-seconds 18`
4. 模式 B（自动出队）离屏运行：同上加 `--auto-dequeue`
5. 审计 session JSON 的 `plc_status_counts` / `plc_state_last` 与截图

## 预期结果

- 全量 pytest 通过，且原有 5 个 PC↔PLC 离线场景仍全过。
- 队列满时**不写入**，报 `QUEUE_FULL` 并把命令暂存；出队腾出空间后自动补发。
- 同一语义号不会写第二次（重发不可能重复入队）。
- 控制字被静默丢弃时会重发，直到读回一致。
- 每笔命令都能给出“队列真的涨了”或“刚出队的语义号就是它”的确认依据。
- 写入既没报错也没让队列增长时，必须报 `UNCONFIRMED`，不能算成功。

## 实际结果

**全量回归**

```
231 passed, 1 skipped
```

其中本轮新增 `pc/tests/test_communication_reliability.py` 共 13 项；原有离线验收仍为
`scenario_count=5 / all_scenarios_pass=true`。

**模式 A：队列涨满 → 通知 + 暂存**（`--plc-fake`，不按键）

| 字段 | 值 |
|---|---|
| sorting_result_count | 5 |
| plc_status_counts | `{"QUEUE_FULL": 12, "SENT": 3}` |
| plc_state_last.queue_length | 3（满） |
| plc_state_last.queue_full | true |
| plc_state_last.deferred_count | 2（两条命令暂存待补发） |
| counters.queue_full_deferrals | 2（首次暂存计数，不含重试） |
| counters.deferred_retries | 10（节流后的补发尝试） |
| counters.errors / unconfirmed / timeouts | 0 / 0 / 0 |

**模式 B：自动出队 → 5/5 确认**（`--auto-dequeue`）

| 字段 | 值 |
|---|---|
| plc_status_counts | `{"SENT": 5}` |
| plc_state_last.last_dequeued_shape | 2（最后出队的是矩形） |
| plc_state_last.leds | `[true, true, false]` = 2 盏 |
| counters.sent_confirmed | 5，`unconfirmed=0` |

模式 B 里队列在 `send_event` 内部就被排空，长度回到 0；确认改用“刚出队的语义号”，
否则会被误判成 `UNCONFIRMED`。该分支已有专门用例
`test_auto_dequeue_is_still_reported_as_confirmed`。

**截图审计**

- `evidence/screenshots/sorting/2026-09-11-sorting-buffer-and-queue-full.png`：
  左侧“缓冲区 1/6”停着一个待入队物料块；PLC 面板 `Queue length 3`、`Queue full FULL（队列满）`（红字）、
  `Deferred (queue full) 2 条待入队`；右侧分拣日志 #1–#6。
- `evidence/screenshots/sorting/2026-09-11-sorting-plc-leds.png`：
  PLC 面板 `Queue length 0`、`Queue full ok`、`Real LEDs ●●○`，与“矩形 = 2 盏”一致。

## 结论

- 队列满在 PC 页面有明确提示（红字 `FULL（队列满）`）并默认**延后**而不是丢件。
- 写入确认与重发可量化（`write_resends`），静默丢写在 Fake PLC 上用 `drop_control_writes=4` 复现并确认已重发。
- 重复保护使“重发导致重复入队”在 PC 侧不可能发生。
- 写入未确认时报 `UNCONFIRMED` 而不是假成功。

## 未执行 / 待补

1. **真机队列满 / 真机重发**：待 LAB PLC 恢复 PUT/GET 后实测；当前真机只读都报 `class=0x81 code=0x04`。
2. **COMM-002 心跳 1 s 与断连 2 s 全闪**：未实现，仍 TODO。
3. **PLC 侧序列号/ACK 去重**：未实现，属 `docs/PLC_INTERFACE.md` 未冻结项；本轮不声称完成。
4. 本轮所有数据均为 Fake PLC，不得填入 PLC-001–004 / COMM-001–003 的真实证据行。

## 证据位置

- 实现：`pc/communication/reliability.py`、`pc/communication/models.py`、`pc/communication/config.py`、`pc/config/plc.json`
- 界面：`pc/sorting/window.py`、`pc/sorting/widget.py`、`pc/sorting/worker.py`、`pc/sorting/app.py`
- 测试：`pc/tests/test_communication_reliability.py`
- 数据：`evidence/data/sorting/2026-09-11-sorting-fake-plc-queue-full.json`、`...-fake-plc-leds.json`
- 截图：`evidence/screenshots/sorting/2026-09-11-sorting-buffer-and-queue-full.png`、`...-plc-leds.png`
