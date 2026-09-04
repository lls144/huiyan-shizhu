# M3：多目标识别与抗光照最小验收方案

## 当前状态

M3 为 `DOING`。多目标代码、Otsu 与 CLAHE+Otsu 同帧对比、确定性合成数据集、离线批处理、版本化离线证据和自动化测试已完成；真实摄像头的三种光照、部分遮挡和目标接触/粘连尚未执行，因此 VISION-003、VISION-004 和 M3 不得标记 `DONE`。

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

两种模式共享后续轮廓筛选和分类参数。CLAHE 的 clip limit 与 tile grid size 位于 `pc/config/vision.json`。当前不预先宣称哪种更好；必须用同一真实帧的成对结果决定。若两者表现一致，优先保留更简单的 Otsu 基线。

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

## 实时入口

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

## 证据边界

完整 runtime 数据默认位于被 Git 忽略的 `output/m3/live-evidence/`。所有新证据初始写为 `pending_user_validation`。只有实际读取 JSON、核对截图和 session、记录失败情况后，才从中选择少量代表性材料进入 `evidence/`。

遮挡和粘连不要求本阶段完全解决。当前使用 `RETR_EXTERNAL`，接触目标可能形成一个轮廓；M3 的要求是如实保存结果和局限，不为单个失败场景引入复杂分水岭、实例分割或跟踪。

## 剩余真实验收

今晚软件与离线验证结束后，项目负责人只需：固定相机并启动上述 `multi-live` 命令，完成 ROI 校准，依次摆放五个场景并按 `1`～`5`，最后按 `Q`。随后必须审计 frame、两种 annotated 图、JSON/CSV、session 中的设备、FPS、failed reads 和 error，再决定 M3 是否可以关闭。
