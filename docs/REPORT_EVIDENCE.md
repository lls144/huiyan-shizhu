# 报告证据链

本表用于从真实项目记录反向生成综合实验报告、测试报告、答辩 PPT 和演示视频。只有实际完成并可定位的材料才能替换 `TODO`。不得填写预测准确率、虚构测试结果或补拍后无法关联版本的截图。

| Requirement ID | 实现代码 | Git commit | Test ID | 实验日志 | 截图 | 数据文件 | 报告章节 |
|---|---|---|---|---|---|---|---|
| SCOPE-001 | TODO | TODO | TODO | TODO | TODO | TODO | 系统总体设计/系统集成 |
| VISION-001 | `pc/vision/preprocess.py`、`contours.py`、`roi.py`、`live.py`、`pc/config/vision.json` | 实现 `9f7ae794`；证据 `d8f6f60b` | TEST-002（离线 PASS）、TEST-003（实时 PASS） | `notes/daily/2026-09-04-M2-离线单目标轮廓识别.md`、`2026-09-04-M2-最终真实验收.md` | 离线：`evidence/screenshots/m2/`；实时：`evidence/screenshots/m2/live/` | 离线：`test_data/m2/2026-09-04-offline-results.*`；实时精选摘要：`evidence/data/m2-live-acceptance-summary.json` | 视觉算法/图像预处理 |
| VISION-002 | `pc/vision/classifier.py`、`pipeline.py`、`live.py` | 实现 `9f7ae794`；证据 `d8f6f60b` | TEST-002（离线 PASS）、TEST-003（实时 PASS） | 同上 | 离线：`evidence/screenshots/m2/`；实时：`evidence/screenshots/m2/live/` | 离线：`test_data/m2/2026-09-04-offline-results.*`；实时：`evidence/data/m2-live-acceptance-summary.json` | 视觉算法/形状分类 |
| VISION-003 | `pc/vision/pipeline.py`、`m3_live.py`、`m3_reporting.py`、`synthetic.py` | 基础实现 `8815e443`；数据集 `935e637`；离线 runner `32c06ba`；离线证据 `445f0b2` | TEST-004（离线 synthetic 已验证；真实 PENDING） | `notes/daily/2026-09-04-M3-最小实现与验收准备.md`、`2026-09-04-M3-离线合成验证.md` | 合成：`evidence/screenshots/m3/synthetic/`；真实 TODO | 合成真值：`test_data/m3/synthetic/ground_truth.json`；结果：`evidence/data/m3/m3-offline-synthetic-results.*`；真实 runtime 待产生 | 视觉算法/多目标检测 |
| VISION-004 | `pc/vision/preprocess.py`、`m3_live.py`、`m3_reporting.py`、`pc/config/vision.json` | 基础实现 `8815e443`；数据集 `935e637`；离线 runner `32c06ba`；离线证据 `445f0b2` | TEST-004（离线 synthetic 已验证；真实 PENDING） | 同上 | 合成：`evidence/screenshots/m3/synthetic/`；真实三种光照 TODO | 合成同帧双方案：`evidence/data/m3/m3-offline-synthetic-results.*`；真实同帧 JSON/CSV 待产生 | 视觉算法/抗光照处理 |
| GUI-001 | TODO | TODO | TODO | TODO | TODO | TODO | 上位机界面 |
| PLC-001 | TODO | TODO | TODO | TODO | TODO | TODO | PLC 设计/FIFO |
| PLC-002 | M4 子能力：`pc/events/`、`pc/config/events.json`；PLC 部分 TODO | M4 实现 `7d83c57`；离线测试 `bdaca0b`；证据 `46bb2a6`；live 证据结构测试 `506fad2`；PLC TODO | TEST-005（离线模拟 PASS；真实 PENDING）；完整 PLC 测试 TODO | `notes/daily/2026-09-04-M4-离线事件去重验证.md` | M4 无需截图；真实 live TODO | `test_data/m4/detection-sequences.json`；`evidence/data/m4/m4-offline-event-results.*` | 事件去重/生产者消费者前置 |
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
| HW-003 | `pc/camera/`、`pc/config/camera.json` | `d2b864d` | TEST-001 | `notes/daily/2026-09-03-M1-USB摄像头稳定采集.md` | `evidence/screenshots/M1-insta360-1080p-sample.jpg` | `test_data/m1/2026-09-03-insta360-stability.json` | 硬件平台/摄像头 |
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
- M3 的 `test_data/m3/synthetic/` 与 `evidence/**/m3/` 均为合成软件验证材料，不能替代 `output/m3/` 中待执行的真实摄像头验收及后续精选真实证据。
- M4 的 `test_data/m4/` 与 `evidence/data/m4/` 是 detection-sequence 离线模拟证据，不是 PLC 队列证据，也不能替代待执行的真实摄像头生命周期验收。
- **报告章节**：当前仅是建议归属；最终目录确定后再填写准确章节号。
