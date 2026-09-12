# 视觉接入 → PLC 亮灯 实施手册

目标：视觉模块到位后，用最少的现场动作把「识别一个图形 → PLC 实验箱亮灯」跑通。

适用范围：PC→PLC 命令桥已由 TEST-008（离线）验证；真实 PLC 侧仍需 `PLC_FIELD_CHECKLIST.md`。本文不改变任何 Requirement 或 milestone 状态。

---

## 0 先看懂一件事：识别不点灯，出队才点灯

这是最容易被误解、也最容易在现场白折腾半小时的地方。

按任务书语义和已实现的 PLC 逻辑：

| 动作 | 队列 | 灯 |
|---|---|---|
| 识别到 triangle/rectangle/circle 并入队 | +1 | **不变**（保持上一次出队的结果） |
| 按一下出队键 | −1 | 锁存为 1/2/3 盏 |
| Reset | 清空 | 全灭 |

也就是说，"识别一个图形就亮灯" 实际有两种做法：

- **模式 A（符合任务书，推荐演示用）**：识别入队 → 操作者按物理按键 → 出队 → 亮 1/2/3 盏。`auto_dequeue=false`。
- **模式 B（只想快速看到灯亮，用于开发自测）**：识别入队后 PC 立刻自动发出队请求 → 亮灯。`auto_dequeue=true`。**这不是任务书要求的闭环，报告里不能当最终演示。**

如果你在现场发现"放了三角形，PLC 有反应但灯不亮"，先确认是不是没按键 —— 那是设计如此，不是故障。

---

## 1 现状：代码层面已经通了什么

已经存在、不需要新写的链路（都已在仓库里）：

```text
摄像头帧
  → pc/vision/           识别 triangle/rectangle/circle（M2/M3 已真实验收）
  → pc/events/           逐帧检测 → 离散事件 ENTER / EXIT（M4 已真实验收）
  → pc/gui/worker.py     _dispatch_plc_events() 只挑 OBJECT_ENTER
  → pc/communication/    S7PlcCommandSink.send_event() 写 DB 命令边沿
  → PLC DB_M8_Acceptance FIFO 入队
  → 按键 → FB_ButtonPulse → FB_Fifo 出队
  → FB_LedDisplay        锁存 → SortLed1/2/3
```

具体到代码：

- `pc/gui/app.py` 已经支持 `--plc-config`，并调用 `build_plc_sink()` 构造 sink 传给窗口。
- `pc/gui/worker.py` 的 `_dispatch_plc_events()` 在每个 `OBJECT_ENTER` 上调 `command_sink.send_event(event)`，结果与错误记进会话摘要（`plc_command_count` / `plc_sink_error` / `plc_results`）。
- `pc/communication/models.py` 的 `SHAPE_CODES` 与 `plc/src/FB_LedDisplay.scl` 的锁存规则一致：triangle=1、rectangle=2、circle=3。
- `pc/communication/sink.py` 写的是 `FALSE → TRUE → FALSE` 的三次 DB 写，专门配合 PLC 侧的上升沿。

**所以视觉模块到位后不需要改 PC 代码**，需要做的是配置 + 现场接线 + 验证。

---

## 2 落地步骤（按顺序做，每步都有判据）

### 步骤 0 前置：PLC 册子里先准备好 DB（在 TIA 里，需要你操作）

1. 从 `plc/src/` 导入 7 个外部源并**按序**生成（清单与方法见 [TIA_V20_COMPILE_GUIDE.md](../plc/project/TIA_V20_COMPILE_GUIDE.md) 第 1 节）：
   `PLC_Types.scl` → `FB_Fifo.scl` → `FB_ButtonPulse.scl` → `FB_LedDisplay.scl` → `FB_PlcApplication.scl` → `FB_M8_AcceptanceHarness.scl` → `DB_M8_Acceptance.scl`。
   （`PLC_VARIABLES.csv` 只是参考符号表，不导入。）
2. 在 OB1 里只调用一次 `FB_M8_AcceptanceHarness`（它内部已调用 `FB_PlcApplication`，不要再单独调一次），把 `Acceptance` 形参连到 `"DB_M8_Acceptance".Data`；`PhysicalDequeueRaw` / `PhysicalResetRaw` / `SortLed1..3` 先在 I/O 确认后接真实地址。
3. `Compile → Software (rebuild all)`，把 error/warning 数和截图记下来。
4. 下载并进入 RUN。

> 用 harness 而不是直接用 `FB_PlcApplication` 的原因是：harness 让 PLC 同时接受「PC 写的 DB 命令」和「真实按键」，这正是联调需要的组合。

### 步骤 1 读出 `DB_M8_Acceptance` 的实际 DB 号（需要你操作）

在 TIA 左侧项目树里点开该 DB，标题栏/属性里能看到编号，例如 `DB_M8_Acceptance [DB12]` —— 记下 **12** 这个数字。

这个号**必须**填进 PC 配置，填错了 PC 会写到别的 DB，PLC 不会有任何反应。

### 步骤 2 改 PC 配置（我可以代改，但需要你给 DB 号）

`pc/config/plc.json`：

```json
{
  "enabled": true,
  "host": "192.0.2.1",
  "rack": 0,
  "slot": 1,
  "db_number": 12,
  "auto_dequeue": false,
  "command_pulse_seconds": 0.05,
  "dequeue_pulse_seconds": 0.20,
  "reset_pulse_seconds": 0.20,
  "timeout_seconds": 2.0,
  "poll_seconds": 0.02
}
```

要点：

- `db_number` 换成步骤 1 的真实值。
- S7-1200 固定 `rack=0`、`slot=1`。
- 先保持 `auto_dequeue=false`（模式 A）。
- `enabled=false` 时 PC 完全不发命令，GUI 照常运行 —— 这是最安全的默认值，别急着改。

### 步骤 3 只读连通性 + DB 布局自检（不需要按键）

```powershell
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --check-access --db-number 12
```

期望：`magic=0x4D38`、`version=1`、`AcceptanceReady=TRUE`、两次读到的 `CycleCounter` 不同（说明 PLC 在 RUN）。

失败含义：

- 连不上 → 网线/IP/网卡（先看 `PLC_FIELD_CHECKLIST.md` B 组）。
- 连上但 `magic` 不对 → DB 号填错，或 DB 不是非优化访问，或 harness 没在 OB1 里跑。

### 步骤 4 不带视觉，先让灯亮一次（最快的成功体验）

```powershell
# 命令 PC 入队一条 triangle
.\.venv\Scripts\python.exe -m pc.communication --config pc/config/plc.json send --shape triangle --semantic-id 101

# 用工具读出队状态（或直接按物理按键）
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --check-access --db-number 12
```

或者直接跑完整自动验收（会自己入队/出队并断言灯状态）：

```powershell
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --all --db-number 12
```

到这一步应该已经能看到 **1/2/3 盏真实 LED** 逐个亮起。如果这步没过，先别接视觉 —— 问题在 PLC 侧或接线，与视觉无关。

### 步骤 5 再接视觉（这一步才是"视觉模块来了"）

```powershell
.\.venv\Scripts\python.exe -m pc.gui --source camera `
  --camera-config pc/config/camera.json `
  --vision-config pc/config/vision.json `
  --event-config pc/config/events.json `
  --plc-config pc/config/plc.json `
  --roi-mode auto `
  --expected-labels triangle rectangle circle
```

操作顺序：

1. 让画面里没有物体，等 GUI 状态变成 `running`（ROI 校准完成）。
2. 把三角形放进画面中央，停住约 1 秒。
3. GUI 的 events 区应出现一条 `OBJECT_ENTER label=triangle`。
4. 按一下实验箱上的出队键 → **亮 1 盏**。
5. 拿走三角形，再放矩形 → ENTER rectangle → 按键 → **亮 2 盏**；圆形 → **亮 3 盏**。

### 步骤 6 记录证据

停止会话后会生成 session 摘要，`WorkerSummary` 里会带 `plc_command_count` 和 `plc_results`。把摘要 JSON、GUI 截图、灯的照片和 `git rev-parse HEAD` 一起归档，再写 `notes/tests/` 记录。

---

## 3 故障排查

| 现象 | 最可能的原因 | 怎么确认 |
|---|---|---|
| GUI 里没有 `OBJECT_ENTER` | 视觉没认出来（`unknown`），或 `min_confirm_frames=2` 没满足 | 看 GUI 上有没有检测框；把物体停住 ≥1 秒；确认没有遮挡/粘连 |
| 有 `OBJECT_ENTER` 但队列不动 | DB 号错 / `enabled=false` / PLC 不在 RUN | 看 session 摘要里的 `plc_sink_error` 与 `plc_command_count` |
| PLC 连不上但 GUI 正常跑 | 设计如此：`_start_plc_sink` 捕获异常后只记录 `plc_sink_error`，不中断视觉 | 查 session 摘要的 `plc_sink_error` |
| 队列动了但不亮灯 | **没按出队键**（见第 0 节） | 按一下按键 |
| 灯亮了但盏数不对 | PC 与 PLC 的形状编码不一致，或 Q 地址接错 | 对照 `SHAPE_CODES` 与 `FB_LedDisplay`；查 `plc/docs/IO_MAP.md` |
| 识别一次却入队两次 | 物体进入后被短暂丢失又重入 | 看 events 是否有连续两条 ENTER；调 `pc/config/events.json` 的 `max_missing_frames` |
| 视觉卡顿 | 每次发命令会 `time.sleep` 2×`command_pulse_seconds`（默认约 0.1 s）阻塞工作线程 | 属已知设计；现场可把 `command_pulse_seconds` 调小，但要保证 PLC 扫描周期能采到上升沿 |

---

## 4 需要你（操作者）做的事

| # | 事项 | 为什么只能你做 |
|---|---|---|
| 1 | TIA：导入含 harness 的工程、编译、下载、进 RUN | 需要实验室设备和 TIA 授权 |
| 2 | 读并告诉我 `DB_M8_Acceptance` 的实际 DB 号 | 只有 TIA 里能看到 |
| 3 | 确认按键 / LED 的端子与有效逻辑（`IO_MAP.md` 仍 TODO） | 需要看实验箱实际接线 |
| 4 | 按物理按键、观察实体灯 | 需要人在现场 |
| 5 | 提供固件在线读数截图（裁定 ISSUE-002） | 需要 TIA 在线诊断 |
| 6 | 决定用模式 A 还是模式 B 做演示 | 属需求/演示决策，我不替你定 |

---

## 5 边界提醒

- 本文描述的设计满足 `PLC-002` 的**语义**，但 `PLC-001/002/003/004`、`COMM-001/002/003`、`M8`、`M10` 的**真实验收状态不变**，仍为 `TODO`。
- 心跳 1 s / 断连 2 s 全闪 / 超时重发 / 队列满通知属 **M9**，当前未实现，不能在本手册流程里声称已验证。
- 没有真实 PLC 时，模式 C（`enabled=false` + `python -m pc.communication acceptance`）可以复现整条 PC 侧链路，但它不是真实硬件证据。
