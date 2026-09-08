# PLC M8 硬件、环境与内部验证记录

日期：2026-09-08
代码基线：`46e231c`；本记录与本轮 PLC-only 修正一同提交
分支：`codex/plc-m8-fifo-led`

## 环境与硬件事实

| 项目 | 已记录值 | 来源/状态 |
|---|---|---|
| PLC | SIMATIC S7-1200 CPU 1214C DC/DC/DC | TIA Accessible devices/在线信息截图；不是 G2 |
| MLFB | `6ES7 214-1AG40-0XB0` | TIA 在线信息截图 |
| 固件 | `V4.5.1` | TIA 在线信息截图 |
| PLC 网络 | `192.0.2.1/24`，无默认网关 | 操作者现场报告与在线信息；协议未冻结 |
| Windows Host PLC 网卡 | 接口“以太网”；Realtek PCIe GbE Family Controller；`192.0.2.10/24`；无网关、无 DNS；Up | 管理员 PowerShell 只读输出；Host→PLC ping 4/4，ARP reachable |
| TIA VM PLC-facing 网卡 | `Ethernet0`；Intel(R) 82574L Gigabit Network Connection；`192.0.2.2/24`；无默认网关；Up | VM `ipconfig /all`、`Get-NetAdapter`、`Get-NetIPAddress` 输出；VM→PLC ping 4/4 |
| VMware 模式/桥接目标 | TODO | 未保存设置页或 `.vmx` 明确字段，不猜测为 Bridged/Realtek |
| TIA PG/PC 接口 | TODO | 目标可发现，但完整接口名称未归档 |

## 实验箱接线与 I/O

`DequeueButton`、`ResetButton`、`SortLed1`、`SortLed2`、`SortLed3` 的端子标签、候选 DI/DQ 地址、常开/常闭、按下/释放值、亮/灭有效电平均为 **TODO/待现场确认**。指导书示例地址不作为项目映射。`QueueFull` 保留为内部 BOOL；`QueueFullLed` 仅为 optional diagnostic/status hook，不绑定真实 Q，也不是第四盏批准的实体灯。

## TIA V20 导入状态

操作者已按以下顺序完成外部源生成：

1. `PLC_Types.scl` → `PLC_Command`、`PLC_FifoBuffer`
2. `FB_Fifo.scl`
3. `FB_ButtonPulse.scl`
4. `FB_LedDisplay.scl`
5. `FB_PlcApplication.scl`
6. `DB_PlcApplication` 实例 DB、`DB_M8_Test` 全局测试 DB
7. `Main [OB1]` 调用 `FB_PlcApplication`

截图观察结果：每个外部源生成均为 0 error、1 条“优化的访问属性”warning。早期 `FB_LedDisplay` 空 `ELSE` 语法错误已从仓库源文件移除。全工程 `Compile → Software (rebuild all)` 的最终结果没有归档，仍为 **PENDING**；PLCSIM、下载、真实 I/O 也均为 **PENDING**。

## 内部参考模型测试

环境：仓库提供的 Python 参考模型；使用工作区捆绑 Python 直接调用 6 个 `test_*` 函数（系统 PATH 无 pytest）。

预期与实际：

| 覆盖项 | 结果 |
|---|---|
| 三项 FIFO 顺序、第四项拒绝、空队列出队 | PASS（参考模型） |
| 满队列同一扫描出队后复用槽位 | PASS（参考模型） |
| 入队不改变 LED；triangle/rectangle/circle 锁存 1/2/3 灯 | PASS（参考模型） |
| unknown 不改变已有显示 | PASS（参考模型） |
| 按键去抖、持续按住只产生一次 Pulse | PASS（参考模型） |
| Reset 清除按键状态 | PASS（参考模型） |

测试输出：`6 reference tests passed`。该结果不等同于 TIA 编译、PLCSIM 或真实 PLC PASS。

## 未执行与待补证据

- TIA 全工程最终编译 error/warning 截图：PENDING。
- 实验箱端子/引脚、I/O 地址和有效电平：TODO。
- 真实 PLC 下载、在线监视、按键后实体 LED：PENDING；本轮未下载、未强制 I/O。
- 证据归档：操作者聊天截图尚未复制到仓库 `plc/evidence/`，待负责人审核后归档。
