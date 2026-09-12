# M7 PC–PLC 通信协议 草案 v1（2026-09-11）

状态：**草案 v1，已实现并部分真机验证**；`docs/PLC_INTERFACE.md` 的冻结登记仍待 PLC 同学评审后由负责人定版。
本文取代"协议未开始"的状态，把**已经跑通的真实实现**写成可评审的契约。

## 1 传输与拓扑

| 项 | 取值 | 依据 |
|---|---|---|
| 物理介质 | 以太网（任务书硬件表写"网线"） | `HW-006` |
| 应用层 | S7 通信（ISO-on-TCP，端口 102），PC 主动连 PLC | 真机已验证 |
| PC 地址 | `192.0.2.10/24`（Realtek 专用网卡） | `docs/PLC_HARDWARE.md` |
| PLC 地址 | `192.0.2.1/24`，rack 0 / slot 1 | 同上 |
| 业务数据载体 | 全局 DB `DB_M8_Acceptance`（当前 **DB3**，非优化访问） | 真机 `magic=0x4D38` 已验证 |
| CPU | S7-1200 CPU 1214C DC/DC/DC，在线固件 V4.5.1 | ISSUE-002 已结案 |

> 选择 S7/PUT-GET 而不是自定义串口帧的理由：任务书正文允许"串口/以太网"，
> 而现场只确认了以太网口与 S7 能力；自定义帧需要 PLC 侧写接收/解析逻辑，
> 在仍有课程时限的前提下没有收益。若后续要求"可打印的帧格式"，本文件的字段表即为帧体。

## 2 数据块布局（视为帧结构）

`DB_M8_Acceptance` 共 24 字节，**非优化访问**，PC 按绝对偏移读写。

### 2.1 PC → PLC 控制区（DBB0–DBB7）

| 偏移 | 字段 | 类型 | 含义 |
|---|---|---|---|
| DBX0.0 | TestEnable | Bool | 1 = PLC 采用 DB 内的测试输入（联调/验收模式） |
| DBX0.1 | CommandValidTest | Bool | 命令有效，**上升沿入队** |
| DBX0.2 | CommandDataValid | Bool | 携带的 shape/semantic 有效 |
| DBX0.3 | DequeueTestRequest | Bool | 上升沿出队一条 |
| DBX0.4 | ResetTestRequest | Bool | 上升沿清空队列与显示 |
| **DBX0.5** | **HeartbeatEnabled** | Bool | 1 = 武装 PLC 侧 2 s 看门狗（原保留位） |
| DBB1 | ShapeCode | USInt | 形状编码，见 §3 |
| **DBB2** | **HeartbeatCounter** | USInt | 每秒自增，**变化即心跳**（原保留字节） |
| DBD4 | SemanticId | DInt | 事件语义号（PC 侧全局唯一自增） |

### 2.2 PLC → PC 状态区（DBB8–DBB23，PC 只读）

| 偏移 | 字段 | 类型 | 含义 |
|---|---|---|---|
| DBX8.0 | AcceptanceReady | Bool | harness 已在扫描 |
| DBX8.1 | QueueEmpty | Bool | 队列空 |
| DBX8.2 | QueueFull | Bool | 队列满（容量 3） |
| DBX8.3–8.5 | SortLed1–3 | Bool | 三盏分拣灯当前状态 |
| DBX8.6 | LastDequeuedValid | Bool | 自上次复位后是否出队过 |
| **DBX8.7** | **CommLostAlarm** | Bool | PLC 侧看门狗报警（原保留位） |
| DBB9 | QueueLength | USInt | 0–3 |
| DBB10 | LastDequeuedShape | USInt | 最近出队的形状编码 |
| DBD12 | LastDequeuedSemanticId | DInt | 最近出队的语义号 |
| DBD16 | CycleCounter | UDInt | 每扫描 +1（用于确认 PLC 在 RUN） |
| DBW20 | LayoutMagic | Word | 固定 `16#4D38`（"M8"） |
| DBB22 | LayoutVersion | USInt | 固定 `1` |

## 3 编码

| 形状 | ShapeCode | 灯数 |
|---|---|---|
| triangle | 1 | 1 盏 |
| rectangle | 2 | 2 盏 |
| circle | 3 | 3 盏 |
| unknown/非法 | — | 不入队，PC 端 `SKIPPED` |

## 4 时序与可靠性

### 4.1 命令（识别结果 → 队列）

1. PC 写 `CommandDataValid=1, ShapeCode, SemanticId`（`CommandValid=0`）；
2. 间隔 `command_pulse_seconds`（默认 0.05 s）后写 `CommandValid=1`；
3. 再间隔后写 `CommandValid=0`；
4. PLC 在 `CommandValid` **上升沿**且容量未满时入队。

**关键实测事实**：该 CPU 对 `DBB0–DBB7` 的 PUT/GET 写**约一半会被静默丢弃**（2026-09-10 实测）。
因此每次写都**读回校验**，不一致就重发，直到 PLC 真的持有该值（`write_confirm_attempts`，默认 12 次 × 20 ms）。
读回确认是**幂等**的：被丢弃的那次写从未产生上升沿。

### 4.2 确认（ACK 等效）

由于 DB 布局中没有专门的 ACK 字段，ACK 由**状态回读**表达：

1. 写前读 `QueueLength`；
2. 写后读 `QueueLength`：**等于写前 +1** 即确认；
3. 若命令已被立即出队（`auto_dequeue` 或操作者手快），则以
   `LastDequeuedSemanticId == 本命令 SemanticId` 作为确认；
4. 都不成立则**短暂复读**（默认 3 次 × 0.15 s）；
5. 仍不成立 → 状态 `UNCONFIRMED`，**计入计数并在界面显示"待核实"**，
   不写 `plc_sink_error`（因为人工按键会与读窗口重叠，属已知歧义，不是丢命令）。

### 4.3 超时、重发与去重

| 机制 | 取值 | 说明 |
|---|---|---|
| 写重发 | 12 次 × 20 ms | 应对静默丢写 |
| 单命令超时 | 3 s | 超时记 `timeouts` |
| 重复保护 | `duplicate_policy=refuse` | **已确认过的 semantic id 永不第二次写入**，因此重发不可能重复入队 |
| 重连 | 每笔写最多 1 次；最小间隔 2 s；重连前先做 0.5 s TCP 探活 | 对比发现：snap7 客户端不会自愈，且 connect 对无应答对端要阻塞约 10 s |
| 套接字超时 | Ping 0.5 s / Send 1 s / Recv 1 s / KeepAlive 1 s | 让断链快速失败，2 s 报警才有意义 |

### 4.4 心跳与断连报警（COMM-002）

| 侧 | 行为 |
|---|---|
| PC | 每 1 s 把 `HeartbeatCounter` 自增并写回读校验；同时看门狗监控读成功率 |
| PLC | `TestEnable AND HeartbeatEnabled` 时启动 `TON` 2 s 看门狗；计数器 2 s 无变化 → `CommLostAlarm=1`，三盏灯 2 Hz 全闪 |
| 恢复 | 计数器再次变化 → 看门狗复位 → 报警位清零、灯恢复锁存显示 |
| 隔离 | 验收工具不写 `HeartbeatEnabled`，因此其 12 项行为完全不受报警逻辑影响 |

实测：PC 心跳周期 1.00–1.03 s（真机）；PLC 报警在最后一条心跳后 **2.047 s** 触发（真机）。

### 4.5 队列满

- PLC：容量 3，满时 `QueueFull=1`；**对满队列的入队请求会被静默忽略**；
- PC：写前先读 `QueueFull`，满则**不写**，返回 `QUEUE_FULL`，
  默认策略 `defer` —— 命令暂存，队列腾出空间后自动补发（每 0.5 s 尝试一次）；
  也可设 `drop` 直接丢弃并计数。

## 5 测试向量（均已实现）

| 编号 | 场景 | 期望 |
|---|---|---|
| T-M7-01 | 单形状入队 + 出队 | 队列 0→1→0，灯按 1/2/3 盏锁存 |
| T-M7-02 | 三形状 FIFO | 出队顺序 = 入队顺序 |
| T-M7-03 | 控制字被静默丢弃 | 读回不一致 → 重发 → 最终确认，入队一次 |
| T-M7-04 | 同语义号重发 | `DUPLICATE`，队列不重复增长 |
| T-M7-05 | 队列满 | `QUEUE_FULL`，默认延后，腾空后补发 |
| T-M7-06 | 写后队列未增长 | 复读；仍无 → `UNCONFIRMED`（不当作成功） |
| T-M7-07 | 心跳中断 2 s | PLC 报警位置位 + 三盏灯全闪 |
| T-M7-08 | 心跳恢复 | 报警位清零，灯恢复 |
| T-M7-09 | 断开网线 | PC 侧 2 s 内判定中断；插回后自动重连恢复 |
| T-M7-10 | 断电重启 | 队列空、灯灭、`last_dequeued` 清零 |

离线向量见 `pc/tests/`（250 项全量通过）；真机向量见 `notes/tests/TEST-009`、`TEST-013`、
`TEST-014`、`TEST-015`、`TEST-016`、`TEST-020`。

## 6 已知限制与未冻结项

1. **无 PLC 侧序列号去重**：PLC 只按 `CommandValid` 上升沿入队。
   PC 靠"已确认语义号不重发"保证不重复；若未来要求"确认超时后受控重发且 PLC 去重"，
   需要在 DB 中增加"最后处理的序列号"字段并改 harness——属**未冻结项**。
2. **单生产者假设**：同一时刻只有一个 PC 进程写该 DB；多客户端并发未定义。
3. **`UNCONFIRMED` 语义**：人工按键与读窗口重叠时会歧义，PC 如实报"待核实"。
4. **PUT/GET 依赖 CPU 防护设置**：需勾选"Permit access with PUT/GET communication from remote partner"，
   否则报 `class=0x81 code=0x04`（2026-09-11 现场遇到过）。
5. **DB 号会变**：重新导入后块号可能改变（曾从 DB3 变为导入新工程的编号）；
   `pc/config/plc.json` 的 `db_number` 必须与 TIA 中一致。
6. **心跳只有 1 字节**：8 位回绕在 1 s 周期下需 256 s，足以区分"变化/未变化"，但不表达时间戳。

## 7 定版流程

1. PLC 同学按 `plc/docs/` 提案格式评审本草案（尤其 §6.1 的序列号字段）；
2. 负责人确认字段与 §5 测试向量；
3. 更新 `docs/PLC_INTERFACE.md` 状态为已冻结并记录 Decision 与 commit；
4. 双方引用同一版本实现，变更重复此流程。
