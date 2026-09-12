---
title: "ISSUE-002 固件版本登记不一致"
date: "2026-09-10"
tags:
  - 慧眼识珠
  - issue
status: resolved
---

# ISSUE-002 固件版本登记不一致

- **Issue ID**：ISSUE-002
- **创建日期**：2026-09-10
- **状态**：RESOLVED（2026-09-11 由负责人批准后在“文档一致性”任务中结案）
- **所属模块**：PLC 硬件登记 / 文档一致性

## 问题现象

同一台目标 PLC 的固件版本在两处文档中登记为不同值，且两个值都没有仓库内证据文件：

| 位置 | 登记的固件 | 声称来源 | 文档日期 |
|---|---|---|---|
| `docs/PLC_HARDWARE.md` | `V4.1` | 操作者报告，**待 TIA 在线读取** | 2026-09-07 |
| `plc/records/2026-09-08-plc-m8-validation.md` | `V4.5.1` | **TIA 在线信息截图**（截图未归档） | 2026-09-08 |
| `plc/project/TIA_V20_COMPILE_GUIDE.md` | `V4.5.1` | 引用现场核验 | 未注明日期 |

`plc/docs/SCL_STATIC_AUDIT.md` 又要求“保留工程截图”以证明设备目录接受实际 MLFB 与固件组合，因此该值会直接影响 TIA 工程能否编译。

## 复现步骤

1. 打开 `docs/PLC_HARDWARE.md` 参数表“固件”行。
2. 打开 `plc/records/2026-09-08-plc-m8-validation.md` 环境事实表“固件”行。
3. 对比两者。

## 预期结果

同一设备只存在一个带证据的固件版本值，所有文档引用同一来源。

## 实际结果

存在 `V4.1` 与 `V4.5.1` 两个值；记录 `V4.5.1` 声称来自 TIA 在线信息截图，但该截图尚未复制进仓库（`plc/records/2026-09-08` 自述“证据归档：操作者聊天截图尚未复制到仓库”）。

## 环境

- 电脑：Windows 11（当前开发机）
- OS：Windows 11
- Python/PLC 软件版本：Python 3.12.10；TIA Portal V20
- Git commit：`59bc247`（发现时 HEAD）
- 摄像头/PLC/通信：PLC 未接入本机；无真实 PLC 证据
- 光照及其他条件：不适用

## 初步假设

- 假设 1：`plc/records` 的 `V4.5.1` 来自较新的 TIA 在线读取，而 `docs/PLC_HARDWARE.md` 更新滞后。
- 假设 2：`V4.1` 是操作者早期口述，在线读取后被取代但未回填。
- 两者都只能由一次新的 TIA Online & diagnostics 读数裁定。

## 尝试方案

1. 在 `docs/PLC_FIELD_CHECKLIST.md` A3 项登记该冲突，要求现场读取在线固件。
2. 本 Issue 只登记差异，不修改 `docs/PLC_HARDWARE.md` 的既有值。

## 失败方案

- 不采用“按时间取最新”直接覆盖：`plc/records` 的来源截图未归档，无法只读复核。
- 不采用“取指导书值”：指导书示例为 1215C / V4.1，不适用于项目实物。

## 根因

待确认（推测为登记流程缺少单一入口回填）。

## 最终解决方案

2026-09-10 的隔离环境读数给出了独立于 TIA 界面的第二个来源：
原生 `python-snap7 1.3` 读到在线订单号 `6ES7 214-1AG40-0XB0` 与固件 **`4.5.1`**，
与 TIA 下载预览的“(在线) V4.5”一致。据此：

1. `docs/PLC_HARDWARE.md` 参数表“固件”行更新为 **`V4.5.1`（在线读数）**，并写明来源与“截图未归档”的缺口；
2. `plc/project/TIA_V20_COMPILE_GUIDE.md` 与 `plc/docs/PLC_HARDWARE_VERIFICATION.md` 原本就记 `V4.5.1`，与更新后的值一致；
3. 指导书中的 `V4.1` 明确标注为 1215C 教学示例，不适用于项目实物。

**仍未补齐**：TIA Online & diagnostics 的固件截图。它不影响本次结案（已有两个独立来源互证），
但按 `plc/docs/SCL_STATIC_AUDIT.md` 的要求仍需归档，列入待补材料。

## 修改 commit

`docs(notes): resolve ISSUE-002 and align the camera/firmware descriptions`（见 `docs/PLC_HARDWARE.md` 与本人文件的同一提交）

## 验证结果

- 两个独立来源一致：TIA 下载预览“(在线) V4.5” 与 原生 snap7 读数 `4.5.1`；
- 同一读数还确认了订单号 `6ES7 214-1AG40-0XB0`，与现场登记的 MLFB 一致；
- 未使用“按时间取最新”或“取指导书值”这类推断性做法。

## 是否可以写入实验报告的问题分析章节

- [x] 是
- [ ] 否
- 理由：可作为“文档一致性与证据链管理”的真实案例；结论须在证据补齐后重写。
