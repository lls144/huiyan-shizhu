# M3：多目标识别与抗光照最小验收方案

## 当前状态

M3 为 `DONE`。多目标代码、Otsu 与 CLAHE+Otsu 同帧对比、确定性合成数据集、离线批处理和自动化测试已完成；2026-09-07 又完成并审计真实 Insta360 摄像头的正常、较亮/侧光、较暗、部分遮挡和目标接触/粘连五个场景。VISION-003、VISION-004 均已有真实证据。

## 最小实现

M3 直接复用 M2 的 ROI、灰度/滤波/二值化、外轮廓提取、面积/solidity/触边筛选和 `approxPolyDP` 分类逻辑。唯一核心扩展是：

```text
M2: 通过筛选的最大轮廓 -> 单个结果
M3: 所有通过筛选的外轮廓 -> 分别分类 -> 按中心从左到右输出
```

`analyze_image()` 保留 M2 单目标语义；新接口 `analyze_multiple_objects()` 返回全部有效轮廓。没有加入跟踪、物体 ID、入队事件或防重复识别，这些属于 M4。

## 两种抗光照方案

| 模式 | 处理链 | 用途 |
|---|---|---|
| `otsu` | 灰度 -> Gaussian blur -> inverse Otsu | M2 基线 |
| `clahe_otsu` | 灰度 -> CLAHE -> Gaussian blur -> inverse Otsu | 最小改动的局部对比度增强方案 |

两种模式共享后续轮廓筛选和分类参数。CLAHE 的 clip limit 与 tile grid size 位于 `pc/config/vision.json`。真实实验前不预先宣称哪种更好；必须用同一真实帧的成对结果决定。2026-09-07 的三种真实分离光照中两者分类结果一致，因此最终保留更简单的 Otsu 基线，CLAHE+Otsu 继续作为对照/诊断方法。本轮没有独立性能对比，不声称两者存在速度差异。

## 离线合成验证

`pc.vision.synthetic` 使用 OpenCV/NumPy 生成 1920×1080 的确定性几何场景，`source_type` 固定为 `synthetic`，generator version 为 `1.0`，seed 为 `0`。`multi_normal`、`multi_bright`、`multi_dark` 与 `multi_side_light` 使用相同目标位置和尺寸，只改变照明模型；`multi_occlusion` 与 `multi_touching` 显式记录重叠/接触关系。完整多边形、中心、bbox、期望数量和照明参数位于 `test_data/m3/synthetic/ground_truth.json`。

```powershell
.\.venv\Scripts\python.exe -m pc.vision.synthetic `
  --output-root test_data/m3/synthetic

.\.venv\Scripts\python.exe -m pc.vision `
  --config pc/config/vision.json `
  multi-batch `
  --input-root test_data/m3/synthetic `
  --ground-truth test_data/m3/synthetic/ground_truth.json `
  --output-json output/m3/offline-results.json `
  --output-csv output/m3/offline-results.csv `
  --diagnostics-dir output/m3/offline-diagnostics
```

版本化结果显示：正常、较亮、较暗、侧光四个分离场景在 Otsu 与 CLAHE+Otsu 下均输出 `triangle, rectangle, circle`，每种方案均为 4/4 场景通过。合成遮挡和接触场景在两种方案下均输出 `triangle, unknown` 两个轮廓；这是相同颜色目标经 `RETR_EXTERNAL` 合并后的真实观察，不计为强制通过项。当前合成结果未体现 CLAHE 收益，因此真实测试前暂以更简单的 Otsu 为基线，不形成最终抗光照结论。

数据见 `evidence/data/m3/m3-offline-synthetic-results.json` 与 `.csv`，标注图见 `evidence/screenshots/m3/synthetic/`。这些是软件验证证据，不是相机实拍证据。

## 实时入口与真实验收

```powershell
.\.venv\Scripts\python.exe -m pc.vision `
  --config pc/config/vision.json `
  multi-live `
  --camera-config pc/config/camera.json `
  --roi-mode auto `
  --expected-labels triangle rectangle circle
```

按键：

- `T`：切换屏幕当前显示的预处理模式。
- `R`：重新校准 ROI。
- `1`：保存正常光照成对证据。
- `2`：保存较亮或侧光成对证据。
- `3`：保存较暗成对证据。
- `4`：保存部分遮挡成对证据。
- `5`：保存目标接触/粘连成对证据。
- `Q` / Esc：退出并完成 session JSON。

按 `1`～`5` 时，两种预处理方案会处理同一原始帧，并保存 frame、ROI、两套 normalized gray/binary/Canny/annotated、JSON 和 CSV。`scenario` 来自操作者按键，`expected_labels` 来自启动参数；两者仍需结合截图人工核对，程序不会把操作者声明冒充视觉真值。

2026-09-07 五组真实 runtime 均使用运行基线 `78597f58`，设备为 Insta360 Ace Pro 2、DirectShow、MJPG、1920×1080@30。auto ROI 未找到合格中央白色四边形，按设计降级到 manual/selected ROI `[548,126,1346,698]`，随后整次运行锁定。

| 场景 | Otsu | CLAHE+Otsu | 结论 |
|---|---|---|---|
| normal | 3：circle/rectangle/triangle | 同左 | PASS |
| bright/side | 3：circle/rectangle/triangle | 同左 | PASS |
| dark | 3：circle/rectangle/triangle | 同左 | PASS |
| partial occlusion | 3：circle/unknown/triangle | 同左 | 遮挡目标变为 unknown，诊断局限 |
| touching/merged | 2：unknown/triangle | 同左 | 圆形与矩形合并为外轮廓，诊断局限 |

人工逐张查看了 frame 与两种 annotated 图，确认 normal 为三个分离目标、bright/side 有手机侧向补光、dark 整体亮度降低、occlusion 有手部遮挡、touching 中矩形与圆形实际接触。详细数值和路径见 TEST-004。

## 证据边界

完整 runtime 数据仍位于被 Git 忽略的 `output/m3/live-evidence/`，未覆盖或删除；runtime 文件的初始 `pending_user_validation` 字段保持原样。审计后的原始 JSON/CSV 精选副本位于 `evidence/data/m3/live/`，每个场景的 frame 与两种 annotated 图位于 `evidence/screenshots/m3/live/`。normalized gray/binary/Canny/ROI 等完整中间图仍只保留在 runtime。

遮挡和粘连不要求本阶段完全解决。当前使用 `RETR_EXTERNAL`，接触目标可能形成一个轮廓；M3 的要求是如实保存结果和局限，不为单个失败场景引入复杂分水岭、实例分割或跟踪。

## 最终结论

真实多目标与三种光照满足 M3 原定验收；遮挡和粘连结果没有被美化或额外修算法。M3 于 2026-09-07 封口为 `DONE`，后续更复杂遮挡分割、严重透视、更多材质与系统级鲁棒性归入 M11，不在 M3 继续扩展。
