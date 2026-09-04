---
title: DECISION-002 M2 启动时 ROI 校准
date: 2026-09-04
tags:
  - 慧眼识珠
  - decision
  - M2
  - ROI
status: accepted
---

# DECISION-002 M2 启动时 ROI 校准

- **Decision ID**：DECISION-002
- **日期**：2026-09-04
- **状态**：ACCEPTED（2026-09-04 两轮真实摄像头验收通过）

## 背景

Insta360 Ace Pro 2 每次重新架设时，高度、水平位置和视角可能变化；单次运行期间相机保持固定。只使用第一次拍摄得到的 fixed normalized ROI 无法证明重新架设后的适用性，而逐帧更新 ROI 会造成面积、边界距离和 confidence 抖动。

## 最终选择

采用“一次校准、运行锁定”模型，启动优先级为 `auto -> manual -> fixed_normalized`。按 `R` 时明确暂停识别并重新执行校准；除此之外不更新 ROI。

- auto：从高亮度、低饱和度的大型中央凸四边形中定位白色工作区，向内缩小 margin。
- manual：通过 OpenCV `selectROI` 鼠标框选，并保存 normalized runtime calibration。
- fixed_normalized：保留 `(0.24, 0.08) - (0.76, 0.75)` 作为最终 fallback。

runtime calibration 和实时证据保存在被 Git 忽略的 `output/m2/`，不修改默认 `vision.json`。

最终运行流程为：

```text
camera setup
  -> startup calibration
  -> ROI locked
  -> recognition
```

相机重新架设时重新 calibration。auto ROI 是便利功能，不要求精确贴合纸张边缘；只要足以隔离主要工作区且不造成误检即可。它不是背景板语义分割，也不承诺 100% 成功。

## 失败与回退原则

auto 找不到可信候选时必须输出原因并进入 manual；manual 取消或过小必须输出原因后才可进入 fixed。显式 `--reuse-calibration` 才允许复用旧 normalized ROI，相机重新架设后应重新校准。

## 透视处理

当前不加入 perspective transform。已有离线证据未显示分类必须依赖透视矫正；若 [[../tests/TEST-003-M2-实时摄像头与ROI验收]] 出现圆明显椭圆化、矩形严重变形或分类不稳，再依据真实帧评估。

## 代价和局限

- auto 在旧 10 张图片的只读预检中只接受 7 张，其余 3 张明确失败，因此 manual 是必要路径。
- 轴对齐 ROI 不能严格贴合强旋转的背景板。
- fixed fallback 仍可能不适合重新架设后的机位，使用时必须观察 ROI 边框。
- 本机制不包含多目标、跟踪、物体 ID、入队或防重复识别。

## 真实验证

- 第一轮原机位：auto 未找到可接受区域，按设计进入 manual；`manual / selected` ROI 锁定后，background、triangle、rectangle、circle 四项全部正确。这验证了 manual fallback 的必要性。
- 第二轮改变相机高度/水平位置：未复用旧 ROI，auto 重新检测并接受 `score=0.6772652070154296` 的 ROI；四项输入再次全部正确。这验证了方案不依赖第一次拍摄的固定像素位置。
- 两个 session 均 `failed_reads=0`、`error=null`。详见 [[../tests/TEST-003-M2-实时摄像头与ROI验收]]。

真实样本数量仍有限，目标仅为黑色简单几何图形；极端光照、遮挡、多目标和严重透视尚未覆盖，属于 M3 或后续系统测试范围。

## 关联记录

- [[../tests/TEST-003-M2-实时摄像头与ROI验收]]
- [[../daily/2026-09-04-M2-实时集成准备]]
- [[../daily/2026-09-04-M2-最终真实验收]]
