---
title: TEST-004 M3 多目标与抗光照验收
date: 2026-09-04
tags:
  - 慧眼识珠
  - test
  - M3
  - camera
result: offline-synthetic-pass-live-pending
---

# TEST-004 M3 多目标与抗光照验收

- **Test ID**：TEST-004
- **对应 Requirement ID**：VISION-003、VISION-004
- **Git commit**：多目标基础 `8815e443`；合成数据集 `935e637`；离线 runner `32c06ba`；离线证据 `445f0b2`；后续真实运行的准确 HEAD 与 dirty 状态由 session JSON 自动记录
- **结果**：离线 synthetic 验证 PASS；真实 M3 摄像头验收 PENDING

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

## 离线 synthetic 实际结果

2026-09-04 使用固定生成器参数运行 6 个场景、2 种方案。分离目标场景要求精确匹配；遮挡/接触只记录观察，不强制通过。

| 场景 | 期望 | Otsu | CLAHE+Otsu | 结论 |
|---|---|---|---|---|
| normal | 3：triangle、rectangle、circle | 3，三类正确 | 3，三类正确 | PASS（synthetic） |
| bright | 3：triangle、rectangle、circle | 3，三类正确 | 3，三类正确 | PASS（synthetic） |
| dark | 3：triangle、rectangle、circle | 3，三类正确 | 3，三类正确 | PASS（synthetic） |
| side_light | 3：triangle、rectangle、circle | 3，三类正确 | 3，三类正确 | PASS（synthetic） |
| partial_occlusion | 物理目标 3 | 2：triangle、unknown | 2：triangle、unknown | 已记录合并轮廓局限 |
| touching | 物理目标 3 | 2：triangle、unknown | 2：triangle、unknown | 已记录合并轮廓局限 |

版本化原始结果位于 `../../evidence/data/m3/m3-offline-synthetic-results.json` 和 `.csv`；其中包含每个目标的 confidence、bbox、area ratio、solidity、circularity、处理耗时、真值匹配和环境。12 张两方案标注图位于 `../../evidence/screenshots/m3/synthetic/`。

## 自动化与回归结果

- 最新完整 pytest：`72 passed in 1.40s`。
- M2 真实离线数据回归：10/10 与标签一致。
- `pip check`：`No broken requirements found.`。
- 数据集测试确认 6 张图片、尺寸、确定性和 ground truth 字段完整。
- 离线 runner 测试确认双方案结构一致、JSON 可序列化、CSV 字段完整。
- 正常合成三目标图验证 triangle、rectangle、circle 分别输出并按中心从左到右排序。
- 接触/遮挡结果只记录观察，不把合并轮廓虚假拆分成多个对象。
- 这些 PASS 只代表软件与 synthetic 离线验证，不能替代真实摄像头验收。

## 关联记录

- [[../decisions/DECISION-003-M3-多目标与抗光照最小扩展]]
- [[../daily/2026-09-04-M3-最小实现与验收准备]]
- [[../daily/2026-09-04-M3-离线合成验证]]
