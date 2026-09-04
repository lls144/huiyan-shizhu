---
title: TEST-003 M2 实时摄像头与 ROI 验收
date: 2026-09-04
tags:
  - 慧眼识珠
  - test
  - M2
  - camera
result: pass
---

# TEST-003 M2 实时摄像头与 ROI 验收

- **Test ID**：TEST-003
- **对应 Requirement ID**：VISION-001、VISION-002
- **日期**：2026-09-04
- **Git commit**：真实测试工作区基于 `58507475b304748a81c3d4e0349f9d6536f01070`；实现归档于 `9f7ae794070a9d1cd853cc2893e71e742f25da52`，验收证据归档于 `d8f6f60b7801c7a8ff8d6d5d6bc809a3875069bb`

## 测试目标

验证实时入口复用 M1 的 Insta360 摄像头打开逻辑；启动时能通过 `auto -> manual -> fixed_normalized` 获得本次运行固定 ROI；在原机位和主动改变一次机位后，均能正确识别空背景及三类单目标，并保存可追溯证据。

## 证据审计

在修改本记录前，逐项读取 `output/m2/live-evidence/` 下 8 组单帧证据、2 个 session JSON 和 `output/m2/runtime-calibration.json`，并实际解码全部图片。

- 第一轮 4 组、第二轮 4 组证据均存在。
- 每组均包含非空的 `frame.jpg`、`roi.jpg`、`binary.png`、`canny.png`、`annotated.jpg` 和 `evidence.json`，JSON 中的 artifact 引用均可解析。
- 8 张 `annotated.jpg` 的画面内容经人工核对，真实输入依次为 background、triangle、rectangle、circle，均与 `predicted_class` 和 `stable_class` 一致。
- 第一轮四组证据均为 `roi_mode=manual`、`roi_source=selected`，并使用同一 ROI。
- 第二轮四组证据均为 `roi_mode=auto`、`roi_source=detected`；第二轮 session 记录 `auto_score=0.6772652070154296`，且没有复用旧 ROI。
- 两个 session 均为 `status=completed`、`failed_reads=0`、`error=null`。

> [!note] 第一轮 session 的完整校准历史
> 第一轮四次验收保存均发生在初始 manual ROI 锁定期间，使用像素 ROI `[512, 60, 1428, 720]`。四次保存之后、退出 session 之前，另有 3 次按 `R` 重新校准记录（两次 auto 成功、一次 auto 失败后 manual 成功）。这些后续操作不改变已保存四组验收证据的 ROI 来源；原始 session 历史保持不删改。

## 真实测试环境

| 项目 | 实际记录 |
|---|---|
| 摄像头 | Insta360 Ace Pro 2 USB Webcam，VID `2E1A`、PID `1003` |
| OpenCV 后端 | DirectShow（`DSHOW`） |
| 请求模式 | MJPG，1920×1080，30 fps |
| 实际分辨率 | 1920×1080 |
| 设备报告 FPS | 30.00003000003 |
| 相机配置 | `pc/config/camera.json` |
| 视觉配置 | `pc/config/vision.json` |
| 完整 runtime 证据 | `output/m2/live-evidence/`，Git ignored |
| 精选永久证据 | `evidence/screenshots/m2/live/`、`evidence/data/m2-live-acceptance-summary.json` |

## 第一轮：原机位，manual ROI

- session：`session-20260904-154927-634992.json`
- initial auto：未找到可接受中央白色凸四边形，按设计进入 manual。
- 验收 ROI：`manual / selected`。
- 像素 ROI：`[512, 60, 1428, 720]`。
- normalized ROI：`left=0.2666666667, top=0.0555555556, right=0.74375, bottom=0.6666666667`。
- session：606.130473 s；有效处理 475.073471 s；13087 帧；0 failed reads；处理 FPS 27.547318；保存 4 组。

| Runtime ID | 真实输入 | predicted / stable | confidence | 顶点 | 面积占比 | solidity | circularity | 通过轮廓筛选 | 显示 FPS | 结果 |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 20260904-155308-019724 | background | no_object / no_object | 0.000000 | — | — | — | — | 否（符合预期） | 29.962377 | PASS |
| 20260904-155331-109955 | triangle | triangle / triangle | 0.976873 | 3 | 0.043062 | 0.991016 | 0.558056 | 是 | 29.924228 | PASS |
| 20260904-155349-192425 | rectangle | rectangle / rectangle | 1.000000 | 4 | 0.102140 | 0.992765 | 0.659400 | 是 | 30.070258 | PASS |
| 20260904-155416-044725 | circle | circle / circle | 0.977744 | 8 | 0.073977 | 0.995670 | 0.899228 | 是 | 27.191580 | PASS |

本轮证明 manual 选择可完成并转为 normalized ROI；同一 ROI 在四次验收保存期间保持锁定，空背景不产生目标，三类目标均正确识别，`S` 可保存完整证据。

## 第二轮：改变相机高度/水平位置，auto ROI

- session：`session-20260904-155959-711034.json`
- 启动时未复用旧 ROI，重新执行 auto calibration。
- 验收 ROI：`auto / detected`，`auto_score=0.6772652070154296`。
- 像素 ROI：`[579, 33, 1426, 798]`。
- normalized ROI：`left=0.3015625, top=0.0305555556, right=0.7427083333, bottom=0.7388888889`。
- session：305.664036 s；有效处理 304.986836 s；8989 帧；0 failed reads；处理 FPS 29.473403；保存 4 组。

| Runtime ID | 真实输入 | predicted / stable | confidence | 顶点 | 面积占比 | solidity | circularity | 通过轮廓筛选 | 显示 FPS | 结果 |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 20260904-160150-046598 | background | no_object / no_object | 0.000000 | — | — | — | — | 否（符合预期） | 29.964816 | PASS |
| 20260904-160222-814113 | triangle | triangle / triangle | 0.914507 | 3 | 0.024352 | 0.984710 | 0.561299 | 是 | 27.165515 | PASS |
| 20260904-160247-336181 | rectangle | rectangle / rectangle | 1.000000 | 4 | 0.059911 | 0.990976 | 0.662528 | 是 | 28.050187 | PASS |
| 20260904-160257-383167 | circle | circle / circle | 0.951759 | 8 | 0.042316 | 0.994577 | 0.898881 | 是 | 27.135163 | PASS |

本轮证明相机重新架设后，可以不复用第一次 ROI 而重新 auto calibration；检测到的 ROI 虽未严格贴合白纸边缘，但足以隔离主要工作区，本轮空背景无误检且三类目标均正确。

## Pass / Fail

**PASS**。8/8 真实实时工况与预期一致；两个 session 无 failed frame 或运行异常。离线回归和完整 pytest 见本次最终回归记录。

## 最终回归

- 最终完整测试：`57 passed in 0.47s`。
- 10 张真实离线图片：10/10 与目录标签一致；background 1/1 为 `no_object`，circle 3/3、rectangle 3/3、triangle 3/3 均为对应类别。
- 依赖检查：`No broken requirements found.`。
- 最终回归没有为实时阶段修改阈值，也没有破坏离线结果。

## 工程结论与边界

最终 ROI 策略为：

```text
camera setup
  -> startup calibration
  -> ROI locked
  -> recognition
```

相机重新架设时重新 calibration，不逐帧动态追踪。auto 是便利功能，不要求精确贴合纸张边界，也不声称 100% 成功；只要能隔离主要工作区且不产生误检即可。失败回退为 `auto -> manual -> fixed_normalized`。第一轮验证了 manual fallback 的必要性，第二轮验证了改变机位后 auto 可成功工作。

本次未覆盖极端光照、遮挡、多目标、严重透视或复杂目标；真实样本仍只限于黑色简单几何图形。`confidence` 是几何规则符合度，不是概率。这些属于 M3 或后续系统测试范围，不阻碍 M2 单目标里程碑验收。

## 关联记录

- [[TEST-002-M2-离线单目标轮廓识别]]
- [[../decisions/DECISION-002-M2-启动时ROI校准]]
- [[../daily/2026-09-04-M2-最终真实验收]]
