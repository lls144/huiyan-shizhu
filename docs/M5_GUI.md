# M5：PySide6 实时视觉 GUI

## 当前状态与边界

M5 为 `DOING`。离线软件、线程生命周期、异常处理、自动化测试和 60 秒 synthetic soak 已完成；真实 Insta360 摄像头 GUI 验收尚未执行，因此 GUI-001 和 M5 不得标记 `DONE`。本模块不包含 Fake PLC、通信、FIFO、ACK、心跳或重发。

## 数据流与线程边界

```text
FrameSource (synthetic / camera)
    -> VisionWorker in QObject + QThread
    -> existing M3 analyze_multiple_objects()
    -> existing M4 ObjectStateManager
    -> immutable GuiSnapshot
    -> bounded latest-frame buffer + Qt signal
    -> MainWindow on the UI thread
```

UI 线程只做 `QImage/QPixmap` 转换和控件刷新，不读取摄像头、不执行 OpenCV 轮廓识别，也不更新 M4 状态机。每个 `GuiSnapshot` 在 worker 内一次性组装，图像、detections、confidence 和 object states 来自同一帧。confidence 直接使用 M3 的几何规则符合度，不是神经网络或统计概率。

显示帧使用容量为 1 的 `LatestSnapshotBuffer`。当 UI 尚未消费上一帧时，新帧覆盖旧帧且不再追加 Qt 通知，从结构上避免无界 signal backlog。过期画面允许被丢弃，处理与事件完整记录仍保留在 session summary 中。

## 界面与交互

界面采用克制的深色桌面工具风格，参考现代编辑器的信息层级和密度，但不复制 Claude、Codex 或 VS Code 的品牌资源。主区域为保持宽高比的标注画面，右侧依次显示运行状态、detections、tracked objects 和最近事件。

已实现：

- 视频、bbox、label 和几何 confidence；
- M4 object ID、confirmed/active 状态和 ENTER/EXIT；
- processed FPS、单帧 processing ms、frame index；
- ROI mode/source/coordinates、preprocess、source 和 last error；
- Start、Stop、再次 Start、安全关闭；
- source open/read failure 和 vision exception 可见且可重试；
- synthetic 与 camera 两种 source adapter。

没有加入无实际功能的重校准按钮。camera source 启动时直接复用 M2/M3 的 `auto -> manual -> fixed_normalized` 校准流程，ROI 在本次运行内锁定，不做逐帧动态追踪。

## Synthetic source

`SyntheticFrameSource` 复用 `test_data/m3/synthetic/`：blank、normal、normal hold、bright、dark、partial occlusion、touching、blank。默认 20 FPS、每场景 20 帧并循环；blank 为由已加载图像尺寸构造的确定性纯白帧。normal 连续帧触发 M4 ENTER，末尾 blank 触发 EXIT；遮挡/接触场景仍保留 M3 已知 merged contour / unknown 局限。

```powershell
.\.venv\Scripts\python.exe -m pc.gui --source synthetic
```

## 性能定义与离线实测

- `processed FPS`：worker 完成 source read、M3、M4 和标注后的实际吞吐，不使用摄像头 advertised FPS。
- `GUI update FPS`：主线程实际消费并展示 snapshot 的速率。
- M5 软件目标：处理链不低于 20 FPS，GUI 更新不低于 15 FPS；真实摄像头是否达到目标仍须 TEST-006 Part B 验证。

2026-09-04 的 offscreen synthetic soak 请求 30 FPS，实际运行 60.011 s，处理和展示 1284 帧：`processing_fps=21.395960`、`gui_update_fps=21.395960`、平均处理 6.538 ms、P95 9.372 ms、0 failed read、0 display drop、0 buffer overwrite、`error=null`、正常停止。Python `tracemalloc` 峰值 64,671,161 bytes，只代表 Python 可追踪分配，不是进程总内存，也不据此宣称无内存泄漏。

上述是 synthetic/offscreen 软件证据，不能替代真实摄像头 FPS、画面流畅性或窗口交互验收。

## Camera 启动与联合验收

```powershell
.\.venv\Scripts\python.exe -m pc.gui `
  --source camera `
  --camera-config pc/config/camera.json `
  --vision-config pc/config/vision.json `
  --event-config pc/config/events.json `
  --roi-mode auto `
  --expected-labels triangle rectangle circle
```

相机模式下数字键或界面按钮 `1`～`5` 分别保存 normal、bright/side、dark、occlusion、touching 的 M3 同帧双预处理 runtime evidence。M4 状态和事件自动进入 M5 session JSON。完整 runtime 位于被忽略的 `output/`；审计后才能精选真实证据进入 `evidence/`。

## 已知限制

- camera GUI 尚未真实运行；不能将 synthetic 截图或 FPS 描述为摄像头结果。
- 当前 recent events 控件最多保留 30 条，完整事件保存在 session JSON。
- M3 合并轮廓的 `unknown` 会原样进入 M4/GUI，GUI 不负责修复分类。
- Stop 等待 worker 最多 5 秒；若未退出，窗口拒绝关闭并显示错误，不强杀线程。
- camera manual ROI 继续使用现有 OpenCV selector，没有为 Qt 重写一套 ROI 工具。
