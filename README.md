# “慧眼识珠”——AI 视觉仓库物流模拟系统

## 项目简介

本仓库用于课程项目自动化专业综合实验。系统以 PC 端视觉识别和 PLC 队列控制为核心，模拟仓库物料识别、指令缓存与分拣执行过程。

## 系统目标

`USB 摄像头 -> Python/OpenCV 识别 -> PC/PLC 通信 -> PLC FIFO -> 按键逐条出队 -> LED 模拟分拣`

最终目标与验收依据见 [项目需求规格](docs/PROJECT_SPEC.md)。

## 当前状态

- 当前阶段：M1 USB 摄像头稳定采集已完成。
- 已建立可按设备名称选择摄像头的采集模块、配置、稳定性测试和真实证据记录。
- 视觉识别、GUI、通信、PLC 程序和形状工况测试均尚未开始。
- 所有尚无真实测试证据的结果均标记为 `TODO` 或“待测试”。

## 项目目录结构

```text
pc/                    PC 端代码（后续）
  camera/              摄像头采集
  vision/              OpenCV 视觉处理
  gui/                 上位机 GUI
  communication/       PC/PLC 通信
  config/              可配置参数
  tests/               PC 端单元/集成测试
plc/                   PLC 工程与导出文件
simulator/             Fake PLC 模拟器
tests/                 系统级测试
test_data/             小型可提交测试数据；raw/ 被忽略
docs/                  需求、路线图、环境与报告证据链
notes/                 Obsidian 实验记录 Vault
evidence/              可用于报告的精选截图与图表
reference/             原始任务书
scripts/               辅助脚本
```

## 开发环境

当前已探测环境见 [开发环境记录](docs/ENVIRONMENT.md)。PC 端 M1 使用 Python、OpenCV；GUI 后续优先考虑 PySide6。

## 如何开始

1. 阅读 `AGENTS.md` 和 `docs/PROJECT_SPEC.md`。
2. 创建并激活环境：`python -m venv .venv`，然后运行 `python -m pip install -r requirements.txt`。
3. 枚举摄像头：`python -m pc.camera --config pc/config/camera.json enumerate`。
4. 运行 M1 稳定性测试：`python -m pc.camera --config pc/config/camera.json stability --output test_data/m1/camera-stability.json --sample-frame evidence/screenshots/M1-camera-sample.jpg`。
5. 使用 `notes/templates/` 中的模板记录真实实验、问题、测试和技术决策。

以上命令只涉及摄像头采集与测试，不包含轮廓识别。

## 当前尚未确定的硬件信息

- PLC 型号、固件、IP、编程软件及版本。
- PLC 可用通信协议、端口和网络拓扑。
- PLC 按键、LED 的 I/O 地址与电气行为。
- Insta360 Ace Pro 2 已在当前电脑验证；三脚架垂直俯拍和 A3 背景尚未布置验证。
- 实验室最终使用串口还是以太网；任务书技术要求允许二者之一，但硬件方案表列出了网线。

## Milestone 状态

| Milestone | 名称 | 状态 |
|---|---|---|
| M0 | 项目初始化 | DONE |
| M1 | USB 摄像头稳定采集 | DONE |
| M2 | 单目标轮廓识别 | TODO |
| M3 | 多目标识别与抗光照 | TODO |
| M4 | 防重复识别/事件生成 | TODO |
| M5 | GUI 上位机 | TODO |
| M6 | Fake PLC 模拟器 | TODO |
| M7 | PC-PLC 通信协议 | TODO |
| M8 | PLC FIFO 与 LED 逻辑 | TODO |
| M9 | 心跳、超时重发、队列满处理 | TODO |
| M10 | 实验室真实 PLC 联调 | TODO |
| M11 | 多工况系统测试 | TODO |
| M12 | 报告、PPT、演示视频整理 | TODO |
