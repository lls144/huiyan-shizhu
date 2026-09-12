---
title: "TEST-019 M4 事件生命周期与 M5 GUI 长跑（内置 HD Webcam）"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
  - M4
  - M5
  - camera
result: pass
---

# TEST-019 M4 事件生命周期与 M5 GUI 长跑（内置 HD Webcam）

- **Test ID**：TEST-019
- **对应 Requirement ID**：PLC-002 的 PC 端子能力（M4）、GUI-001（M5）
- **日期**：2026-09-11

> [!warning] 证据边界
> 新相机复测。旧 Insta360 的 `TEST-005` / `TEST-006` 保留为历史，不作为新相机证据。
> 离线 detection-sequence 的 12 个 M4 场景不受相机影响，仍然有效。
> M5 分两次跑：一次 600 s **空场**长跑（性能与生命周期），一次 75 s **带三类目标**短跑
> （识别信息与界面同步）。

## M4 事件生命周期（新相机）

来源：`multi-live --events` 真实会话 `output/m3/live-evidence-builtin-v3/session-20260911-131749-649474.json`
（该会话的 M3 存证因构图无效被弃用，但事件跟踪本身有效，且事件里能看到高置信度识别）。

| 字段 | 值 |
|---|---|
| frames_processed | 3965 |
| failed_reads | 0 |
| status / error | completed / null |
| 事件总数 | 66（`OBJECT_ENTER` 33、`OBJECT_EXIT` 33） |
| event_id 范围 | 1 → 66，连续 |
| 目标数（object_id） | 33 |
| **一个目标出现多次 ENTER 的个数** | **0** |
| 事件序列不是 `ENTER[,EXIT]` 的个数 | **0** |
| 标签分布 | rectangle 30、circle 16、triangle 10、unknown 10 |
| 事件配置 | `min_confirm_frames=2`、`max_missing_frames=3`、`iou 0.3`、`center 80 px` |

**结论**：新相机下 33 个目标全部满足"至多一次 ENTER、至多一次 EXIT"，
没有出现重复入队事件（这是 M4 的核心判据）。`unknown` 的出现与遮挡/合并轮廓的既有局限一致。

## M5 GUI 长跑（新相机）

```powershell
.\.venv\Scripts\python.exe -m pc.gui --source camera `
  --plc-config output/tmp/plc-disabled.json `
  --calibration-file output/m2/runtime-calibration.json --reuse-calibration `
  --soak-seconds 600 --summary-json output/m5/live-builtin/session.json `
  --screenshot output/m5/live-builtin/running.png
```

（本轮用禁用 PLC 的临时配置跑，避免长跑期间向实验箱灌命令。）

| 指标 | 实测 | 软件目标 | 结果 |
|---|---|---|---|
| 时长 | 600.294 s | — | — |
| frames_read / frames_processed | 17549 / 17549 | — | 一致 |
| failed_reads | 0 | 0 | PASS |
| processing_fps | **29.234** | ≥ 20 | PASS |
| gui_update_fps | **29.234** | ≥ 15 | PASS |
| average_processing_ms | 5.723 | — | — |
| p95_processing_ms | 6.915 | — | — |
| display_frames_dropped | 0 | 0 | PASS |
| buffer_overwrites | 0 | 0 | PASS |
| ended_reason / clean_shutdown | stopped / true | — | PASS |
| error | null | — | PASS |
| detection_count / event_count | 0 / 0 | — | 见待补项 |
| ROI | `manual / restored`，`[256,180,1024,634]` | — | 与 M2/M3 同一 ROI |

结束截图 `evidence/screenshots/m5/live-builtin/m5-builtin-running.png` 显示：
实时画面、`29.2 FPS`、`6.57 ms`、`FRAME 17548`、`ROI MANUAL`、`OTSU`、`No errors`，停止后回到 Idle。

**结论**：新相机下 GUI 连续 10 分钟处理与界面更新同为 29.234 FPS、零丢帧、零缓冲覆盖、
正常停止，性能与生命周期指标满足 GUI-001 的软件目标。

### 补充：75 秒带目标的短跑（识别信息与界面同步）

同命令，`--soak-seconds 75`，操作者在整个过程中举着三个图形保持在画面内：

| 指标 | 实测 |
|---|---|
| 时长 | 75.275 s |
| frames_read / frames_processed | 1790 / 1790 |
| failed_reads | 0 |
| detection_count | **3720** |
| event_count | **29**（OBJECT_ENTER 16、OBJECT_EXIT 13） |
| 目标数 / 重复 ENTER 的目标数 | 16 / **0** |
| 事件标签分布 | triangle 11、rectangle 7、circle 5、unknown 6 |
| processing_fps | 23.779 |
| gui_update_fps | **23.779（与处理完全同步）** |
| average / p95 processing_ms | 4.515 / 5.782 |
| display_frames_dropped / buffer_overwrites | 0 / 0 |
| ended_reason / clean_shutdown / error | stopped / true / null |

> 关于 23.779 FPS：该值按整个进程时长计算，其中包含约 13 秒的相机打开时间；
> 按实际采集窗口（约 62 s）折算约 **28.9 FPS**，与空场长跑的 29.234 FPS 一致。
> 两个数字都如实列出，不挑选好看的。

结束截图 `evidence/screenshots/m5/live-builtin/m5-builtin-with-targets.png` 显示：
画面同时标注 `#15 TRIANGLE 95.3%`、`#14 RECTANGLE 98.7%`、`#18 CIRCLE 95.8%`；
右侧 `DETECTIONS` 三行、`TRACKED OBJECTS` 三个目标均为 `CONFIRMED`、`EVENTS` 区按时间倒序列出
ENTER/EXIT；状态栏 `CAMERA · 23.9 FPS · 4.93 ms · FRAME 1789 · ROI MANUAL · OTSU`。
**这一张同时证明了画面、类别、置信度、目标状态与事件在同一界面上同步显示。**

会话里 16 个 ENTER 对 13 个 EXIT：结束时仍有 3 个目标在画面内，其 EXIT 尚未产生，符合设计。

## 未执行 / 待补

1. ~~**M5 带目标的运行**~~ ✅ 已完成：75 s 短跑，`detection_count=3720`、`event_count=29`、
   处理与界面更新同为 23.779 FPS，截图见上
2. **M4 短暂遮挡保持 ID**：新相机未单独做；旧 Insta360 结论保留在 TEST-005
3. **M5 长时间稳定性**：本轮 600 s；旧 Insta360 为 1577 s，若报告需要更长时长可再跑

## 证据位置

- M4 会话：`output/m3/live-evidence-builtin-v3/session-20260911-131749-649474.json`（Git ignored）
- M5 数据：`evidence/data/m5/live-builtin/session.json`
- M5 带目标数据：`evidence/data/m5/live-builtin/session-with-targets.json`
- M5 截图：`evidence/screenshots/m5/live-builtin/m5-builtin-running.png`（空场长跑）、
  `evidence/screenshots/m5/live-builtin/m5-builtin-with-targets.png`（带目标短跑）
- 相关记录：`TEST-017`（M2）、`TEST-018`（M3）
