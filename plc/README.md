# PLC 工程入口

[返回项目](../README.md)

`src/` 保留可读的 SCL 导出：FIFO、按钮沿检测、LED 显示、应用 FB 与独立的 M8 验收 Harness。PLC 部分由团队协作完成，PC 通信、集成与现场验证在上层项目中记录。

- [构建与导入顺序](project/TIA_V20_COMPILE_GUIDE.md)
- [I/O 映射](docs/IO_MAP.md) · [内部设计](docs/M8_INTERNAL_DESIGN.md) · [SCL 静态审查](docs/SCL_STATIC_AUDIT.md)
- [真机条件与检查](docs/PLC_HARDWARE_VERIFICATION.md)
- [纯软件参考测试](tests/README.md)
- [真机验收工具](tools/m8_real_plc_acceptance.py) · [看门狗检查](tools/m8_comm002_real_check.py)

`FB_M8_AcceptanceHarness.scl` 与 `DB_M8_Acceptance.scl` 服务于测试链路。导入前按现场 CPU 和 I/O 重新核对，不把 Harness 的 DB 地址混用为其他应用的通信协议。
