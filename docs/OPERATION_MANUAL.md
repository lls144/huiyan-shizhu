# 项目打开与使用说明书

面向“我要开机、跑一遍、交作业”的读者。每一步都写清楚**打开哪个文件、在哪里、看到什么算正常**。

---

## 0 十分钟跑一遍完整闭环（最短路径）

| 顺序 | 做什么 | 命令 / 位置 | 正常表现 |
|---|---|---|---|
| 1 | 实验箱上电，PLC 进 RUN | 实验箱电源开关 | CPU 的 RUN 绿灯常亮 |
| 2 | 电脑网线插到实验箱 | 笔记本“以太网”口 ↔ 实验箱 PROFINET 口 | — |
| 3 | 验证 PLC 可读 | `plc\tools\m8_real_plc_acceptance.py --check-access --db-number 3` | `pass: true`、`magic 0x4D38`、`CycleCounter` 递增 |
| 4 | 启动排序程序（带 PLC） | 见 §2 命令 | 窗口出现三节传送带 + 摄像头画面 |
| 5 | 举纸 | 白纸占满画面中间蓝框，三角形/矩形/圆形各举一次 | 物料块在自己那一段离开 |
| 6 | 按出队键 | 实验箱 `%I0.0` | 三角形 1 盏、矩形 2 盏、圆形 3 盏 |
| 7 | 收证据 | 程序退出后自动写 session JSON | `output/sorting/sessions/` |

> 相机要 **13 秒左右**才出画面，属正常现象。

---

## 1 仓库里“必须知道位置”的文件

### 1.1 规则与需求（先读）

| 文件 | 作用 |
|---|---|
| `AGENTS.md` | 协作规则、当前硬件事实（**先读这个**） |
| `docs/PROJECT_SPEC.md` | 需求规格与验收标准（最高需求来源是任务书） |
| `docs/ROADMAP.md` | M0–M12 里程碑与当前状态 |
| `docs/REPORT_EVIDENCE.md` | **证据总表**：每条需求对应哪个测试、哪张图 |

### 1.2 运行配置（要改参数只动这几个）

| 文件 | 内容 |
|---|---|
| `pc/config/camera.json` | 相机设备名/后端/分辨率 |
| `pc/config/vision.json` | 视觉阈值与固定 ROI（**不要轻易改**，见 ISSUE-003） |
| `pc/config/events.json` | 事件去重参数 |
| `pc/config/sorting.json` | 传送带速度、缓冲容量、PLC 触发时点 |
| `pc/config/plc.json` | **PLC 地址、DB 号、心跳/重连/队列满策略** |
| `output/m2/runtime-calibration.json` | 运行时 ROI（git 忽略；换机位后重新校准会覆盖它） |

### 1.3 PLC 侧

| 文件 | 作用 |
|---|---|
| `plc/src/*.scl` | 7 个外部源（导入 TIA 用，顺序见下） |
| `plc/project/TIA_V20_COMPILE_GUIDE.md` | **TIA 导入顺序与编译指南** |
| `plc/docs/IO_MAP.md` | I/O 表（I0.0 出队、I0.1 复位、Q0.1–Q0.3 三盏灯） |
| `plc/docs/M8_INTERNAL_DESIGN.md` | PLC 内部设计（FIFO/按键/灯） |
| `plc/tools/m8_real_plc_acceptance.py` | 真机自动验收工具 |

TIA 导入顺序（**不能反**）：
`PLC_Types.scl → FB_Fifo.scl → FB_ButtonPulse.scl → FB_LedDisplay.scl → FB_PlcApplication.scl → FB_M8_AcceptanceHarness.scl → DB_M8_Acceptance.scl`

### 1.4 记录与证据

| 位置 | 用途 |
|---|---|
| `notes/daily/` | 每次开机的实验日志 |
| `notes/tests/` | 每条验收记录（TEST-001 … TEST-020） |
| `notes/issues/` | 问题记录（ISSUE-001 … ISSUE-004） |
| `notes/decisions/` | 技术决策 |
| `evidence/screenshots/` | 精选截图（报告用） |
| `evidence/data/` | 精选数据（报告用） |
| `output/` | 运行时输出，**git 忽略**，可随时删 |

---

## 2 四个可运行入口（记这四条命令就够）

全部在仓库根目录执行，用仓库自己的虚拟环境。

### 2.1 摄像头 + 三节传送带 + PLC（**演示主力**）

```powershell
.\.venv\Scripts\python.exe -m pc.sorting --source camera --reuse-calibration `
  --plc-config pc/config/plc.json
```

- 不接 PLC 试跑：加 `--no-plc`
- 想让信号直接点灯（开发自测）：加 `--auto-dequeue`
- 不是任务书的按键闭环，报告演示请用物理按键

### 2.2 原版视觉界面（M5 GUI，单目标/多目标观察）

```powershell
.\.venv\Scripts\python.exe -m pc.gui --source camera --reuse-calibration `
  --plc-config output/tmp/plc-disabled.json
```

### 2.3 单目标 / 多目标实时预览（M2 / M3 存证）

```powershell
# M2：S 存证、R 重新校准、Q 退出
.\.venv\Scripts\python.exe -m pc.vision live --reuse-calibration `
  --calibration-file output/m2/runtime-calibration.json --evidence-dir output/m2/live-evidence-builtin

# M3：1–5 存五个场景、T 切换预处理、Q 退出
.\.venv\Scripts\python.exe -m pc.vision multi-live --reuse-calibration `
  --calibration-file output/m2/runtime-calibration.json `
  --evidence-dir output/m3/live-evidence-builtin-v4 `
  --expected-labels triangle rectangle circle --events

# 手持纸不方便按热键时，用定时采集版（屏幕显示倒计时，不用按键）
.\.venv\Scripts\python.exe scripts\m3_timed_capture.py `
  --calibration-file output/m2/runtime-calibration.json `
  --evidence-dir output/m3/live-evidence-builtin-v4 `
  --scenarios normal_light bright_or_side_light dark_light
```

### 2.4 真机 PLC 验收（只读 / 自动）

```powershell
# 只读连通性与 DB 布局（最安全，先跑这个）
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --check-access --db-number 3

# 12 项自动验收（会驱动队列和灯）
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --all --db-number 3 --output output/m8-real
```

---

## 3 TIA 工程在哪里、怎么打开

- **虚拟机里的路径**：`C:\Users\developer\Documents\Automation\项目1\项目1`，
  工程文件 `项目1.ap20`（TIA V20）。
- TIA 启动页的“最近使用的项目”列表是**按 Windows 用户存的**，虚拟机换会话/非正常关机后会空——
  此时用 **打开现有项目 → 浏览** 找到上面的路径即可，工程本身不会丢。
- 工程里与本项目有关的对象：

| 对象 | 用途 |
|---|---|
| `Main [OB1]` | 只调用一次 `FB_M8_AcceptanceHarness` |
| `FB_M8_AcceptanceHarness` | 验收/联调包装块（含 COMM-002 看门狗与全闪） |
| `DB_M8_Acceptance` | **PC 读写的 DB，当前是 DB3**，必须非优化访问 |
| `FB_Fifo` / `FB_ButtonPulse` / `FB_LedDisplay` / `FB_PlcApplication` | 业务逻辑 |
| `PLC 变量表` | I0.0 / I0.1 / Q0.1–Q0.3 符号 |

**改 `plc/src/*.scl` 之后**：外部源是工程内副本，必须“删除旧源 → 重新添加 → 从源生成块”，
再编译下载（详见 `plc/project/TIA_V20_COMPILE_GUIDE.md` 与 ISSUE-004）。

---

## 4 出问题先看哪里

| 现象 | 先看 |
|---|---|
| GUI 没有 `OBJECT_ENTER` | 物体停住 ≥1 秒；看画面有没有检测框 |
| PLC 连不上 / 读 DB 报错 | `notes/issues/` 与 `docs/PLC_FIELD_CHECKLIST.md`；先跑 `--check-access` |
| 有 ENTER 但 PLC 队列不动 | `pc/config/plc.json` 的 `enabled`、`db_number` |
| 队列动了但灯不亮 | **是不是没按出队键**（入队不亮灯，出队才亮） |
| 相机打不开/很慢 | 打开要 13 秒；后端必须是 MSMF（见 `docs/ENVIRONMENT.md`） |
| 举着纸却识别不到 | 图形要**完整落在画面中间的蓝框内**（触边会被排除） |

---

## 5 相关文档索引

- 视觉接入真机流程：`docs/INTEGRATION_VISION_TO_LED.md`
- 传送带分拣程序说明：`docs/SORTING_LINE.md`
- M2/M3/M5 实现说明：`docs/M2_LIVE_VISION.md`、`docs/M3_MULTI_LIGHTING.md`、`docs/M5_GUI.md`
- 协议与接口：`docs/PLC_INTERFACE.md`、`docs/PLC_PROTOCOL_M7.md`
- 现场核对表：`docs/PLC_FIELD_CHECKLIST.md`
