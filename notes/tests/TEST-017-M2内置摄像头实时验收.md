---
title: "TEST-017 M2 单目标实时验收（内置 HD Webcam）"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
  - M2
  - camera
result: pass
---

# TEST-017 M2 单目标实时验收（内置 HD Webcam）

- **Test ID**：TEST-017
- **对应 Requirement ID**：VISION-001、VISION-002、HW-003
- **日期**：2026-09-11
- **Git commit**：`f49e065`（本次运行基线；工作区含被 Git 忽略的 runtime 输出）

> [!warning] 证据边界
> 本记录是**新相机（内置 HD Webcam）**的 M2 实时验收。
> 旧 Insta360 的 `TEST-003` 保留为历史，**不**作为新相机的证据；两者不可混用。
> 本轮只覆盖单目标 + 空背景；多目标、光照、事件生命周期与 GUI 长跑见 TEST-018 / TEST-019。

## 测试目标

相机已从 Insta360 换成笔记本内置摄像头（MSMF / 1280×720 / YUY2）。按 M2 的正式流程重跑：
启动时复用运行时校准的 ROI，验证空背景不产生目标、三类单目标均正确识别，并保存可追溯证据。

## 环境

| 项目 | 实际记录 |
|---|---|
| 摄像头 | `HD Webcam`，VID `11134`（`0x2B7E`）、PID `46691`（`0xB663`） |
| OpenCV 后端 | MSMF（`backend_id=1400`） |
| 实际属性 | 1280×720，reported 30.0 fps，fourcc YUY2 |
| ROI | `manual / restored`，normalized `0.20/0.25/0.80/0.88`，像素 `[256,180,1024,634]` |
| 视觉配置 | `pc/config/vision.json`（**未修改任何阈值**） |
| 光照 | 室内顶灯 + 显示器侧光（未做受控照明） |

## 操作步骤

```powershell
.\.venv\Scripts\python.exe -m pc.vision live --camera-config pc/config/camera.json `
  --reuse-calibration --calibration-file output/m2/runtime-calibration.json `
  --evidence-dir output/m2/live-evidence-builtin
```

操作者在预览窗口中：不放物体按 `S`，分别举 triangle / rectangle / circle 各按一次 `S`，最后按 `Q` 退出。

## 预期结果

- 启动时复用已保存的运行时 ROI，不重新校准
- 空背景不产生目标；三类单目标分别输出 triangle / rectangle / circle
- session 正常结束、`failed_reads=0`、`error=null`

## 实际结果

**session 摘要**（`session-20260911-124125-591734.json`）

| 字段 | 值 |
|---|---|
| status | completed |
| 起止 | 12:41:25.591 → 12:46:28.003（302.110 s） |
| frames_processed | 9036 |
| measured_processing_fps | **30.011203** |
| failed_reads | 0 |
| error | null |
| evidence_frames_saved | 7 |
| runtime_roi | `manual / restored`，`0.20/0.25/0.80/0.88` |

**7 组证据逐条审计**（全部解码图片与 JSON 后核对）

| Runtime ID | 时间 | 真实输入 | predicted / stable | confidence | 顶点 | 面积占比 | solidity | circularity | Otsu | 显示 FPS | 轮廓筛选 | 结果 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 20260911-124254-331521 | 12:42:54 | background | no_object / no_object | 0.0000 | — | — | — | — | 135 | 30.24 | 否（符合预期） | PASS |
| 20260911-124301-551001 | 12:43:01 | background | no_object / no_object | 0.0000 | — | — | — | — | 137 | 30.15 | 否（符合预期） | PASS |
| 20260911-124332-941842 | 12:43:32 | background | no_object / no_object | 0.0000 | — | — | — | — | 146 | 30.27 | 否（符合预期） | PASS |
| 20260911-124345-055108 | 12:43:45 | triangle | triangle / triangle | 1.0000 | 3 | 0.1353 | 0.9846 | 0.5540 | 90 | 29.65 | 是 | PASS |
| 20260911-124356-013321 | 12:43:56 | background | no_object / no_object | 0.0000 | — | — | — | — | 98 | 30.26 | 否（符合预期） | PASS |
| 20260911-124407-054912 | 12:44:07 | rectangle | rectangle / rectangle | 0.9843 | 4 | 0.1712 | 0.9803 | 0.7225 | 84 | 29.21 | 是 | PASS |
| 20260911-124417-283076 | 12:44:17 | circle | circle / circle | 0.9797 | 8 | 0.1910 | 0.9962 | 0.9010 | 115 | 29.59 | 是 | PASS |

操作者实际按了 7 次 `S`（4 次空背景 + 3 类目标），**7/7 与真实输入一致**。

## Pass / Fail

**PASS**。新相机在 M2 正式实时流程下：复用运行时 ROI、空背景无误检、三类单目标识别全部正确、
session 30.01 FPS、0 读失败、正常结束。

## 工程结论与边界

- 换相机后**不需要改任何识别阈值**，只需重标 ROI（本次复用运行时校准 `0.20/0.25/0.80/0.88`）。
- 旧 Insta360 的 M2 结论（TEST-003）保留为历史，不作为新相机证据。
- 本轮未覆盖极端光照、遮挡、多目标、严重透视；这些属 TEST-018 / 系统测试范围。

## 证据位置

- 精选标注图：`evidence/screenshots/m2/live-builtin/M2-builtin-live-{background,triangle,rectangle,circle}.jpg`
- 会话与逐帧数据：`evidence/data/m2/live-builtin/`（session JSON + 4 份 evidence.json）
- 完整 runtime（Git ignored）：`output/m2/live-evidence-builtin/`
- 运行时校准（Git ignored）：`output/m2/runtime-calibration.json`
