# 报告证据链

本表用于从真实项目记录反向生成综合实验报告、测试报告、答辩 PPT 和演示视频。只有实际完成并可定位的材料才能替换 `TODO`。不得填写预测准确率、虚构测试结果或补拍后无法关联版本的截图。

| Requirement ID | 实现代码 | Git commit | Test ID | 实验日志 | 截图 | 数据文件 | 报告章节 |
|---|---|---|---|---|---|---|---|
| SCOPE-001 | TODO | TODO | TODO | TODO | TODO | TODO | 系统总体设计/系统集成 |
| VISION-001 | `pc/vision/preprocess.py`、`contours.py`、`roi.py`、`live.py`、`pc/config/vision.json` | 实现 `9f7ae794`；证据 `d8f6f60b` | TEST-002（离线 PASS）、TEST-003（Insta360 实时 PASS，历史）、**TEST-017（内置相机实时 PASS）** | `notes/daily/2026-09-04-M2-离线单目标轮廓识别.md`、`2026-09-04-M2-最终真实验收.md`、`notes/tests/TEST-017-M2内置摄像头实时验收.md` | 离线：`evidence/screenshots/m2/`；Insta360：`evidence/screenshots/m2/live/`；**内置相机：`evidence/screenshots/m2/live-builtin/`** | 离线：`test_data/m2/2026-09-04-offline-results.*`；Insta360 摘要：`evidence/data/m2-live-acceptance-summary.json`；**内置相机：`evidence/data/m2/live-builtin/`** | 视觉算法/图像预处理 |
| VISION-002 | `pc/vision/classifier.py`、`pipeline.py`、`live.py` | 实现 `9f7ae794`；证据 `d8f6f60b` | TEST-002（离线 PASS）、TEST-003（Insta360 实时 PASS，历史）、**TEST-017（内置相机实时 PASS）** | 同上 | 离线：`evidence/screenshots/m2/`；Insta360：`evidence/screenshots/m2/live/`；**内置相机：`evidence/screenshots/m2/live-builtin/`** | 离线：`test_data/m2/2026-09-04-offline-results.*`；Insta360：`evidence/data/m2-live-acceptance-summary.json`；**内置相机：`evidence/data/m2/live-builtin/`** | 视觉算法/形状分类 |
| VISION-003 | `pc/vision/pipeline.py`、`m3_live.py`、`m3_reporting.py`、`synthetic.py` | 基础实现 `8815e443`；离线证据 `445f0b2`；真实运行 `78597f58`；精选证据 `68c89d9` | TEST-004（synthetic + Insta360 五场景 PASS，历史）、**TEST-018（内置相机：正常/侧光各 3/3 PASS）** | `notes/daily/2026-09-04-M3-离线合成验证.md`、`2026-09-07-M3-M4-M5-最终真实验收.md`、`notes/tests/TEST-018-M3内置摄像头多目标与光照验收.md` | 合成：`evidence/screenshots/m3/synthetic/`；Insta360：`evidence/screenshots/m3/live/`；**内置相机：`evidence/screenshots/m3/live-builtin/`** | 合成：`evidence/data/m3/m3-offline-synthetic-results.*`；Insta360：`evidence/data/m3/live/`；**内置相机：`evidence/data/m3/live-builtin/`** | 视觉算法/多目标检测 |
| VISION-004 | `pc/vision/preprocess.py`、`m3_live.py`、`m3_reporting.py`、`pc/config/vision.json` | 基础实现 `8815e443`；离线证据 `445f0b2`；真实运行 `78597f58`；精选证据 `68c89d9` | TEST-004（Insta360 三种光照双方案 PASS，历史）、**TEST-018（内置相机：正常 + 侧光 PASS；"较暗"因自动曝光补偿未成立，如实记录）** | 同上 | `evidence/screenshots/m3/live/{normal_light,bright_or_side_light,dark_light}/`（历史）、**`evidence/screenshots/m3/live-builtin/`** | `evidence/data/m3/live/`（历史）、**`evidence/data/m3/live-builtin/`** | 视觉算法/抗光照处理 |
| GUI-001 | `pc/gui/`（PySide6、QThread worker、source adapters、snapshot/latest-frame buffer、desktop workspace theme/overlay） | 实现 `bbb6fa7`；自动化测试 `eb7a1fd`；真实运行 `78597f58`；精选证据 `68c89d9` | TEST-006（Part A synthetic、Part B Insta360 camera 均 PASS，历史）、**TEST-019（内置相机 600 s 长跑 + 75 s 带目标短跑）** | `notes/daily/2026-09-04-M5-GUI离线软件验证.md`、`2026-09-07-M3-M4-M5-最终真实验收.md`、`notes/tests/TEST-019-M4事件与M5界面新相机验收.md` | synthetic：`evidence/screenshots/m5/synthetic/`；Insta360：`evidence/screenshots/m5/live/`；**内置相机：`evidence/screenshots/m5/live-builtin/`** | synthetic soak：`evidence/data/m5/m5-offline-gui-results.*`；Insta360 摘要：`evidence/data/m5/m5-live-camera-session-summary.json`；**内置相机：`evidence/data/m5/live-builtin/`** | 上位机界面 |
| PLC-001 | TODO | TODO | TODO | TODO | TODO | TODO | PLC 设计/FIFO |
| PLC-002 | M4 子能力：`pc/events/`、`pc/config/events.json`；PLC 部分 TODO | M4 实现 `7d83c57`；离线证据 `46bb2a6`；真实运行 `78597f58`；精选证据 `68c89d9`；PLC TODO | TEST-005（M4 离线 + camera 生命周期 PASS）；完整 PLC 测试 TODO | `notes/daily/2026-09-04-M4-离线事件去重验证.md`、`2026-09-07-M3-M4-M5-最终真实验收.md` | `evidence/screenshots/m4/live/m4-live-lifecycle-events.png.png` | 离线：`evidence/data/m4/m4-offline-event-results.*`；真实：`evidence/data/m4/m4-live-lifecycle-summary.json`、`evidence/data/m4/m4-live-lifecycle-events.csv` | 事件去重/生产者消费者前置 |
| PLC-003 | TODO | TODO | TODO | TODO | TODO | TODO | PLC 设计/LED 分拣 |
| PLC-004 | TODO | TODO | TODO | TODO | TODO | TODO | PLC 设计/队列状态与复位 |
| COMM-001 | TODO | TODO | TODO | TODO | TODO | TODO | 通信协议/帧格式 |
| COMM-002 | TODO | TODO | TODO | TODO | TODO | TODO | 通信协议/心跳报警 |
| COMM-003 | TODO | TODO | TODO | TODO | TODO | TODO | 通信协议/重发与满通知 |
| SYS-001 | TODO | TODO | TODO | TODO | TODO | TODO | 系统集成与联调 |
| TEST-001 | TODO | TODO | TODO | TODO | TODO | TODO | 测试方案与结果 |
| DOC-001 | TODO | TODO | TODO | TODO | TODO | TODO | 问题分析与改进方向 |
| HW-001 | TODO | TODO | TODO | TODO | TODO | TODO | 硬件平台/PLC |
| HW-002 | `pc/camera/`、`requirements.txt` | `d2b864d` | TEST-001 | `notes/daily/2026-09-03-M1-USB摄像头稳定采集.md` | `evidence/screenshots/M1-insta360-1080p-sample.jpg` | `test_data/m1/2026-09-03-insta360-stability.json` | 软件与运行环境 |
| HW-003 | `pc/camera/`、`pc/config/camera.json` | `d2b864d`（历史）、`6324f64`（现用相机） | TEST-001（Insta360，历史）、**TEST-010（内置 HD Webcam）** | `notes/daily/2026-09-03-M1-USB摄像头稳定采集.md`、`notes/tests/TEST-010-内置摄像头重新验收.md` | `evidence/screenshots/M1-insta360-1080p-sample.jpg`（历史）、`evidence/screenshots/M1-builtin-720p-sample.jpg` | `test_data/m1/2026-09-03-insta360-stability.json`（历史）、`test_data/m1/2026-09-10-builtin-msmf-stability.json` | 硬件平台/摄像头 |
| HW-004 | TODO | TODO | TODO | TODO | TODO | TODO | 实验对象与样本 |
| HW-005 | TODO | TODO | TODO | TODO | TODO | TODO | 实验场地与背景 |
| HW-006 | TODO | TODO | TODO | TODO | TODO | TODO | 硬件平台/通信连接 |
| DELIV-001 | TODO | TODO | TODO | TODO | TODO | TODO | 综合实验报告自检 |
| DELIV-002 | TODO | TODO | TODO | TODO | TODO | TODO | 源码交付自检 |
| DELIV-003 | TODO | TODO | TODO | TODO | TODO | TODO | PLC 工程交付自检 |
| DELIV-004 | TODO | TODO | TODO | TODO | TODO | TODO | 通信协议文档自检 |
| DELIV-005 | TODO | TODO | TODO | TODO | TODO | TODO | 测试报告自检 |
| DELIV-006 | TODO | TODO | TODO | TODO | TODO | TODO | 答辩材料自检 |
| DELIV-007 | TODO | TODO | TODO | TODO | TODO | TODO | 演示视频自检 |
| PLAN-001 | TODO | TODO | TODO | TODO | TODO | TODO | 实验过程与进度 |

## 填写约定

- **实现代码**：仓库相对路径，必要时精确到函数、PLC 程序块或文档标题。
- **Git commit**：能够重建该证据的 commit hash；工作区未提交状态不能作为最终证据。
- **Test ID**：链接到 `notes/tests/` 中的实际测试记录。
- **实验日志**：链接到 `notes/daily/` 中对应日期记录。
- **截图/数据文件**：只登记真实存在的仓库路径或明确的外部归档位置。
- `output/m2/` 中完整 runtime 数据被 Git 忽略；最终证据链只引用从这些真实文件审计后筛选出的标注图和摘要，不提交完整运行数据。
- M3 的 `synthetic/` 子目录与 `m3-offline-synthetic-results.*` 仍只表示合成软件验证；真实证据必须明确指向 `evidence/data/m3/live/` 和 `evidence/screenshots/m3/live/`，二者不可混称。
- M4 的 `m4-offline-event-results.*` 是 detection-sequence 离线模拟；`m4-live-lifecycle-*` 与 `screenshots/m4/live/` 才是 camera 生命周期证据。即使 M4 已 DONE，也不是 PLC 队列证据。
- M5 的 `screenshots/m5/synthetic/` 和 `m5-offline-gui-results.*` 仍是离线证据；`m5-live-camera-session-summary.json` 与 `screenshots/m5/live/` 才是本次真实 camera GUI 验收材料。
- **报告章节**：当前仅是建议归属；最终目录确定后再填写准确章节号。

## M3/M4/M5 最终真实验收（2026-09-07）

真实运行基线为 `78597f58e63f8f262fd0df25757218994345dc39`，精选原始证据 commit 为 `68c89d9`。M3 的 5 个原始场景 JSON/CSV、15 张 frame/annotated 图片，M4 focused lifecycle JSON/CSV 和截图，以及 M5 camera session 摘要与 running/Idle 截图均已进入上表对应路径。完整 runtime 继续位于 ignored `output/`，未提交、未覆盖、未删除。

本次最终回归为 172 项 pytest 全部通过、M2 10/10、M3 synthetic 必验光照 4/4、M4 12/12、M5 短时功能冒烟正常关闭、M6 16/16 且确定性重放；摘要见 `evidence/data/m3-m5-final-regression-summary.json`。M5 短时 synthetic 的 17.327158 FPS 不作为性能证据，真实性能只引用 camera session 的 29.315668 FPS。

## PLC 资料来源（非测试证据，2026-09-05）

指导书已原样归档到 `reference/PLC实验指导书（实验箱版20251015）(1).docx`，SHA-256 见 `reference/README.md`，核查结果见 `docs/PLC_HARDWARE.md`。负责人确认实物 CPU 1214C DC/DC/DC；没有执行 TIA 编译、下载、I/O、通信或真实 PLC 验收，不替换上表的测试 TODO。PLC 同学后续提交 `plc/records/` 和精选证据，由负责人审核并汇总。

## M6 模拟器独立验收（2026-09-05）

| 范围 | 实现与版本 | Test / Daily | 数据 | 结论 |
|---|---|---|---|---|
| M6 软件模拟器 | `simulator/`、`pc/tests/test_m6_simulator.py`；`00fa6fb3256f8d763cb6b8be765fdf34a716b007` | `notes/tests/TEST-007-M6-Fake-PLC模拟器验收.md`；`notes/daily/2026-09-05-M6-Fake-PLC离线验收.md` | `evidence/data/m6/m6-fake-plc-scenario-results.json` 与 `.csv` | 16/16 场景、确定性重放、M4集成 PASS；M6 DONE |
| 本轮上游离线回归 | 同一代码commit | 同上 | `evidence/data/m6/m6-regression-summary.json`、M2–M5 CSV、`m5-synthetic-smoke.json` | 全量172 passed；照片10/10、M3四必验光照通过、M4十二场景通过、M5功能冒烟正常关闭 |

正式模拟器 JSON 生成时 dirty=false；含源码SHA-256、配置、故障、步骤、expected/actual、最终PLC状态及benchmark。所有 M6 数据为 **simulated / Fake PLC / no physical PLC**，没有截图要求。M5短时冒烟16.73FPS不算性能验收。实现和接口限制见 `M6_FAKE_PLC.md`。

M6 fault scenarios 可供未来 M7/M9 复用，仅为 supporting simulator available；上表 PLC-001–004、COMM-001–003 的真实/正式验收仍待执行，不填未来 PASS。

## PC-PLC 通信桥离线验收（2026-09-10，非硬件证据）

| 范围 | 实现与版本 | Test / Daily | 数据 | 结论 |
|---|---|---|---|---|
| PC 侧命令桥 + Fake PLC | `pc/communication/`（`sink.py`、`s7.py`、`fake_plc.py`、`acceptance.py`）；运行基线 `59bc247` | `notes/tests/TEST-008-PC-PLC通信桥离线验收.md`；`notes/daily/2026-09-10-PC-PLC通信桥离线验收与全量回归.md` | `output/m8-bridge/m8-bridge-offline.json` 与 `.csv`（**被 Git 忽略**，可用 CLI 重放） | 5/5 离线场景 PASS |
| 上游全量回归 | 同上 | TEST-008 | 无单独数据文件 | 190 passed, 1 skipped |

本行的 5 个场景为 `single_shape_led_mapping`、`three_shape_fifo_order`、`held_command_valid_single_shot`、`unknown_event_skipped`、`reset_clears_state`，输入为**合成** `OBJECT_ENTER` 事件，PLC 为**内存** `FakeAcceptancePlc`（`DB_M8_Acceptance` 固定布局）。该结果**不是**真实 PLC 证据，不填入上表 PLC-001–004 或 COMM-001–003 的 TODO，也不改变 M7–M10 状态。

本轮同时修复了两处测试基础设施缺陷（`plc/tests` 的 pytest 收集、验收工具 `--dry-run` 参数），使全量回归首次真正覆盖 `plc/tests` 的 10 项；此前 M6 时段的“全量 172 项”并未包含它们。

现场执行清单见 `docs/PLC_FIELD_CHECKLIST.md`；最终交付物骨架见 `docs/deliverables/`。

同一轮的**报告图件**（非测试证据，属于由规格与 SCL 反推的示意图，均已标注未验证部分）：

| 图 | 源文件 | 导出 | 依据 |
|---|---|---|---|
| 系统架构图 | `evidence/plots/system-architecture.svg` | `system-architecture.png` | `PROJECT_SPEC.md`、`ROADMAP.md`、本表 M1–M6 行 |
| 入队/出队/LED 判定流程图 | `evidence/plots/plc-fifo-flow.svg` | `plc-fifo-flow.png` | `plc/docs/M8_INTERNAL_DESIGN.md`、`plc/src/*.scl`、`plc/docs/SCL_STATIC_AUDIT.md` |

视觉接入真机的操作步骤见 `docs/INTEGRATION_VISION_TO_LED.md`（流程手册，不含验收结论）。

## 三节传送带分拣可视化（2026-09-11，非硬件证据）

| 范围 | 实现与版本 | Test / Daily | 数据 | 结论 |
|---|---|---|---|---|
| PC 端“三节传送带”分拣可视化 | `pc/sorting/`（`model.py`、`controller.py`、`worker.py`、`widget.py`、`window.py`、`app.py`）、`pc/config/sorting.json`；实现与测试 commit `8d306b7` | `notes/tests/TEST-011-三节传送带分拣可视化.md`；`notes/daily/2026-09-11-三节传送带分拣可视化.md` | `evidence/screenshots/sorting/2026-09-11-sorting-synthetic-proof.png`、`evidence/data/sorting/2026-09-11-sorting-synthetic-proof.json` | 合成自检通过（8 条分拣，triangle/rectangle/circle 各按 1/2/3 盏离开）；真实摄像头与真机 PLC 待测试 |

本行的输入为 M3 已提交的**合成**夹具，渲染走 Qt offscreen，**没有使用摄像头，也没有连接 PLC**。
形状→灯映射沿用 `pc/communication/models.py` 的 `SHAPE_CODES` 与 `plc/src/FB_LedDisplay.scl`，
不是本程序新定的规则。传送带不做二次识别，只是把视觉已给出的标签可视化，
因此**不得**填入 VISION-001~004 的证据，也**不改变** PLC-001~004、COMM-001~003、SYS-001 的 TODO 状态。
运行手册见 `docs/SORTING_LINE.md`。

同一轮补充的 **PC 侧可靠性层**（同样是非硬件证据）：

| 范围 | 实现与版本 | Test / Daily | 数据 | 结论 |
|---|---|---|---|---|
| PC 侧写入确认、重复保护、队列满通知与延后 | `pc/communication/reliability.py`、`pc/communication/models.py`、`pc/communication/config.py`、`pc/config/plc.json` | `notes/tests/TEST-012-PC侧可靠性队列满与写入确认.md` | `evidence/data/sorting/2026-09-11-sorting-fake-plc-queue-full.json`、`...-fake-plc-leds.json`；截图 `evidence/screenshots/sorting/2026-09-11-sorting-buffer-and-queue-full.png`、`...-plc-leds.png` | Fake PLC 下 13 项用例通过；队列满报 `QUEUE_FULL` 并暂存，5/5 自动出队全部确认 |

该表的数据源是内存 `FakeAcceptancePlc`（容量 3）+ 合成事件，**不是**真机证据。
**心跳 1 s 与断连 2 s 全闪（COMM-002）本轮未实现**；PLC 侧序列号/ACK 去重仍未冻结。
因此 PLC-001–004、COMM-001–003 的真实/正式验收状态不变。

## 真机闭环里程碑（2026-09-11，硬件证据）

| 范围 | 实现与版本 | Test / Daily | 数据/截图 | 结论 |
|---|---|---|---|---|
| 视觉 → 传送带 → 真机 PLC → 实体灯 | `pc/sorting/`、`pc/communication/reliability.py`；PLC 侧为操作者重建后的 TIA 工程（`DB_M8_Acceptance`=DB3）| `notes/tests/TEST-014-视觉到真机灯的完整闭环.md`、`notes/tests/TEST-013-真机LED与物理按键验收.md` | `evidence/data/sorting/2026-09-11-vision-to-plc-closed-loop.json`、`evidence/screenshots/sorting/2026-09-11-vision-to-plc-closed-loop.png` | 首次完整跑通：20 条分拣全部段位/灯数正确，操作者目视 1/2/3 盏均正确 |
| 重建工程后的真机自动验收 | `plc/tools/m8_real_plc_acceptance.py`，commit `04b4622` | TEST-009（前次）、TEST-013 | `evidence/data/m8-real/2026-09-11-postrebuild-acceptance.json` / `.csv` / `-summary.md` | 12/12 AUTO PASS；193 次确认写、90 次重发 |

这两行是**真机证据**，但仍然只覆盖单次会话与既有 I/O：
断电重启、故障注入、心跳/断连报警（COMM-002）与多工况矩阵（TEST-001）仍为 TODO，
SYS-001 / M10 状态不变。

断电重启与状态清空见 `notes/tests/TEST-015-断电重启状态清空.md`（真机 PASS）：
打脏状态（队列 2、亮 1 盏、last_sid=501）后断电上电，队列/灯/last-dequeued 全部清除；
同轮发现 `DB_M8_Acceptance` 的值掉电后保留，因而在 PC 侧加入 `safe_init()` 防止残留脉冲造成幽灵入队。

COMM-002 目前只完成 **PC 半边**：`notes/tests/TEST-016-COMM002-PC半边心跳与断连看门狗.md`
（真机心跳周期 1.00–1.03 s、落点 DBB2 已读回确认；2 s 无响应判定通信中断）。
**PLC 侧“2 s 无心跳 → 三盏灯全闪”的源码已实现**（`notes/tests/TEST-020-COMM002-PLC侧看门狗与全闪.md`，
复用 DBB2/DBX0.5/DBX8.7 保留字段，改动面仅 `FB_M8_AcceptanceHarness.scl`），
但**尚未下载到真机、尚未观察到实体灯闪烁**，因此 COMM-002 仍是 TODO，不能记 PASS。

## 新相机（内置 HD Webcam）重新验收（2026-09-11）

相机由 Insta360 换成笔记本内置 `HD Webcam`（MSMF / 1280×720 / YUY2，实测 30 fps），
M2–M5 的**真实验收全部重跑**；旧 Insta360 记录（TEST-003/004/005/006）保留为历史，不作为新相机证据。

| Milestone | Test | 结果 | 证据 |
|---|---|---|---|
| M2 单目标实时 | `notes/tests/TEST-017-M2内置摄像头实时验收.md` | PASS：302 s、30.01 FPS、0 读失败；空背景 4/4 无目标，triangle/rectangle/circle 各 1 次全对 | `evidence/screenshots/m2/live-builtin/`、`evidence/data/m2/live-builtin/` |
| M3 多目标与光照 | `notes/tests/TEST-018-M3内置摄像头多目标与光照验收.md` | 多目标 PASS（正常 + 侧光各 3/3 全对）；"较暗"工况**未成立**（自动曝光补偿，3 次尝试亮度均未低于正常） | `evidence/screenshots/m3/live-builtin/`、`evidence/data/m3/live-builtin/` |
| M4 事件生命周期 | `notes/tests/TEST-019-M4事件与M5界面新相机验收.md` | PASS：66 事件 = 33 ENTER / 33 EXIT，33 个目标**零重复 ENTER** | `evidence/data/m4/m4-builtin-lifecycle-session.json` |
| M5 GUI 长跑 | 同上 | PASS：600 s、17549 帧、处理与界面更新同为 29.234 FPS、0 丢帧、0 缓冲覆盖、正常停止 | `evidence/data/m5/live-builtin/session.json`、`evidence/screenshots/m5/live-builtin/` |

本批仍有的欠账：M3 的 `partial_occlusion` / `touching_or_merged` 未在新相机上做；
"较暗"需先关闭摄像头自动曝光并固定曝光值；M5 长跑期间画面无目标（`detection_count=0`），
需补一次带目标的短时运行。**上述不足以改变 VISION-003/004、GUI-001 的已有 DONE 判定，
但报告引用时必须注明是新相机还是旧 Insta360 的证据。**
