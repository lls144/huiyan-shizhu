---
title: "ISSUE-003 vision.json 的 ROI 与合成夹具耦合"
date: "2026-09-10"
tags:
  - 慧眼识珠
  - issue
status: open
---

# ISSUE-003 vision.json 的 ROI 与合成夹具耦合

- **Issue ID**：ISSUE-003
- **创建日期**：2026-09-10
- **状态**：OPEN
- **所属模块**：PC 视觉配置 / 测试夹具

## 问题现象

把 `pc/config/vision.json` 的归一化 ROI 从 `0.24/0.08/0.76/0.75` 改为新相机机位的
`0.20/0.25/0.80/0.88` 后，**8 个测试失败**（`test_vision_preprocess`、`test_vision_live`、
`test_m3_synthetic`、`test_event_tracker`、`test_gui_overlay`、`test_gui_window` 两项等），
表现都是"检测到的目标从 3 个变成 0 个"。

## 复现步骤

1. 修改 `pc/config/vision.json` 的 `roi_*`。
2. `.\.venv\Scripts\python.exe -m pytest -q`。

## 预期结果

修改"当前相机机位"的 ROI 不应影响与机位无关的合成测试。

## 实际结果

合成夹具与已提交的 `test_data/m3/synthetic/` 数据集（`test_m3_synthetic` 校验其 SHA-256）都是
按旧 ROI 覆盖区域生成/放置目标的；多个测试直接 `load_vision_config(REPO_ROOT / "pc/config/vision.json")`
加载 shipped 配置，因此 ROI 一改，目标就落到裁剪窗口之外。

## 影响

- 换相机或调机位时无法直接更新默认配置，只能走运行时校准（这本身符合 DECISION-002，但**测试与配置的耦合没有被记录**）。
- 合成数据集哈希绑定旧 ROI，任何 ROI 变更都会同时影响 M3 的合成证据，容易被误判成"识别回归"。

## 初步假设

- 合成夹具把"工作区"隐含定义成 shipped ROI，而不是显式的夹具参数。

## 尝试方案

1. 本次按 DECISION-002 走运行时校准（`output/m2/runtime-calibration.json`，git-ignored），
   不改 `pc/config/vision.json`，测试恢复 200 passed / 1 skipped。见 TEST-010。

## 失败方案

- 直接改 `pc/config/vision.json`：破坏 8 个测试，并让已提交的 M3 合成数据集与配置脱钩。
- 重新生成 M3 合成数据集：会作废现有 M3 合成证据与哈希，代价远超本次需求。

## 根因

待确认（推测：合成夹具与 shipped 配置共用一个 ROI，缺少显式的夹具级配置）。

## 最终解决方案

待解决。可选方向：给合成夹具/测试使用独立的测试配置（或在测试里用 `dataclasses.replace` 固定夹具 ROI），
让 shipped `vision.json` 只代表"当前默认机位"。改动前需评估对 M3 合成证据与哈希的影响。

## 修改 commit

待填写。

## 验证结果

待测试。

## 是否可以写入实验报告的问题分析章节

- [x] 是
- [ ] 否
- 理由：可作为"配置与测试夹具耦合导致换硬件成本被低估"的真实案例；结论须在方案落地后重写。
