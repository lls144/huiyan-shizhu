# M8 内部 PLC 设计（transport-independent）

状态：DESIGN ONLY；尚未在 TIA 编译、PLCSIM 或真实 PLC 下载验证。

## 边界

`FB_PlcApplication` 只接收一个抽象 `PLC_Command`，其中 `CommandValid` 约定为单扫描脉冲（未来 M7 适配器负责边沿化）。它不包含 Modbus/S7/PROFINET 帧、寄存器、端口或最终 shape 编码，因此可在 M7 冻结前独立审阅。`plc/src/` 中的 `1/2/3` 仅为 TEST-ONLY 内部值。

## 数据流

```text
符号 CommandIn → FB_Fifo → DequeuedItem → FB_LedDisplay → SortLed1..3
按键原始输入 → FB_ButtonPulse → 单扫描 Dequeue/Reset 脉冲
```

- FIFO 固定容量 3，`Head/Tail/Count` 环形索引；满时拒绝入队，空时忽略出队。
- 同一扫描同时请求出队和入队时，先出队再入队；即使扫描开始时已满，也允许新项占用该扫描刚释放的位置。
- Reset 脉冲优先于其他操作并清空数组、索引和计数。
- `FB_ButtonPulse` 使用稳定扫描次数（默认 2）抑制抖动；有效按下只产生一个脉冲，持续按住不会重复出队。实际扫描周期和电气极性待现场核验。
- LED 只由 `FB_LedDisplay` 写入。识别/入队不会点灯；成功出队后锁存最近一次结果：triangle=1 灯、rectangle=2 灯、circle=3 灯，直到下一次成功出队或 Reset。FIFO 满时独立 `QueueFullLed` 常亮。`CommLost/BlinkPhase` 仅为后续 M9 报警覆盖钩子，当前应用未驱动它们。unknown 不改变既有显示。

## 并发与协议隔离

通信适配器未来只能写入 `CommandIn/CommandValid`，不能直接写 FIFO 内部或物理输出。ACK、重发、心跳、queue_full 线上字段属于 M7/M9，当前不实现。
