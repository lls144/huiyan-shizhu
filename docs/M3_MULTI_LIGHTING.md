# M3：多目标识别与抗光照最小验收方案

## 当前状态

M3 为 `DOING`。多目标代码、Otsu 与 CLAHE+Otsu 同帧对比、证据保存和合成自动化测试已完成；真实摄像头的三种光照、部分遮挡和目标接触/粘连尚未执行，因此 VISION-003、VISION-004 和 M3 不得标记 `DONE`。

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
