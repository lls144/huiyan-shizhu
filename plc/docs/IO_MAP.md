# 项目 I/O 映射（待现场确认）

状态：TODO。指导书各实验的地址不能直接充当本表。CPU 自身 RUN/STOP、ERROR、MAINT 不作为业务分拣灯。

| 符号 | 功能 | DI/DQ 地址 | 实验箱端子/接线 | 有效电平/常开常闭 | 验证证据 |
|---|---|---|---|---|---|
| DequeueButton | 一次有效按键出队一条 | TODO | TODO | TODO | 待测试 |
| ResetButton | 清空 FIFO 与相关状态 | TODO | TODO | TODO | 待测试 |
| SortLed1 | 分拣灯 1 | TODO | TODO | TODO | 待测试 |
| SortLed2 | 分拣灯 2 | TODO | TODO | TODO | 待测试 |
| SortLed3 | 分拣灯 3 | TODO | TODO | TODO | 待测试 |
| QueueFullLed | 可选诊断/状态输出钩子；不属于已批准的第四盏业务灯 | 不绑定 | 不绑定 | 需负责人批准后定义 | 不适用 |

组态起始地址、公共端、电源与输出负载先核实。每个输入记录按下/释放的监视值；每盏灯记录输出逻辑值与实际亮灭。补充去抖时间、按键沿、上电/STOP/断连/复位行为及 LED 保持时间；未冻结的行为先提案。形状编码与亮灯数量由共享接口统一决定。
