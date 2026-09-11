---
title: "TEST-014 视觉 → 传送带 → 真机 PLC → 实体灯 完整闭环"
date: "2026-09-11"
tags:
  - 慧眼识珠
  - test
result: pass
---

# TEST-014 视觉到真机灯的完整闭环（单次会话）

- **Test ID**：TEST-014
- **对应 Requirement ID**：SCOPE-001、SYS-001 的闭环方向；PLC-002/003；COMM-001
- **日期**：2026-09-11
- **Git commit**：`04b4622`（PLC 侧基线）；PC 侧确认逻辑修订见本轮后续 commit

> [!warning] 证据边界
> 本轮是**一次真机完整闭环会话**，证明“放物体 → 识别 → 三段传送带分拣 → 真机 PLC 收到命令 →
> 按键出队 → 实体灯亮 1/2/3 盏”这条路可以跑通。
> 它**不**等于 SYS-001 / M10 验收完成：只有一次会话、没有视频、没有多工况矩阵、
> 没有断电重启、没有故障注入，心跳/断连报警（COMM-002）仍未实现。

## 环境

- 相机：内置 `HD Webcam`，MSMF，1280×720，运行时校准 ROI 复用（`--reuse-calibration`）
- PLC：S7-1200 1214C DC/DC/DC，`192.0.2.1`，CPU RUN，`DB_M8_Acceptance` = DB3
- I/O：`%I0.0` 出队键（操作者手动按）、`%Q0.1..Q0.3` 三盏灯
- PC：Windows 11，Python 3.12.10，PySide6 6.11.2

## 操作步骤

```powershell
.\.venv\Scripts\python.exe -m pc.sorting --source camera --reuse-calibration `
  --plc-config pc/config/plc.json --soak-seconds 180 `
  --summary-json output/sorting/camera-plc-live.json `
  --screenshot output/sorting/camera-plc-live.png
```

操作者依次举起三角形、矩形、圆形；物料块在自己那一段离开传送带后，操作者按实验箱出队键。

## 预期结果

- 三类形状都能识别，物料块在对应段离开
- 每段的 PLC 命令写入成功，按键后灯分别亮 1/2/3 盏
- 会话正常结束，`failed_reads=0`、`error=null`

## 实际结果

### 采集与识别

| 字段 | 值 |
|---|---|
| frames_read / frames_processed | 4747 / 4747 |
| failed_reads | 0 |
| detection_count | 612 |
| event_count | 60 |
| 实测帧率（状态栏） | 26.4 FPS（含 13 s 相机打开时间） |
| ended_reason / clean_shutdown | stopped / true |
| error | null |

### 分拣结果（20 条）

| 形状 | 条数 | 离开段 | 灯 |
|---|---|---|---|
| triangle | 10 | 第 1 段 | 1 |
| rectangle | 5 | 第 2 段 | 2 |
| circle | 5 | 第 3 段 | 3 |

**20 条全部进入正确的段位、灯数全部正确**，`stage_index` 与 `lamp_count` 一一对应。

### PLC 侧

| 字段 | 值 |
|---|---|
| plc_enabled | true |
| 派发 | 20 |
| 状态分布 | `SENT` 19、`UNCONFIRMED` 1、`ERROR` 0 |
| 丢写重发 | 55 次 |
| 队列满延后 | 11 条（`deferred_retries` 114 次） |
| 队列满丢件 | 0 |

**操作者目视确认：三种形状对应的 1 / 2 / 3 盏灯均正确。**

### 关于那 1 条 `UNCONFIRMED`

明细：`write did not raise but the queue did not grow (2 -> 2); elapsed=0.342s`。

原因是**人工按键与我们"写前读 / 写后读"的窗口重叠**：读前队列 2 → 操作者按了一下变 1 →
命令写进去变 2 → 前后相等，于是判据认为"没涨"。命令实际已经入队。

这是"人工按键 + 队列长度确认"的固有盲区，不是丢命令。本轮据此做了两项收敛：

1. 首次读数不成立时，再短暂复读（`confirm_repoll_attempts`，默认 3 次 × 0.15 s），
   捕捉"晚一点才看到队列增长 / 语义号出现在刚出队记录里"的情况；
2. `UNCONFIRMED` 不再被当成错误写进会话的 `plc_sink_error`，
   改为在 PLC 面板的单列计数里显示，避免演示时出现误导性的红字。
   真正写失败（`ERROR`）仍然会报错。

## 结论

- 视觉 → 三段传送带 → 真机 PLC → 按键出队 → 1/2/3 盏实体灯，**首次完整跑通**。
- 传送带的段位判定与形状编码/灯数映射一致；PLC 队列满时按设计延后而非丢件。
- 本结果不改变 SYS-001 / M10 的 TODO：需要多次会话、多工况、视频与断电重启证据。

## 未执行 / 待补

1. **视频/照片**：LED 与整个操作过程的人工影像证据仍为 TODO
2. **多工况矩阵**：正常/较亮/较暗、遮挡、连续多物体（对应 TEST-001）
3. **断电重启 `--verify-power-on`**
4. **心跳 1 s / 断连 2 s 全闪**（COMM-002 未实现）
5. **新相机上的 M2/M3/M4/M5 正式重跑**（仍是旧 Insta360 结论）

## 证据位置

- 会话数据：`evidence/data/sorting/2026-09-11-vision-to-plc-closed-loop.json`
- 截图：`evidence/screenshots/sorting/2026-09-11-vision-to-plc-closed-loop.png`
  （画面里操作者正举着三角形与矩形，第 1 段上有三角物料块，右侧为真实 PLC 状态与分拣日志）
- 重建后的自动验收：`evidence/data/m8-real/2026-09-11-postrebuild-acceptance.json`（12/12 AUTO PASS）
- 真机灯与按键：`notes/tests/TEST-013-真机LED与物理按键验收.md`
