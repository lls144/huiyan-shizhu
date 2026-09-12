# TIA Portal V20 手工导入与编译指南

目标：`TIA V20 COMPILED`。本指南只准备导入和编译，**不授权下载到 PLC**。

## 0 先建工程

在 TIA Portal V20 新建与 Online & diagnostics 完全一致的**普通** S7-1200 CPU 1214C DC/DC/DC 项目；MLFB `6ES7 214-1AG40-0XB0`，固件以现场在线读数与核验为准（见 [PLC_HARDWARE.md](../../docs/PLC_HARDWARE.md) 与 [ISSUE-002](../../notes/issues/ISSUE-002-固件版本登记不一致.md)）。不得改写为 G2。

## 1 要导入的文件（全部在 `plc/src/`）

**导入方法**：项目树 → `PLC_1` → **外部源文件 / External source files** → 右键 **添加新的外部文件 / Add new external file** → 选中下表的 `.scl` → 然后对每个源文件右键 **从源生成块 / Generate blocks from source**。

必须按顺序生成，否则前面的块引用后面的块会报“未找到类型/块”。

| 顺序 | 文件名 | 生成的对象 |
|---|---|---|
| 1 | `PLC_Types.scl` | 3 个 UDT：`PLC_Command`、`PLC_FifoBuffer`、`M8_AcceptanceData` |
| 2 | `FB_Fifo.scl` | `FB_Fifo` |
| 3 | `FB_ButtonPulse.scl` | `FB_ButtonPulse` |
| 4 | `FB_LedDisplay.scl` | `FB_LedDisplay` |
| 5 | `FB_PlcApplication.scl` | `FB_PlcApplication` |
| 6 | `FB_M8_AcceptanceHarness.scl` | `FB_M8_AcceptanceHarness` |
| 7 | `DB_M8_Acceptance.scl` | 全局 DB `DB_M8_Acceptance`（**非优化访问**，`S7_Optimized_Access := 'FALSE'`） |

**不要导入** `PLC_VARIABLES.csv`：它是人工参考的符号表（scope/name/type/writer），不是 TIA 可导入的外部源，需要时手工建符号或做成变量表。

> 第 6、7 个文件是 **PC 联调/自动验收专用**。如果只想在 PLC 里单独跑逻辑，可以只导入 1–5；但那样 PC 侧命令桥和 `plc/tools/m8_real_plc_acceptance.py` 都没有落点。

## 2 OB1 调用（两条路径，二选一）

### 路径 A：仅 PLC 内部自测（导入 1–5）

OB1 调用一次 `FB_PlcApplication`，建立一个实例 DB（如 `DB_PlcApplication`）。

### 路径 B：需要 PC 联调 / 自动验收（导入 1–7，推荐）

OB1 调用一次 `FB_M8_AcceptanceHarness`，建立一个实例 DB（如 `DB_M8_Harness`），形参接线：

| 形参 | 方向 | 接什么 |
|---|---|---|
| `Acceptance` | IN_OUT | `"DB_M8_Acceptance".Data` |
| `CommandIn` / `CommandValid` | IN | 留空或用内部测试变量；`TestEnable=TRUE` 时由 DB 覆盖 |
| `PhysicalDequeueRaw` / `PhysicalResetRaw` | IN | 先用内部变量；I/O 确认后接真实 DI |
| `QueueEmpty` / `QueueFull` / `QueueLength` | OUT | 先接内部监视变量 |
| `SortLed1` / `SortLed2` / `SortLed3` | OUT | 先用内部变量；I/O 确认后接真实 DQ |
| `QueueFullLed` | OUT | 可选诊断钩子，**不接物理 Q**，除非负责人另行批准 |

> [!warning] 不要在 OB1 里同时调用 `FB_PlcApplication` 和 `FB_M8_AcceptanceHarness`
> harness 内部已经调用了一次 `FB_PlcApplication`。再单独调一次会产生两套 FIFO 与两套灯状态，互相打架，症状是“按键有时出队有时不出队、灯和队列对不上”。

## 3 为什么 `DB_M8_Acceptance` 的编号必须记下来

PC 侧按 **绝对偏移** 读写这个 DB：写 `DBB0..DBB7`（控制字），读 `DBB8..DBB23`（状态）。所以：

- DB 必须保持 **非优化访问**，否则偏移不成立；
- 它的 **DB 编号** 必须填进 `pc/config/plc.json` 的 `db_number`；
- 偏移是否真的对上，由工具自检：`--check-access` 会校验 `DBW20 = 16#4D38`（"M8"）与 `DBB22 = 1`。

该 DB 内 `Data` 结构从偏移 0 开始，因此 `Data.TestEnable = DBX0.0`、`Data.SemanticId = DBD4`、`Data.AcceptanceReady = DBX8.0`、`Data.LayoutVersion = DBB22`，与 `plc/src/PLC_Types.scl` 中 `M8_AcceptanceData` 的注释一致。

## 4 编译记录（当前操作记录）

操作者已按 `PLC_Types.scl` → `FB_Fifo.scl` → `FB_ButtonPulse.scl` → `FB_LedDisplay.scl` → `FB_PlcApplication.scl` 顺序导入并生成，已建立 `DB_PlcApplication` 实例 DB、`DB_M8_Test` 全局测试 DB，并把 `FB_PlcApplication` 放入 `Main [OB1]`。各 SCL 源生成结果：0 error、1 条“优化的访问属性”warning。

**尚未完成**：`FB_M8_AcceptanceHarness.scl` 与 `DB_M8_Acceptance.scl` 的导入与生成、OB1 改写为路径 B。

操作者完成 `Compile → Software (rebuild all)` 后，请回报：

- TIA 完整版本与 Update；
- CPU 显示名称与 MLFB；
- 编译时间；
- error / warning 数；
- 每条 error 的原文与截图路径；
- `DB_M8_Acceptance` 的**实际 DB 编号**。

编译通过只记为 `COMPILED`，不等同于 PLCSIM 或真实 PLC PASS。
