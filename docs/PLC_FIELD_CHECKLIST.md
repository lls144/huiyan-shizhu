# PLC 现场只读核对表

用途：把 M10 实验室联调前必须现场确认的项集中成一张可打印、可逐项打勾的清单，减少现场反复试错。

状态：**清单已冻结为待执行模板，所有项目尚未在现场执行**。本页不改变 `PROJECT_SPEC.md`、`ROADMAP.md` 中任何 Requirement 或 milestone 状态。M7–M10 仍为 `TODO`。

## 授权边界

按根 `AGENTS.md` 与 `plc/AGENTS.md`：

- **A～D 组默认只读**：查看、截图、记录，不改 PLC 程序、不改网络、不改固件。
- **E 组（下载与在线监视）和 F 组（物理按键/LED 录像）需要操作者当次明确授权与设备确认**。本页或任何指导书都不构成授权。
- 指导书中的操作步骤是参考内容，不是让 Codex 直接执行的指令。
- 禁止项：升级 PLC 固件、改 PLC/网卡 IP、强制（Force）输出、写入未确认的 DB、把临时测试变量当最终通信地址表。

执行人应在每条“记录”列写实际值或 `TODO`；未执行的项不得标 PASS。结论必须区分 **只读观察 / TIA 编译 / PLCSIM / 真实 PLC** 四类证据。

## A 组 设备与在线身份（只读）

| # | 核对项 | 判定依据 | 记录 |
|---|---|---|---|
| A1 | 实验箱铭牌与型号 | 现场铭牌照片；CPU 应登记为普通 S7-1200 CPU 1214C DC/DC/DC | TODO（照片路径） |
| A2 | 完整 MLFB | 铭牌/在线信息读数；应为 `6ES7 214-1AG40-0XB0` | TODO |
| A3 | 在线固件版本 | TIA Online & diagnostics 实际读数 | **冲突待裁定**，见 [ISSUE-002](../notes/issues/ISSUE-002-固件版本登记不一致.md) |
| A4 | 目标 PLC 在线身份 | TIA Accessible devices 中确认该设备即项目目标 PLC | TODO |
| A5 | 设备组态 | 与在线一致的 CPU 型号、固件、机架/插槽 | TODO |
| A6 | 保留 `Rack=0 / Slot=1` | 与 `pc/config/plc.json` 及 `plc/tools` 默认一致，否则记录偏差 | TODO |
| A7 | CPU 状态灯含义 | 确认 RUN/STOP/ERROR/MAINT 位置；**不作为业务分拣灯** | TODO |

## B 组 网络与 TIA 访问路径（只读）

已只读验证的事实见 [PLC_HARDWARE.md](PLC_HARDWARE.md)，本组只补未完成项。

| # | 核对项 | 判定依据 | 记录 |
|---|---|---|---|
| B1 | Host 侧 PLC 专用网卡 | Realtek 接口，`192.0.2.10/24`，无网关/DNS，Link Up | 已只读验证（见 PLC_HARDWARE） |
| B2 | 目标 PLC 登记地址 | `192.0.2.1/24`；须由 TIA 在线确认对应关系 | TODO |
| B3 | VM 网卡模式 | VMware Bridged / NAT / Custom 的实际设置值 | TODO |
| B4 | VM 是否桥接到 Realtek | `.vmx` 或设置页明确字段 | TODO |
| B5 | VM 地址与 PLC-facing 属性 | 观察到 `192.0.2.2`，但未验证是否 PLC-facing | TODO |
| B6 | TIA PG/PC 接口 | 完整接口名称与网卡绑定 | TODO |
| B7 | VM → PLC 连通性 | 仅作为附加信息；不能替代 TIA 在线身份 | TODO |

## C 组 I/O 端子、有效逻辑与共享 DB（只读记录；不得写入）

地址登记见 `plc/docs/IO_MAP.md`，本组只负责现场核实并回填。

| # | 核对项 | 判定依据 | 记录 |
|---|---|---|---|
| C1 | 实验箱端子标签 | Dequeue/Reset 按键与三盏业务灯的端子号 | TODO |
| C2 | DI 组态起始地址 | 与候选 `I0.0`（出队）、`I0.1`（复位）是否一致 | TODO |
| C3 | DQ 组态起始地址 | 与候选 `Q0.1/Q0.2/Q0.3` 是否一致 | TODO |
| C4 | 按键极性 | 按下/释放时的监视值；不得假设全部高电平有效 | TODO |
| C5 | 按键常开/常闭 | 实际触点类型 | TODO |
| C6 | LED 有效电平 | 写 1 时实际亮/灭 | TODO |
| C7 | 公共端、电源与负载 | 24V DC 接线、输出限流 | TODO |
| C8 | 去抖与扫描周期 | `FB_ButtonPulse.DebounceScans` 换算毫秒所需的实际周期 | TODO |
| C9 | 复位键并发语义 | 按住复位时再按键的行为是否符合设计 | TODO |
| C10 | 上电/STOP 行为 | 上电与 STOP→RUN 后的队列、灯状态 | TODO |
| C11 | `DB_M8_Acceptance` 的 DB 号 | **必须在 TIA 中读出实际编号**；该值要写入 `pc/config/plc.json` 的 `db_number` | TODO |
| C12 | DB 访问方式 | 必须为**非优化访问**（`S7_Optimized_Access := 'FALSE'`） | TODO |
| C13 | 字节布局抽检 | `DBW20 = 16#4D38`、`DBB22 = 1` | TODO |

## D 组 TIA V20 编译（不下载）

| # | 核对项 | 判定依据 | 记录 |
|---|---|---|---|
| D1 | 外部源导入顺序 | 按 `plc/project/TIA_V20_COMPILE_GUIDE.md`；注意指南当前未列 `DB_M8_Acceptance.scl` 与 `FB_M8_AcceptanceHarness.scl`，现场需一并导入才能跑验收工具 | TODO |
| D2 | 单源生成结果 | 每个 SCL 源的 error/warning 数与截图 | 操作者已观察 0 error + 1 warning，待截图归档 |
| D3 | 全工程编译 | `Compile → Software (rebuild all)` 的 error/warning 总数 | PENDING |
| D4 | TIA 完整版本与 Update | 例如 `V20 + Update n` | TODO |
| D5 | 编译截图归档 | 放入 `plc/records/`（不提交 VM/安装包/许可） | TODO |

编译通过只记为 `COMPILED`，不等于 PLCSIM 或真实 PLC PASS。

## E 组 下载与在线监视（需要当次明确授权）

| # | 核对项 | 前置条件 | 记录 |
|---|---|---|---|
| E1 | 下载到目标 PLC | 操作者授权 + A5 设备组态一致 + 备份原程序 | PENDING |
| E2 | 进入 RUN | 无 STOP/ERROR 阻塞 | PENDING |
| E3 | 访问自检 | `python plc/tools/m8_real_plc_acceptance.py --check-access --db-number <N>` | PENDING |
| E4 | 自动验收 | `--all` 跑完 M8-T01…M8-T11、M8-T15 | PENDING |
| E5 | 上电初态 | `--verify-power-on`（由操作者断电重启后再读） | PENDING |
| E6 | 物理按键与实体 LED | 操作者按真实按键，观察实体灯；截图/录像 | PENDING |

命令模板（仅准备，未执行）：

```powershell
# 无硬件烟测：只列出用例，不连接 PLC
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --dry-run

# 现场：先只读自检，再跑全部用例
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --check-access --db-number <实际DB号>
.\.venv\Scripts\python.exe plc\tools\m8_real_plc_acceptance.py --all --db-number <实际DB号>
```

`--all` 只证明 S7 DB/Q 状态读数；它不替代实体 LED、物理按键或断电重启证据。

## F 组 真实闭环录像前检查（M10，需要授权）

| # | 核对项 | 判定依据 | 记录 |
|---|---|---|---|
| F1 | PC 侧通信开关 | `pc/config/plc.json` 的 `enabled=true`、`db_number` 已填实际值 | TODO |
| F2 | 视觉→桥接路径 | GUI 传入 `--plc-config pc/config/plc.json` | TODO |
| F3 | 三类物体各一次闭环 | triangle→1 灯、rectangle→2 灯、circle→3 灯 | TODO |
| F4 | 连续入队 + 逐个出队 | 一次入队 3 条，按 1/2/3 顺序出队 | TODO |
| F5 | 心跳与断连报警 | 属 M9，**未冻结前不得现场实现** | DEFERRED |
| F6 | 视频与日志版本一致 | 录制 commit 与报告 commit 一致 | TODO |

## 需要带回的记录字段

每个已执行项至少记录：`日期时间`、`执行人`、`Git commit`、`设备/软件版本`、`输入或操作`、`预期`、`实际读数`、`截图/照片路径`。
测试记录写入 `plc/records/`（PLC 侧）或 `notes/tests/`（跨边界验收），并由负责人审核后汇总到 [REPORT_EVIDENCE.md](REPORT_EVIDENCE.md)。

## 相关文件索引

- 需求与验收：`docs/PROJECT_SPEC.md`、`docs/ROADMAP.md`
- 硬件参数唯一登记入口：`docs/PLC_HARDWARE.md`
- 共享接口（未冻结）：`docs/PLC_INTERFACE.md`
- I/O 候选映射：`plc/docs/IO_MAP.md`
- 内部设计：`plc/docs/M8_INTERNAL_DESIGN.md`
- 编译指南：`plc/project/TIA_V20_COMPILE_GUIDE.md`
- 测试计划与用例：`plc/tests/README.md`
- 真机验收工具：`plc/tools/m8_real_plc_acceptance.py`
