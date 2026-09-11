---
title: "TEST-020 COMM-002 PLC 侧：2 s 看门狗与三盏灯全闪"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
  - PLC
status: 待下载验证
---

# TEST-020 COMM-002 PLC 侧看门狗与全闪

- **Test ID**：TEST-020
- **对应 Requirement ID**：COMM-002 的 **PLC 侧**（PLC 检测中断 2 秒 → LED 全闪）
- **日期**：2026-09-11
- **状态**：**已实现，待 TIA 重新生成并下载后做真机验证**（本轮不宣称通过）

> [!warning] 证据边界
> 本记录只证明**源码与 PC 侧配套已改好**，并且 PC 侧全程有单元测试支撑（全量 250 passed / 1 skipped）。
> **PLC 侧尚未下载、真机上尚未观察到三盏灯闪烁**，因此 COMM-002 整体仍为 `TODO`，不能记 PASS。

## 实现

只改一个 PLC 文件：`plc/src/FB_M8_AcceptanceHarness.scl`（TEST-ONLY 包装块）。
**不动 `DB_M8_Acceptance` 的布局、不动 `FB_PlcApplication`**，全部复用既有保留字段：

| 字段 | 偏移 | 方向 | 含义 |
|---|---|---|---|
| `ReservedInputByte2` | DBB2 | PC → PLC | 每秒自增的心跳计数 |
| `ReservedControl5` | DBX0.5 | PC → PLC | 心跳/看门狗**使能位** |
| `ReservedStatus7` | DBX8.7 | PLC → PC | 通信中断报警位 |

harness 内新增：

```scl
    #BlinkTimer(IN := NOT #BlinkTimer.Q, PT := T#250MS);
    IF #BlinkTimer.Q THEN
        #BlinkPhaseState := NOT #BlinkPhaseState;   // 2 Hz square wave
    END_IF;

    #HeartbeatArmed := #Acceptance.TestEnable AND #Acceptance.ReservedControl5;
    #HeartbeatChanged := (#Acceptance.ReservedInputByte2 <> #HeartbeatLast);
    IF #HeartbeatChanged THEN
        #HeartbeatLast := #Acceptance.ReservedInputByte2;
    END_IF;

    #HeartbeatWatchdog(IN := #HeartbeatArmed AND NOT #HeartbeatChanged,
                       PT := T#2S, Q => #CommLost);

    IF #CommLost THEN
        #SortLed1 := #BlinkPhaseState;
        #SortLed2 := #BlinkPhaseState;
        #SortLed3 := #BlinkPhaseState;
    END_IF;
```

并把 `#CommLost` 写进 `Acceptance.ReservedStatus7`、同时输出到新增输出形参 `CommLostAlarm`。

**为什么把报警放在 harness 而不是 `FB_PlcApplication`**：`FB_LedDisplay` 现有语义是
`CommLost AND BlinkPhase` 点亮三盏、其余时刻显示锁存结果；需求要的是"全闪"，
因此由 TEST-ONLY 包装块直接覆盖三盏灯输出，业务核心保持不变。这样改动面只有 1 个文件。

**为什么自动验收不受影响**：报警只在 `TestEnable AND DBX0.5` 同时为 TRUE 时武装。
`plc/tools/m8_real_plc_acceptance.py` 从不写该使能位，因此它的 12 项行为完全不变。

## PC 侧配套（已实现、有测试）

- `pc/communication/s7.py`：`PlcControls` 新增 `heartbeat_enabled`（DBX0.5），打包/解包均覆盖；
  `PlcState` 新增 `comm_lost_alarm`（DBX8.7）。
- `pc/communication/sink.py`：`_write` 默认带 `heartbeat_enabled = config.heartbeat_enabled`，
  因此桥一启动（含 `safe_init`）就武装看门狗。
- `pc/communication/reliability.py`：`PlcLinkStatus` 暴露 `plc_comm_lost_alarm`。
- `pc/sorting/window.py`：面板 `Link (COMM-002)` 行在读到 PLC 报警位时显示"（PLC 报警位置位）"。
- `pc/communication/fake_plc.py`：离线模型新增 `alarm` 位，供单元测试模拟看门狗跳闸。

新增 3 项测试（心跳使能位/报警位往返、桥武装看门狗并回读报警），全量 **250 passed / 1 skipped**。

## 操作者需要做的（TIA，约 5 分钟）

1. 项目树 → **外部源文件** → 右键 `FB_M8_AcceptanceHarness.scl` → **删除**
2. 右键 外部源文件 → **添加新的外部文件** → 选
   `D:\agent project\shiyanPLC\plc\src\FB_M8_AcceptanceHarness.scl`
3. 右键它 → **从源生成块**（弹覆盖选覆盖）
4. 打开 `Main [OB1]`：harness 多了一个输出 `CommLostAlarm`。若编译提示参数问题，
   右键调用块 → **更新块调用**；该输出**可以留空**
5. `Compile → Software (rebuild all)` → 期望 **0 error**
6. **Download** → 转 **RUN**

> 若第 3 步报"数据类型 `TON_TIME` 未找到"，把错误原文发回，改成 TIA 对应的定时器实例类型即可，
> 逻辑不变。

## 验证步骤（下载后）

1. PC 侧跑心跳脚本（`pc/communication/heartbeat.py` 已由排序程序使用），确认 PLC 报警位为 FALSE；
2. 停止心跳 / 拔掉网线 → **2 秒后实验箱三盏灯应开始全闪**，PC 读到 DBX8.7 = TRUE；
3. 恢复心跳 / 插回网线 → 报警位清零、灯恢复正常显示。

## 未执行 / 待补

1. TIA 重新生成与下载（操作者）
2. 真机观察"2 秒后三盏灯全闪"与自动恢复
3. 报警闪烁频率（2 Hz）是否符合需求未确认；需求只写"全闪"，频率为本轮设计选择
4. 报警期间是否应暂停出队/入队：本轮未改，仍按原语义工作

## 证据位置

- PLC 源码：`plc/src/FB_M8_AcceptanceHarness.scl`
- PC 实现：`pc/communication/s7.py`、`sink.py`、`reliability.py`、`pc/sorting/window.py`、`fake_plc.py`
- 测试：`pc/tests/test_communication_heartbeat.py`
- 相关记录：`TEST-016`（PC 半边）、`docs/PLC_INTERFACE.md`（共享契约仍未冻结）
