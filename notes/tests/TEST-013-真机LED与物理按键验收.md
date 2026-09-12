---
title: "TEST-013 真机 LED 映射与物理按键出队验收"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-013 真机 LED 映射与物理按键出队

- **Test ID**：TEST-013
- **对应 Requirement ID**：PLC-002（生产者-消费者/按键逐条出队）、PLC-003（1/2/3 盏 LED）、PLC-004（复位）、COMM-001（PC→PLC 指令落点）
- **日期**：2026-09-11
- **Git commit**：`a0cd50e`（PC 侧代码基线；PLC 侧为操作者当日修复后的 TIA 工程）

> [!warning] 证据边界
> 本轮是**真机**证据，但只覆盖“PC 入队 → PLC FIFO → 按键/P C 出队 → 灯位”这一段。
> **不含**心跳/断连报警（COMM-002 未实现）、不含 M9/M10 整体验收；视觉接入见同日 `TEST-014`。
> LED 目视照片已归档；操作视频仍为 TODO。

## 前置：TIA 工程修复

操作者修复了 `notes/issues/ISSUE-004` 记录的三个同步问题（`PLC_Types.scl`、
`FB_PlcApplication.scl` 外部源副本落后，以及 OB1 调用点接口过期），
`Compile → Software (rebuild all)` 达到 0 error 后下载，CPU 转 RUN。

## 环境

- PLC：S7-1200 CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`，`192.0.2.1`，CPU RUN
- `DB_M8_Acceptance` = **DB3**（非优化访问），与 `pc/config/plc.json` 的 `db_number` 一致
- PC：Windows 11，Python 3.12.10，`pc/communication/reliability.py` 的 `GuardedPlcSink`
- I/O：`%I0.0` DequeueButton、`%I0.1` ResetButton、`%Q0.1..Q0.3` SortLed1..3
- 摄像头：**未使用**

## 操作步骤

1. 只读自检：`m8_real_plc_acceptance.py --check-access --db-number 3`
2. PC 侧依次入队并出队 triangle/rectangle/circle（软件出队请求），观察灯位
3. 复位后一次性入队三条（队列满），由**操作者按物理按键 `%I0.0` 三次**逐条出队
4. 每按一次读取 `queue_length`、`leds`、`last_dequeued_shape`、`last_dequeued_semantic_id`

## 预期结果

- 只读自检 `pass=true`，`magic=0x4D38`、`version=1`、`AcceptanceReady=TRUE`、`CycleCounter` 递增
- 入队不改变灯位；出队后 triangle→1 盏、rectangle→2 盏、circle→3 盏
- 一次按键只出队一条，顺序与入队一致

## 实际结果

### 1. 只读自检

```
pass: true
magic=0x4D38  version=1  AcceptanceReady=TRUE
CycleCounter 59492 → 59663（递增 → harness 在 RUN 中执行）
queue_length=0  queue_empty=true  leds=[0,0,0]
```

### 2. PC 入队 + PC 出队请求（软件出队）

| 步骤 | 形状 | 入队结果 | 入队后队列 | 入队后灯 | 出队后灯 | 出队形状 / 语义号 |
|---|---|---|---|---|---|---|
| 1 | triangle | SENT，`confirmed by queue 0 -> 1`，重发 0 次，0.196 s | 1 | [0,0,0] | **[1,0,0] = 1 盏** | 1 / 101 |
| 2 | rectangle | SENT，重发 1 次，0.207 s | 1 | [1,0,0] | **[1,1,0] = 2 盏** | 2 / 102 |
| 3 | circle | SENT，重发 0 次，0.170 s | 1 | [1,1,0] | **[1,1,1] = 3 盏** | 3 / 103 |
| 收尾 | 复位 | SENT | 0 | [0,0,0] | [0,0,0] | — |

### 3. 物理按键 `%I0.0` 出队（操作者操作）

```
入队 3 条      → queue=3  full=True   leds=[0,0,0]        ← 入队不亮灯
10:59:44 按键1 → queue=2  leds=[1,0,0]  shape=1 sid=401   ← 三角形 1 盏
10:59:52 按键2 → queue=1  leds=[1,1,0]  shape=2 sid=402   ← 矩形   2 盏
10:59:55 按键3 → queue=0  leds=[1,1,1]  shape=3 sid=403   ← 圆形   3 盏
final          → queue=0  leds=[1,1,1]
```

操作者目视确认：**三次灯位（1 盏 / 2 盏 / 3 盏）均正确**。

照片证据（操作者拍摄，按顺序对应三个阶段）：

- `evidence/screenshots/m8-real/2026-09-11-led-1-lamp.jpg`：仅 `M1` 红色 LED 点亮（1 盏）
- `evidence/screenshots/m8-real/2026-09-11-led-2-lamps.jpg`：`M1`、`M2` 点亮（2 盏）
- `evidence/screenshots/m8-real/2026-09-11-led-3-lamps.jpg`：`M1`、`M2` 与 `M3`（琥珀色）点亮（3 盏）

三张照片中左下角标号 `L1` 的指示灯始终点亮，属实验箱模块自身的指示，不是本项目的分拣灯。

### 4. 控制字丢写复现

PC 侧计数器终值：`dispatches=3、sent_confirmed=3、write_resends=4、
unconfirmed=0、timeouts=0、errors=0`（另有第二轮 3 次派发 `write_resends=10`）。
说明 2026-09-10 记录的“PUT/GET 写 `DB_M8_Acceptance` 控制字被静默丢弃约一半”在重建工程后
仍然存在，且“写→读回→重发”机制正常兜住。

## 结论

- 真机链路、`DB_M8_Acceptance`(DB3) 布局、harness 运行、FIFO 顺序、按键逐条出队、
  三种形状→1/2/3 盏灯、复位清空，**均在真机上按预期工作**。
- “入队不亮灯、出队才亮灯”的语义在真机上得到确认。
- 本结果**不**使 M8/M9/M10 进入 DONE：视觉接入、共享协议定版、心跳/断连报警仍未完成。

## 未执行 / 待补

1. LED 目视照片 ✅ 已完成（`evidence/screenshots/m8-real/`）；操作视频仍 TODO
2. **断电重启后 `--verify-power-on`**：TODO
3. **`DB_M8_Acceptance` 重建后的全量自动验收 `--all`**：TODO（本轮只做了 `--check-access` 与手工步骤）
4. **视觉 → 传送带 → 真机灯闭环**：TODO（下一步）
5. **心跳 1 s / 断连 2 s 全闪**：未实现（COMM-002）
6. **实验箱端子标签与 I/O 照片**：TODO（`plc/docs/IO_MAP.md`）

## 证据位置

- 只读自检与逐拍状态：本记录正文（控制台输出原文）
- PC 侧实现：`pc/communication/reliability.py`、`pc/communication/sink.py`
- PLC 侧源码：`plc/src/FB_M8_AcceptanceHarness.scl`、`FB_PlcApplication.scl`、`FB_Fifo.scl`、`FB_LedDisplay.scl`
- 现场修复过程：`notes/issues/ISSUE-004-TIA工程UDT版本落后于仓库.md`
- 当日日志：`notes/daily/2026-09-11-三节传送带分拣可视化.md`
