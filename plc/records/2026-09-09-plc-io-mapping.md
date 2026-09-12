# PLC I/O 映射确认记录

日期：2026-09-09
分支：`codex/plc-m8-fifo-led`
来源：操作者现场确认

## 当前映射

| 符号 | 地址 | 有效逻辑 | 状态 |
|---|---|---|---|
| `DequeueButton` | `I0.0` | 高电平按下 | 已由操作者确认；按键实测证据待补 |
| `ResetButton` | `I0.1` | 高电平按下 | 已由操作者确认；按键实测证据待补 |
| `SortLed1` | `Q0.1` | 高电平点亮 | 已由操作者确认；LED 实测证据待补 |
| `SortLed2` | `Q0.2` | 高电平点亮 | 已由操作者确认；LED 实测证据待补 |
| `SortLed3` | `Q0.3` | 高电平点亮 | 已由操作者确认；LED 实测证据待补 |

`QueueFull` 继续作为内部 BOOL 状态；`QueueFullLed` 仍是 optional diagnostic/status hook，不绑定实体 Q 地址。

## 待补证据

- 实验箱端子标签和导线照片：TODO。
- TIA 变量表/设备组态截图：TODO。
- 真实 PLC 按键按下/释放监视值及 LED 实际亮灭：PENDING。
