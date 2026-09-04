---
title: TEST-004 M3 多目标与抗光照验收
date: 2026-09-04
tags:
  - 慧眼识珠
  - test
  - M3
  - camera
result: pending
---

# TEST-004 M3 多目标与抗光照验收

- **Test ID**：TEST-004
- **对应 Requirement ID**：VISION-003、VISION-004
- **Git commit**：软件与自动化测试 `8815e44335bf3287af37ad2dafd5269cdf998545`；后续真实运行的准确 HEAD 与 dirty 状态由 session JSON 自动记录
- **结果**：PENDING，尚无真实 M3 摄像头运行

## 测试目标

以最少操作验证同屏多个独立目标，以及 Otsu 与 CLAHE+Otsu 在三种真实光照下的同帧结果；额外记录部分遮挡和目标接触/粘连，不要求后两者必须完全识别。

## 启动命令

```powershell
.\.venv\Scripts\python.exe -m pc.vision `
  --config pc/config/vision.json `
  multi-live `
  --camera-config pc/config/camera.json `
  --roi-mode auto `
  --expected-labels triangle rectangle circle
```

## 操作步骤

1. 固定相机和白色工作区，启动后完成 auto 或 manual ROI 校准。
2. 将 triangle、rectangle、circle 三个目标彼此分开放入 ROI；确认画面分别标注后，在正常光照按 `1`。
3. 保持目标位置，增加亮度或形成可重复侧光，按 `2`。
4. 保持目标位置，降低环境亮度，按 `3`。
5. 恢复正常光照，使一个目标被部分遮挡，按 `4`。
6. 让两个目标边缘接触或产生粘连，按 `5`。
7. 可按 `T` 切换屏幕显示，但每个数字键都会自动保存两种方案对同一帧的结果。
8. 按 `Q` 或 Esc 退出；保留控制台输出和完整 session JSON。

> [!warning] 真值与场景声明
> `--expected-labels` 和数字键场景来自操作者声明，不是算法自动获得的真值。验收时必须查看 `frame.jpg` 和两张 annotated 图确认实际摆放与光照，不能只读取 `matches_expected_labels`。

## 预期及判定

| 场景 | 最小验收要求 | 当前结果 |
|---|---|---|
| 正常光照、三个目标分离 | 至少 2 个目标分别输出；优先要求三类全部输出 | 待测试 |
| 较亮/侧光 | 两种方案对同一帧均有完整记录 | 待测试 |
| 较暗 | 两种方案对同一帧均有完整记录 | 待测试 |
| 部分遮挡 | 记录真实输出、几何特征和失败情况 | 待测试 |
| 接触/粘连 | 记录真实输出；合并为一个轮廓可作为已知局限 | 待测试 |

VISION-003 只有在真实分离多目标画面中至少两个目标被独立输出后才能 PASS。VISION-004 只有三种真实光照均有同帧双方案证据并形成选择结论后才能 PASS。遮挡/粘连失败本身不阻碍 M3，但必须保留并分析。

## 输出

- 完整 runtime：`output/m3/live-evidence/`，Git ignored。
- 每个场景：原帧、ROI、两种 normalized gray、binary、Canny、annotated、`evidence.json`、`comparison.csv`。
- 运行级 session：设备、ROI、处理帧数、failed reads、FPS、保存记录和异常。

## 自动化前置结果

- 最新完整 pytest：`67 passed in 0.61s`。
- M2 真实离线数据回归：10/10 与标签一致。
- `pip check`：`No broken requirements found.`。
- 合成三目标图验证 triangle、rectangle、circle 分别输出并按中心从左到右排序。
- Otsu 与 CLAHE+Otsu 均通过暗灰合成背景测试。
- 接触目标测试只要求不虚假拆分。
- 证据测试确认同帧双方案 JSON/CSV 和图片齐全，且状态固定为 `pending_user_validation`。
- 这些结果不能替代真实摄像头验收。

## 关联记录

- [[../decisions/DECISION-003-M3-多目标与抗光照最小扩展]]
- [[../daily/2026-09-04-M3-最小实现与验收准备]]
