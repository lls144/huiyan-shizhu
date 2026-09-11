---
title: "TEST-015 断电重启后的状态清空验证"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-015 断电重启后状态清空（M8-T12 方向）

- **Test ID**：TEST-015
- **对应 Requirement ID**：PLC-004（队列空/满/长度与复位语义）、M8-T12 `--verify-power-on`
- **日期**：2026-09-11
- **Git commit**：见本记录所在 commit

> [!warning] 证据边界
> 本轮只验证“掉电再上电后队列与灯是干净的”这一条。它**不**证明断电期间的历史被审计，
> 也**不**代表 M8/M10 验收完成。断电动作由操作者执行，操作者需确认 PLC 本体指示灯确实全灭。

## 环境

- PLC：S7-1200 1214C DC/DC/DC，`192.0.2.1`，`DB_M8_Acceptance` = DB3（非优化访问）
- PC：Windows 11，Python 3.12.10；探针使用仓库 `.venv` 的 `pcn.communication.s7.Snap7LowLevelClient`
- 摄像头：未使用

## 操作步骤

1. **故意打脏状态**：复位 → 依次入队 triangle/rectangle/circle → 出队一次
   → 队列剩 2 条、灯亮 1 盏、`last_dequeued_semantic_id=501`
2. 操作者关掉实验箱主电源，等 5 秒后重新上电
3. PC 侧每约 2.7 秒只读 `DBB8..DBB23`，记录「掉线 → 重新上线 → 状态」全过程

## 预期结果

上电后：`queue_length=0`、`queue_empty=TRUE`、`queue_full=FALSE`、`leds=(F,F,F)`、
`last_dequeued_valid=FALSE`，且 `magic=0x4D38`、`AcceptanceReady=TRUE`（harness 已在运行）。

## 实际结果

```
12:04:12  magic=0x4D38 ready=True queue=2 leds=[True,False,False] last_sid=501 cycle=4171703
12:04:14  …同样状态，cycle 持续递增…
12:05:14  magic=0x4D38 ready=True queue=2 leds=[True,False,False] last_sid=501 cycle=4232061
12:05:21  UNREACHABLE                       ← 断电
12:05:38  magic=0x4D38 ready=True queue=0 leds=[False,False,False] last_sid=0 cycle=4238165
12:05:38  PASS: 上电后队列空、灯灭、last-dequeued 已清除
```

**结论：通过。** 打脏的状态（队列 2 条 + 亮 1 盏 + last_sid=501）在重新上电后全部清除，
harness 重新置位 `AcceptanceReady` 与布局字。

### 同日更早一次尝试（判为无效，已重做）

第一次在 12:01–12:03 的探测中，断电前后状态**本来就都是干净的**（队列 0、灯灭），
因此“上电后干净”什么都证明不了；而且 `CycleCounter` 未归零，无法排除只是网络瞬断。
该次结果**不作为证据**，重做后才得到上面的有效数据。

## 关键发现：`DB_M8_Acceptance` 的值掉电后仍然保留

断电前后 `CycleCounter` 连续（4,232,061 → 4,238,165，速率与断电前一致），说明**全局 DB 的值没有被复位**；
被清空的是 FIFO 与灯锁存——它们位于 `FB_PlcApplication` 的**实例静态变量**（非保持），
掉电后归零，随后 harness 每扫描把它们写回 `Acceptance.*`。

由此引出一个真实风险：如果上一次 PC 会话是**被强杀**而不是正常停止，
`DB_M8_Acceptance` 里可能残留 `TestEnable=TRUE` + `CommandValidTest=TRUE`；
PLC 的入队判据是 `CommandValid` 的上升沿，而上电后 FB 的边沿记忆是 FALSE，
于是**上电第一扫描可能产生一条幽灵入队**。

### 处置（PC 侧，已实现）

`S7PlcCommandSink.safe_init()` 在每次连接后先写一次“使能但全空转”的控制字
（`TestEnable=TRUE`，`CommandValid/CommandDataValid/Dequeue/Reset=FALSE`，`ShapeCode=0`，`SemanticId=0`），
`GuardedPlcSink.start()` 调用它；失败只记录不阻断（PLC 未就绪时不应阻止桥启动）。

真机复验（同次）：连接 → 干净状态 → 入队 triangle → 出队 → `leds=[1,0,0]`、`last_shape=1` → 复位 → 全灭，
`unconfirmed=0、errors=0`，`write_resends=3`（真机丢写照常被重发兜住）。

## 未执行 / 待补

1. 操作者确认断电时 **PLC 本体 RUN/STOP 指示灯确实全灭**（用于排除“只是网线断了”）
2. `m8_real_plc_acceptance.py --verify-power-on` 工具化留档（本轮为等效只读检查）
3. TIA 侧是否把 `DB_M8_Acceptance` 的 Retain 关掉：**建议但未执行**，属 PLC 侧改动
4. 心跳 1 s / 断连 2 s 全闪（COMM-002）：未实现

## 证据位置

- 过程日志：本记录正文（控制台输出原文）
- PC 侧防护：`pc/communication/sink.py` 的 `safe_init()`、`pc/communication/reliability.py` 的 `start()`
- 单元测试：`pc/tests/test_communication_reliability.py` 的
  `test_starting_a_session_clears_a_retained_ghost_command`
- 相关真机记录：`notes/tests/TEST-013-真机LED与物理按键验收.md`
