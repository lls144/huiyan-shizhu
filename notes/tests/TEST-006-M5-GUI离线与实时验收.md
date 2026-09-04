---
title: TEST-006 M5 GUI 离线与实时验收
date: 2026-09-04
tags:
  - 慧眼识珠
  - test
  - M5
result: offline-pass-live-pending
---

# TEST-006 M5 GUI 离线与实时验收

- **Test ID**：TEST-006
- **对应 Requirement ID**：GUI-001
- **实现 commit**：`bbb6fa7`
- **自动化测试 commit**：`eb7a1fd`
- **环境**：Windows 11 10.0.26200、Python 3.12.10、PySide6 6.11.2、Qt 6.11.2、OpenCV 5.0.0、NumPy 2.5.2
- **总结果**：Part A synthetic/offscreen PASS；Part B Insta360 live PENDING

## Part A：离线软件验收

### 自动化检查

| 检查项 | 实际验证 | 结果 |
|---|---|---|
| window create | offscreen `QApplication` 创建、显示并关闭 `MainWindow`；无 Card，72:28 splitter、40 px app bar、≤26 px status bar | PASS |
| synthetic start | 注入 synthetic sequence，worker 进入 RUNNING 并产生 snapshot | PASS |
| frame/result sync | 每个 detection 的 `frame_index` 等于 snapshot frame | PASS |
| multi-target | `multi_normal.png` 得到 triangle、rectangle、circle | PASS |
| confidence | GUI snapshot 与 M3 直接输出逐项相同 | PASS |
| M4 states | 第二帧出现 3 个 confirmed object states | PASS |
| M4 events | 第二帧显示 3 个 ENTER；blank 后 summary 出现 3 个 EXIT | PASS |
| start-stop | worker 正常停止，session `clean_shutdown=true` | PASS |
| restart | 同一窗口 Start/Stop 两轮，无重复连接或残留 thread | PASS |
| source open failure | 显示类型和 message，转 ERROR，随后可重新 Start | PASS |
| source read failure | 显示错误、worker 退出、GUI 可重试 | PASS |
| vision failure | 注入 `ValueError` 后显示错误且进程不崩溃 | PASS |
| close running | `closeEvent` 请求中断并等待 worker 正常退出 | PASS |
| backpressure | 容量 1；连续发布 1/2/3 后只取得 frame 3，2 次 overwrite | PASS |
| resize | pixmap 使用 `KeepAspectRatio`，不触发视觉重算 | PASS |
| compact overlay | ROI 细线、ID-aware label、源图不被修改 | PASS |

相关 pytest 文件：`../../pc/tests/test_gui_buffer.py`、`../../pc/tests/test_gui_overlay.py`、`../../pc/tests/test_gui_window.py`。测试没有使用几秒固定 `sleep()`，而是确定性 source 和有上限的 Qt event-loop 条件等待。

### 60 秒 synthetic soak

| 字段 | 实际值 |
|---|---:|
| source | `synthetic` |
| requested cadence | 30 FPS |
| duration | 60.011330 s |
| frames read / processed | 1284 / 1284 |
| GUI updates | 1284 |
| processing FPS | 21.395960 |
| GUI update FPS | 21.395960 |
| average / P95 processing | 6.537603 / 9.372350 ms |
| display drops / buffer overwrites | 0 / 0 |
| failed reads | 0 |
| error | `null` |
| ended reason | `stopped` |
| clean shutdown | `true` |

soak 由真实 `.venv` 进程运行，但输入是 synthetic、Qt 平台是 offscreen。循环过程中真实产生 64 个 M4 事件；其中 touching/occlusion 段出现 `unknown`，与 M3 已记录的合并轮廓局限一致，不隐藏也不作为 GUI 故障。`tracemalloc` current/peak 为 55,931,591 / 64,671,161 bytes，仅是 Python 可追踪分配粗测。

### 回归

- 完整 pytest：UI/UX 重构后 `109 passed in 4.03s`。
- M2 十张真实离线图片：`10/10`，background 1/1、circle 3/3、rectangle 3/3、triangle 3/3。
- M3 synthetic：4 个强制光照场景、两种方案均精确输出三类，`all_required_scenes_pass=true`；遮挡/接触局限未改写。
- M4：12/12 detection-sequence 场景通过，`failing_scenarios=0`。
- `pip check`：`No broken requirements found.`。

### Part A 证据

- JSON：`../../evidence/data/m5/m5-offline-gui-results.json`
- CSV：`../../evidence/data/m5/m5-offline-gui-results.csv`
- 三目标 GUI：`../../evidence/screenshots/m5/synthetic/m5-gui-three-target-demo.png`
- soak 结束画面：`../../evidence/screenshots/m5/synthetic/m5-gui-soak.png`
- desktop workspace 重构验收图：`../../evidence/screenshots/m5/synthetic/m5-gui-desktop-workspace.png`

## Part B：真实 Insta360 摄像头 GUI 验收 — PENDING

待验证：启动 calibration、画面连续刷新、三目标 label/confidence、M4 ID/ENTER/EXIT、五个 M3 场景保存、processed/GUI FPS、failed reads/error、Stop/Close。未经读取真实 session JSON 和截图，不填写 PASS。

> [!warning] 验收边界
> Part A 证明软件链路、线程、异常处理和 synthetic 性能；不能证明真实摄像头 GUI 稳定性。因此 GUI-001 与 M5 保持 `DOING`。

## 关联记录

- [[../daily/2026-09-04-M5-GUI离线软件验证]]
- `../../docs/M5_GUI.md`
