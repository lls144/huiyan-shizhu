# TIA Portal V20 手工导入与编译指南

目标：`TIA V20 COMPILED`。本指南只准备导入和编译，不授权下载到 PLC。

## 导入/创建顺序

1. 在 TIA Portal V20 新建与 Online & diagnostics 完全一致的普通 S7-1200 CPU 1214C DC/DC/DC 项目；MLFB `6ES7 214-1AG40-0XB0`、固件 `V4.5.1` 和设备目录以现场核验为准。不得改写为 G2。
2. 先导入 `plc/src/PLC_Types.scl`，建立 `PLC_Command` 与 `PLC_FifoBuffer` UDT。
3. 依次导入 `FB_Fifo.scl`、`FB_ButtonPulse.scl`、`FB_LedDisplay.scl`，再导入 `FB_PlcApplication.scl`。
4. 创建各 FB 的实例 DB（名称由工程师按项目规范决定），并建立一个调用 `FB_PlcApplication` 的 OB1 实例。
5. 创建 `DB_M8_Test` 全局 DB，按 `plc/src/PLC_VARIABLES.csv` 建立符号变量。`CommandIn`、按键和 LED 先使用内部测试变量，不绑定真实 I/Q 地址。

## OB1 调用要点

OB1 每一扫描调用一次 `FB_PlcApplication`：

- `CommandIn`：内部 `PLC_Command` 测试变量；`CommandValid` 必须是单扫描脉冲。
- `DequeueButtonRaw`、`ResetButtonRaw`：内部 BOOL 测试变量，先用监视表改变。
- `SortLed1..3`：仅连接到内部 BOOL 监视变量。
- `QueueFullLed`：可选诊断输出钩子，不连接任何物理 Q，除非负责人另行批准。

## 当前操作记录

- 已按 `PLC_Types.scl` → `FB_Fifo.scl` → `FB_ButtonPulse.scl` → `FB_LedDisplay.scl` → `FB_PlcApplication.scl` 顺序导入并生成。
- 已创建 `DB_PlcApplication` 实例 DB、`DB_M8_Test` 全局测试 DB，并将 `FB_PlcApplication` 放入 `Main [OB1]`。
- 各 SCL 源生成结果：0 error、1 条“优化的访问属性”warning；全工程最终编译结果仍须操作者在 DB 编译后补报。

## 编译记录

操作者完成 Compile → Software (rebuild all) 后，请回报：TIA 完整版本/Update、CPU 显示名称与 MLFB、编译时间、error/warning 数、每条 error 的文本和截图路径。编译通过也只记为 `COMPILED`，不等同于 PLCSIM 或真实 PLC PASS。
