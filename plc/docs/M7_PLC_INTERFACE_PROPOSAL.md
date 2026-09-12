# M7 PLC 侧通信接口提案（候选，未冻结）

状态：PROPOSAL ONLY。本文不修改 `docs/PLC_INTERFACE.md`，不构成负责人批准的共享契约。

## 传输候选比较

| 候选 | Python PC 接入 | TIA 复杂度 | 调试/抓包 | ACK、重发、心跳 | 部署/报告可解释性 |
|---|---|---|---|---|---|
| PROFINET IO | 需额外 IO 控制器栈，跨平台门槛高 | 组态耦合强 | 诊断好，通用抓包较难 | 需自建语义 | 实验箱相关但 PC 侧复杂 |
| S7 通信 | Python 需 S7 库与 DB 优化/安全差异 | 中等，DB 读写 | TIA 监控好，线上帧解释依赖库 | 可做但时序由应用承担 | 西门子专用，复现依赖环境 |
| **Modbus TCP（候选推荐）** | Python `socket`/成熟库易接入 | 标准 MB_SERVER/寄存器映射清晰 | Wireshark 易抓包 | 寄存器显式表达 ACK/重发/心跳 | 以太网直连、课程报告易解释 |

推荐仅为候选：Ethernet + Modbus TCP。最终传输、端口、地址、字节序和 DB/寄存器布局必须由负责人结合实机能力批准。

## 候选寄存器语义（草案）

以下是便于评审的语义草案，不是地址承诺；16-bit holding register、字节序、起始地址均 TODO。

| 方向 | 语义 | 建议类型 | 说明 |
|---|---|---|---|
| PC→PLC | protocol_version | UINT | 兼容性门槛 |
| PC→PLC | command_seq | UDINT（拆 2×UINT） | 重发幂等键，重启策略待定 |
| PC→PLC | command_type | UINT | OBJECT_ENTER 等，枚举待定 |
| PC→PLC | shape_code | UINT | triangle/rectangle/circle 编码待共同冻结 |
| PC→PLC | heartbeat_counter | UDINT | 建议 PC 每 1 s 递增 |
| PLC→PC | ack_seq | UDINT | ACK 是“收到”还是“入队成功”待定 |
| PLC→PC | ack_status | UINT | ACCEPTED/QUEUE_FULL/INVALID/DUPLICATE 等语义对齐 M6 |
| PLC→PC | queue_length | UINT | 0..capacity |
| PLC→PC | queue_full | BOOL/UINT | 满队列流控反馈 |
| PLC→PC | plc_heartbeat | UDINT | PLC 活跃计数 |
| PLC→PC | fault/status | UINT | Ready/Busy/Done/Error 等状态待定 |

## 时序与未决决策

- PC 心跳候选周期 1 s；PLC 连续 2 s 未收到时进入告警候选。闪烁频率、业务 LED 优先级、恢复/复位语义属于 M9/M8 联合决策。
- 重发必须以 `command_seq` 幂等，不能重复入队；设备重启后的已见序列保留策略待定。
- `QUEUE_FULL` 不应修改队列；释放容量后的重发行为需测试向量确认。
- 非法 shape 的拒绝/忽略、ACK 时点、容量数值、端口（通常 502 仅作候选）和 endian 仍未冻结。

## M6 语义 → PLC 能力 → 候选线上字段

| M6 语义 | PLC 内部能力（M8） | 候选线上字段 |
|---|---|---|
| ACCEPTED 入队 | `FB_Fifo` Enqueue + Count | ack_seq + ACCEPTED；queue_length |
| QUEUE_FULL 不入队 | Count=3，拒绝写入 | ack_status=QUEUE_FULL；queue_full |
| INVALID shape/ID | 适配器校验后 CommandValid=FALSE | ack_status=INVALID |
| DUPLICATE 幂等 | M8 预留已见序列表（M9 实现） | command_seq + DUPLICATE |
| consume_one FIFO | DequeueButton 上升沿一次出队 | queue_length、完成状态（待定） |
| heartbeat healthy/lost | M8 `CommLost/BlinkPhase` 报警钩子；M9 定时器实现 | heartbeat_counter、status/fault |

该映射保持 M6 语义边界，但不把 Python 对象或 ID 直接当成线上编码。
