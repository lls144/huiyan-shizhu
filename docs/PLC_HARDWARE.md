# PLC 硬件与环境登记

更新：2026-09-07。本页是 PLC 参数唯一登记入口；本次更新登记现场操作与只读检查已经确认的硬件/网络事实，不等于通信、I/O、PLC 程序或系统联调验收。

## 来源与优先级

任务功能以 `PROJECT_SPEC.md` 和原任务书为准。按负责人要求，硬件资料以 `reference/PLC实验指导书（实验箱版20251015）(1).docx` 为基线；现场确认、只读检查、操作者报告和教学示例分层登记，冲突不静默覆盖。2026-09-07，负责人根据现场设备确认实物为普通 SIMATIC S7-1200 CPU 1214C DC/DC/DC，完整 MLFB 为 `6ES7 214-1AG40-0XB0`；不得将它写成 S7-1200 G2 / 1214C G2。教学截图只证明示例配置，不能覆盖项目实物。

定位采用第二章小节名及 DOCX 内图片名，避免把软件重排页码当固定页码。正文和表格已提取，关键组态与下载截图已人工查看；未声称逐图审核整本指导书。

## 参数表

| 参数 | 指导书 / 资料事实 | 项目采用状态 |
|---|---|---|
| 实验箱 | 封面 HKPLC-1；第二章“一、S7-1200认知实验”设备表 HKPLC-01 | 保留原文名称差异，现场型号待核实 |
| PLC 系列 | S7-1200 | 文档基线 |
| CPU | 创建项目截图 `word/media/image8.jpeg`：CPU 1215C DC/DC/DC | **现场确认：SIMATIC S7-1200 CPU 1214C DC/DC/DC**；不是 G2。1215C 仅为教学示例 |
| 订货号 / MLFB | 同图：6ES7 215-1AG40-0XB0 | **现场确认：`6ES7 214-1AG40-0XB0`**；教学示例订货号不适用于项目实物 |
| 固件 | 同图：V4.1；操作者此前也报 V4.1 | **`V4.5.1`（在线读数）**：TIA 下载预览显示“(在线) V4.5”，隔离环境中原生 `python-snap7 1.3` 独立读到固件 `4.5.1` 与订单号 `6ES7 214-1AG40-0XB0`，两者一致，见 `plc/records/2026-09-10-m8-real-plc-write-verification.md`。指导书截图 V4.1 仅为教学示例。**注意**：该在线读数目前只有文字记录，**TIA Online & diagnostics 截图尚未归档**（ISSUE-002 已据此结案，截图仍列为待补材料）；TIA 离线工程组态固件是否已改为与在线一致，待操作者确认 |
| 板载 I/O | image8 / image9：DI14 × 24VDC、DQ10 × 24VDC、AI2、AQ2；说明含 2 个 PROFINET 端口 | 对应示例 1215C，不可套到实际 1214C；实际模拟量配置和网口数量另核 |
| 编程软件 | 正文“打开Portal V16”，image5 为 TIA V16 | **TIA Portal V20 当前作为实际编程环境使用**；操作者已于 2026-09-11 完成工程修复、编译与下载（`notes/issues/ISSUE-004`）。Update、许可、设备目录兼容性仍待记录 |
| PLC IP / 子网 | 教学下载截图 image14 为 192.0.2.1 | **现场登记：`192.0.2.1` / `255.255.255.0`**；仍须 TIA Accessible devices / Online diagnostics 最终确认该可达地址对应目标 PLC |
| Windows Host PLC 专用网卡 | 指导书未规定本机地址 | **只读检查确认：Realtek PCIe GbE Family Controller（接口“以太网”），`192.0.2.10/24`，无网关、无 DNS，Link Up/Connected，100 Mbps** |
| TIA 虚拟机 | 指导书未规定；此前提供 192.0.2.2 | VMware Tools **观察到** guest IP `192.0.2.2`；VM 网卡模式、桥接目标、PLC-facing 属性和 TIA PG/PC 接口均未验证 |
| 网络 | 指导书列 PROFINET（以太网）线缆 | Host 物理网卡至 `192.0.2.1` 可达已经只读检查；VM 到 PLC、TIA 设备发现、在线诊断和业务通信均未执行 |
| PN 物理接口 | 指导书说明 CPU 底部以太网连接器；同学报 RJ45、10/100Mbps | 接口数量与速率按最终订货号/现场确认 |
| DI / DQ 地址 | 同学报 I0.0–I0.7、I1.0–I1.5；Q0.0–Q0.7、Q1.0–Q1.1 | 候选地址范围，不是项目按键/LED 映射；以实际组态起始地址及接线表为准 |
| 电气参数 | 同学报 24V DC、DI 高 >15V / 低 <5V、DQ 0.5A/通道 | 电压阈值与限流未从指导书关键资料确认，不能用作接线依据；需最终型号数据表及现场确认 |
| RUN/STOP / ERROR / MAINT | 同学给出的 CPU 状态灯说明 | 不分配为业务 LED；物理 RUN/STOP 拨动开关是否存在未确认，不写入操作步骤 |

负责人因其所述 Windows 11 家庭版安装兼容问题安排同学使用虚拟机；这是环境安排，不作为已验证的软件兼容性结论。记录虚拟机产品/版本、来宾 OS/版本、TIA Update、许可与安装结果后，才能写“环境可用”。不得自动升级 PLC 固件以迁就软件或协议。

## 2026-09-07 现场网络只读检查

### 已现场确认 / 已只读验证

- PLC 登记地址：`192.0.2.1`，子网掩码 `255.255.255.0`。
- Windows Host PLC 专用物理网卡：Realtek PCIe GbE Family Controller，接口名“以太网”，IPv4 `192.0.2.10`，PrefixLength `24`，子网掩码 `255.255.255.0`，Gateway none，DNS none，Link `Up / Connected`，协商速度 100 Mbps。
- Host 执行 `ping 192.0.2.1`：sent 4、received 4、lost 0、packet loss 0%；min 2 ms、max 719 ms、avg 181 ms。
- ARP / neighbor 只读结果：`192.0.2.1` 为 `Reachable`，MAC `02:00:00:00:00:02`。

ping 与 ARP 只证明 `192.0.2.1` 在当前 Realtek 物理以太网链路上可达，不单独证明该响应设备就是目标 PLC，也不证明任何 PLC 应用协议、TIA 在线访问或项目通信已经可用。目标 PLC 身份仍须由 TIA Accessible devices / Online diagnostics 最终确认。

### 已观察但尚未验证

- 当前运行的 VM 配置文件：`D:\博途V20\博途V20\博途V20\博途V20.vmx`。
- 只发现 `ethernet0`，adapter type 为 `e1000e`；没有发现 `ethernet1`。
- `.vmx` 中没有明确的 `ethernet0.connectionType`。
- VMware Tools 观察到 guest IP `192.0.2.2`。
- VM adapter mode（Bridged / NAT / Custom）：TODO / pending verification。
- 是否桥接到 Realtek：TODO / pending verification。
- `192.0.2.2` 是否为 PLC-facing adapter：TODO / pending verification。
- TIA PG/PC interface：TODO / pending verification。
- VM → PLC ping、TIA Accessible devices、TIA Online diagnostics：均未执行。

因此不能写“VMware 已桥接 Realtek”“TIA VM 已能访问 PLC”或“192.0.2.2 已验证为 PLC-facing adapter”。

## 通信能力核对

| 项目 | 当前结论 |
|---|---|
| PROFINET IO、S7 通信、TCP/UDP、Modbus TCP | 同学提供的候选能力清单，尚未针对实际 CPU、固件、程序块及权限实测；尚未选定业务通信协议 |
| S7 TCP 102 | 同学提供的候选端口，不等于当前设备已经开放或业务已选 S7 |
| 开放式 TCP/UDP / HTTP | 不沿用“HTTP/TCP/UDP 都是动态端口”的模糊描述；应用监听端口、客户端临时端口和 Web 服务分开登记，最终值 TODO |
| OPC UA Server | 不列为 V4.1 已可用能力。西门子说明 S7-1200 从 V4.4 起提供 OPC UA Server；当前基线不采用，亦不授权升级固件 |

官方核查来源（2026-09-05）：[西门子 S7-1200 OPC UA 概述](https://www.ad.siemens.com.cn/productportal/prods/s7-1200_plc_easy_plus/11-Comm/05-OPC/05-OPC_UA/01-Overview.html)。该资料用于核查能力限制，不替代指导书硬件基线与实际设备信息。

## 现场必须补齐

1. CPU、完整 MLFB 与在线固件（`V4.5.1`）已登记；仍须补**铭牌照片**、**TIA Online & diagnostics 固件截图**（当前只有文字记录）、Accessible devices 结果和设备组态截图，以锁定可下载的具体设备配置与在线身份。
2. Host 物理网卡和 PLC 登记地址已记录；继续确认 VM 网卡模式、桥接目标、PG/PC 接口与 VM → PLC 连通性。ping/ARP 成功不能替代 TIA 在线身份或业务通信验收。
3. 实验箱按键/灯的端子标签、导线接法、DI/DQ 组态地址和按下/释放、亮/灭的实际逻辑值。指导书有两种接线方式，不能假设全部按键都是高电平有效。
4. 项目出队键、复位键、LED1/2/3 的地址、常开/常闭、有效电平、去抖、上电/STOP 行为；见 `../plc/docs/IO_MAP.md`。
5. 用匹配实际型号的 TIA 工程完成编译/下载/在线监视后分别记录结果；PLC 状态灯不能替代任务要求的 1/2/3 盏外部 LED。

上述未完成项继续待测试。指导书其他实验（电梯、流水灯等）的地址表是教学例子，不直接复用为“慧眼识珠”接线表。
