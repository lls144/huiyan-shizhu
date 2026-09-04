# M2 第二阶段：实时摄像头与启动 ROI 校准

## 当前状态

代码、自动化测试和两轮真实 Insta360 验收均已完成。M2、VISION-001、VISION-002 为 `DONE`；下一 milestone 为 M3，但未经明确用户指令不得开始。

## 固定运行 ROI 模型

```text
相机重新架设
  -> 启动程序
  -> auto / manual / fixed_normalized 校准
  -> ROI 锁定
  -> 每帧复用同一 ROI
  -> 按 R 时暂停并重新校准
```

程序不会每帧重新计算 ROI，不使用目标位置反推 ROI，也不实现目标跟踪。运行时 ROI 保存到被 Git 忽略的 `output/m2/runtime-calibration.json`，不会修改版本控制中的 `pc/config/vision.json`。

## 三种模式

### auto

从启动帧的 HSV 图像中寻找高亮度、低饱和度、面积合理、中心附近的凸四边形。候选按面积、矩形度、中心距离和亮色覆盖比例评分；黑色目标可作为白色区域内部的孔洞存在，不会被当作 ROI。接受后按配置比例向内缩小。

auto 失败会在控制台打印具体原因，再打开 manual。旧的 10 张照片只读预检中，7 张 auto 成功且分类保持正确，3 张明确失败并要求 manual；这不是实时验收，也说明 manual 兜底不可删除。

### manual

OpenCV 鼠标框选窗口中拖出白色工作区域，按 Enter 或 Space 接受，按 C 取消。坐标转换为 normalized ROI 并在本次运行锁定。取消或区域过小时会明确提示，再使用 fixed fallback。

添加 `--reuse-calibration` 可显式复用本地保存的 normalized ROI。相机重新架设后不应复用旧 ROI，应重新校准。

### fixed_normalized

使用版本控制配置中的 `(0.24, 0.08) - (0.76, 0.75)`，作为最后 fallback 和离线兼容方案。

## 实时显示稳定

原始每帧结果仍由与离线批处理相同的 `analyze_image` 产生并显示为 `raw`。`stable` 只用于画面显示：默认最近 5 帧中至少 3 帧一致才更新。不生成物体 ID、入队事件或防重复识别逻辑。

## 启动命令

```powershell
.\.venv\Scripts\python.exe -m pc.vision `
  --config pc/config/vision.json `
  live `
  --camera-config pc/config/camera.json `
  --roi-mode auto
```

其他模式：

```powershell
# 直接手动框选
.\.venv\Scripts\python.exe -m pc.vision --config pc/config/vision.json live --camera-config pc/config/camera.json --roi-mode manual

# 使用固定 fallback
.\.venv\Scripts\python.exe -m pc.vision --config pc/config/vision.json live --camera-config pc/config/camera.json --roi-mode fixed_normalized

# 明确复用上次本地校准；相机移动后不要使用
.\.venv\Scripts\python.exe -m pc.vision --config pc/config/vision.json live --camera-config pc/config/camera.json --roi-mode manual --reuse-calibration
```

## 画面与按键

画面显示 ROI、原始/稳定标签、几何 confidence、轮廓、bounding box、中心点、顶点数、面积占比、圆度、FPS 和校准模式。

- `R`：重新执行当前请求模式的校准并重置显示投票窗口。
- `S`：保存 frame、ROI、binary、Canny、annotated 和 JSON。
- `Q` 或 `Esc`：退出并写入运行级 session JSON。

本地证据默认保存在 `output/m2/live-evidence/`。单帧 JSON 记录 Git 状态、摄像头配置/设备、分辨率、ROI 模式及坐标、分类和几何特征；session JSON 记录请求/实际摄像头属性、校准历史、运行时 ROI、处理帧数、失败读取数和实测预览处理 FPS。

## 透视处理决策

离线图以及两轮真实摄像头验收中的圆度、矩形角度和分类结果均未显示必须做透视矫正，故 M2 不增加 perspective transform。严重透视尚未覆盖，后续只有出现圆明显椭圆化、矩形特征严重变化或分类不稳定的真实证据时才重新评估。

## 真实验收结果

2026-09-04 共完成两轮真实摄像头验收：

| 轮次 | 相机条件 | ROI | session 处理 FPS | failed reads | 四项结果 |
|---|---|---|---:|---:|---|
| 第一轮 | 原机位 | manual / selected，`[512, 60, 1428, 720]` | 27.547318 | 0 | background、triangle、rectangle、circle 全部正确 |
| 第二轮 | 改变高度/水平位置，未复用旧 ROI | auto / detected，`[579, 33, 1426, 798]`，score 0.677265 | 29.473403 | 0 | background、triangle、rectangle、circle 全部正确 |

两个 session 均正常完成且 `error=null`。auto 检出的 ROI 不严格贴合纸张边缘，但本轮足以隔离工作区且 background 无误检。第一轮验证 manual fallback 必要，第二轮验证改变机位后 auto 可重新定位；不据此声称 auto 100% 成功。

完整 runtime 数据保留在被 Git 忽略的 `output/m2/`。版本库只保存 8 张精选标注图 `evidence/screenshots/m2/live/` 与结构化摘要 `evidence/data/m2-live-acceptance-summary.json`。

## 已知限制

- 当前真实样本数量仍有限，目标为黑色简单几何图形。
- 未覆盖极端光照、遮挡、多个目标和严重透视。
- auto ROI 不是精确背景板语义分割。
- `confidence` 是几何规则符合度，不是概率。

这些属于 M3 或后续系统测试范围，不阻碍 M2 完成。
