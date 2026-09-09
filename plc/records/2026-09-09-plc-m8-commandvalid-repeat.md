# M8 实物测试：CommandValid 跨扫描重复入队

日期：2026-09-09
分支：`codex/plc-m8-fifo-led`
状态：修复进行中；不得将 M8-T02 标记为通过

## 环境

- PLC：SIMATIC S7-1200 CPU 1214C DC/DC/DC
- MLFB：`6ES7 214-1AG40-0XB0`
- 固件：操作者报告 `V4.1`
- PLC IP：`192.0.2.1`
- TIA Portal：V20
- 测试对象：实体 PLC，在线监控 `DB_M8_Test`
- 修复前代码基线：`0eb8f6e`

## 复现输入

```text
CommandIn.Valid      = TRUE
CommandIn.ShapeCode  = 1
CommandIn.SemanticId = 101
CommandValid         = FALSE -> TRUE -> FALSE
```

操作者在监控表执行一次“立即一次性修改 TRUE”，随后执行一次“立即一次性修改 FALSE”。

## 实际结果（修复前）

```text
CommandValid = FALSE
QueueLength  = 3
QueueEmpty   = FALSE
QueueFull    = TRUE
SortLed1/2/3 = FALSE
```

证据：操作者提供的本次对话在线监控截图；原始截图尚未复制到 `plc/evidence/`。

## 根因

`FB_PlcApplication` 修复前将电平 `CommandValid` 直接连接到 `FB_Fifo.Enqueue`。TIA 写入 TRUE 到 PLC 变量后，TRUE 跨越多个 PLC 扫描周期，FIFO 每一扫描都接受同一条有效命令，直到容量 3。

## 修复目标与待复测

- `FALSE -> TRUE` 只产生一个内部入队脉冲。
- 保持 TRUE 不重复入队。
- 重新变为 FALSE 后再次 TRUE，才允许下一次入队。
- Reset 扫描更新边沿前值；保持 TRUE 的命令在 Reset 释放后不得幽灵入队。
- 修复后的实体 PLC 复测、TIA 编译和重新下载：PENDING。
- M8-T02 实物验收：PENDING，不能标记 PASS。

## 修复后离线检查

- PowerShell 边沿序列断言：PASS。
- 源码静态检查：未发现其他 `Enqueue := #CommandValid` 直接消费点；FIFO 只接收上升沿表达式。
- Python 参考测试：`7 reference tests passed`（Python 3.12.10）。
- TIA V20 重新编译：PENDING。
- 实体 PLC 重新下载与保持 TRUE 复测：PENDING。

## 操作者提供的修复后监控截图

证据来源：本次对话附件 `codex-clipboard-3c34be80-6989-4e76-bf72-861b5dd374ee.png`、`codex-clipboard-6c7f7ba6-4425-436f-bed8-ce5d31577e67.png`、`codex-clipboard-38f5b145-b478-46f7-b949-d263657f096d.png`。以下按截图实际值记录；截图标签由操作者提供，未将 M8-T02 标记为 PASS。

| 操作者标签 | CommandValid | QueueLength | QueueEmpty | QueueFull | Q0.1 / SortLed1 | Q0.2 / SortLed2 | Q0.3 / SortLed3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 第一张：入队后 | TRUE | 0 | TRUE | FALSE | TRUE | FALSE | FALSE |
| 第二张：入队前 | TRUE | 1 | FALSE | FALSE | FALSE | FALSE | FALSE |
| 第三张：出队后，Valid 改为 FALSE | FALSE | 0 | TRUE | FALSE | TRUE | FALSE | FALSE |

第二、三张的状态支持“队列有 1 项且业务灯保持全灭 → 出队后队列归零并点亮 SortLed1”。第一张的 `QueueLength=0/QueueEmpty=TRUE/SortLed1=TRUE` 与“单纯入队后”不一致，具体操作时序待操作者澄清。

仍待补：CommandValid 保持 TRUE 多个扫描周期时 QueueLength 始终为 1 的证据、Reset 后正式三角形复测、TIA V20 重新编译结果及修复后下载记录。
