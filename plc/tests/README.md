# M8 测试计划

状态：设计与参考模型测试；真实 PLC/PLCSIM 均 `PENDING REAL PLC TEST`。

| ID | 场景 | 预期 |
|---|---|---|
| M8-T01 | 空队列出队 | 不出队，Empty=TRUE，Length=0 |
| M8-T02 | 1 项入队/出队 | 顺序保持，单次按键只出队 1 项 |
| M8-T03 | 三项 FIFO | triangle→rectangle→circle 顺序保持（内部测试值） |
| M8-T04 | 第四项入队 | Full=TRUE，队列不改变 |
| M8-T05 | 持续按键 | 去抖后仅一个 Pulse，不连续疯狂出队 |
| M8-T06 | 多次独立按键 | 每次一个 Pulse，严格按序出队 |
| M8-T07 | Reset | 清空数组、Head/Tail/Count，Empty=TRUE |
| M8-T08 | LED 映射 | 成功出队 triangle/rectangle/circle 后锁存 1/2/3 灯；入队不点灯 |
| M8-T09 | FIFO 满 | `QueueFullLed` 常亮，业务灯保持最近出队结果 |
| M8-T10 | unknown/空队列按键 | unknown 不入队且不改变灯；空队列按键不执行动作 |
| M8-T11 | Reset | 三盏业务灯与 Full 状态灯熄灭 |
| M8-T12 | 上电初始化 | 状态明确为 Empty、业务灯全灭，真实上电行为待实机 |
| M8-T13 | PC 失联超过 2 s | 仅在 M9 心跳块批准后验证三灯闪烁；当前 DEFERRED |
| M8-T14 | 重复数据包/ACK 丢失 | 不重复点灯或入队；依赖 M7/M9，当前 DEFERRED |

编译、PLCSIM 和真实 PLC 证据必须分别记录，不能互相替代。
