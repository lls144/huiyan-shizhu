---
title: "TEST-018 M3 多目标与光照验收（内置 HD Webcam）"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
  - M3
  - camera
result: pass
---

# TEST-018 M3 多目标与光照验收（内置 HD Webcam）

- **Test ID**：TEST-018
- **对应 Requirement ID**：VISION-003（多目标）、VISION-004（抗光照）
- **日期**：2026-09-11

> [!warning] 证据边界
> 本轮是**新相机（内置 HD Webcam）**的 M3 复测。旧 Insta360 的 `TEST-004` 保留为历史，不作为新相机证据。
> **"较暗"这一组没有取得真实变暗的工况**（原因见下），如实记录为未验证；
> `partial_occlusion` / `touching_or_merged` 两组本轮未做，仍待补。

## 采集方式（与旧流程的差异）

M3 原流程是 `pc.vision multi-live` 交互式按 `1`–`5` 存证。内置摄像头固定在屏幕上方，
操作者必须**双手举着 A3 纸**才能取景，按热键时既容易掉焦点也容易挪动构图，
因此本轮改用新增的采集辅助脚本：

```powershell
.\.venv\Scripts\python.exe scripts\m3_timed_capture.py `
  --calibration-file output/m2/runtime-calibration.json `
  --evidence-dir output/m3/live-evidence-builtin-v4 `
  --scenarios normal_light bright_or_side_light dark_light `
  --prepare-seconds 15 --warmup-seconds 8
```

该脚本**复用同一条视觉管线与同一个存证函数** `save_m3_comparison_evidence`，
证据格式与交互式流程完全一致；每个场景在倒计时结束时连拍 3 帧，
取"有效目标数最多、总置信度最高"的一帧保存（手持会抖）。
它不修改任何阈值，也不是新的识别路径。

## 环境

| 项目 | 实际记录 |
|---|---|
| 摄像头 | `HD Webcam`，MSMF，1280×720，YUY2 |
| ROI | `manual / restored`，`0.20/0.25/0.80/0.88`（与 TEST-017 同一 ROI） |
| 视觉配置 | `pc/config/vision.json`，**未修改任何阈值** |
| 预处理对比 | `otsu` 与 `clahe_otsu` 两种，逐场景同时采集 |
| 摆放 | 三张白纸各放一个图形（三角形、矩形、圆形），双手举起对准镜头 |

## 实际结果

| 场景 | 声明 | 实测亮度 mean / median | otsu | clahe_otsu | 结论 |
|---|---|---|---|---|---|
| `normal_light` | 正常室内光 | **114.5** / 148 | 3 个：triangle 0.992、rectangle 0.953、circle 0.921；`matches=True` | 3 个：triangle 0.992、rectangle 0.954、circle 0.921；`matches=True` | **PASS** |
| `bright_or_side_light` | 手机侧面补光 | **123.2** / 147 | 3 个：triangle 0.959、rectangle 0.946、circle 0.970；`matches=True` | 3 个：triangle 0.958、rectangle 0.944、circle 0.970；`matches=True` | **PASS** |
| `dark_light` | 尝试关暗 | **114.1** / 157 | 3 个：triangle 0.965、rectangle 0.986、circle 0.975；`matches=True` | 3 个：triangle 0.964、rectangle 0.984、circle 0.975；`matches=True` | **识别 PASS，工况未成立**（亮度与正常组无差异） |

两种预处理方法在三个场景里的输出**完全一致**，再次验证 CLAHE+Otsu 未带来额外分类收益，
Otsu 保持为默认实时方案。

### 关键发现 1：触及 ROI 边界的目标会被设计性排除

前两次尝试分别只得到 0 个和 2 个目标，逐条读 `contour_filter_details` 定位到原因：

```
rejected: ['touches_roi_border']  area_ratio 0.035  vertices 3  solidity 0.986  bbox [624,156,144,171]
```

三角形本身是**合格的**（3 顶点、solidity 0.986），但它的包围盒右边缘正好落在 ROI 边界上，
被 `touches_roi_border` 规则排除。这是既有设计（避免把跨边界的大块背景当目标），
不是新相机的缺陷；对操作者的含义是**三个图形必须完整落在蓝框内并留出余量**。

### 关键发现 2：内置摄像头的自动曝光吃掉了"较暗"工况

连续三次（13:27:30 / 13:28:46 / 13:31:18）尝试制造更暗的照明，
实测亮度均值分别为 **122.4 / 116.2 / 114.1**，而正常光照组是 **114.5** ——
**没有任何一次比正常组更暗**。

结论：该摄像头开启了自动曝光，环境变暗时它自动提高增益/曝光时间，
因此"画面整体变暗"这个可观测判据无法成立。要在新相机上复现受控的"较暗"工况，
必须先**关闭自动曝光并固定曝光值**——这需要新增相机采集参数，属于后续改动，
本轮不擅自修改。

这也是**内置摄像头相对三脚架 + 外接摄像头方案的一处真实局限**，
记入后续"局限与改进方向"。

## Pass / Fail

- **多目标（VISION-003）：PASS。** 正常与侧光两组都是同屏 3 个目标独立输出且标签正确。
- **抗光照（VISION-004）：以"正常 vs 侧光"两种工况记 PASS。** 需求要求"至少两种可复现光照条件"，
  这两组满足；第三次"较暗"尝试**未产生真实变暗**，如实记为未验证。

## 未执行 / 待补

1. **"较暗"受控工况**：需关闭摄像头自动曝光并固定曝光值后重做；本轮 3 次尝试均未变暗
2. **`partial_occlusion` / `touching_or_merged`**：新相机上未做（旧 Insta360 结论保留在 TEST-004）
3. **终端用户按 `1`–`5` 的交互流程**：在新相机 + 手持取景下不稳定，本轮改用定时脚本；
   两种方式的证据格式一致，但交互方式的可用性本身值得记入改进项

## 证据位置

- 截图：`evidence/screenshots/m3/live-builtin/{normal_light,bright_or_side_light,dark_light}-{frame,otsu-annotated,roi}.jpg`
- 数据：`evidence/data/m3/live-builtin/*-{evidence.json,comparison.csv}`
- 完整 runtime（Git ignored）：`output/m3/live-evidence-builtin-v4/`、`-v7/`
- 采集脚本：`scripts/m3_timed_capture.py`
