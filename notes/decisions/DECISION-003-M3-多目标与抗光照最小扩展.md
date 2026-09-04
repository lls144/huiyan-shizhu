---
title: DECISION-003 M3 多目标与抗光照最小扩展
date: 2026-09-04
tags:
  - 慧眼识珠
  - decision
  - M3
status: proposed-pending-real-validation
---

# DECISION-003 M3 多目标与抗光照最小扩展

- **Decision ID**：DECISION-003
- **状态**：PROPOSED，等待真实光照证据决定最终预处理模式

## 选择

多目标识别不重写 M2：保留相同 ROI、二值图、`RETR_EXTERNAL`、轮廓筛选和 `approxPolyDP` 分类，对所有通过筛选的轮廓逐个分类并按中心从左到右输出。

抗光照只比较两种低复杂度方案：

1. M2 原始 Otsu。
2. CLAHE 灰度增强后继续使用同一 Otsu 和轮廓链路。

真实预览按 `1`～`5` 时对同一帧同时保存两种方案，避免用不同瞬间的画面做不公平对比。若真实结果没有显示 CLAHE 的收益，优先保留更简单的 Otsu。

## 明确不做

- 不加入物体 ID、跨帧跟踪、事件去重或入队逻辑；这些属于 M4。
- 不为遮挡或粘连无限优化；`RETR_EXTERNAL` 将接触区域视为一个外轮廓时，如实记录。
- 不用合成测试代替正常、较亮/侧光、较暗三种真实光照测试。
- 未经真实证据不把 VISION-003、VISION-004 或 M3 标记 `DONE`。

## 验证入口

- [[../tests/TEST-004-M3-多目标与抗光照验收]]
- [[../daily/2026-09-04-M3-最小实现与验收准备]]
