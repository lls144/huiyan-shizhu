# PLC 硬件与 TIA 环境核验记录

日期：2026-09-07
操作者：PLC 开发接手记录（远程资料审计；未连接实验室设备）
状态：PENDING REAL PLC TEST

## 已提供、待现场核验的输入事实

| 项目 | 当前记录 | 证据/结论 |
|---|---|---|
| PLC | SIMATIC S7-1200 G2，CPU 1214C DC/DC/DC | 负责人/操作者提供；待铭牌和 TIA Online 截图 |
| 固件 | V4.1 | 口述值；待在线诊断核验 |
| TIA | Portal V20 | 计划虚拟机环境；Update、许可、设备目录待核验 |
| Windows Host IP | 192.0.2.1 | 口述值；不是 PLC IP |
| TIA VM IP | 192.0.2.2 | 口述值；网卡模式/掩码待核验 |
| PLC IP/掩码/PN 接口 | TODO | 禁止猜测，需在线访问设备确认 |
| MLFB（6ES7…） | TODO | 1215C 示例 `6ES7 215-1AG40-0XB0` 不适用于本机 |
| 候选通信能力 | PROFINET IO、S7、Modbus TCP | 资料/口述候选，未对实际 CPU 与块权限实测 |

## 现场核验清单

1. 在 TIA Online & diagnostics 记录 CPU 完整显示名称、MLFB、实际固件和诊断页截图。
2. 分别记录 Host、VM、PLC 的 IPv4、掩码、网卡模式和 TIA PG/PC interface；确认 TIA 能发现、在线并读取诊断。
3. 读取实验箱端子和组态起始地址，逐一核实 `DequeueButton`、`ResetButton`、`SortLed1..3` 的 I/Q 地址、常开/常闭、有效电平和接线。
4. 在获得操作者当次明确授权后，才可下载程序、强制输出、改 IP/网卡；本记录未执行这些操作。

## 未执行项目

- TIA 编译：PENDING REAL PLC TEST（当前无 TIA 环境）
- PLCSIM：PENDING REAL PLC TEST
- 真实 PLC 下载/在线监视/I/O：PENDING REAL PLC TEST
- 实际通信能力与业务链路：PENDING REAL PLC TEST
