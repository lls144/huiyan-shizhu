---
title: "TEST-011 三节传送带分拣可视化与 PLC 触发（合成自检）"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-011 三节传送带分拣可视化（合成自检）

- **Test ID**：TEST-011
- **对应 Requirement ID**：PLC-003（形状→1/2/3 盏灯的映射）的 PC 侧前置；SYS-001 的演示可视化组件
- **日期**：2026-09-11
- **Git commit**：`8d306b736ab706f8e8ece47b0d2e92f3b9e1df46`（实现与测试）

> [!warning] 证据边界
> 本测试使用 **合成数据集**（`test_data/m3/synthetic/`）+ 离屏 Qt 渲染，**没有使用摄像头，也没有连接 PLC**。
> 它证明：三段传送带的分拣判定、动画状态机、形状→灯映射、以及 PC 侧命令桥的触发逻辑按设计工作。
> 它**不**证明真实摄像头识别的实时表现，也**不**证明真机 PLC 收到命令并点亮实体灯。
> 真机联调待测试，见文末“未执行 / 待补”。

## 测试目标

按操作者 2026-09-11 要求，实现并验证“识别一个图形 → 三节传送带（三角形/矩形/圆形）→
物料块在自己那一段离开并示意 → 结果发给 PLC，三角形 1 盏、矩形 2 盏、圆形 3 盏”。

## 环境

- 电脑：Windows 11（当前开发机）；Python 3.12.10；PySide6 6.11.2；OpenCV 5.0.0；numpy 2.5.2
- 数据源：`test_data/m3/synthetic/`（M3 已提交的合成夹具，含 blank/normal/bright/dark/occlusion/touching 场景）
- 渲染：Qt offscreen 平台
- 摄像头、PLC：**未使用**

## 输入条件

- `pc/config/sorting.json`：`belt_speed_units_per_second=0.60`、`min_gap_units=0.30`、
  `eject_seconds=0.85`、`max_pending_items=6`、`plc_trigger=exit`
- `pc/config/events.json` 未改；`pc/config/vision.json` 未改（仍为原值，ROI 走运行时校准）

## 操作步骤

1. `.\.venv\Scripts\python.exe -m pytest -q`
2. `.\.venv\Scripts\python.exe -m pc.sorting --source synthetic --offscreen --soak-seconds 26`
   `--summary-json output/sorting/synthetic-proof.json --screenshot output/sorting/synthetic-proof.png`
3. 审计 session JSON：`sorting_results`、`sorting_results_by_shape`、`error`、`ended_reason`
4. 目视审计截图：三段传送带、料框灯点、分拣日志、本帧识别

## 预期结果

- 单元测试全绿；新用例覆盖三形状的段位与灯数、未知标签拒绝、入口排队、不越位、确定性重放、
  以及 `plc_trigger` 的 enter/exit 两种时点。
- 合成会话里三种形状都出现，`lamp_count` 分别为 1/2/3，`error=null`，正常停止。
- 截图能看到物料块在自己那一段离开、对应料框灯点亮、分拣日志记录该条结果。

## 实际结果

**全量回归**

```
218 passed, 1 skipped in 3.54s
```

其中本轮新增 `pc/tests/test_sorting_simulator.py`（12 项）与 `pc/tests/test_sorting_controller.py`（6 项）共 18 项。

**合成会话**（`--source synthetic --offscreen --soak-seconds 26`，PLC 桥默认关闭）

| 字段 | 值 |
|---|---|
| frames_read / frames_processed | 460 / 460 |
| detection_count | 960 |
| event_count | 22 |
| sorting_result_count | 8 |
| sorting_results_by_shape | triangle 3、rectangle 3、circle 2 |
| error | null |
| ended_reason | stopped |
| clean_shutdown | true |
| plc_enabled | false（合成且未显式给 `--plc-config`，按设计不写 PLC） |

分拣结果序列（`frame_index` 为该次分拣完成时的工作帧号）：

| item | 形状 | frame | 离开段 | 灯 |
|---|---|---|---|---|
| #1 | triangle | 63 | 第 1 段 | 1 |
| #2 | rectangle | 118 | 第 2 段 | 2 |
| #3 | circle | 173 | 第 3 段 | 3 |
| #4 | triangle | 225 | 第 1 段 | 1 |
| #5 | rectangle | 279 | 第 2 段 | 2 |
| #6 | circle | 333 | 第 3 段 | 3 |
| #7 | triangle | 385 | 第 1 段 | 1 |
| #8 | rectangle | 438 | 第 2 段 | 2 |

**截图审计**（`evidence/screenshots/sorting/2026-09-11-sorting-synthetic-proof.png`）

截图为运行 26 秒后的界面：`#8 矩形 离开 · 2 盏灯` 提示条出现在第 2 段上方，
第 2 段料框显示 2 个亮灯点且标注“示意中…”，第 1/3 段料框分别常亮 1/3 个灯点并标注“等待物料”；
一个圆形物料块正在第 3 段行进（即“不是三角形、也不是矩形 → 进入第 3 段”）；
右侧分拣日志按时间倒序列出 #8…#1；下方预览显示合成帧的三个物体与 `triangle 99.1%` 识别结果。

## 结论

- 三节传送带的判定与示意按操作者描述的规则工作：属于本段形状则在该段离开，否则进入下一段。
- 形状→灯映射与仓库既有编码一致：triangle=1 盏、rectangle=2 盏、circle=3 盏。
- 传送带不做二次识别，只是把视觉已给出的标签可视化；不能作为新的识别证据。
- PC 侧命令桥只在配置允许时启动，合成自检不会误写实验室 PLC。

## 证据位置

- 实现：`pc/sorting/`（`model.py`、`controller.py`、`worker.py`、`widget.py`、`window.py`、`app.py`）、`pc/config/sorting.json`
- 测试：`pc/tests/test_sorting_simulator.py`、`pc/tests/test_sorting_controller.py`
- 截图：`evidence/screenshots/sorting/2026-09-11-sorting-synthetic-proof.png`
- 数据：`evidence/data/sorting/2026-09-11-sorting-synthetic-proof.json`
- 运行手册：`docs/SORTING_LINE.md`

## 未执行 / 待补

1. **真实摄像头实时轮次**：用内置 HD Webcam + `--reuse-calibration` 举三类物体各一次，
   确认物料块在第 1/2/3 段离开并示意。待操作者举纸。
2. **真机 PLC 闭环**：`--plc-config pc/config/plc.json`，放三形状并按物理出队键，
   确认亮 1/2/3 盏；需要 session JSON 的 `plc_sent_count` 与人工目视/照片证据。待测试。
3. 2026-09-11 09:16 起，真机 PLC 对 DB3 的读访问返回 `class=0x81 code=0x04`
   （PUT/GET 未开放），在 TIA 重新勾选并下载前无法做真机写读；本轮 13 次命令写入全部报同一错误，
   **没有一条进入 PLC 队列**，实验室 FIFO 未被本次自检改动。
4. `plc_trigger=enter` 的多物体顺序行为只在单元测试里覆盖，未做真机验证。
