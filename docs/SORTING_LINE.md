# 三节传送带分拣可视化（运行手册）

状态：PC 端实现完成，**合成数据自检通过**；真实摄像头与真实 PLC 联调**待测试**。
本文只描述 `pc/sorting/` 的用法与边界，不改变任何 Requirement 或 milestone 状态。

---

## 1 形状 → 灯 映射（本次要回答的问题）

| 第几段 | 传送带代表的形状 | 识别到该形状时 | 亮灯 | 形状编码 |
|---|---|---|---|---|
| 第 1 段 | 三角形 triangle | 从第 1 段离开并示意 | **1 盏** | 1 |
| 第 2 段 | 矩形 rectangle | 从第 2 段离开并示意 | **2 盏** | 2 |
| 第 3 段 | 圆形 circle | 从第 3 段离开并示意 | **3 盏** | 3 |

该映射不是本程序新定的，而是沿用仓库里已经写好的编码：
`pc/communication/models.py` 的 `SHAPE_CODES` 与 `plc/src/FB_LedDisplay.scl` 的 `CASE` 分支一致
（triangle=1、rectangle=2、circle=3）。程序启动后右侧 “形状 → 灯 映射” 面板也会列出同一张表。

## 2 它到底做了什么（以及没做什么）

流程：

```text
摄像头帧
  → pc/vision/      识别 triangle / rectangle / circle
  → pc/events/      逐帧检测 → 离散 OBJECT_ENTER 事件
  → pc/sorting/     物料块进入第 1 段，按标签在自己那一段被推出并示意
  → pc/communication/  把形状编码写进 PLC 命令边沿
  → PLC FIFO → 出队 → 1/2/3 盏 LED
```

必须说清楚的一点：**传送带不做第二次识别**。物料块身上带的标签就是视觉模块已经给出的结果，
三段传送带只是把这个分类结果的“分拣去向”可视化出来。它不是新的识别能力，不能当作视觉证据引用。

## 3 运行方式

### 3.1 合成数据自检（不需要相机、不需要 PLC）

```powershell
.\.venv\Scripts\python.exe -m pc.sorting --source synthetic --offscreen `
  --soak-seconds 26 `
  --summary-json output/sorting/synthetic-proof.json `
  --screenshot output/sorting/synthetic-proof.png
```

默认情况下**合成运行不会连 PLC**：只有当显式给出 `--plc-config` 时才会打开命令桥，
避免离线自检把命令写进实验室 PLC。

判据：`sorting_results` 里 triangle/rectangle/circle 三种都出现，
且每条的 `lamp_count` 分别是 1/2/3，`error=null`。

### 3.2 真实摄像头 + 真机 PLC（演示用）

```powershell
.\.venv\Scripts\python.exe -m pc.sorting --source camera --reuse-calibration `
  --camera-config pc/config/camera.json `
  --vision-config pc/config/vision.json `
  --event-config pc/config/events.json `
  --sorting-config pc/config/sorting.json `
  --plc-config pc/config/plc.json
```

操作顺序：等界面状态变成 `running`（ROI 校准完成）→ 把物体放进画面中央停约 1 秒 →
物料块进入第 1 段 → 走到自己那一段被推出并示意 → PLC 收到形状命令。

### 3.3 灯什么时候亮：两种模式

PLC 侧的设计是“**入队不亮灯，出队才亮灯**”（见 `docs/INTEGRATION_VISION_TO_LED.md` 第 0 节）。

| 模式 | 怎么做 | 灯何时亮 |
|---|---|---|
| A（任务书闭环，默认） | `pc/config/plc.json` 保持 `auto_dequeue=false` | 识别入队后，操作者按实验箱出队键，才亮 1/2/3 盏 |
| B（只想看信号点灯） | 加 `--auto-dequeue` | 物料块离开传送带后，PC 立刻发出队请求，灯随即亮起 |

模式 B 只是开发/演示自测手段，不是任务书要求的“按键出队”闭环，报告里不要当最终演示证据。

## 4 命令写入 PLC 的时点

`pc/config/sorting.json` 的 `plc_trigger` 决定何时写 PLC 命令：

| 取值 | 含义 | 备注 |
|---|---|---|
| `exit`（默认） | 物料块从自己那一段离开后写命令 | 演示时“块离开 → 亮灯”同步感最好 |
| `enter` | 识别到物体时立刻写命令 | 与 M5 现有行为一致；多物体同屏时命令顺序严格等于识别顺序 |

两种取值写入的形状编码完全相同，因此**灯的盏数不受影响**；差别只在多物体同屏时的命令先后顺序。
单件逐个演示时两者没有区别。任务书要求“AI 连续识别多个物体，指令依次入队”，
若演示要同时放多个物体并按识别顺序入队，请用 `enter`。

## 5 参数

`pc/config/sorting.json`：

| 字段 | 含义 |
|---|---|
| `belt_speed_units_per_second` | 物料块每秒走过多少“段”（1 段 = 一条传送带） |
| `min_gap_units` | 同一条带上两个物料块之间的最小间距，也是入口放行阈值 |
| `eject_seconds` | 从传送带被推出到落入料框的示意时长 |
| `max_pending_items` | 入口最多缓存几个待入场物料块 |
| `plc_trigger` | `exit` 或 `enter`，见第 4 节 |

## 6 边界与未验证项

- 真实摄像头 + 真机 PLC 的端到端闭环**待测试**；本程序只完成了合成数据自检。
- 传送带不产生新的识别结论，不能替代 M2/M3 的视觉验收。
- 本程序不实现心跳、断连报警、超时重发、队列满处理（属 M9），不要据此声称这些已完成。
- 真机当前需要 CPU 侧允许 PUT/GET 访问（TIA: Protection & Security → Connection mechanisms），
  否则读 DB 会报 `class=0x81 code=0x04`；处理步骤见 `docs/PLC_FIELD_CHECKLIST.md`。
