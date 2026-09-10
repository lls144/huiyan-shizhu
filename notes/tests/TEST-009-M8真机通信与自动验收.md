---
title: "TEST-009 M8 真机 S7 通信、写入确认与自动验收"
date: "2026-09-10"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-009 M8 真机 S7 通信、写入确认与自动验收

- **Test ID**：TEST-009
- **对应 Requirement ID**：COMM-001/002/003 与 PLC-001~004 的**真机链路前置**；M8 真机自动验收
- **日期**：2026-09-10
- **Git commit**：`b3061d3`（运行基线；本轮写入确认修复见"本次修复"）

> [!warning] 证据边界
> 本测试证明：PC 能连上真实 CPU、`DB_M8_Acceptance` 布局正确、harness 在 OB1 中运行、FIFO/出队/LED 语义在真机 DB 上正确。
> 它**不**证明实体 LED 亮灭、物理按键出队、断电重启行为，也**不代表** M7/M8/M9 整体完成（视觉接入、共享协议定版、心跳/报警仍未做）。

## 测试目标

1. 确认 PC 侧 S7 客户端能访问真机 `DB_M8_Acceptance`（PUT/GET 防护已放开）。
2. 确认与 PLC 程序的 FIFO/出队/LED 语义一致。
3. 定位并修复真机验收随机失败的原因。

## 环境

- 电脑：Windows 11（当前开发机）
- Python：3.12.10（仓库 `.venv`）；python-snap7 3.1.2（`plc/tools/requirements.txt`）
- 对照用隔离环境：`%TEMP%\s7check`（原生 `python-snap7 1.3`，ctypes 封装官方 C 库）
- PLC：S7-1200 CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`，在线固件 4.5.1，`192.0.2.1`
- TIA Portal V20（操作者使用）；`PLC_1` 组态固件为 V4.1，与在线 V4.5 不一致（待改工程）
- 摄像头：**未使用**

## 输入条件

- `DB_M8_Acceptance`：DB3，非优化访问，24 字节；OB1 以路径 B 调用一次 `FB_M8_AcceptanceHarness`，`Acceptance := "DB_M8_Acceptance".Data`
- 物理 I/O：`%I0.0` DequeueButton、`%I0.1` ResetButton、`%Q0.1..0.3` SortLed1..3

## 操作步骤

1. `.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --diagnose --db-number 3`
2. `... --check-access --db-number 3`
3. `... --all --db-number 3`（多轮；含修复前后对比）
4. 用独立连接 / 原生库做写入确认与丢包对照实验
5. `.\.venv\Scripts\python.exe -m pytest -q`（全量回归）

## 预期结果

- `--check-access`：`magic=0x4D38`、`version=1`、`AcceptanceReady=TRUE`、两次 `CycleCounter` 不同
- `--all`：12 项全部 AUTO PASS

## 实际结果

| 步骤 | 结果 |
|---|---|
| `--diagnose` | `connect_ok=true`；PUT/GET 放开后 `db_read_ok=true`、`hint=[]` |
| 只读量测 | DB3 大小恰为 24 字节（读 24 成功 / 读 25 报 `Invalid address`）→ 确认为 `DB_M8_Acceptance` |
| `--check-access` | PASS（`magic=0x4D38`、`version=1`、`CycleCounter` 递增） |
| 修复前 `--all` | FAIL，且失败点每次不同（第 1/3 次入队、或出队超时） |
| 手动逐拍时序 | reset→入队 triangle/101→出队，读回 `leds=[1,0,0]`、`lastShape=1`、`lastSid=101`；circle/103 → `leds=[1,1,1]` |
| 丢包定位 | M 区写 10/10 生效；DB3.DBB0 写 5/10；写入加读回校验后 20/20 |
| 修复后 `--all` | **12/12 AUTO PASS**，193 次确认写、88 次需重发、最多 9 次（4 次连续运行均为全绿） |
| 全量 pytest | 196 passed / 1 skipped |

## 结论与影响

- 真机通信、DB 布局、harness 运行、FIFO/出队/LED 语义均正确。
- **真机随机失败的根因是 PUT/GET 写 `DB_M8_Acceptance` 控制字被静默丢弃约一半**（详见 `plc/records/2026-09-10-m8-real-plc-write-verification.md`）。因此 `plc/tools/m8_real_plc_acceptance.py` 与 `pc/communication/sink.py` 均改为"写→读回→重发"。
- M7 协议必须包含写入确认/ACK，"写一次即送达"不可行。

## 未执行 / 待补证据

- 实体 1/2/3 盏 LED 亮灭的目视确认（AUTO 只读 Q 状态）
- 物理按键出队、断电重启（M8-T12）
- 视觉事件经 GUI 驱动真机（M7 接入，未做）
- 离线工程固件 V4.1 → 在线 V4.5 的组态修正
