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

## 离线观察与暂定结论

2026-09-04 的确定性合成验证中，normal、bright、dark、side-light 四个分离场景在 Otsu 与 CLAHE+Otsu 下都精确输出三类目标，CLAHE 未显示额外收益。因此真实摄像头验收前暂时保留 Otsu 为默认主链路，CLAHE+Otsu 继续作为同帧比较方案；最终选择仍由三种真实光照证据决定。

部分遮挡与接触场景在两种方案下都把相连黑色区域作为一个外轮廓，输出 `triangle + unknown`。该行为与 `RETR_EXTERNAL` 设计一致，记录为局限，不扩展分水岭或实例分割。

## 明确不做

- 不加入物体 ID、跨帧跟踪、事件去重或入队逻辑；这些属于 M4。
- 不为遮挡或粘连无限优化；`RETR_EXTERNAL` 将接触区域视为一个外轮廓时，如实记录。
- 不用合成测试代替正常、较亮/侧光、较暗三种真实光照测试。
- 未经真实证据不把 VISION-003、VISION-004 或 M3 标记 `DONE`。

## 验证入口

- [[../tests/TEST-004-M3-多目标与抗光照验收]]
- [[../daily/2026-09-04-M3-最小实现与验收准备]]
