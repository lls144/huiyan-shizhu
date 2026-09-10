# M8 真机 PUT/GET 写入丢包核实与"写入确认"修复记录

日期：2026-09-10
分支：`codex/plc-m8-fifo-led`
设备：SIMATIC S7-1200 CPU 1214C DC/DC/DC，MLFB `6ES7 214-1AG40-0XB0`，在线固件 **4.5.1**，`192.0.2.1/24`
目标块：`DB_M8_Acceptance` = **DB3**（非优化访问，24 字节）
证据位置：`evidence/data/m8-real/`（`m8-real-acceptance.json` / `.csv` / `m8-real-summary.md`）

## 背景

M8 真机自动验收此前随机失败，失败点每次不同（有时第一次入队就超时，有时第三次入队，有时出队）。
同一套测试在内存 `FakeAcceptancePlc` 上一直全过。需要区分"PLC 程序语义错"和"PC↔PLC 写入不可靠"。

## 实测结果（均为 PC 侧只读/写入观测）

| 实验 | 结果 |
|---|---|
| 同一客户端写 **M 区**（程序不访问 M）10 次并读回 | **10/10 生效** |
| 同一客户端写 **DB3.DBB0** 10 次并读回 | 5/10 生效 |
| 单次写 DB3 控制字 ×20 | 14/20 生效 |
| 背靠背写两次同一值 ×20 | 16/20 生效 |
| **写 + 读回校验 + 重发** ×20 | **20/20 生效**（多数 1 次，个别 2–4 次） |
| 工具加校验重发后跑 `--all` | **12/12 AUTO PASS**；193 次确认写中 88 次需重发，最多 9 次，允许 12 次 |

丢包特征：

- **没有任何协议错误**：`db_write` 正常返回，CPU 也不报错。
- **不是读缓存**：用第二条独立连接读、以及换成原生 `python-snap7 1.3`（ctypes 封装官方 C 库）读，同样看不到被丢的那次写。
- **不是被程序改回去**：写入后 0.4 s 内以 ~90 Hz 采样 36 次，值要么全程是新值、要么全程是旧值，没有闪烁或中间态。
- **与本机数字输入无关**：整轮采集 `%I0.0`/`%I0.1` 恒为 0。

结论：该 CPU 对**程序每扫描都在访问的** `DB_M8_Acceptance` 的 PUT/GET 写会**静默丢弃约一半**；同一客户端写 M 区一条不丢，说明链路、IP、防护设置和客户端本身都是好的。

## 顺带纠正的两条旧结论

1. `plc/tools/requirements.txt` 锁定的 `python-snap7 3.1.2` 是**纯 Python 重实现**，其 `get_cpu_state()` 是占位实现（发送残缺帧、返回硬编码 `S7CpuStatusRun`）。此前"CPU 拒绝一切远程访问"的判断是被它误导的，该探针已从 `--diagnose` 中移除，换成 SZL 订单号读取。
2. 用原生 `python-snap7 1.3` 在隔离临时环境读到在线订单号 `6ES7 214-1AG40-0XB0`、固件 **4.5.1**，与 TIA 下载预览的"(在线) V4.5"一致。可据此更新 `docs/PLC_HARDWARE.md` 与 ISSUE-002（本次未改根文档）。

## 修复

- `plc/tools/m8_real_plc_acceptance.py`：`S7AcceptanceClient.write_controls()` 改为**写→读回→不一致则重发**，默认 12 次、间隔 20 ms（`--write-attempts` / `--write-interval` 可调）；无法确认时抛 `AcceptanceError`，不再假装成功。重发统计写入证据（`control_writes`）。
- `pc/communication/sink.py`：`S7PlcCommandSink._write()` 同样加确认重发，重发次数进入 `PlcCommandResult.detail` 与 `write_retry_count`。
- `pc/communication/config.py` / `pc/config/plc.json`：新增 `write_confirm_attempts`、`write_confirm_interval_seconds`。
- `pc/communication/fake_plc.py`：补上控制区读回；新增 `drop_control_writes` 以便离线复现真机丢写。

## 对 M7 的影响

任务书要求的"超时重发 / 队列满通知"不再是纸面要求：**PC→PLC 单向"写一次就算送达"不可行**。M7 协议必须包含写入确认或显式 ACK。

## 未确认 / 待办

- 丢包**机制**仍是推测（与程序每扫描访问该 DB 有关），未做 CPU STOP / 程序不访问该 DB 的对照实验。
- `drop_control_writes` 的统计只反映"第一次未确认"，未区分"真丢"与"读回本身偶发失败"。
- 实体 LED 亮灭、物理按键出队、断电重启（M8-T12）仍是**人工证据**，AUTO 结果不能替代。
- 已提交的 `evidence/data/m8-real/` 由当前分支代码产生；正式归档前请确认与提交的 commit 对应。
