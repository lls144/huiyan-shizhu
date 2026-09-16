# 从空白博图（TIA V20）项目到完全体：逐步操作手册

面向“给我一台空电脑、一个实验箱，我要把 PLC 侧从零做到可以联调”的读者。
每一步都写清楚**点哪里、填什么、看到什么算成功、失败怎么查**。

- 目标产物：可下载运行的 PLC 工程，PC 能通过 S7 读写 `DB_M8_Acceptance`，
  按键出队点灯、心跳中断全闪全部可用。
- 本文只讲 PLC 侧；PC 侧见 `docs/OPERATION_MANUAL.md`。
- 字段与偏移的权威定义见 `docs/PLC_PROTOCOL_M7.md`；导入顺序的简版见
  `TIA_V20_COMPILE_GUIDE.md`（本文是它的完整展开版）。

---

## 0 前置条件

| 项 | 要求 | 怎么确认 |
|---|---|---|
| 软件 | TIA Portal V20 | 打开能看到“启动 → 创建新项目” |
| 实物 | S7-1200 CPU 1214C DC/DC/DC（`6ES7 214-1AG40-0XB0`） | 看 CPU 铭牌 |
| 固件 | 在线 **V4.5.1** | TIA 在线读；或见 `docs/PLC_HARDWARE.md` |
| 网络 | 实验箱 PROFINET 口 ↔ 电脑网口 | 网口灯亮 |
| 电脑网卡 | PLC 专用网卡设 `192.0.2.10/255.255.255.0` | `ipconfig` 看到 |
| 源码 | `plc/src/` 下 7 个 `.scl` | 打开仓库目录 |

> **注意**：外部源文件是**导入到工程里的副本**，不是链接。以后改仓库里的 `.scl`
> 必须“删除旧源 → 重新添加 → 重新生成块”，否则工程里还是旧版本（这是 ISSUE-004 的根因）。

---

## 1 新建项目并选对 CPU

1. TIA 启动页 → **创建新项目** → 项目名 `项目1`，路径默认（如
   `C:\Users\developer\Documents\Automation\项目1`）→ 创建。
2. 开始页 → **添加新设备**：
   - 控制器 → SIMATIC S7-1200 → **CPU 1214C DC/DC/DC**
   - 订货号选 **`6ES7 214-1AG40-0XB0`**
   - **固件版本选 V4.5**（与在线一致；选 V4.1 会与实物不符）
   - 设备名称：`PLC_1`
3. 选中 PLC_1 → **设备组态** → 双击 PROFINET 口：
   - IP 地址：`192.0.2.1`
   - 子网掩码：`255.255.255.0`
4. 保存（Ctrl+S）。

**成功标志**：项目树出现 `PLC_1 [CPU 1214C DC/DC/DC]`，设备视图里 CPU 型号与订货号正确。

> 不要选 G2 型号；不要照抄指导书里的 1215C（那只是教学示例）。

---

## 2 打开 PUT/GET（不做这步，PC 一行都读不到）

1. 项目树选中 `PLC_1` → 右键 **属性**
2. **防护与安全 → 连接机制**
3. 勾选 **允许来自远程对象的 PUT/GET 通信访问**（Permit access with PUT/GET communication from remote partner）
4. 确定 → 保存

**这一步必须随下载一起生效。** 如果漏了，PC 端会报
`S7ProtocolError: class=0x81 code=0x04`——那不是网线问题，是这个开关。

---

## 3 导入 7 个外部源并生成块（顺序不能反）

项目树 → `PLC_1` → **外部源文件** → 右键 **添加新的外部文件**，按下面顺序**逐个**添加，
每添加一个就右键 → **从源生成块**：

| 顺序 | 文件 | 生成的对象 |
|---|---|---|
| 1 | `plc/src/PLC_Types.scl` | 3 个 UDT：`PLC_Command`、`PLC_FifoBuffer`、`M8_AcceptanceData` |
| 2 | `plc/src/FB_Fifo.scl` | `FB_Fifo` |
| 3 | `plc/src/FB_ButtonPulse.scl` | `FB_ButtonPulse` |
| 4 | `plc/src/FB_LedDisplay.scl` | `FB_LedDisplay` |
| 5 | `plc/src/FB_PlcApplication.scl` | `FB_PlcApplication` |
| 6 | `plc/src/FB_M8_AcceptanceHarness.scl` | `FB_M8_AcceptanceHarness`（含 COMM-002 看门狗） |
| 7 | `plc/src/DB_M8_Acceptance.scl` | 全局 DB `DB_M8_Acceptance` |

**为什么顺序不能反**：后面的块引用前面的类型/块（DB 引用 UDT，harness 引用 `FB_PlcApplication`）。
顺序错会报“未找到类型/块”。

**成功标志**：程序块下出现 7 个对象；生成日志 0 error。
会有 **1 条“优化的访问属性”警告**，那是 FB 自身的默认属性，**可以忽略**——
我们要求非优化的是数据块，不是 FB。

> 不要导入 `PLC_VARIABLES.csv`：它是给人看的参考表，不是 TIA 可导入的源。

---

## 4 建 PLC 变量表（符号名）

项目树 → PLC_1 → **PLC 变量 → 默认变量表**，按下面逐行录入（顺序无所谓）：

| 名称 | 数据类型 | 地址 |
|---|---|---|
| `DequeueButton` | Bool | `%I0.0` |
| `ResetButton` | Bool | `%I0.1` |
| `SortLed1` | Bool | `%Q0.1` |
| `SortLed2` | Bool | `%Q0.2` |
| `SortLed3` | Bool | `%Q0.3` |

**成功标志**：OB1 里能把 `%I0.0` 显示成 `"DequeueButton"`。

> 地址依据是现场实测确认的接线，见 `plc/docs/IO_MAP.md` 与
> `evidence/screenshots/plc-io/` 的变量表截图与接线照片。**不要**用指导书里其他实验的地址。

---

## 5 写 OB1（只调用一次 harness）

打开 `Main [OB1]`，在程序段 1 里放一个 `FB_M8_AcceptanceHarness` 调用（从右侧“程序块”拖进来，
实例 DB 命名如 `DB_M8_Harness`），按下面接线：

| 形参 | 方向 | 接什么 |
|---|---|---|
| `Acceptance` | IN_OUT | `"DB_M8_Acceptance".Data` |
| `PhysicalDequeueRaw` | IN | `%I0.0` |
| `PhysicalResetRaw` | IN | `%I0.1` |
| `SortLed1` | OUT | `%Q0.1` |
| `SortLed2` | OUT | `%Q0.2` |
| `SortLed3` | OUT | `%Q0.3` |
| `CommandIn`、`CommandValid` | IN | **留空**（`TestEnable=TRUE` 时由 DB 覆盖） |
| `QueueEmpty/Full/Length`、`QueueFullLed`、`CommLostAlarm` | OUT | **留空**（PC 通过 DB 读状态） |

> ⚠️ **不要在 OB1 里再单独调用 `FB_PlcApplication`**：harness 内部已经调用过一次，
> 再放一个会产生**两套 FIFO**，症状是“按键有时出队有时不出队、灯和队列对不上”。

**成功标志**：编译 OB1 无错误；调用块上 `Acceptance` 显示为 `"DB_M8_Acceptance".Data`。

---

## 6 确认 DB 是非优化访问，并记下 DB 号

1. 项目树 `DB_M8_Acceptance` → 右键 → **属性 → 属性** → 取消勾选
   **优化的块访问（Optimized block access）** → 确定。
   （SCL 源里已写 `S7_Optimized_Access := 'FALSE'`，这里只是复核）
2. 记下它的**块号**：标题栏会显示 `DB_M8_Acceptance [DB3]` 这样的形式。

**为什么必须非优化**：PC 是按**绝对偏移**读写的（写 DBB0–7、读 DBB8–23），
优化访问的块没有绝对地址，PC 会报 `Object does not exist (0x0a)`。

**为什么必须记块号**：块号会随导入顺序变化（新工程常从 DB1 开始）。这个数字要填进
PC 配置 `pc/config/plc.json` 的 `db_number`（当前项目是 **3**）。

---

## 7 编译

项目树选中 `PLC_1` → 右键 → **编译 → 软件（全部重建）**。

**成功标志**：`编译完成（错误：0；警告：N）`，错误必须是 0。

把 **错误数/警告数 + 时间 + 截图** 记进 `plc/records/`，这是交付证据的一部分。

---

## 8 下载并进入 RUN

1. 选中 `PLC_1` → **下载到设备**
2. 接口类型 PN/IE、PG/PC 接口选你的 PLC 专用网卡、子网连接
3. 勾选“全部覆盖” → 下载
4. 下载完成后让 CPU 进入 **RUN**

**成功标志**：CPU 的 RUN 绿灯常亮；TIA 在线视图能看到程序在跑。

---

## 9 验证（三步，从只读到交互）

在仓库根目录执行：

```powershell
# ① 只读：确认能访问 DB、布局对、harness 在跑
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --check-access --db-number 3
# 期望：pass=true，magic=0x4D38，version=1，CycleCounter 两次读数不同

# ② 12 项自动验收：会驱动队列和灯
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --all --db-number 3
# 期望：12/12 AUTO PASS

# ③ 心跳与断连报警：跑的时候盯着实验箱
.\.venv\Scripts\python.exe plc\tools\m8_comm002_real_check.py
# 期望：最后心跳后约 2 s 报警，三盏灯约 2 Hz 同步全闪，恢复心跳后报警清除
```

也可以通过 `launchers/` 里的 `7-`、`8-`、`9-` 三个 `.bat` 双击运行。

**成功标志**：三条全过 → PLC 侧“完全体”达成，可以接 PC 视觉做闭环。

---

## 10 PC 侧对齐（两处配置）

PLC 好了之后，确认 PC 这边对得上：

| 配置 | 文件 | 值 |
|---|---|---|
| PLC 地址 | `pc/config/plc.json` | `host: 192.0.2.1`，`rack: 0`，`slot: 1` |
| **DB 号** | `pc/config/plc.json` | `db_number` = 第 6 步记下的块号（当前 3） |
| 闭环触发 | `pc/config/sorting.json` | `plc_trigger: exit`（默认）或 `enter` |

然后跑完整闭环：

```powershell
.\.venv\Scripts\python.exe -m pc.sorting --source camera --reuse-calibration --plc-config pc/config/plc.json
```

---

## 11 完全体自检清单

做完上面 10 步，逐条打勾：

- [ ] 项目树有 7 个块 + 3 个 UDT
- [ ] OB1 只调用一次 `FB_M8_AcceptanceHarness`，6 个必要形参都接好
- [ ] `DB_M8_Acceptance` **非优化访问**，块号已知
- [ ] CPU 防护里 **PUT/GET 已勾选**并随下载生效
- [ ] 变量表有 `I0.0 / I0.1 / Q0.1 / Q0.2 / Q0.3`
- [ ] `编译（全部重建）` **0 error**
- [ ] 已下载，CPU 在 **RUN**
- [ ] `--check-access` → `pass=true`
- [ ] `--all` → **12/12 AUTO PASS**
- [ ] `m8_comm002_real_check.py` → **PASSED**
- [ ] 按出队键能亮 1/2/3 盏；按复位键清零
- [ ] `pc/config/plc.json` 的 `db_number` 与实际块号一致

---

## 12 真实踩过的坑（照这个排查）

| 现象 | 真正原因 | 处置 |
|---|---|---|
| 改了 `.scl` 但工程没变 | 外部源是**工程内副本** | 删除旧源 → 重新添加该文件 → 从源生成块 |
| 31 个 `#Acceptance.xxx 未定义` | 工程里的 `PLC_Types` 是旧副本，缺 `M8_AcceptanceData` | 重新添加 `PLC_Types.scl` 并生成块，然后按序重新生成依赖块 |
| 剩 4 个“参数数目不匹配/形参无效” | 调用块还是旧接口 | 右键调用块 → **更新块调用** |
| 读 DB 报 `Object does not exist (0x0a)` | ①该 DB 被设成优化访问，或 ②块号不对（不是 DB3） | 取消优化访问；核对块号并同步 `pc/config/plc.json` |
| 读 DB 报 `class=0x81 code=0x04` | CPU 未允许 PUT/GET | 第 2 步重新勾选并下载 |
| 写入“成功”但队列不动 | 该 CPU 对 DBB0–7 的 PUT/GET 写**约一半会静默丢弃** | 已在 PC 侧做“写→读回→重发”；不要用“写一次就成功”的判据 |
| 按键有时出队有时不出队 | OB1 里同时调用了 `FB_PlcApplication` 和 harness | 删掉多余的那个，只留 harness |
| 报警位对了但灯不闪 | 直接读定时器实例成员 `#Timer.Q` 在同一次扫描取到旧值 | 用 `Q => #变量` 输出参数形式（本仓库已改用这种写法） |
| 断电后队列还在 | `DB_M8_Acceptance` 是保持性的，PC 写入的控制位会残留 | PC 侧 `safe_init()` 每次连接先清脉冲；不要把“掉电必清空”当默认行为 |
| 写入 `plc/src/*.scl` 被拒绝 | 虚拟机里的 TIA 正打开着该文件 | 先在 TIA 里关掉该文件（或关掉 TIA），再改磁盘文件 |

---

## 13 相关文档

| 文档 | 内容 |
|---|---|
| `TIA_V20_COMPILE_GUIDE.md` | 导入顺序速查（本文的精简版） |
| `../docs/PLC_HARDWARE.md` | CPU/固件/网络参数 |
| `../docs/PLC_PROTOCOL_M7.md` | DB 字段表、时序、测试向量 |
| `../docs/IO_MAP.md` | I/O 地址与接线证据 |
| `../docs/PLC_FIELD_CHECKLIST.md` | 现场只读核对表 |
| `../records/2026-09-10-m8-real-plc-write-verification.md` | PUT/GET 丢写实测 |
| `../../notes/issues/ISSUE-002/004` | 固件登记冲突、外部源副本问题 |
