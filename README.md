# “慧眼识珠”——AI 视觉仓库物流模拟系统

## 项目简介

本仓库用于课程项目自动化专业综合实验。系统以 PC 端视觉识别和 PLC 队列控制为核心，模拟仓库物料识别、指令缓存与分拣执行过程。

## 系统目标

`USB 摄像头 -> Python/OpenCV 识别 -> PC/PLC 通信 -> PLC FIFO -> 按键逐条出队 -> LED 模拟分拣`

最终目标与验收依据见 [项目需求规格](docs/PROJECT_SPEC.md)。

## 当前状态

- 当前阶段：M2 单目标轮廓识别已完成；M3 多目标识别与抗光照、M4 防重复识别与事件生成、M5 GUI 均处于 `DOING`。
- 10 张真实离线图片回归与两种机位下共 8 项 Insta360 实时摄像头验收均通过；实时证据见 `TEST-003` 和 `evidence/screenshots/m2/live/`。
- 实时入口复用 M1 的设备选择和 `open_configured_camera`，没有复制第二套摄像头管理逻辑。
- M3 已建立多目标薄层扩展、确定性合成数据集、离线双方案评估和 Otsu / CLAHE+Otsu 同帧实时证据入口；6 个合成场景的离线结果已留档，真实三种光照、遮挡和粘连测试待项目负责人执行。
- M4 的软件与离线模拟验证已完成：连续停留、短时漏检、离场、重入、多目标和同类多目标均有确定性测试；真实摄像头生命周期验收待执行。
- M5 已完成 PySide6 离线软件部分及 desktop vision workspace UI/UX 重构：threaded worker、synthetic/camera source adapter、M3/M4 同步展示、异常恢复、109 项全量测试和 60 秒 synthetic soak；真实摄像头 GUI 验收待执行。
- M6、通信和 PLC 均尚未开始。
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

当前已探测环境见 [开发环境记录](docs/ENVIRONMENT.md)。PC 端使用 Python/OpenCV；M5 已锁定 PySide6 6.11.2（Qt 6.11.2）。

## 如何开始

1. 阅读 `AGENTS.md` 和 `docs/PROJECT_SPEC.md`。
2. 创建并激活环境：`python -m venv .venv`，然后运行 `python -m pip install -r requirements.txt`。
3. 枚举摄像头：`python -m pc.camera --config pc/config/camera.json enumerate`。
4. 运行 M1 稳定性测试：`python -m pc.camera --config pc/config/camera.json stability --output test_data/m1/camera-stability.json --sample-frame evidence/screenshots/M1-camera-sample.jpg`。
5. 运行 M2 离线批处理：`.\.venv\Scripts\python.exe -m pc.vision --config pc/config/vision.json batch --input-root test_data/raw/m2 --output-json test_data/m2/m2-offline-results.json --output-csv test_data/m2/m2-offline-results.csv --diagnostics-dir output/m2/diagnostics --evidence-dir evidence/screenshots/m2`。
6. 运行自动化测试：`.\.venv\Scripts\python.exe -m pytest -q`。
7. 运行 M2 实时预览：`.\.venv\Scripts\python.exe -m pc.vision --config pc/config/vision.json live --camera-config pc/config/camera.json --roi-mode auto`。
8. 重新生成 M3 合成数据：`.\.venv\Scripts\python.exe -m pc.vision.synthetic --output-root test_data/m3/synthetic`。
9. 运行 M3 离线双方案批处理：`.\.venv\Scripts\python.exe -m pc.vision --config pc/config/vision.json multi-batch --input-root test_data/m3/synthetic --ground-truth test_data/m3/synthetic/ground_truth.json --output-json output/m3/offline-results.json --output-csv output/m3/offline-results.csv --diagnostics-dir output/m3/offline-diagnostics`。
10. 运行 M3 多目标/光照真实验收：`.\.venv\Scripts\python.exe -m pc.vision --config pc/config/vision.json multi-live --camera-config pc/config/camera.json --roi-mode auto --expected-labels triangle rectangle circle`。
11. 运行 M4 离线检测序列：`.\.venv\Scripts\python.exe -m pc.events --config pc/config/events.json simulate --input test_data/m4/detection-sequences.json --output-json output/m4/event-results.json --output-csv output/m4/event-results.csv`。
12. 在 M3 live 中启用 M4：在第 10 步命令末尾增加 `--events --event-config pc/config/events.json`。
13. 运行 M5 synthetic GUI：`.\.venv\Scripts\python.exe -m pc.gui --source synthetic`。
14. 运行 M3/M4/M5 联合 camera GUI：`.\.venv\Scripts\python.exe -m pc.gui --source camera --camera-config pc/config/camera.json --vision-config pc/config/vision.json --event-config pc/config/events.json --roi-mode auto --expected-labels triangle rectangle circle`。
15. 使用 `notes/templates/` 中的模板记录真实实验、问题、测试和技术决策。

`pc.vision` 实时预览使用 OpenCV 窗口，`pc.gui` 使用 PySide6；二者复用同一视觉管线。Canny 仅生成诊断证据，分类轮廓来自二值图；ROI 只在启动（或 OpenCV live 的 `R` 键）校准，运行期间不会逐帧漂移。

## 当前尚未确定的硬件信息

- PLC 型号、固件、IP、编程软件及版本。
- PLC 可用通信协议、端口和网络拓扑。
- PLC 按键、LED 的 I/O 地址与电气行为。
- Insta360 Ace Pro 2 与白色工作区已在 M2 实时识别中完成两种机位验证；背景板是否严格为 A3 及其材质仍未单独测量。
- 实验室最终使用串口还是以太网；任务书技术要求允许二者之一，但硬件方案表列出了网线。

## Milestone 状态

| Milestone | 名称 | 状态 |
|---|---|---|
| M0 | 项目初始化 | DONE |
| M1 | USB 摄像头稳定采集 | DONE |
| M2 | 单目标轮廓识别 | DONE |
| M3 | 多目标识别与抗光照 | DOING（软件与离线合成验收完成，五项真实摄像头验收待执行） |
| M4 | 防重复识别/事件生成 | DOING（软件与离线模拟验收完成，真实摄像头生命周期验收待执行） |
| M5 | GUI 上位机 | DOING（离线软件与 synthetic 验收完成，真实摄像头 GUI 验收待执行） |
| M6 | Fake PLC 模拟器 | TODO |
| M7 | PC-PLC 通信协议 | TODO |
| M8 | PLC FIFO 与 LED 逻辑 | TODO |
| M9 | 心跳、超时重发、队列满处理 | TODO |
| M10 | 实验室真实 PLC 联调 | TODO |
| M11 | 多工况系统测试 | TODO |
| M12 | 报告、PPT、演示视频整理 | TODO |
