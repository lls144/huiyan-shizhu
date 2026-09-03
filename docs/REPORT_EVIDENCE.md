# 报告证据链

本表用于从真实项目记录反向生成综合实验报告、测试报告、答辩 PPT 和演示视频。只有实际完成并可定位的材料才能替换 `TODO`。不得填写预测准确率、虚构测试结果或补拍后无法关联版本的截图。

| Requirement ID | 实现代码 | Git commit | Test ID | 实验日志 | 截图 | 数据文件 | 报告章节 |
|---|---|---|---|---|---|---|---|
| SCOPE-001 | TODO | TODO | TODO | TODO | TODO | TODO | 系统总体设计/系统集成 |
| VISION-001 | TODO | TODO | TODO | TODO | TODO | TODO | 视觉算法/图像预处理 |
| VISION-002 | TODO | TODO | TODO | TODO | TODO | TODO | 视觉算法/形状分类 |
| VISION-003 | TODO | TODO | TODO | TODO | TODO | TODO | 视觉算法/多目标检测 |
| VISION-004 | TODO | TODO | TODO | TODO | TODO | TODO | 视觉算法/抗光照处理 |
| GUI-001 | TODO | TODO | TODO | TODO | TODO | TODO | 上位机界面 |
| PLC-001 | TODO | TODO | TODO | TODO | TODO | TODO | PLC 设计/FIFO |
| PLC-002 | TODO | TODO | TODO | TODO | TODO | TODO | PLC 设计/生产者消费者 |
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
- **报告章节**：当前仅是建议归属；最终目录确定后再填写准确章节号。
