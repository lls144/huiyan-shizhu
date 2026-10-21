# 从视觉目标到 PLC 指令

[首页](../README.md) · [文档索引](INDEX.md)

## 一帧图像与一条指令不是同一件事

摄像头采集后先在 ROI 内提取轮廓，再按几何特征分类。默认使用 Otsu；CLAHE+Otsu 用于同帧对比与光照测试。分类器会保留 `unknown`，不强行给遮挡或粘连轮廓贴上三种形状标签。

事件层跨帧维护目标 ID，稳定目标进入时产生 `OBJECT_ENTER`，离开时产生 `OBJECT_EXIT`。下游消费事件而非每帧识别结果，目标停留时不会不断向队列写入。ROI 在启动时校准，不逐帧漂移。

GUI 将采集/处理和界面更新分开；分拣过程展示命令从视觉到队列的状态。真实 PLC 通信桥处理确认复读、重发与队列满延后。Fake PLC 则用虚拟时钟重放超时和故障，不访问硬件。

## PLC 接口与执行

现场控制器为 S7-1200 CPU 1214C DC/DC/DC，记录固件 V4.5.1，编程环境 TIA Portal V20。当前真机通信路径采用 M8 验收 Harness 数据区；其测试接口与正式应用 FB 分开维护，不能把测试专用地址直接视为工业接口标准。

| 入口 | 作用 |
|---|---|
| [S7 适配器](../pc/communication/s7.py) | 序列化命令与读取状态 |
| [M8 内部设计](../plc/docs/M8_INTERNAL_DESIGN.md) | FIFO、Harness 与应用结构 |
| [I/O 映射](../plc/docs/IO_MAP.md) | 实体输入输出与按钮映射 |
| [接口提案](../plc/docs/M7_PLC_INTERFACE_PROPOSAL.md) | 接口边界与后续规范化方向 |

## 同一综合实验，两条控制后端

两套后端共享识别与事件思路，但通信和工位映射分别实现，不能直接互换配置。

| | PLC 路线 | [Linux 路线](https://github.com/lls144/huiyan-shizhu-imx6ull) |
|---|---|---|
| 传输 | S7 数据区 | TCP JSON Lines |
| 队列/执行 | PLC FIFO、按钮与 1–3 灯 | 容量 3 FIFO、三工位 FSM、KEY/RGB |
| 形状映射 | triangle 1、rectangle 2、circle 3 | triangle Branch1、circle Branch2、rectangle Branch3 |
| 界面 | Windows GUI | Windows GUI + 800×480 LCD HMI |

我承担视觉、接口与系统集成，PLC 部分由团队协作完成；Linux 控制器与 HMI 的实现、部署和验收单独记录在对应仓库。
