---
title: TEST-005 M4 事件去重离线验收
date: 2026-09-04
tags:
  - 慧眼识珠
  - test
  - M4
result: offline-pass-live-pending
---

# TEST-005 M4 事件去重离线验收

- **Test ID**：TEST-005
- **对应 Requirement ID**：PLC-002 的 PC 端事件生成前置子能力
- **实现 commit**：`7d83c57`
- **测试 commit**：离线场景 `bdaca0b`；live 证据结构 `506fad2`
- **证据 commit**：`46bb2a6`
- **环境**：Windows 11、Python 3.12.10；核心状态测试不使用墙钟等待
- **结果**：离线 detection-sequence 12/12 PASS；真实摄像头生命周期 PENDING

## 配置

- `min_confirm_frames=2`
- `max_missing_frames=3`
- `iou_threshold=0.30`
- `center_distance_threshold=80.0 px`

## 实际结果

| 场景 | 预期 | 实际 | 结果 |
|---|---|---|---|
| persistent object | 一个 ENTER，无重复 | F1 `ENTER #1 circle` | PASS |
| single-frame noise | 不产生事件 | 无事件 | PASS |
| short dropout | 同一 ID、无第二次 ENTER | 仅 F1 `ENTER #1` | PASS |
| true removal | 一个 ENTER、一个 EXIT | F1 ENTER；F5 EXIT | PASS |
| re-entry | #1 EXIT 后 #2 ENTER | F1 ENTER #1；F5 EXIT #1；F7 ENTER #2 | PASS |
| multi-class | triangle、circle 分别 ENTER | 两个独立 ID/ENTER | PASS |
| three objects | 三类分别 ENTER | #1 triangle、#2 rectangle、#3 circle | PASS |
| same-label objects | 两个 circle 两个 ID | #1 与 #2 分离 | PASS |
| small movement | ID 不变 | 仅一次 ENTER #1 | PASS |
| confidence variation | 不因置信度波动重建 | 仅一次 ENTER #1 | PASS |
| detection order change | ID 不因列表顺序改变 | triangle #1、circle #2 保持 | PASS |
| clear all | 三个对象分别且仅 EXIT 一次 | F5 三个 EXIT | PASS |

所有期望与逐帧 object states、actual events、confidence 和 frame index 均位于结构化 JSON；CSV 为事件摘要。输入明确标为 `offline_simulated_detection_sequence`。

## M3 → M4 集成

测试 `test_m3_synthetic_detections_feed_m4_without_classifier_changes` 实际读取 M3 `multi_normal.png`，获得 triangle、rectangle、circle 三个 detections，连续输入两帧：第一帧无事件，第二帧产生三个独立 ENTER。该测试直接复用 M3 pipeline，没有复制 classifier。

## 性能

300 帧、每帧 3 个 detection，共 900 detections；状态管理实测 `4.294 ms`，产生 3 个 ENTER。该值不含图像处理和文件 I/O，仅证明 M4 状态层不是当前视觉链路瓶颈。

## 回归

- 完整 pytest：`95 passed in 1.52s`。
- M2 十张真实离线图片：`10/10`。
- M3 synthetic：normal、bright、dark、side-light 在两种方案下仍全部精确识别三类；遮挡/接触局限未改写。
- `pip check`：`No broken requirements found.`。

## 证据

- 输入：`../../test_data/m4/detection-sequences.json`
- JSON：`../../evidence/data/m4/m4-offline-event-results.json`
- CSV：`../../evidence/data/m4/m4-offline-event-results.csv`

> [!warning] 验收边界
> 本记录的 PASS 只代表离线模拟和 synthetic 接口集成。`multi-live --events` 尚未真实运行；按本轮用户要求，M4 milestone 保持 `DOING`。

## 关联记录

- [[../decisions/DECISION-004-M4-确定性关联与事件状态机]]
- [[../daily/2026-09-04-M4-离线事件去重验证]]
