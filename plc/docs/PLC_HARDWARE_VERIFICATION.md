# PLC 硬件与 TIA 环境核验记录

日期：2026-09-08
操作者：PLC 开发接手记录
状态：TIA V20 源生成已观察；真实 I/O/下载仍 PENDING

## 已提供、待现场核验的输入事实

| 项目 | 当前记录 | 证据/结论 |
|---|---|---|
| PLC | SIMATIC S7-1200，CPU 1214C DC/DC/DC | TIA/Accessible devices 与操作者截图；不是 G2 |
| MLFB | `6ES7 214-1AG40-0XB0` | TIA 在线信息截图；现场铭牌照片仍待补 |
| 固件 | V4.5.1 | TIA 在线信息截图；以该在线读数为当前记录 |
| TIA | Portal V20.0 | 操作者截图；Update/许可细节待补 |
| PLC IP/掩码 | `192.0.2.1/24` (`255.255.255.0`) | Accessible devices/在线信息与连通性记录 |
| Windows Host PLC 专用网卡 | 接口“以太网”；Realtek PCIe GbE Family Controller；`192.0.2.10/24`；无网关、无 DNS；Up | 管理员 PowerShell 只读输出；Host→PLC ping 4/4 |
| TIA VM PLC-facing 网卡 | `Ethernet0`；Intel(R) 82574L Gigabit Network Connection；`192.0.2.2/24`；无默认网关；Up | VM `ipconfig /all`、`Get-NetAdapter`、`Get-NetIPAddress` 输出 |
| VMware 模式/桥接目标 | TODO | 尚无 VMware 设置页或 `.vmx` 明确字段证据；不得猜测为 Bridged/Realtek |
| TIA PG/PC 接口 | TODO（需记录完整接口名称） | Accessible devices 已发现目标，但接口选择文字未留存 |
| 候选通信能力 | PROFINET IO、S7、Modbus TCP | 资料/口述候选，未对实际 CPU 与块权限实测 |

## 现场核验清单

1. 保存 TIA Online & diagnostics 的 CPU 完整显示名称、MLFB、实际固件和诊断页截图。
2. 保存 VMware 设置页/`.vmx` 中的适配器模式和桥接目标，并记录 TIA PG/PC interface 完整名称。
3. 读取实验箱端子和组态起始地址，逐一核实 `DequeueButton`、`ResetButton`、`SortLed1..3` 的 I/Q 地址、常开/常闭、有效电平和接线。
4. 在获得操作者当次明确授权后，才可下载程序、强制输出、改 IP/网卡；本记录未执行这些操作。

## 已观察与未执行项目

- TIA 源导入/生成：已观察 `PLC_Types`、`FB_Fifo`、`FB_ButtonPulse`、`FB_LedDisplay`、`FB_PlcApplication` 均生成成功；各源生成结果为 0 error、1 条优化访问属性 warning。
- TIA 工程软件编译：曾因 `DB_M8_Test` 未编译产生 11 个引用错误；操作者随后需单独编译 DB 后再报告最终全工程结果，当前不宣称全工程 COMPILED。
- PLCSIM：PENDING REAL PLC TEST
- 真实 PLC 下载/在线监视/I/O：PENDING REAL PLC TEST
- 实际通信能力与业务链路：PENDING REAL PLC TEST
