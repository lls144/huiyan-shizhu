# “慧眼识珠”——AI 视觉仓库物流模拟系统

## 项目简介

本仓库用于课程项目自动化专业综合实验。系统以 PC 端视觉识别和 PLC 队列控制为核心，模拟仓库物料识别、指令缓存与分拣执行过程。

## 系统目标

`USB 摄像头 -> Python/OpenCV 识别 -> PC/PLC 通信 -> PLC FIFO -> 按键逐条出队 -> LED 模拟分拣`

最终目标与验收依据见 [项目需求规格](docs/PROJECT_SPEC.md)。

## 当前状态

- 当前阶段：M2 单目标、M3 多目标与抗光照、M4 防重复识别与事件生成、M5 GUI、M6 Fake PLC 均已完成各自定义范围内的验收；M7 及以后未开始。
- 10 张真实离线图片回归与两种机位下共 8 项 Insta360 实时摄像头验收均通过；实时证据见 `TEST-003` 和 `evidence/screenshots/m2/live/`。
- 实时入口复用 M1 的设备选择和 `open_configured_camera`，没有复制第二套摄像头管理逻辑。
- M3 已用 Insta360 对正常、较亮/侧光、较暗、部分遮挡和接触/粘连 5 个真实场景完成 Otsu / CLAHE+Otsu 同帧审计。前三种光照两种方法均完整识别三类；遮挡输出 `circle + unknown + triangle`，接触输出 `unknown + triangle`，失败样例已保留。默认方案继续使用更简单的 Otsu。
- M4 已完成真实 circle 生命周期审计：同一 #75 持续停留仅一次 ENTER，离场产生 EXIT，重入后新 #76 产生 ENTER；短暂遮挡保持 ID 的结论明确标记为现场人工观察 + GUI 截图，而非 JSON 逐帧证据。
- M5 已完成 1577.142974 秒 Insta360 GUI 真实运行：46235/46235 帧，processing/GUI 均为 29.315668 FPS，0 failed read、0 error，Stop 后 clean shutdown。auto ROI 未找到合格区域后 manual ROI 成功并锁定。
- M6 Fake PLC 已完成纯离线验收（16 场景、确定性故障重放、M4 集成）；通信协议与真实 PLC 实现仍未开始。
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

- 现场确认实际设备为普通 S7-1200 CPU 1214C DC/DC/DC，完整 MLFB `6ES7 214-1AG40-0XB0`；固件 V4.1 仍为操作者报告、待 TIA 在线读取。TIA Portal V20 当前作为实际编程环境使用，其 Update、许可和设备目录兼容性仍待记录。
- PLC 登记地址为 `192.0.2.1/24`；Windows Host 的 Realtek PLC 专用网卡为 `192.0.2.10/24`，Host ping 4/4 且 ARP reachable。该结果只证明物理链路上地址可达，目标 PLC 身份仍待 TIA Accessible devices / Online diagnostics 确认。完整参数和待核实项见 [PLC 硬件登记](docs/PLC_HARDWARE.md)，最终 I/O 映射仍待确认。
- PLC 同学克隆后先读 [协作约定](docs/COLLABORATION.md)、[共享接口登记](docs/PLC_INTERFACE.md) 和 [PLC 目录规则](plc/AGENTS.md)；只在 PLC 分支开展所分配工作，负责人审核合并。
- Insta360 Ace Pro 2 与白色工作区已在 M2 实时识别中完成两种机位验证；背景板是否严格为 A3 及其材质仍未单独测量。
- 实验室最终使用串口还是以太网；任务书技术要求允许二者之一，但硬件方案表列出了网线。

## Milestone 状态

| Milestone | 名称 | 状态 |
|---|---|---|
| M0 | 项目初始化 | DONE |
| M1 | USB 摄像头稳定采集 | DONE |
| M2 | 单目标轮廓识别 | DONE |
| M3 | 多目标识别与抗光照 | DONE（5 个真实摄像头场景及双方案证据已审计） |
| M4 | 防重复识别/事件生成 | DONE（PC 事件层真实生命周期已审计；不代表 PLC-002 整体完成） |
| M5 | GUI 上位机 | DONE（真实 Insta360 GUI 性能、同步显示与正常关闭已审计） |
| M6 | Fake PLC 模拟器 | DONE（纯软件模拟器验收；无真实 PLC） |
| M7 | PC-PLC 通信协议 | TODO |
| M8 | PLC FIFO 与 LED 逻辑 | TODO |
| M9 | 心跳、超时重发、队列满处理 | TODO |
| M10 | 实验室真实 PLC 联调 | TODO |
| M11 | 多工况系统测试 | TODO |
| M12 | 报告、PPT、演示视频整理 | TODO |

## M6 Fake PLC

```powershell
.\.venv\Scripts\python.exe -m simulator --scenario all
```

输出 JSON/CSV 至 `output/m6/`；所有预期通过退出 0，否则非零。支持 `--scenario ack_loss` 等单场景和 `--config`。使用虚拟毫秒时钟，无摄像头、无真实 PLC、无真实通信。Fake PLC ≠ real PLC，不代表 M7/M8/M9 完成。架构、接口、边界见 [M6 使用说明](docs/M6_FAKE_PLC.md)，正式证据见 [TEST-007](notes/tests/TEST-007-M6-Fake-PLC模拟器验收.md)。

## PC→PLC 命令桥（离线，非真实硬件）

```powershell
.\.venv\Scripts\python.exe -m pc.communication acceptance --output-dir output/m8-bridge
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --dry-run
```

用合成 `OBJECT_ENTER` 事件驱动命令桥，对内存 Fake PLC 核对 FIFO 顺序、`CommandValid` 边沿、1/2/3 灯映射、unknown 拒绝与 Reset；输出 JSON/CSV 至被 Git 忽略的 `output/m8-bridge/`。这不连接真实 PLC，不代表 M7/M8/M9 完成。见 [TEST-008](notes/tests/TEST-008-PC-PLC通信桥离线验收.md)。

## 现场联调与交付物准备

- PLC 现场只读核对表：[docs/PLC_FIELD_CHECKLIST.md](docs/PLC_FIELD_CHECKLIST.md)（A 设备身份 / B 网络 / C I/O 与 DB / D 编译 / E 下载 / F 录像前检查）。A~D 只读，E/F 需操作者当次授权。
- 视觉接入 → PLC 亮灯的操作手册：[docs/INTEGRATION_VISION_TO_LED.md](docs/INTEGRATION_VISION_TO_LED.md)（含“识别不点灯、出队才点灯”的语义说明、分步命令与故障排查表）。
- 最终交付物骨架：[docs/deliverables/](docs/deliverables/README.md)（报告、测试用例矩阵、PPT、视频分镜）。所有结果列在真机执行前保持 `TODO` / 待测试。
- 报告图件：[evidence/plots/](evidence/plots/) 下的系统架构图与 PLC 判定流程图（`.svg` 可编辑，`.png` 供文档嵌入）。
