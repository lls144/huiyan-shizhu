# SCL 静态审计（面向 TIA Portal V20）

日期：2026-09-07
结论：TEXT REVIEW ONLY；尚未有 TIA 编译器结果。

## 检查项目

- UDT 使用 `TYPE "Name" : STRUCT ... END_STRUCT; END_TYPE`，数组为 `ARRAY[0..2] OF "PLC_Command"`，容量边界明确为 3。
- FB 接口按 `VAR_INPUT`、`VAR_OUTPUT`、`VAR_IN_OUT`、`VAR_TEMP`/静态 `VAR` 分区；实例调用集中在 `FB_PlcApplication`。
- FIFO 的 `Head/Tail/Count` 为 `USInt`，仅允许 0..2 索引和 0..3 计数；已用显式 `IF >= 2 THEN 0 ELSE +1` 回绕，避免依赖不同环境对 `USInt MOD` 的隐式类型处理。
- `Count=0` 时出队被忽略；`Count=3` 时入队被拒绝；同一扫描出队后允许入队复用释放槽位；Reset 优先。
- `FB_ButtonPulse` 的 `DebounceScans` 是扫描次数而非毫秒；默认 2，实际扫描周期和电气极性待现场核验。
- `FB_LedDisplay` 是唯一业务 LED 写入块；三盏业务灯由锁存的最近一次成功出队结果驱动。`QueueFullLed` 仅为 optional diagnostic/status hook，不绑定物理 Q。
- `ShapeCode` 的 1/2/3 明确标为 INTERNAL TEST；没有写入最终 M7 协议字段、端口或地址。

## 待 TIA V20 编译确认

- 实际设备目录是否接受现场 1214C G2 MLFB 与固件组合。
- 导入后结构化参数的类型推导、FB 实例 DB 生成和 OB1 调用。
- 编译器报告的 error/warning 文本；本审计不替代 Compile → Software (rebuild all)。
