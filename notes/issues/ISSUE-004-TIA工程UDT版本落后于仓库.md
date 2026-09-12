---
title: "ISSUE-004 TIA 工程里的 PLC_Types 外部源副本落后于仓库"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - issue
status: open
---

# ISSUE-004 TIA 工程里的 `PLC_Types` 副本落后于仓库

## 现象

2026-09-11，操作者在 TIA 里按指南补做“路径 B”后，`Compile → Software (rebuild all)` 报
**31 error / 0 warning**，错误清一色是 `FB_M8_AcceptanceHarness` 里的
`#Acceptance.<成员>` **未定义**（`AcceptanceReady`、`QueueEmpty`、`QueueFull`、`SortLed1..3`、
`LastDequeuedValid`、`QueueLength`、`LastDequeuedShape`、`LastDequeuedSemanticId`、
`CycleCounter`、`LayoutMagic`、`LayoutVersion`），并附带
“正在访问块 `FB_M8_AcceptanceHarness` 未编译”。

## 根因

`Acceptance : "M8_AcceptanceData"` 这个 UDT 在**该 TIA 工程里是旧版/不存在**。

仓库时间线：

- 2026-09-08：操作者生成 `PLC_Types.scl`，`plc/records/2026-09-08-plc-m8-validation.md` 记录结果只有
  `PLC_Command`、`PLC_FifoBuffer` **两个** UDT。
- 2026-09-10 16:16：commit `da32354` 才把 `M8_AcceptanceData`（含 DBB0..DBB23 固定布局）
  **加进** `plc/src/PLC_Types.scl`。

关键机制：**TIA 的“外部源文件”是存进工程里的副本**。只替换磁盘上的 `.scl` 文件不会更新工程副本，
因此今天只补导入 `FB_M8_AcceptanceHarness.scl` 与 `DB_M8_Acceptance.scl` 时，
它们引用到的是 9 月 8 日那份没有 `M8_AcceptanceData` 的旧 `PLC_Types`。

## 处理

在 TIA 中：删除工程里的 `PLC_Types.scl` 外部源 → 重新从 `plc/src/PLC_Types.scl` 添加 →
从源生成块（应得到 3 个 UDT）→ 按顺序重新生成 `FB_Fifo` … `DB_M8_Acceptance` → 重接 OB1 形参 →
确认 `DB_M8_Acceptance` 为非优化访问 → `rebuild all`。

## 影响与预防

- 影响：真机闭环在 TIA 工程修好前无法进行；PC 侧只读探测显示 CPU 在 RUN，
  但 DB3 不存在、DB1/DB2 为优化访问不可按绝对地址读。
- 预防：以后 `plc/src/*.scl` 有改动时，**必须同时删除并重新添加对应的外部源副本**，
  不能只在磁盘上替换文件；导入清单以 `plc/project/TIA_V20_COMPILE_GUIDE.md` 第 1 节为准。
- 记录：操作者完成后的编译 error/warning 数与 `DB_M8_Acceptance` 实际块号需回报，
  按指南第 4 节格式补进 `plc/records/`。

## 同日后续：编译降到 4 个错误（同一根因的第二形态）

操作者按上述步骤重新添加 `PLC_Types.scl` 并生成后，`rebuild all` 从 **31 error** 降到
**4 error / 0 warning**：`M8_AcceptanceData` 更新成功、`DB_M8_Acceptance (DB3)` 编译成功，
只剩 OB1 里那一处 harness 调用：

| 路径 | 描述 |
|---|---|
| 16 | 传递到函数或功能块的参数数目不匹配 |
| 27 | 形参 `LastDequeuedValid` 无效 |
| 28 | 形参 `LastDequeuedShape` 无效 |
| 29 | 形参 `LastDequeuedSemanticId` 无效 |

原因与前一条同源：`da32354` 在给 UDT 加 `M8_AcceptanceData` 的同时，也给
`FB_M8_AcceptanceHarness` 加了三个 OUT 形参；而 OB1 里那个调用块是在此之前放置的，
缓存的接口还是旧版，因此“形参无效 / 数目不匹配”。

处理：在 OB1 里右键该调用块 → **更新块调用**；若菜单不可用，删掉调用块后从“程序块”重新拖入
`FB_M8_AcceptanceHarness` 再接线。新增的三个 OUT 形参可以留空。

预防同上：FB/DB 的接口变动后，**调用点也要更新**，不能只重新生成被调用的块。
