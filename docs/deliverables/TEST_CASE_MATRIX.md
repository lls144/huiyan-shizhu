# 测试用例矩阵（DELIV-005 / TEST-001）

用途：把 `TEST-001` 要求的“正常光照、连续多物体、遮挡干扰”等场景固化成可填写的用例表，并登记每行对应的真实记录。

所有“结果”列在真实执行前保持 `待测试`。**未执行不得填 Pass。**

## 1 视觉与事件场景

| 用例 ID | 场景 | 输入条件 | 步骤要点 | 预期 | 结果 | 证据 |
|---|---|---|---|---|---|---|
| T-SYS-NORMAL-001 | 正常光照单/多目标 | 真实摄像头 + 三类纸板 | 逐个放入 3 个物体 | 三类各自独立识别且标签正确 | 待测试（M2/M3 已覆盖部分，需按 TEST-001 口径重跑） | `evidence/data/m3/live/normal_light/` |
| T-SYS-MULTI-001 | 连续多物体 | 同屏 ≥ 3 个物体 | 连续放入并触发事件 | 多目标独立输出，事件不重复 | 待测试 | `evidence/data/m4/m4-live-lifecycle-*` |
| T-SYS-OCCLUSION-001 | 遮挡干扰 | 部分遮挡三类物体 | 遮挡后观察标签 | 记录实际输出，允许 Fail | 待测试（当前已知输出 `circle + unknown + triangle`） | `evidence/data/m3/live/partial_occlusion/` |
| T-SYS-BRIGHT-001 | 较亮/侧光 | 强光或侧光 | 重复识别 | 与正常光一致或记录退化 | 待测试 | `evidence/data/m3/live/bright_or_side_light/` |
| T-SYS-DARK-001 | 较暗 | 降低照度 | 重复识别 | 与正常光一致或记录退化 | 待测试 | `evidence/data/m3/live/dark_light/` |
| T-SYS-TOUCH-001 | 接触/粘连 | 两物体相邻接触 | 同屏识别 | 记录实际输出（当前为 `unknown + triangle`） | 待测试 | `evidence/data/m3/live/touching_or_merged/` |

## 2 PLC 内部逻辑（参考模型 / Fake PLC）

| 用例 ID | 场景 | 预期 | 结果 | 证据 |
|---|---|---|---|---|
| M8-T01 | 空队列出队 | 不出队，Empty=TRUE | PASS（参考模型，见 `plc/tests/README.md`） | `plc/records/2026-09-08-plc-m8-validation.md` |
| M8-T02 | 1 项入队/出队 | 顺序保持，单次按键只出 1 项 | PASS（参考模型） | 同上 |
| M8-T03 | 三项 FIFO | triangle→rectangle→circle 保序 | PASS（参考模型） | 同上 |
| M8-T04 | 第四项入队 | Full=TRUE，队列不变 | PASS（参考模型） | 同上 |
| M8-T05 | 持续按键 | 去抖后仅 1 个 Pulse | PASS（参考模型） | 同上 |
| M8-T06 | 多次独立按键 | 每次 1 个 Pulse，严格按序 | PASS（参考模型） | 同上 |
| M8-T07 | Reset | 清空数组/索引/计数 | PASS（参考模型） | 同上 |
| M8-T08 | LED 映射 | 1/2/3 灯锁存；入队不点灯 | PASS（参考模型） | 同上 |
| M8-T09 | FIFO 满 | QueueFull=TRUE，业务灯保持 | PASS（参考模型） | 同上 |
| M8-T10 | unknown / 空队列按键 | unknown 不变灯，空队列不动作 | PASS（参考模型） | 同上 |
| M8-T11 | Reset | 三灯熄灭，Full 清零 | PASS（参考模型） | 同上 |
| M8-T12 | 上电初始化 | Empty、灯全灭 | PENDING（需真实断电重启） | `plc/tools/m8_real_plc_acceptance.py --verify-power-on` |
| M8-T13 | PC 失联 > 2 s | 三灯闪烁 | DEFERRED（属 M9） | — |
| M8-T14 | 重复包/ACK 丢失 | 不重复入队/点灯 | DEFERRED（属 M7/M9） | — |
| M8-T15 | `CommandValid` 持续 TRUE | 只入队一次 | PASS（参考模型） | `plc/records/2026-09-09-plc-m8-commandvalid-repeat.md` |

“参考模型 PASS”只证明内部语义，**不能**替代 TIA 编译或真实 PLC。

## 3 PC→PLC 命令桥（离线，非真实硬件）

| 用例 ID | 场景 | 预期 | 结果 | 证据 |
|---|---|---|---|---|
| M8-BRIDGE-01 | 单形状 1/2/3 灯映射 | triangle/rectangle/circle → 1/2/3 | 离线 PASS | `notes/tests/TEST-008-PC-PLC通信桥离线验收.md` |
| M8-BRIDGE-02 | 三项 FIFO 顺序 | 依次出队 1→2→3 | 离线 PASS | 同上 |
| M8-BRIDGE-03 | `CommandValid` 持续 TRUE | 不重复入队 | 离线 PASS | 同上 |
| M8-BRIDGE-04 | unknown 事件 | 不发送、不改队列 | 离线 PASS | 同上 |
| M8-BRIDGE-05 | Reset | 清空队列与灯 | 离线 PASS | 同上 |

Fake PLC 输出位于被忽略的 `output/m8-bridge/`，可用 CLI 重放，不作为真实 PLC 证据。

## 4 真实 PLC 验收（M10，未执行）

| 用例 ID | 场景 | 预期 | 结果 | 证据 |
|---|---|---|---|---|
| T-HW-PLC-001 | 设备铭牌与在线身份 | 型号/MLFB/固件一致 | PENDING | `docs/PLC_FIELD_CHECKLIST.md` A 组 |
| T-HW-LINK-001 | 网络与 PG/PC 接口 | TIA 可达 | PENDING | 同上 B 组 |
| T-PLC-FIFO-001 | 真实 FIFO 顺序 | 1→2→3 保序 | PENDING | `plc/tools/m8_real_plc_acceptance.py --all` |
| T-PLC-LED-001 | 实体 1/2/3 灯 | 实际亮灭与映射一致 | PENDING | 同上 + 照片/视频 |
| T-PLC-STATE-001 | 空/满/长度/复位 | 状态正确 | PENDING | 同上 |
| T-COMM-FRAME-001 | 真实协议帧解析 | 三类指令正确解析 | PENDING（协议未冻结） | `docs/PLC_INTERFACE.md` |
| T-COMM-HEARTBEAT-001 | 1 s 心跳 / 2 s 全闪 | 阈值处触发报警 | PENDING（M9） | — |
| T-COMM-RETRY-001 | 超时重发 | 不重复入队 | PENDING（M9） | — |
| T-COMM-FULL-001 | 队列满通知 | PC 收到通知并退避 | PENDING（M9） | — |
| T-SYS-E2E-001 | 三类物体端到端闭环 | 识别→入队→出队→灯 | PENDING | M10 录像 |

## 5 每个用例的记录要求

按 `notes/templates/Test测试记录模板.md`：Test ID、Requirement ID、日期、Git commit、环境、输入条件、步骤、预期、实际、原始数据位置、截图位置、Pass/Fail、备注。
