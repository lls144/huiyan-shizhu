---
title: "TEST-016 COMM-002 PC 半边：1 s 心跳与 2 s 断连看门狗"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-016 COMM-002 PC 半边

- **Test ID**：TEST-016
- **对应 Requirement ID**：COMM-002 的 **PC 侧**（每秒心跳、断连判定）
- **日期**：2026-09-11
- **Git commit**：`d7a1e93` + 本记录所在 commit

> [!warning] 证据边界
> 本轮完成并验证的是 **PC 半边**：PC 每秒发心跳、PC 在 2 s 无响应时判定通信中断并记录恢复。
> 需求原文的另一半——**“PLC 中断 2 秒则三盏灯全闪”**——需要 PLC 侧增加看门狗与闪烁逻辑
> （`FB_M8_AcceptanceHarness` 的 SCL 改动），**本轮未实现**，因此 **COMM-002 整体仍为 TODO**。

## 实现

- `pc/communication/heartbeat.py`：`HeartbeatMonitor`
  - 每 `heartbeat_interval_seconds`（默认 **1 s**）把自增计数写入 `M8_AcceptanceData` 的
    **DBB2**（`ReservedInputByte2`，原有保留字节，**不改块布局**）；
  - 心跳只有在“写→读回”确认 PLC 真的持有该字节后才计数；
  - 独立看门狗：连续 `comm_loss_timeout_seconds`（默认 **2 s**）没有成功读到状态即置 `comm_lost`，
    恢复时记录中断起止与时长；
  - 时钟可注入，因此 1 s / 2 s 行为可以用单元测试确定性地验证，不必真等。
- `pc/communication/sink.py`：`write_heartbeat()`、`safe_init()`；心跳值跨命令写保持一致。
- `pc/sorting/worker.py`：每帧做一次廉价的心跳到期检查（`tick_heartbeat`），
  另按 0.5 s 节奏做一次链路读取与看门狗判定（`tick`）。
- `pc/sorting/window.py`：PLC 面板新增 `Heartbeat` 与 `Link (COMM-002)` 两行，
  中断时整行变红显示“通信中断 N s”。

## 环境

- PLC：S7-1200 1214C DC/DC/DC，`192.0.2.1`，`DB_M8_Acceptance` = DB3，CPU RUN
- 对照：不可达地址 `192.0.2.199`（真实 S7 栈的失败路径，不接任何设备）
- PC：Windows 11，Python 3.12.10；摄像头未使用

## 实际结果

### 1. 单元测试

`pc/tests/test_communication_heartbeat.py`，9 项全部通过：

| 用例 | 验证内容 |
|---|---|
| `test_heartbeat_is_sent_once_per_second` | 1 s 一次，不多不少 |
| `test_no_heartbeat_is_sent_before_the_interval_elapses` | 未到期不发 |
| `test_tick_heartbeat_keeps_the_period_close_to_one_second` | 逐帧调用时周期落在 [1.0, 1.05) |
| `test_link_loss_is_declared_only_after_the_two_second_timeout` | 1.9 s 不报、2.1 s 报 |
| `test_a_link_that_never_answers_still_alarms_after_the_timeout` | 从未连上也报警 |
| `test_recovery_closes_the_outage_and_records_its_duration` | 恢复后记录中断时长 |
| `test_a_failed_heartbeat_is_counted_and_the_rhythm_is_not_advanced` | 失败计数、不推进节拍 |
| `test_the_monitor_disables_itself_for_a_sink_without_heartbeat_support` | 无心跳能力的 sink 自动禁用 |
| `test_the_heartbeat_reaches_a_real_bus_path_and_leaves_the_queue_alone` | 经完整写回读链路落到 DBB2，且不影响队列 |

全量回归：**242 passed / 1 skipped**。

### 2. 真机心跳节拍与落点

对真机连续运行 6 秒（逐帧检查 + 0.5 s 链路判定）：

```
heartbeat_count = 6
intervals       = [1.0, 1.015, 1.016, 1.016, 1.031]
mean interval   = 1.016 s
comm_lost       = False   heartbeat_failures = 0
PLC DBB2        = 6       control bytes: 0100060000000000
after reset: leds=[False, False, False] queue=0
```

即真机上心跳周期为 **1.00–1.03 s**，计数值确实写进了 `DBB2` 并被读回确认。

> 说明：初版把心跳挂在 0.5 s 的状态轮询上，实测周期 1.11 s；
> 改为逐帧到期检查后回到 1.02 s 量级。两次数据都记录在案。

### 3. 断连判定（真实 S7 失败路径）

指向不可达地址 `192.0.2.199`：

```
t+ 0.0s comm_lost=False heartbeats=0 failures=1
t+ 1.0s comm_lost=False heartbeats=0 failures=2
t+ 2.0s comm_lost=True  heartbeats=0 failures=3      ← 2 s 阈值处触发
t+ 4.0s comm_lost=True  heartbeats=0 failures=5
SUMMARY comm_lost=True lost_for=5.0s outages=1 heartbeat_failures=5
```

判定发生在 **2.0 s**，与规格一致；心跳失败被计数，中断被记录。

### 4. 真机拔网线实测：本轮未取得

按计划让操作者在对真机运行时拔掉网线，但 35 s 记录内 **心跳 35 次、失败 0、链路始终正常**，
说明该次网线未被拔下或未被检出，**本项判为未执行**，留待补做。

## 未执行 / 待补

1. **真机拔网线 / 断连恢复实测**（PC 半边）：待补
2. **PLC 侧看门狗与“2 s 全闪”**：未实现。需要改 `FB_M8_AcceptanceHarness`（读 DBB2，
   2 s 无变化则置报警；`FB_PlcApplication` 需把该报警接入 `FB_LedDisplay.CommLost`），
   并重新编译下载；属 PLC 侧改动，需负责人确认后执行
3. **通信恢复策略**：断连期间已入队的命令、恢复后的重发语义，仍属 `docs/PLC_INTERFACE.md` 未冻结项
4. COMM-002 整体状态：**TODO**（本记录只完成 PC 半边）

## 证据位置

- 实现：`pc/communication/heartbeat.py`、`pc/communication/sink.py`、`pc/sorting/worker.py`、`pc/sorting/window.py`
- 测试：`pc/tests/test_communication_heartbeat.py`
- 过程输出：本记录正文（真机心跳、不可达地址断连）
- 配置：`pc/config/plc.json` 的 `heartbeat_enabled` / `heartbeat_interval_seconds` / `comm_loss_timeout_seconds`
