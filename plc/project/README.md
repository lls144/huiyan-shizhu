# TIA Portal 工程交付说明

当前仓库没有可恢复的 `.ap*` TIA 二进制工程或归档。可审阅源码位于 `../src/`，变量表位于 `../src/PLC_VARIABLES.csv`。

## 恢复步骤（待现场 TIA V20 核验）

1. 在 TIA Portal V20 新建与在线诊断完全一致的普通 S7-1200 CPU 1214C DC/DC/DC 项目（MLFB `6ES7 214-1AG40-0XB0`，不得写成 G2）。
2. 核对 MLFB、固件、设备目录和 Optimized block access 后导入 `../src/*.scl`。
3. 按 `../docs/IO_MAP.md` 的现场核验结果建立符号 I/O；当前所有地址均 TODO。
4. 编译并分别记录 compile、PLCSIM、REAL PLC 结果；不得把源码审阅结果当作下载验收。
5. 关闭 TIA 后再生成归档。归档哈希、TIA Update、CPU MLFB 和生成 commit 写入 `plc/records/`。

禁止提交 VM 镜像、TIA 安装包、License、密码、缓存或正在写入的工程数据库。
