---
title: "TEST-010 内置摄像头（HD Webcam）重新验收"
date: "2026-09-10"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-010 内置摄像头（HD Webcam）重新验收

- **Test ID**：TEST-010
- **对应 Requirement ID**：HW-001 / HW-002 / HW-003（摄像头平台）；VISION-001 的新相机复测
- **日期**：2026-09-10
- **Git commit**：`6324f64`（运行基线）

> [!warning] 证据边界
> 本测试证明：内置摄像头能稳定采集，且在新机位下三类形状的**单帧识别**正确。
> 它**不**等于 M2/M3 的正式重新验收：多目标、光照、遮挡、事件生命周期和 GUI 长跑仍是 Insta360 的结论，
> **不适用于**新相机。M1 已于本次在新相机上重跑通过。

## 背景

操作者把相机从 Insta360 Ace Pro 2 换成**笔记本内置摄像头**。旧配置（按名字选 Insta360、DSHOW/MJPG/1920×1080、
ROI `0.24/0.08/0.76/0.75`）对新相机全部失效：设备名匹配不到、分辨率被降级、ROI 落在人脸上。

## 环境

- 电脑：Windows 11（当前开发机）；Python 3.12.10；OpenCV 5.0.0
- 相机：`HD Webcam`，VID `11134`（`0x2B7E`）、PID `46691`（`0xB663`），MSMF，索引 0
- 光照：室内顶灯 + 显示器侧光（未做受控照明）

## 操作步骤

1. `python -m pc.camera --config pc/config/camera.json enumerate` 确认可见设备。
2. 探测后端与分辨率：DSHOW vs MSMF、1920×1080 vs 1280×720、MJPG vs YUY2。
3. 用自动 ROI 检测手持白纸的构图，据此重写 `pc/config/vision.json` 的归一化 ROI。
4. 依次举 triangle / rectangle / circle，连拍 12 帧并逐帧分析。
5. 跑正式 60 秒 M1 稳定采集验收（含 3 次重开）。

## 预期结果

- 采集：读成功率 ≥ 99%、最大帧间隔 ≤ 2 s、实际分辨率与请求一致、3 次重开全部成功
- 识别：三个形状分别输出 triangle / rectangle / circle

## 实际结果

采集后端对比（同一机位，1280×720，请求 30 fps）：

| 后端 | 实测帧率 |
|---|---|
| DSHOW | **10.07 fps** |
| MSMF | **30.00 fps** |

M1 正式验收（`.\.venv\Scripts\python.exe -m pc.camera --config pc/config/camera.json stability`）：

- 1800/1800 帧成功，`success_rate=1.0`，实测 **29.99 fps**，最大成功帧间隔 **0.084 s**
- 3 次重开全部成功（每次约 13.9 s）
- 实际 `1280×720 @30`，与请求一致；`criteria` 四项全 True，`passed=true`

识别（新机位 ROI `0.20/0.25/0.80/0.88`，**未修改任何阈值**）：

| 形状 | 结果 | 说明 |
|---|---|---|
| triangle | 1/1 帧 → `triangle`，confidence 1.0 | 顶点 3、solidity 0.982、area_ratio 0.100 |
| rectangle | 12/12 帧 → `rectangle`，confidence 0.96–1.0 | Otsu 76–77 |
| circle | 12/12 帧 → `circle`，confidence 0.97–0.98 | Otsu 79–81 |

一次 12 帧连拍里 `total_external_contours` 从 1 变到 3（圆那组 t=3s/9–11s），
额外轮廓都被面积/实心度条件刷掉，未造成误检。

## ROI 的处理（为什么没有改 `pc/config/vision.json`）

最初把新 ROI 直接写进 `pc/config/vision.json`，结果 **8 个测试失败**：合成夹具与已提交的
`test_data/m3/synthetic/` 数据集（带 SHA-256）都是按旧 ROI 生成的，改动 shipped 配置等于改动了这些夹具的隐含输入。
按 [DECISION-002](../../notes/decisions/DECISION-002-M2-启动时ROI校准.md) 的设计，"相机重新架设后重新校准"
本来就属于**运行时校准**，默认配置只作为最终 fallback。因此：

- `pc/config/vision.json` 保持原值未改；
- 新机位 ROI 通过 `save_runtime_calibration` 存到被 Git 忽略的 `output/m2/runtime-calibration.json`
  （`normalized_roi = {left:0.20, top:0.25, right:0.80, bottom:0.88}`，像素 `(256,180,1024,634)`）；
- 复现本次识别结果时用该 ROI（GUI/实时命令加 `--reuse-calibration`，或按 `--roi-mode manual` 现场框选）。

配置与合成夹具的这层耦合已登记为 `notes/issues/ISSUE-003`。

## 结论

- 内置摄像头在 MSMF 下能稳定 30 fps 采集，M1 在新相机上重新通过。
- 新机位只需重标 ROI，**现有识别阈值不需要改**；三类形状单帧识别全部正确。
- 旧 Insta360 的 M1–M5 证据保留为历史，不能用于新相机。

## 证据位置

- 采集数据：`test_data/m1/2026-09-10-builtin-msmf-stability.json`
- 代表帧：`evidence/screenshots/M1-builtin-720p-sample.jpg`
- 识别帧：`evidence/screenshots/m2/live/M2-live-round3-builtin-triangle.png`、
  `M2-live-round3-builtin-rectangle-burst.png`、`M2-live-round3-builtin-circle-burst.png`
- 运行时校准（git-ignored）：`output/m2/runtime-calibration.json`

## 未执行 / 待补

- M2 的正式实时轮次（含 runtime session 与逐工况记录）、M3 多目标与光照、M4 事件生命周期、M5 GUI 长跑
  均未在新相机上重跑。
- 受控光照与 A3 背景板材质仍未单独测量。
- `docs/ROADMAP.md` / `PROJECT_SPEC.md` / `REPORT_EVIDENCE.md` / `README.md` / 根 `AGENTS.md`
  的摄像头描述仍写 Insta360，待负责人确认后统一更新。
